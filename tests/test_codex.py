"""Codex CLI against a fake executable.

Checks command building and parsing of the documented JSONL events; the
failure case uses event lines captured from a real (unauthenticated) run.
"""

import asyncio
import json
import sys

import pytest

from cli_to_api.clis import CLIError, CodexCLI
from cli_to_api.clis.codex import DISABLED_FEATURES

FAKE_CODEX = f"""#!{sys.executable}
import json, os, sys

with open(os.environ["FAKE_RECORD"], "w") as f:
    json.dump({{
        "argv": sys.argv[1:],
        "stdin": sys.stdin.read(),
        "codex_api_key": os.environ.get("CODEX_API_KEY"),
        "openai_api_key": os.environ.get("OPENAI_API_KEY"),
    }}, f)
sys.stdout.write(os.environ.get("FAKE_STDOUT", ""))
sys.stderr.write(os.environ.get("FAKE_STDERR", ""))
sys.exit(int(os.environ.get("FAKE_EXIT", "0")))
"""


def jsonl(*events: dict) -> str:
    return "".join(json.dumps(event) + "\n" for event in events)


SUCCESS = jsonl(
    {"type": "thread.started", "thread_id": "t1"},
    {"type": "turn.started"},
    {"type": "item.completed", "item": {"id": "i0", "type": "reasoning", "text": "thinking"}},
    {"type": "item.completed", "item": {"id": "i1", "type": "agent_message", "text": "draft"}},
    {"type": "item.completed", "item": {"id": "i2", "type": "agent_message", "text": "4"}},
    {"type": "turn.completed", "usage": {"input_tokens": 10, "output_tokens": 1}},
)

# Captured from `codex exec --json` 0.160.0 with no credentials.
UNAUTHORIZED = (
    '{"type":"error","message":"Reconnecting... 5/5 (unexpected status 401 Unauthorized)"}\n'
    '{"type":"error","message":"unexpected status 401 Unauthorized: Missing bearer or basic '
    'authentication in header"}\n'
    '{"type":"turn.failed","error":{"message":"unexpected status 401 Unauthorized: Missing '
    'bearer or basic authentication in header"}}\n'
)


@pytest.fixture
def fake_codex(tmp_path, monkeypatch):
    executable = tmp_path / "codex"
    executable.write_text(FAKE_CODEX)
    executable.chmod(0o755)
    record = tmp_path / "record.json"
    monkeypatch.setenv("FAKE_RECORD", str(record))

    def run(*, stdout="", stderr="", exit_code=0, api_key=None) -> str:
        monkeypatch.setenv("FAKE_STDOUT", stdout)
        monkeypatch.setenv("FAKE_STDERR", stderr)
        monkeypatch.setenv("FAKE_EXIT", str(exit_code))
        cli = CodexCLI(["gpt-a"], executable=str(executable), api_key=api_key)
        return asyncio.run(cli.query("-what is 2+2?", "gpt-a"))

    run.recorded = lambda: json.loads(record.read_text())
    return run


def test_returns_last_agent_message(fake_codex):
    assert fake_codex(stdout=SUCCESS) == "4"


def test_invocation(fake_codex):
    fake_codex(stdout=SUCCESS)
    seen = fake_codex.recorded()
    argv = seen["argv"]

    assert argv[0] == "exec"
    assert argv[-1] == "-"
    assert seen["stdin"] == "-what is 2+2?"
    assert argv[argv.index("--model") + 1] == "gpt-a"
    assert argv[argv.index("--sandbox") + 1] == "read-only"
    for flag in ["--json", "--skip-git-repo-check", "--ephemeral", "--ignore-user-config"]:
        assert flag in argv
    disabled = {argv[i + 1] for i, arg in enumerate(argv) if arg == "--disable"}
    assert disabled == set(DISABLED_FEATURES)
    assert not any(arg.startswith("--dangerously") for arg in argv)


def test_api_key_mode(fake_codex, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "inherited-openai")

    fake_codex(stdout=SUCCESS, api_key="codex-key")
    seen = fake_codex.recorded()

    assert seen["codex_api_key"] == "codex-key"
    assert seen["openai_api_key"] is None
    assert "codex-key" not in seen["argv"]


def test_login_mode_drops_inherited_keys(fake_codex, monkeypatch):
    monkeypatch.setenv("CODEX_API_KEY", "inherited-codex")
    monkeypatch.setenv("OPENAI_API_KEY", "inherited-openai")

    fake_codex(stdout=SUCCESS)
    seen = fake_codex.recorded()

    assert seen["codex_api_key"] is None
    assert seen["openai_api_key"] is None


@pytest.mark.parametrize(
    ("stdout", "exit_code", "message"),
    [
        (
            UNAUTHORIZED,
            1,
            "unexpected status 401 Unauthorized: Missing bearer or basic authentication in header",
        ),
        (jsonl({"type": "error", "message": "stream disconnected"}), 1, "stream disconnected"),
        ("", 2, "codex exited with status 2: Error: Unknown feature flag: x"),
        (jsonl({"type": "turn.completed", "usage": {}}), 0, "Unexpected output from codex."),
    ],
    ids=["turn-failed", "error-event", "no-output", "no-agent-message"],
)
def test_failures(fake_codex, stdout, exit_code, message):
    with pytest.raises(CLIError) as excinfo:
        fake_codex(stdout=stdout, stderr="Error: Unknown feature flag: x", exit_code=exit_code)
    assert str(excinfo.value) == message

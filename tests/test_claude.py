import asyncio
import json
import os
import sys
from pathlib import Path

import pytest

from cli_to_api.clis import ClaudeCLI, CLIError

API_KEY = "sk-ant-test-key"

# Stands in for `claude`. FAKE_MODE picks the behaviour; everything the
# process saw is recorded as JSON in FAKE_RECORD.
FAKE_CLAUDE = f"""#!{sys.executable}
import json, os, sys, time

record = {{
    "argv": sys.argv[1:],
    "stdin": sys.stdin.read(),
    "cwd": os.getcwd(),
    "pid": os.getpid(),
    "api_key": os.environ.get("ANTHROPIC_API_KEY"),
}}
with open(os.environ["FAKE_RECORD"], "w") as f:
    json.dump(record, f)

mode = os.environ["FAKE_MODE"]
if mode == "success":
    print(json.dumps({{"type": "result", "is_error": False, "result": "Paris."}}))
elif mode == "is_error":
    print(json.dumps({{"type": "result", "is_error": True, "result": "Model overloaded."}}))
elif mode == "exit_json":
    print(json.dumps({{"type": "result", "is_error": True, "result": "Invalid model."}}))
    sys.exit(1)
elif mode == "exit_no_json":
    print("Error: not logged in", file=sys.stderr)
    sys.exit(2)
elif mode == "garbage":
    print("this is not json")
elif mode == "sleep":
    time.sleep(30)
"""


@pytest.fixture
def fake_claude(tmp_path, monkeypatch):
    executable = tmp_path / "claude"
    executable.write_text(FAKE_CLAUDE)
    executable.chmod(0o755)
    record = tmp_path / "record.json"
    monkeypatch.setenv("FAKE_RECORD", str(record))

    def run(mode: str, *, api_key: str | None = None, timeout: float = 10) -> str:
        monkeypatch.setenv("FAKE_MODE", mode)
        cli = ClaudeCLI(["claude-a"], executable=str(executable), api_key=api_key)
        return asyncio.run(asyncio.wait_for(cli.query("Capital of France?", "claude-a"), timeout))

    run.recorded = lambda: json.loads(record.read_text())
    return run


def test_returns_result(fake_claude):
    assert fake_claude("success") == "Paris."


def test_invocation(fake_claude):
    fake_claude("success")
    seen = fake_claude.recorded()

    argv = seen["argv"]
    assert argv[0] == "-p"
    assert argv[argv.index("--output-format") + 1] == "json"
    assert argv[argv.index("--model") + 1] == "claude-a"
    assert argv[argv.index("--tools") + 1] == ""
    assert seen["stdin"] == "Capital of France?"
    assert "Capital of France?" not in argv
    assert Path(seen["cwd"]).resolve() != Path.cwd().resolve()
    assert not Path(seen["cwd"]).exists()


def test_api_key_mode(fake_claude):
    fake_claude("success", api_key=API_KEY)
    seen = fake_claude.recorded()

    assert "--bare" in seen["argv"]
    assert seen["api_key"] == API_KEY
    assert API_KEY not in seen["argv"]


def test_subscription_mode_drops_inherited_key(fake_claude, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-inherited")

    fake_claude("success")
    seen = fake_claude.recorded()

    assert "--bare" not in seen["argv"]
    assert seen["api_key"] is None


@pytest.mark.parametrize(
    ("mode", "message"),
    [
        ("is_error", "Model overloaded."),
        ("exit_json", "Invalid model."),
        ("exit_no_json", "claude exited with status 2: Error: not logged in"),
        ("garbage", "Unexpected output from claude."),
    ],
)
def test_failures_raise_cli_error(fake_claude, mode, message):
    with pytest.raises(CLIError) as excinfo:
        fake_claude(mode, api_key=API_KEY)

    assert str(excinfo.value) == message
    assert API_KEY not in str(excinfo.value)


def test_missing_executable(tmp_path):
    cli = ClaudeCLI(["claude-a"], executable=str(tmp_path / "missing"))

    with pytest.raises(CLIError, match="Could not run claude executable"):
        asyncio.run(cli.query("hi", "claude-a"))


def test_cancellation_kills_process(fake_claude):
    with pytest.raises(TimeoutError):
        fake_claude("sleep", timeout=1)

    with pytest.raises(ProcessLookupError):
        os.kill(fake_claude.recorded()["pid"], 0)


def test_supports_follows_model_list():
    cli = ClaudeCLI(["claude-a"])

    assert cli.supported_models() == ["claude-a"]
    assert cli.supports("claude-a")
    assert not cli.supports("claude-b")

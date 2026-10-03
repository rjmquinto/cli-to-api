"""Gemini and Antigravity CLIs against a fake executable.

These check command building and parsing of the documented output shapes;
neither CLI has been run for real.
"""

import asyncio
import json
import sys

import pytest

from cli_to_api.clis import AntigravityCLI, CLIError, GeminiCLI

# Prints FAKE_STDOUT / FAKE_STDERR, exits with FAKE_EXIT, and records what it saw.
FAKE_CLI = f"""#!{sys.executable}
import json, os, sys

with open(os.environ["FAKE_RECORD"], "w") as f:
    json.dump({{
        "argv": sys.argv[1:],
        "stdin": sys.stdin.read(),
        "gemini_api_key": os.environ.get("GEMINI_API_KEY"),
    }}, f)
sys.stdout.write(os.environ.get("FAKE_STDOUT", ""))
sys.stderr.write(os.environ.get("FAKE_STDERR", ""))
sys.exit(int(os.environ.get("FAKE_EXIT", "0")))
"""


@pytest.fixture
def fake(tmp_path, monkeypatch):
    executable = tmp_path / "fake-cli"
    executable.write_text(FAKE_CLI)
    executable.chmod(0o755)
    record = tmp_path / "record.json"
    monkeypatch.setenv("FAKE_RECORD", str(record))

    def run(cli_class, *, stdout="", stderr="", exit_code=0, **kwargs) -> str:
        monkeypatch.setenv("FAKE_STDOUT", stdout if isinstance(stdout, str) else json.dumps(stdout))
        monkeypatch.setenv("FAKE_STDERR", stderr)
        monkeypatch.setenv("FAKE_EXIT", str(exit_code))
        cli = cli_class(["model-a"], executable=str(executable), **kwargs)
        return asyncio.run(cli.query("-what is 2+2?", "model-a"))

    run.recorded = lambda: json.loads(record.read_text())
    return run


# Gemini


def test_gemini_success(fake):
    answer = fake(GeminiCLI, stdout={"response": "4", "stats": {}})
    seen = fake.recorded()

    assert answer == "4"
    assert seen["stdin"] == "-what is 2+2?"
    assert seen["argv"] == [
        "--output-format", "json", "--model", "model-a", "--approval-mode", "default",
    ]


def test_gemini_api_key(fake, monkeypatch):
    fake(GeminiCLI, stdout={"response": "4"}, api_key="gemini-key")
    assert fake.recorded()["gemini_api_key"] == "gemini-key"

    monkeypatch.setenv("GEMINI_API_KEY", "inherited")
    fake(GeminiCLI, stdout={"response": "4"})
    assert fake.recorded()["gemini_api_key"] is None


@pytest.mark.parametrize(
    ("stdout", "exit_code", "message"),
    [
        ({"error": {"type": "ApiError", "message": "Quota exceeded", "code": 429}}, 1, "Quota exceeded"),
        ({"response": "", "error": "Turn limit exceeded"}, 53, "Turn limit exceeded"),
        ("", 42, "gemini exited with status 42: bad args"),
        ("not json", 0, "Unexpected output from gemini."),
    ],
)
def test_gemini_failures(fake, stdout, exit_code, message):
    with pytest.raises(CLIError) as excinfo:
        fake(GeminiCLI, stdout=stdout, stderr="bad args", exit_code=exit_code)
    assert str(excinfo.value) == message


# Antigravity


def test_antigravity_success(fake):
    answer = fake(AntigravityCLI, stdout={"status": "SUCCESS", "response": "4", "num_turns": 1})
    seen = fake.recorded()

    assert answer == "4"
    assert seen["argv"] == [
        "--prompt=-what is 2+2?", "--output-format", "json", "--model", "model-a",
    ]
    assert "--dangerously-skip-permissions" not in seen["argv"]


@pytest.mark.parametrize(
    ("stdout", "exit_code", "message"),
    [
        ({"status": "ERROR", "error": "invalid model"}, 1, "invalid model"),
        ({"status": "CANCELED", "response": ""}, 0, "antigravity run ended with status CANCELED."),
        ("", 1, "antigravity exited with status 1: bad args"),
        ("not json", 0, "Unexpected output from antigravity."),
    ],
)
def test_antigravity_failures(fake, stdout, exit_code, message):
    with pytest.raises(CLIError) as excinfo:
        fake(AntigravityCLI, stdout=stdout, stderr="bad args", exit_code=exit_code)
    assert str(excinfo.value) == message

import asyncio
import os

import pytest

from cli_to_api.clis import ClaudeCLI

pytestmark = pytest.mark.skipif(
    os.environ.get("CLAUDE_INTEGRATION") != "1",
    reason="Set CLAUDE_INTEGRATION=1 to run against the real claude CLI.",
)


def test_real_query():
    cli = ClaudeCLI(
        ["claude-haiku-4-5"],
        executable=os.environ.get("CLAUDE_CLI", "claude"),
        api_key=os.environ.get("ANTHROPIC_API_KEY") or None,
    )

    answer = asyncio.run(
        cli.query("What is the capital of France? Reply with one word.", "claude-haiku-4-5")
    )

    assert "paris" in answer.lower()

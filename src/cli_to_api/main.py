import os

from cli_to_api.app import create_app
from cli_to_api.clis import ClaudeCLI, MockCLI
from cli_to_api.registry import CLIRegistry

registry = CLIRegistry(
    [
        ClaudeCLI(
            ["claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-4-5"],
            executable=os.environ.get("CLAUDE_CLI", "claude"),
            api_key=os.environ.get("ANTHROPIC_API_KEY") or None,
        ),
        MockCLI("gemini", ["gemini-2.5-pro", "gemini-2.5-flash"]),
    ]
)

app = create_app(registry)

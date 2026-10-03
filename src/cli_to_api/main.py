from cli_to_api.app import create_app
from cli_to_api.clis import MockCLI
from cli_to_api.registry import CLIRegistry

registry = CLIRegistry(
    [
        MockCLI("claude", ["claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-4-5"]),
        MockCLI("gemini", ["gemini-2.5-pro", "gemini-2.5-flash"]),
    ]
)

app = create_app(registry)

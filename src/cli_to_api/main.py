import os

from cli_to_api.app import create_app
from cli_to_api.clis import AntigravityCLI, ClaudeCLI, CodexCLI, GeminiCLI
from cli_to_api.config import apply_rate_limits
from cli_to_api.registry import CLIRegistry

registry = CLIRegistry(
    apply_rate_limits(
        [
            ClaudeCLI(
                ["claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-4-5"],
                executable=os.environ.get("CLAUDE_CLI", "claude"),
                api_key=os.environ.get("ANTHROPIC_API_KEY") or None,
            ),
            GeminiCLI(
                ["gemini-3.1-pro-preview", "gemini-3.5-flash", "gemini-3.5-flash-lite"],
                executable=os.environ.get("GEMINI_CLI", "gemini"),
                api_key=os.environ.get("GEMINI_API_KEY") or None,
            ),
            CodexCLI(
                ["gpt-6.1-sol", "gpt-6-astra", "gpt-6-luna"],
                executable=os.environ.get("CODEX_CLI", "codex"),
                api_key=os.environ.get("CODEX_API_KEY") or None,
            ),
            AntigravityCLI(
                ["gemini-3.1-pro-high", "gemini-3.8-flash-high", "gemini-3.8-flash-medium"],
                executable=os.environ.get("ANTIGRAVITY_CLI", "agy"),
            ),
        ]
    )
)

app = create_app(registry)

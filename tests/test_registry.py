import pytest

from cli_to_api.clis import MockCLI
from cli_to_api.registry import CLIRegistry, UnknownModelError


def test_resolves_to_cli_listing_the_model():
    claude = MockCLI("claude", ["claude-a"])
    gemini = MockCLI("gemini", ["gemini-a", "gemini-b"])
    registry = CLIRegistry([claude, gemini])

    assert registry.resolve("claude-a") is claude
    assert registry.resolve("gemini-b") is gemini


def test_unknown_model_raises():
    registry = CLIRegistry([MockCLI("claude", ["claude-a"])])

    with pytest.raises(UnknownModelError):
        registry.resolve("gpt-9")


def test_duplicate_model_across_clis_is_rejected():
    with pytest.raises(ValueError, match="claude-a"):
        CLIRegistry([MockCLI("one", ["claude-a"]), MockCLI("two", ["claude-a"])])


def test_models_lists_each_clis_models():
    registry = CLIRegistry(
        [MockCLI("claude", ["claude-a"]), MockCLI("gemini", ["gemini-a", "gemini-b"])]
    )

    assert registry.models() == {
        "claude": ["claude-a"],
        "gemini": ["gemini-a", "gemini-b"],
    }


def test_supports_follows_supported_models():
    cli = MockCLI("claude", ["claude-a"])

    assert cli.supports("claude-a")
    assert not cli.supports("claude-b")

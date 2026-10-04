import pytest

from cli_to_api.clis import MockCLI
from cli_to_api.config import apply_rate_limits, rate_limit_rpm
from cli_to_api.rate_limit import RateLimitedCLI


@pytest.mark.parametrize(
    ("env", "expected"),
    [
        ({}, -1),
        ({"RATE_LIMIT_RPM": "10"}, 10),
        ({"RATE_LIMIT_RPM": "10", "CLAUDE_RATE_LIMIT_RPM": "2"}, 2),
        ({"RATE_LIMIT_RPM": "10", "CLAUDE_RATE_LIMIT_RPM": ""}, 10),
        ({"RATE_LIMIT_RPM": "", "CLAUDE_RATE_LIMIT_RPM": "  "}, -1),
        ({"CLAUDE_RATE_LIMIT_RPM": "1.5"}, 1.5),
        ({"CLAUDE_RATE_LIMIT_RPM": "0"}, 0),
        ({"RATE_LIMIT_RPM": "0", "CLAUDE_RATE_LIMIT_RPM": "-1"}, -1),
        ({"GEMINI_RATE_LIMIT_RPM": "5"}, -1),
    ],
    ids=[
        "unset", "default", "override", "empty-override", "all-empty",
        "fractional", "zero", "override-unlimits", "other-cli",
    ],
)
def test_rate_limit_rpm(env, expected):
    assert rate_limit_rpm("claude", env) == expected


@pytest.mark.parametrize("value", ["abc", "nan", "1,5"])
def test_invalid_values_name_the_variable(value):
    with pytest.raises(ValueError, match="CLAUDE_RATE_LIMIT_RPM"):
        rate_limit_rpm("claude", {"CLAUDE_RATE_LIMIT_RPM": value})


def test_apply_rate_limits():
    unlimited = MockCLI("unlimited", ["a"])
    infinite = MockCLI("infinite", ["b"])
    disabled = MockCLI("disabled", ["c"])
    limited = MockCLI("limited", ["d"])
    env = {
        "RATE_LIMIT_RPM": "-1",
        "INFINITE_RATE_LIMIT_RPM": "inf",
        "DISABLED_RATE_LIMIT_RPM": "0",
        "LIMITED_RATE_LIMIT_RPM": "0.5",
    }

    configured = apply_rate_limits([unlimited, infinite, disabled, limited], env)

    assert [cli.name for cli in configured] == ["unlimited", "infinite", "limited"]
    assert configured[0] is unlimited
    assert configured[1] is infinite
    assert isinstance(configured[2], RateLimitedCLI)

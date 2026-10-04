import math
import os
from collections.abc import Mapping, Sequence

from cli_to_api.clis import CLI
from cli_to_api.rate_limit import RateLimitedCLI, TokenBucket

DEFAULT_RATE_LIMIT_VAR = "RATE_LIMIT_RPM"
UNLIMITED = -1.0


def rate_limit_rpm(cli_name: str, env: Mapping[str, str] = os.environ) -> float:
    """Return the requests-per-minute limit configured for `cli_name`.

    Reads <CLI_NAME>_RATE_LIMIT_RPM, falling back to RATE_LIMIT_RPM, then to
    unlimited (-1). Empty values count as unset. Negative or infinite means
    unlimited, and 0 means disabled.
    """
    for var in (f"{cli_name.upper()}_RATE_LIMIT_RPM", DEFAULT_RATE_LIMIT_VAR):
        raw = env.get(var, "").strip()
        if not raw:
            continue
        try:
            rpm = float(raw)
        except ValueError:
            raise ValueError(f"{var} must be a number, got {raw!r}.") from None
        if math.isnan(rpm):
            raise ValueError(f"{var} must be a number, got {raw!r}.")
        return rpm
    return UNLIMITED


def apply_rate_limits(clis: Sequence[CLI], env: Mapping[str, str] = os.environ) -> list[CLI]:
    """Drop disabled CLIs and wrap rate-limited ones per the environment."""
    configured: list[CLI] = []
    for cli in clis:
        rpm = rate_limit_rpm(cli.name, env)
        if rpm == 0:
            continue
        if rpm < 0 or math.isinf(rpm):
            configured.append(cli)
        else:
            configured.append(RateLimitedCLI(cli, TokenBucket(rpm)))
    return configured

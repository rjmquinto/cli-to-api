import math
import time
from collections.abc import Callable

from cli_to_api.clis import CLI


class RateLimitedError(Exception):
    """A CLI's rate limit is exhausted; retry after `retry_after` seconds."""

    def __init__(self, cli_name: str, retry_after: float) -> None:
        self.retry_after = retry_after
        super().__init__(
            f"Rate limit for {cli_name} exceeded; retry in {math.ceil(retry_after)}s."
        )


class TokenBucket:
    """Allows `rpm` requests per minute, with bursts of up to a minute's worth.

    Holds at most max(1, rpm) tokens, starts full, and refills continuously at
    rpm / 60 tokens per second. Each request takes one token.
    """

    def __init__(self, rpm: float, *, clock: Callable[[], float] = time.monotonic) -> None:
        if not 0 < rpm < math.inf:
            raise ValueError(f"rpm must be positive and finite, got {rpm}.")
        self._rate = rpm / 60
        self._capacity = max(1.0, rpm)
        self._tokens = self._capacity
        self._clock = clock
        self._updated = clock()

    def try_acquire(self) -> float | None:
        """Take a token and return None, or return seconds until one is available."""
        now = self._clock()
        self._tokens = min(self._capacity, self._tokens + (now - self._updated) * self._rate)
        self._updated = now
        if self._tokens >= 1:
            self._tokens -= 1
            return None
        return (1 - self._tokens) / self._rate


class RateLimitedCLI(CLI):
    """Wraps a CLI so queries beyond its rate limit raise RateLimitedError."""

    def __init__(self, cli: CLI, bucket: TokenBucket) -> None:
        self.name = cli.name
        self._cli = cli
        self._bucket = bucket

    def supported_models(self) -> list[str]:
        return self._cli.supported_models()

    def supports(self, model: str) -> bool:
        return self._cli.supports(model)

    async def query(self, question: str, model: str) -> str:
        retry_after = self._bucket.try_acquire()
        if retry_after is not None:
            raise RateLimitedError(self.name, retry_after)
        return await self._cli.query(question, model)

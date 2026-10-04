import asyncio

import pytest

from cli_to_api.clis import MockCLI
from cli_to_api.rate_limit import RateLimitedCLI, RateLimitedError, TokenBucket


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def test_allows_a_minutes_worth_then_refuses():
    clock = FakeClock()
    bucket = TokenBucket(3, clock=clock)

    assert [bucket.try_acquire() for _ in range(3)] == [None, None, None]
    assert bucket.try_acquire() == pytest.approx(20)


def test_refills_over_time():
    clock = FakeClock()
    bucket = TokenBucket(6, clock=clock)
    for _ in range(6):
        bucket.try_acquire()

    clock.now = 9  # 0.9 tokens back
    assert bucket.try_acquire() == pytest.approx(1)
    clock.now = 10
    assert bucket.try_acquire() is None


def test_refill_is_capped_at_capacity():
    clock = FakeClock()
    bucket = TokenBucket(2, clock=clock)

    clock.now = 3600
    assert [bucket.try_acquire() for _ in range(2)] == [None, None]
    assert bucket.try_acquire() == pytest.approx(30)


def test_rate_below_one_allows_single_request():
    clock = FakeClock()
    bucket = TokenBucket(0.5, clock=clock)

    assert bucket.try_acquire() is None
    assert bucket.try_acquire() == pytest.approx(120)


def test_fractional_capacity():
    clock = FakeClock()
    bucket = TokenBucket(2.5, clock=clock)

    assert [bucket.try_acquire() for _ in range(2)] == [None, None]
    # 0.5 token left; needs 0.5 more at 2.5/60 per second.
    assert bucket.try_acquire() == pytest.approx(12)


@pytest.mark.parametrize("rpm", [0, -1, float("inf")])
def test_bucket_rejects_non_limiting_rates(rpm):
    with pytest.raises(ValueError):
        TokenBucket(rpm)


def test_rate_limited_cli_delegates_and_raises():
    clock = FakeClock()
    cli = RateLimitedCLI(MockCLI("claude", ["claude-a"], answer="ok"), TokenBucket(1, clock=clock))

    assert cli.name == "claude"
    assert cli.supported_models() == ["claude-a"]
    assert cli.supports("claude-a")
    assert asyncio.run(cli.query("hi", "claude-a")) == "ok"

    with pytest.raises(RateLimitedError) as excinfo:
        asyncio.run(cli.query("hi", "claude-a"))
    assert excinfo.value.retry_after == pytest.approx(60)
    assert str(excinfo.value) == "Rate limit for claude exceeded; retry in 60s."


def test_rate_limited_cli_keeps_supports_override():
    class TemplateCLI(MockCLI):
        def supports(self, model: str) -> bool:
            return model.startswith("claude-")

    cli = RateLimitedCLI(TemplateCLI("claude", ["claude-*"]), TokenBucket(1))

    assert cli.supports("claude-anything")

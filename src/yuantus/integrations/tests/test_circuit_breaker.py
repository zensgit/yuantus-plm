from __future__ import annotations

import asyncio

import pytest

from yuantus.integrations.circuit_breaker import (
    CLOSED,
    HALF_OPEN,
    OPEN,
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitOpenError,
    get_or_create_breaker,
    list_breakers,
    reset_registry,
)


def _make_breaker(**overrides) -> CircuitBreaker:
    base = dict(
        name=overrides.pop("name", "test"),
        enabled=overrides.pop("enabled", True),
        failure_threshold=overrides.pop("failure_threshold", 3),
        window_seconds=overrides.pop("window_seconds", 60.0),
        recovery_seconds=overrides.pop("recovery_seconds", 5.0),
        half_open_max_calls=overrides.pop("half_open_max_calls", 1),
        backoff_max_seconds=overrides.pop("backoff_max_seconds", 60.0),
    )
    base.update(overrides)
    return CircuitBreaker(CircuitBreakerConfig(**base))


def test_disabled_breaker_is_passthrough():
    breaker = _make_breaker(enabled=False, failure_threshold=1)

    def boom():
        raise ValueError("nope")

    # Disabled breaker should not record anything and re-raise as-is.
    for _ in range(5):
        with pytest.raises(ValueError):
            breaker.call_sync(boom)
    status = breaker.status()
    assert status["state"] == CLOSED
    assert status["failures_total"] == 0
    assert status["opens_total"] == 0


def test_opens_after_threshold_failures():
    breaker = _make_breaker(failure_threshold=3)

    def boom():
        raise RuntimeError("upstream")

    for i in range(3):
        with pytest.raises(RuntimeError):
            breaker.call_sync(boom)
    assert breaker.status()["state"] == OPEN
    # Subsequent call should short-circuit, not invoke `boom`.
    with pytest.raises(CircuitOpenError):
        breaker.call_sync(boom)
    status = breaker.status()
    assert status["short_circuited_total"] == 1
    assert status["opens_total"] == 1


def test_open_to_half_open_after_recovery():
    fake_time = [1000.0]

    def now():
        return fake_time[0]

    breaker = _make_breaker(failure_threshold=2, recovery_seconds=10.0)
    breaker._now = now  # type: ignore[assignment]

    def boom():
        raise RuntimeError("upstream")

    for _ in range(2):
        with pytest.raises(RuntimeError):
            breaker.call_sync(boom)
    assert breaker.status()["state"] == OPEN

    # advance past recovery window
    fake_time[0] += 11.0

    def ok():
        return "fine"

    # First call after recovery transitions OPEN -> HALF_OPEN, executes, closes.
    assert breaker.call_sync(ok) == "fine"
    assert breaker.status()["state"] == CLOSED
    assert breaker.status()["consecutive_open_cycles"] == 0


def test_half_open_failure_reopens_with_backoff():
    fake_time = [1000.0]

    def now():
        return fake_time[0]

    breaker = _make_breaker(
        failure_threshold=1, recovery_seconds=10.0, backoff_max_seconds=1000.0
    )
    breaker._now = now  # type: ignore[assignment]

    def boom():
        raise RuntimeError("still broken")

    # First failure trips the breaker.
    with pytest.raises(RuntimeError):
        breaker.call_sync(boom)
    assert breaker.status()["state"] == OPEN
    base_recovery = breaker.status()["current_recovery_seconds"]
    assert base_recovery == 10.0

    fake_time[0] += 11.0

    # Half-open trial fails -> reopens.
    with pytest.raises(RuntimeError):
        breaker.call_sync(boom)
    snapshot = breaker.status()
    assert snapshot["state"] == OPEN
    # Backoff doubled.
    assert snapshot["current_recovery_seconds"] == 20.0


def test_intermittent_success_resets_failure_window():
    """Consecutive-failure semantics: a successful call between failures
    must clear the in-progress window so a 4F+1S+1F sequence within the
    same window does not trip a 5-failure threshold."""
    breaker = _make_breaker(failure_threshold=5, window_seconds=60.0)

    def boom():
        raise RuntimeError("flaky")

    for _ in range(4):
        with pytest.raises(RuntimeError):
            breaker.call_sync(boom)
    # 4 failures stack — close to but below threshold.
    assert breaker.status()["failures_in_window"] == 4
    assert breaker.status()["state"] == CLOSED

    # One clean call within the same window must reset the counter.
    assert breaker.call_sync(lambda: "ok") == "ok"
    assert breaker.status()["failures_in_window"] == 0

    # A subsequent failure starts counting from 1, not 5.
    with pytest.raises(RuntimeError):
        breaker.call_sync(boom)
    snapshot = breaker.status()
    assert snapshot["state"] == CLOSED
    assert snapshot["failures_in_window"] == 1


def test_failures_reset_after_window():
    fake_time = [1000.0]

    def now():
        return fake_time[0]

    breaker = _make_breaker(failure_threshold=3, window_seconds=10.0)
    breaker._now = now  # type: ignore[assignment]

    def boom():
        raise RuntimeError("flaky")

    for _ in range(2):
        with pytest.raises(RuntimeError):
            breaker.call_sync(boom)
    assert breaker.status()["state"] == CLOSED

    # Advance beyond window — next failure should restart counting.
    fake_time[0] += 30.0
    with pytest.raises(RuntimeError):
        breaker.call_sync(boom)
    snapshot = breaker.status()
    assert snapshot["state"] == CLOSED
    assert snapshot["failures_in_window"] == 1


def test_async_call_path():
    async def runner():
        breaker = _make_breaker(failure_threshold=2)

        async def ok():
            return 42

        async def boom():
            raise RuntimeError("async upstream")

        result = await breaker.call_async(ok)
        assert result == 42

        for _ in range(2):
            with pytest.raises(RuntimeError):
                await breaker.call_async(boom)
        assert breaker.status()["state"] == OPEN
        with pytest.raises(CircuitOpenError):
            await breaker.call_async(ok)

    asyncio.run(runner())


def test_short_circuit_error_carries_retry_hint():
    breaker = _make_breaker(failure_threshold=1, recovery_seconds=42.0)

    def boom():
        raise RuntimeError("x")

    with pytest.raises(RuntimeError):
        breaker.call_sync(boom)

    def never():
        raise AssertionError("should not run while open")

    with pytest.raises(CircuitOpenError) as info:
        breaker.call_sync(never)
    assert info.value.name == "test"
    assert 0.0 < info.value.retry_in_seconds <= 42.0


def test_registry_reuses_existing_breaker():
    reset_registry()
    cfg = CircuitBreakerConfig(name="reg_test", enabled=True)
    a = get_or_create_breaker(cfg)
    b = get_or_create_breaker(cfg)
    assert a is b
    assert "reg_test" in list_breakers()
    reset_registry()
    assert "reg_test" not in list_breakers()


def test_keyboard_interrupt_does_not_trip_breaker():
    """Process-level interrupts must not be counted as upstream failures."""
    breaker = _make_breaker(failure_threshold=1)

    def cancelled():
        raise KeyboardInterrupt()

    with pytest.raises(KeyboardInterrupt):
        breaker.call_sync(cancelled)
    snapshot = breaker.status()
    assert snapshot["state"] == CLOSED
    assert snapshot["failures_total"] == 0
    assert snapshot["opens_total"] == 0


def test_system_exit_does_not_trip_breaker():
    breaker = _make_breaker(failure_threshold=1)

    def shutdown():
        raise SystemExit("graceful")

    with pytest.raises(SystemExit):
        breaker.call_sync(shutdown)
    snapshot = breaker.status()
    assert snapshot["state"] == CLOSED
    assert snapshot["failures_total"] == 0


def test_async_cancellation_does_not_trip_breaker():
    """asyncio.CancelledError inherits BaseException in 3.8+ and must not
    be counted as an upstream failure."""

    async def runner():
        breaker = _make_breaker(failure_threshold=1)

        async def cancelled():
            raise asyncio.CancelledError()

        with pytest.raises(asyncio.CancelledError):
            await breaker.call_async(cancelled)
        snapshot = breaker.status()
        assert snapshot["state"] == CLOSED
        assert snapshot["failures_total"] == 0

    asyncio.run(runner())


def test_interrupt_in_half_open_releases_inflight_slot():
    """Interrupt during half-open trial must not leak the in-flight slot
    or the breaker would refuse all subsequent recovery attempts."""
    fake_time = [1000.0]

    def now():
        return fake_time[0]

    breaker = _make_breaker(
        failure_threshold=1, recovery_seconds=10.0, half_open_max_calls=1
    )
    breaker._now = now  # type: ignore[assignment]

    # Trip and advance to half-open eligibility.
    with pytest.raises(RuntimeError):
        breaker.call_sync(lambda: (_ for _ in ()).throw(RuntimeError("upstream")))
    fake_time[0] += 11.0

    # Half-open trial gets interrupted.
    with pytest.raises(KeyboardInterrupt):
        breaker.call_sync(lambda: (_ for _ in ()).throw(KeyboardInterrupt()))

    # Slot must be released so a follow-up trial can proceed.
    assert breaker.status()["state"] in (HALF_OPEN, CLOSED)
    assert breaker.call_sync(lambda: "recovered") == "recovered"
    assert breaker.status()["state"] == CLOSED


def test_predicate_can_exclude_exceptions_from_failure_count():
    """Failure predicate lets callers re-raise some exceptions without
    counting them as upstream failures."""

    class ClientError(Exception):
        pass

    class UpstreamError(Exception):
        pass

    def is_failure(exc: Exception) -> bool:
        return isinstance(exc, UpstreamError)

    breaker = _make_breaker(failure_threshold=2, is_failure=is_failure)

    def client_boom():
        raise ClientError("bad input")

    def upstream_boom():
        raise UpstreamError("server down")

    # Many client errors — must not trip the breaker.
    for _ in range(10):
        with pytest.raises(ClientError):
            breaker.call_sync(client_boom)
    snapshot = breaker.status()
    assert snapshot["state"] == CLOSED
    assert snapshot["failures_total"] == 0

    # Two upstream errors — trips.
    for _ in range(2):
        with pytest.raises(UpstreamError):
            breaker.call_sync(upstream_boom)
    assert breaker.status()["state"] == OPEN


def test_excluded_exception_releases_half_open_slot():
    """An excluded exception during half-open trial must still free the
    inflight slot so subsequent recovery calls can proceed."""
    fake_time = [1000.0]

    def now():
        return fake_time[0]

    class ClientError(Exception):
        pass

    breaker = _make_breaker(
        failure_threshold=1,
        recovery_seconds=10.0,
        is_failure=lambda e: not isinstance(e, ClientError),
    )
    breaker._now = now  # type: ignore[assignment]

    # Trip once, advance to half-open eligibility.
    with pytest.raises(RuntimeError):
        breaker.call_sync(lambda: (_ for _ in ()).throw(RuntimeError("upstream")))
    fake_time[0] += 11.0

    # Half-open trial gets a client error — released without re-opening.
    with pytest.raises(ClientError):
        breaker.call_sync(lambda: (_ for _ in ()).throw(ClientError("bad")))

    # Subsequent success closes the breaker.
    assert breaker.call_sync(lambda: "ok") == "ok"
    assert breaker.status()["state"] == CLOSED


def test_predicate_failure_falls_back_to_counting():
    """If the predicate itself raises, defensively count the original exc."""

    def buggy_predicate(_exc):
        raise RuntimeError("bug in predicate")

    breaker = _make_breaker(failure_threshold=1, is_failure=buggy_predicate)

    with pytest.raises(ValueError):
        breaker.call_sync(lambda: (_ for _ in ()).throw(ValueError("orig")))
    # Predicate blew up, so we fell back to counting → breaker opened.
    assert breaker.status()["state"] == OPEN


def test_status_keys_are_stable():
    breaker = _make_breaker(name="status_keys")
    snapshot = breaker.status()
    expected_keys = {
        "name",
        "enabled",
        "state",
        "failures_in_window",
        "failure_threshold",
        "window_seconds",
        "recovery_seconds",
        "current_recovery_seconds",
        "consecutive_open_cycles",
        "open_for_seconds",
        "retry_in_seconds",
        "opens_total",
        "short_circuited_total",
        "failures_total",
        "successes_total",
        "last_failure_error",
    }
    assert set(snapshot.keys()) == expected_keys

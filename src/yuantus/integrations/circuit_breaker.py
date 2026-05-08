"""
Lightweight circuit breaker for outbound integration clients.

Default behaviour is status-quo (no wrapping); each client opts in via a
feature flag in `yuantus.config.settings`. When enabled, the breaker tracks
consecutive failures within a rolling window and short-circuits subsequent
calls once the failure threshold is reached, preventing retry storms when
an upstream service is unavailable.

State machine:
    closed --(failures >= threshold within window)--> open
    open   --(elapsed >= recovery_seconds)----------> half_open
    half_open --(success)---------------------------> closed
    half_open --(failure)---------------------------> open (with backoff)

Recovery time uses exponential backoff up to a cap, reset on transition to
closed. Each instance is thread-safe and exposes a status snapshot for
observability surfaces (metrics + health endpoints).
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Dict, Optional, TypeVar

T = TypeVar("T")


CLOSED = "closed"
OPEN = "open"
HALF_OPEN = "half_open"


class CircuitOpenError(RuntimeError):
    """Raised when a call is short-circuited because the breaker is open."""

    def __init__(self, name: str, retry_in_seconds: float) -> None:
        super().__init__(
            f"circuit breaker '{name}' is open; retry in ~{retry_in_seconds:.1f}s"
        )
        self.name = name
        self.retry_in_seconds = retry_in_seconds


@dataclass
class CircuitBreakerConfig:
    name: str
    enabled: bool = False
    failure_threshold: int = 5
    window_seconds: float = 60.0
    recovery_seconds: float = 30.0
    half_open_max_calls: int = 1
    backoff_max_seconds: float = 600.0


@dataclass
class _State:
    state: str = CLOSED
    failures: int = 0
    failure_window_start: float = 0.0
    opened_at: float = 0.0
    half_open_inflight: int = 0
    consecutive_open_cycles: int = 0
    opens_total: int = 0
    short_circuited_total: int = 0
    failures_total: int = 0
    successes_total: int = 0
    last_transition_at: float = 0.0
    last_failure_error: Optional[str] = None


class CircuitBreaker:
    """Synchronous + async friendly circuit breaker."""

    def __init__(self, config: CircuitBreakerConfig) -> None:
        self._config = config
        self._lock = threading.Lock()
        self._state = _State()
        self._now = time.monotonic

    @property
    def name(self) -> str:
        return self._config.name

    @property
    def enabled(self) -> bool:
        return self._config.enabled

    def status(self) -> Dict[str, object]:
        """Return a JSON-friendly snapshot for health/metrics surfaces."""
        with self._lock:
            cfg = self._config
            now = self._now()
            elapsed_open = (
                now - self._state.opened_at if self._state.state == OPEN else 0.0
            )
            recovery_at = (
                self._state.opened_at + self._current_recovery_seconds_locked()
                if self._state.state == OPEN
                else 0.0
            )
            return {
                "name": cfg.name,
                "enabled": cfg.enabled,
                "state": self._state.state,
                "failures_in_window": self._failures_in_window_locked(now),
                "failure_threshold": cfg.failure_threshold,
                "window_seconds": cfg.window_seconds,
                "recovery_seconds": cfg.recovery_seconds,
                "current_recovery_seconds": self._current_recovery_seconds_locked(),
                "consecutive_open_cycles": self._state.consecutive_open_cycles,
                "open_for_seconds": elapsed_open,
                "retry_in_seconds": max(0.0, recovery_at - now)
                if self._state.state == OPEN
                else 0.0,
                "opens_total": self._state.opens_total,
                "short_circuited_total": self._state.short_circuited_total,
                "failures_total": self._state.failures_total,
                "successes_total": self._state.successes_total,
                "last_failure_error": self._state.last_failure_error,
            }

    def reset(self) -> None:
        """Test helper: clear all counters and force CLOSED state."""
        with self._lock:
            self._state = _State()

    def call_sync(self, func: Callable[..., T], *args: object, **kwargs: object) -> T:
        if not self._config.enabled:
            return func(*args, **kwargs)
        self._before_call()
        try:
            result = func(*args, **kwargs)
        # Catch Exception (not BaseException) so process-level interrupts —
        # KeyboardInterrupt, SystemExit, asyncio.CancelledError — do not get
        # counted as upstream failures and trip the breaker.
        except Exception as exc:
            self._after_failure(exc)
            raise
        except BaseException:
            # Interrupt: release the half-open slot but do not count as
            # an upstream failure or transition state.
            self._after_interrupt()
            raise
        else:
            self._after_success()
            return result

    async def call_async(
        self,
        coro_factory: Callable[..., Awaitable[T]],
        *args: object,
        **kwargs: object,
    ) -> T:
        if not self._config.enabled:
            return await coro_factory(*args, **kwargs)
        self._before_call()
        try:
            result = await coro_factory(*args, **kwargs)
        except Exception as exc:
            self._after_failure(exc)
            raise
        except BaseException:
            self._after_interrupt()
            raise
        else:
            self._after_success()
            return result

    # --- internals -----------------------------------------------------------

    def _before_call(self) -> None:
        with self._lock:
            now = self._now()
            if self._state.state == OPEN:
                if now - self._state.opened_at >= self._current_recovery_seconds_locked():
                    self._transition_locked(HALF_OPEN, now)
                else:
                    self._state.short_circuited_total += 1
                    raise CircuitOpenError(
                        self._config.name,
                        max(
                            0.0,
                            self._state.opened_at
                            + self._current_recovery_seconds_locked()
                            - now,
                        ),
                    )
            if self._state.state == HALF_OPEN:
                if self._state.half_open_inflight >= self._config.half_open_max_calls:
                    self._state.short_circuited_total += 1
                    raise CircuitOpenError(self._config.name, 0.0)
                self._state.half_open_inflight += 1

    def _after_success(self) -> None:
        with self._lock:
            now = self._now()
            self._state.successes_total += 1
            if self._state.state == HALF_OPEN:
                self._state.half_open_inflight = max(
                    0, self._state.half_open_inflight - 1
                )
                self._transition_locked(CLOSED, now)
                self._state.consecutive_open_cycles = 0
            elif self._state.state == CLOSED:
                # Close window: drop stale failure count after a clean call.
                if self._state.failure_window_start and (
                    now - self._state.failure_window_start
                    > self._config.window_seconds
                ):
                    self._state.failures = 0
                    self._state.failure_window_start = 0.0

    def _after_interrupt(self) -> None:
        """Release a half-open trial slot without counting an upstream failure.

        Used for process-level interrupts (KeyboardInterrupt, SystemExit,
        asyncio.CancelledError) that should not contribute to the breaker's
        failure window — the upstream service is not implicated.
        """
        with self._lock:
            if self._state.state == HALF_OPEN:
                self._state.half_open_inflight = max(
                    0, self._state.half_open_inflight - 1
                )

    def _after_failure(self, exc: BaseException) -> None:
        with self._lock:
            now = self._now()
            self._state.failures_total += 1
            self._state.last_failure_error = type(exc).__name__
            if self._state.state == HALF_OPEN:
                self._state.half_open_inflight = max(
                    0, self._state.half_open_inflight - 1
                )
                self._state.consecutive_open_cycles += 1
                self._transition_locked(OPEN, now)
                return
            if self._state.state == CLOSED:
                if (
                    not self._state.failure_window_start
                    or now - self._state.failure_window_start
                    > self._config.window_seconds
                ):
                    self._state.failure_window_start = now
                    self._state.failures = 0
                self._state.failures += 1
                if self._state.failures >= self._config.failure_threshold:
                    self._state.consecutive_open_cycles += 1
                    self._transition_locked(OPEN, now)

    def _transition_locked(self, new_state: str, now: float) -> None:
        if self._state.state == new_state:
            return
        self._state.state = new_state
        self._state.last_transition_at = now
        if new_state == OPEN:
            self._state.opened_at = now
            self._state.opens_total += 1
            self._state.failures = 0
            self._state.failure_window_start = 0.0
        elif new_state == HALF_OPEN:
            self._state.half_open_inflight = 0
        elif new_state == CLOSED:
            self._state.opened_at = 0.0
            self._state.failures = 0
            self._state.failure_window_start = 0.0
            self._state.half_open_inflight = 0

    def _current_recovery_seconds_locked(self) -> float:
        cycles = max(0, self._state.consecutive_open_cycles - 1)
        backoff = self._config.recovery_seconds * (2 ** cycles)
        return min(backoff, self._config.backoff_max_seconds)

    def _failures_in_window_locked(self, now: float) -> int:
        if not self._state.failure_window_start:
            return 0
        if now - self._state.failure_window_start > self._config.window_seconds:
            return 0
        return self._state.failures


# --- registry ----------------------------------------------------------------

_registry: Dict[str, CircuitBreaker] = {}
_registry_lock = threading.Lock()


def get_or_create_breaker(config: CircuitBreakerConfig) -> CircuitBreaker:
    """Return the shared breaker for `config.name`, creating on first call.

    Settings changes during a process lifetime do not propagate; tests should
    call `reset_registry()` between cases when toggling feature flags.
    """
    with _registry_lock:
        breaker = _registry.get(config.name)
        if breaker is None:
            breaker = CircuitBreaker(config)
            _registry[config.name] = breaker
        return breaker


def list_breakers() -> Dict[str, CircuitBreaker]:
    with _registry_lock:
        return dict(_registry)


def reset_registry() -> None:
    """Test-only: drop all registered breakers."""
    with _registry_lock:
        _registry.clear()

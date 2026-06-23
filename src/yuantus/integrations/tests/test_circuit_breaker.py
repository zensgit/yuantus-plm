from yuantus.integrations.circuit_breaker import CircuitBreaker, CircuitBreakerConfig


def test_recovery_backoff_caps_cycles_before_overflow():
    breaker = CircuitBreaker(
        CircuitBreakerConfig(
            name="render",
            enabled=True,
            recovery_seconds=30.0,
            backoff_max_seconds=600.0,
        )
    )
    breaker._state.consecutive_open_cycles = 5000

    assert breaker._current_recovery_seconds_locked() == 600.0

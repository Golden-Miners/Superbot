"""RED tests for M9.5 — Timeout/retry/fallback/skip/conflict and resource-routing tests.

Tests define:
- TimeoutConfig / TimeoutResult: execution timeout handling
- RetryConfig / RetryResult: retry with backoff, max attempts
- FallbackConfig / FallbackResult: fallback to alternative on failure
- SkipConfig / SkipResult: conditional skip of operations
- ConflictConfig / ConflictResult: conflict detection between concurrent ops
- ResourceRouter: route work to resources with capacity checks
- Deterministic: same inputs -> identical results
- Stdlib-only, no import-time network/database activity
"""

from __future__ import annotations

from decimal import Decimal

from superbot.m9.timeout_routing import (
    ConflictConfig,
    ConflictResolver,
    ConflictResult,
    FallbackConfig,
    FallbackHandler,
    FallbackResult,
    OrchestrationResult,
    ResourceRouter,
    RetryConfig,
    RetryHandler,
    RetryResult,
    SkipConfig,
    SkipFilter,
    SkipResult,
    TimeoutConfig,
    TimeoutHandler,
    TimeoutResult,
    execute_with_timeout,
    retry_operation,
    route_resource,
)


def test_timeout_config_creates():
    """TimeoutConfig can be created with timeout and hard_limit."""
    config = TimeoutConfig(timeout_ms=Decimal(1000), hard_limit_ms=Decimal(5000))
    assert config.timeout_ms == Decimal(1000)
    assert config.hard_limit_ms == Decimal(5000)


def test_timeout_result_creates():
    """TimeoutResult stores outcome and timing."""
    result = TimeoutResult(
        timed_out=False,
        elapsed_ms=Decimal(120),
        deadline_ms=Decimal(1000),
        reason=None,
    )
    assert result.timed_out is False
    assert result.elapsed_ms == Decimal(120)


def test_timeout_handler_within_limit():
    """TimeoutHandler returns success when operation completes before deadline."""
    handler = TimeoutHandler(TimeoutConfig(timeout_ms=Decimal(1000), hard_limit_ms=Decimal(5000)))
    result = handler.run(lambda: "ok")
    assert result.timed_out is False
    assert result.result == "ok"


def test_timeout_handler_exceeds_limit():
    """TimeoutHandler marks timeout when operation exceeds deadline."""
    handler = TimeoutHandler(TimeoutConfig(timeout_ms=Decimal(10), hard_limit_ms=Decimal(5000)))

    def slow():
        import time

        time.sleep(0.1)
        return "ok"

    result = handler.run(slow)
    assert result.timed_out is True


def test_retry_config_creates():
    """RetryConfig stores max attempts and backoff."""
    config = RetryConfig(
        max_attempts=3, base_backoff_ms=Decimal(100), backoff_multiplier=Decimal(2)
    )
    assert config.max_attempts == 3
    assert config.base_backoff_ms == Decimal(100)
    assert config.backoff_multiplier == Decimal(2)


def test_retry_result_creates():
    """RetryResult stores attempt count and outcome."""
    result = RetryResult(attempts=2, succeeded=True, final_error=None)
    assert result.attempts == 2
    assert result.succeeded is True


def test_retry_handler_succeeds_first_try():
    """RetryHandler succeeds immediately when operation works."""
    handler = RetryHandler(
        RetryConfig(max_attempts=3, base_backoff_ms=Decimal(10), backoff_multiplier=Decimal(2))
    )
    result = handler.run(lambda: "ok")
    assert result.succeeded is True
    assert result.attempts == 1
    assert result.result == "ok"


def test_retry_handler_succeeds_after_retries():
    """RetryHandler retries until success within max attempts."""
    call_count = 0

    def flaky():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ValueError("transient")
        return "ok"

    handler = RetryHandler(
        RetryConfig(max_attempts=3, base_backoff_ms=Decimal(1), backoff_multiplier=Decimal(2))
    )
    result = handler.run(flaky)
    assert result.succeeded is True
    assert result.attempts == 3


def test_retry_handler_exhausts_attempts():
    """RetryHandler fails after max attempts exhausted."""

    def always_fail():
        raise ValueError("persistent")

    handler = RetryHandler(
        RetryConfig(max_attempts=2, base_backoff_ms=Decimal(1), backoff_multiplier=Decimal(2))
    )
    result = handler.run(always_fail)
    assert result.succeeded is False
    assert result.attempts == 2
    assert result.final_error is not None


def test_fallback_config_creates():
    """FallbackConfig stores primary and fallback callables."""
    config = FallbackConfig(primary=lambda: "primary", fallback=lambda: "fallback")
    assert config.primary is not None
    assert config.fallback is not None


def test_fallback_result_creates():
    """FallbackResult stores source and value."""
    result = FallbackResult(source="primary", value="ok")
    assert result.source == "primary"
    assert result.value == "ok"


def test_fallback_handler_uses_primary():
    """FallbackHandler uses primary when it succeeds."""
    handler = FallbackHandler(
        FallbackConfig(primary=lambda: "primary", fallback=lambda: "fallback")
    )
    result = handler.run()
    assert result.source == "primary"
    assert result.value == "primary"


def test_fallback_handler_uses_fallback():
    """FallbackHandler uses fallback when primary fails."""
    handler = FallbackHandler(
        FallbackConfig(
            primary=lambda: (_ for _ in ()).throw(ValueError("boom")), fallback=lambda: "fallback"
        )
    )
    result = handler.run()
    assert result.source == "fallback"
    assert result.value == "fallback"


def test_skip_config_creates():
    """SkipConfig stores skip condition."""
    config = SkipConfig(skip=True, reason="maintenance")
    assert config.skip is True
    assert config.reason == "maintenance"


def test_skip_result_creates():
    """SkipResult stores skipped flag and reason."""
    result = SkipResult(skipped=True, reason="maintenance")
    assert result.skipped is True
    assert result.reason == "maintenance"


def test_skip_filter_skips():
    """SkipFilter skips when configured to skip."""
    filter_ = SkipFilter(SkipConfig(skip=True, reason="maintenance"))
    result = filter_.should_skip()
    assert result.skipped is True
    assert result.reason == "maintenance"


def test_skip_filter_does_not_skip():
    """SkipFilter does not skip when not configured."""
    filter_ = SkipFilter(SkipConfig(skip=False, reason=None))
    result = filter_.should_skip()
    assert result.skipped is False


def test_conflict_config_creates():
    """ConflictConfig stores conflict detection rule."""
    config = ConflictConfig(detect_conflicts=True, conflict_window_ms=Decimal(1000))
    assert config.detect_conflicts is True
    assert config.conflict_window_ms == Decimal(1000)


def test_conflict_result_creates():
    """ConflictResult stores conflict flag and conflicting ops."""
    result = ConflictResult(conflict=True, conflicting_ops=["op_a", "op_b"])
    assert result.conflict is True
    assert result.conflicting_ops == ["op_a", "op_b"]


def test_conflict_resolver_no_conflict():
    """ConflictResolver reports no conflict for non-overlapping ops."""
    resolver = ConflictResolver(
        ConflictConfig(detect_conflicts=True, conflict_window_ms=Decimal(1000))
    )
    result = resolver.check(["op_a"], ["op_b"])
    assert result.conflict is False


def test_conflict_resolver_conflict():
    """ConflictResolver reports conflict for overlapping ops."""
    resolver = ConflictResolver(
        ConflictConfig(detect_conflicts=True, conflict_window_ms=Decimal(1000))
    )
    result = resolver.check(["op_a"], ["op_a"])
    assert result.conflict is True


def test_resource_router_creates():
    """ResourceRouter can be created with resources."""
    router = ResourceRouter(resources={"cpu": 4, "memory": 8192})
    assert router.resources == {"cpu": 4, "memory": 8192}


def test_route_resource_success():
    """route_resource allocates when capacity available."""
    router = ResourceRouter(resources={"cpu": 4})
    result = route_resource(router, "job_1", {"cpu": 2})
    assert result.allocated is True
    assert result.remaining["cpu"] == 2


def test_route_resource_insufficient_capacity():
    """route_resource rejects when capacity insufficient."""
    router = ResourceRouter(resources={"cpu": 1})
    result = route_resource(router, "job_1", {"cpu": 2})
    assert result.allocated is False


def test_orchestration_result_creates():
    """OrchestrationResult stores overall outcome."""
    result = OrchestrationResult(success=True, steps=["timeout", "retry"], errors=[])
    assert result.success is True


def test_execute_with_timeout_function():
    """execute_with_timeout convenience function works."""
    result = execute_with_timeout(lambda: 42, Decimal(1000), Decimal(5000))
    assert result.timed_out is False
    assert result.result == 42


def test_retry_operation_function():
    """retry_operation convenience function works."""
    result = retry_operation(lambda: "done", 3, Decimal(1), Decimal(2))
    assert result.succeeded is True


def test_route_resource_function():
    """route_resource convenience function works."""
    router = ResourceRouter(resources={"cpu": 4})
    result = route_resource(router, "job_1", {"cpu": 1})
    assert result.allocated is True


def test_deterministic_timeout():
    """Same inputs yield identical timeout results."""
    h1 = TimeoutHandler(TimeoutConfig(timeout_ms=Decimal(1000), hard_limit_ms=Decimal(5000)))
    h2 = TimeoutHandler(TimeoutConfig(timeout_ms=Decimal(1000), hard_limit_ms=Decimal(5000)))
    r1 = h1.run(lambda: "x")
    r2 = h2.run(lambda: "x")
    assert r1.timed_out == r2.timed_out
    assert r1.result == r2.result


def test_deterministic_retry():
    """Same inputs yield identical retry results."""
    call_count = [0]

    def op():
        call_count[0] += 1
        if call_count[0] == 1:
            raise ValueError("x")
        return "y"

    r1 = retry_operation(op, 2, Decimal(1), Decimal(2))
    call_count[0] = 0
    r2 = retry_operation(op, 2, Decimal(1), Decimal(2))
    assert r1.succeeded == r2.succeeded
    assert r1.attempts == r2.attempts

"""RED tests for Phase 4 — Operational correctness: health check states.

Covers: NOT_PROBED status for unprobed services, health registry aggregation
with NOT_PROBED, and dashboard health reflecting actual probe state rather
than seeded HEALTHY.
"""

from __future__ import annotations

from superbot.supervisor.health import (
    HealthCheckResult,
    HealthRegistry,
    HealthStatus,
)


def test_health_status_enum_includes_not_probed():
    """HealthStatus includes NOT_PROBED for services not yet probed."""
    assert HealthStatus.NOT_PROBED == "not_probed"


def test_not_probed_is_distinct_from_other_states():
    """NOT_PROBED is a distinct value from HEALTHY, DEGRADED, BLOCKED."""
    assert HealthStatus.NOT_PROBED != HealthStatus.HEALTHY
    assert HealthStatus.NOT_PROBED != HealthStatus.DEGRADED
    assert HealthStatus.NOT_PROBED != HealthStatus.BLOCKED


def test_overall_not_probed_when_all_not_probed():
    """Overall status is NOT_PROBED when every check is NOT_PROBED."""
    reg = HealthRegistry()
    reg.register("api", lambda: HealthCheckResult(HealthStatus.NOT_PROBED, "not probed"))
    reg.register("mt5", lambda: HealthCheckResult(HealthStatus.NOT_PROBED, "not probed"))
    assert reg.overall() == HealthStatus.NOT_PROBED


def test_overall_healthy_when_any_healthy():
    """Overall is HEALTHY when at least one check is HEALTHY and none are
    degraded/blocked."""
    reg = HealthRegistry()
    reg.register("api", lambda: HealthCheckResult(HealthStatus.HEALTHY, "ok"))
    reg.register("mt5", lambda: HealthCheckResult(HealthStatus.NOT_PROBED, "not probed"))
    assert reg.overall() == HealthStatus.HEALTHY


def test_overall_degraded_when_any_degraded():
    """Overall is DEGRADED when any check is DEGRADED and none are blocked."""
    reg = HealthRegistry()
    reg.register("api", lambda: HealthCheckResult(HealthStatus.NOT_PROBED, "not probed"))
    reg.register("mt5", lambda: HealthCheckResult(HealthStatus.DEGRADED, "stale data"))
    assert reg.overall() == HealthStatus.DEGRADED


def test_overall_blocked_when_any_blocked():
    """Overall is BLOCKED when any check is BLOCKED, even if others are
    NOT_PROBED."""
    reg = HealthRegistry()
    reg.register("api", lambda: HealthCheckResult(HealthStatus.NOT_PROBED, "not probed"))
    reg.register("mt5", lambda: HealthCheckResult(HealthStatus.BLOCKED, "read-only not configured"))
    assert reg.overall() == HealthStatus.BLOCKED


def test_empty_registry_is_not_probed():
    """An empty registry (no checks registered) reports NOT_PROBED rather
    than claiming HEALTHY with no evidence."""
    reg = HealthRegistry()
    assert reg.overall() == HealthStatus.NOT_PROBED

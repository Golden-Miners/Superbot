"""Tests for the supervisor health model (M1.5).

Health checks report status without side effects; no network/MT5/DB/model
calls at import time or during a check unless the check itself wraps one.
"""

from __future__ import annotations

from superbot.supervisor.health import (
    HealthCheckResult,
    HealthRegistry,
    HealthStatus,
)


def test_health_status_enum():
    assert HealthStatus.HEALTHY == "healthy"
    assert HealthStatus.DEGRADED == "degraded"
    assert HealthStatus.BLOCKED == "blocked"


def test_registry_register_and_run_returns_statuses():
    reg = HealthRegistry()
    reg.register("api", lambda: HealthCheckResult(HealthStatus.HEALTHY, "ok"))
    reg.register("mt5", lambda: HealthCheckResult(HealthStatus.BLOCKED, "read-only not configured"))
    results = reg.run_all()
    assert results["api"].status == HealthStatus.HEALTHY
    assert results["mt5"].status == HealthStatus.BLOCKED
    assert reg.overall() == HealthStatus.BLOCKED


def test_overall_healthy_when_all_healthy():
    reg = HealthRegistry()
    reg.register("a", lambda: HealthCheckResult(HealthStatus.HEALTHY, "ok"))
    reg.register("b", lambda: HealthCheckResult(HealthStatus.HEALTHY, "ok"))
    assert reg.overall() == HealthStatus.HEALTHY


def test_overall_degraded_when_any_degraded():
    reg = HealthRegistry()
    reg.register("a", lambda: HealthCheckResult(HealthStatus.HEALTHY, "ok"))
    reg.register("b", lambda: HealthCheckResult(HealthStatus.DEGRADED, "stale data"))
    assert reg.overall() == HealthStatus.DEGRADED

"""Supervisor health model (M1.5).

Health checks are side-effect-free predicates that report a status. The
registry aggregates results into an overall status. No network, MT5,
database, or model calls happen at import time; individual checks may wrap
such calls but declare their own dependencies.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    BLOCKED = "blocked"
    NOT_PROBED = "not_probed"


CheckCallable = Callable[[], "HealthCheckResult"]


@dataclass(frozen=True)
class HealthCheckResult:
    status: HealthStatus
    message: str
    check_name: str = ""
    checked_at_utc: str = ""

    def __post_init__(self) -> None:
        if not self.checked_at_utc:
            object.__setattr__(
                self,
                "checked_at_utc",
                datetime.now(tz=UTC).isoformat(),
            )


class HealthRegistry:
    """Registers named health checks and aggregates their results."""

    def __init__(self) -> None:
        self._checks: dict[str, CheckCallable] = {}

    def register(self, name: str, check: CheckCallable) -> None:
        if not name:
            raise ValueError("health check name is required")
        if not callable(check):
            raise TypeError("health check must be callable")
        self._checks[name] = check

    def run_all(self) -> dict[str, HealthCheckResult]:
        return {name: check() for name, check in self._checks.items()}

    def overall(self) -> HealthStatus:
        statuses = [result.status for result in self.run_all().values()]
        if not statuses:
            return HealthStatus.NOT_PROBED
        if HealthStatus.BLOCKED in statuses:
            return HealthStatus.BLOCKED
        if HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED
        if HealthStatus.HEALTHY in statuses:
            return HealthStatus.HEALTHY
        return HealthStatus.NOT_PROBED

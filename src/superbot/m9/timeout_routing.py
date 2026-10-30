"""M9.5 — Timeout/retry/fallback/skip/conflict and resource-routing tests.

Deterministic execution-control service:
- TimeoutHandler: runs an operation with a deadline; marks timeout if exceeded
- RetryHandler: retries a failing operation up to max_attempts with backoff
- FallbackHandler: uses primary callable, falls back to fallback on failure
- SkipFilter: conditionally skips an operation
- ConflictResolver: detects conflicting operations within a time window
- ResourceRouter: routes jobs to resources with capacity checks
- Stdlib-only; no import-time network/database activity.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class TimeoutConfig:
    """Configuration for timeout handling."""

    timeout_ms: Decimal
    hard_limit_ms: Decimal


@dataclass(frozen=True)
class TimeoutResult:
    """Result of a timed operation."""

    timed_out: bool
    elapsed_ms: Decimal
    deadline_ms: Decimal
    reason: str | None = None
    result: object = None


class TimeoutHandler:
    """Executes a callable with a timeout deadline."""

    def __init__(self, config: TimeoutConfig) -> None:
        self.config = config

    def run(self, func) -> TimeoutResult:
        """Run func, returning TimeoutResult with timed_out flag."""
        deadline_s = float(self.config.timeout_ms / Decimal(1000))
        container: dict = {}

        def target() -> None:
            try:
                container["result"] = func()
            except Exception as exc:  # noqa: BLE001 - capture any failure
                container["error"] = exc

        thread = threading.Thread(target=target, daemon=True)
        start = time.perf_counter()
        thread.start()
        thread.join(timeout=deadline_s)
        elapsed = Decimal(str((time.perf_counter() - start) * 1000))

        if thread.is_alive():
            return TimeoutResult(
                timed_out=True,
                elapsed_ms=elapsed,
                deadline_ms=self.config.timeout_ms,
                reason=f"exceeded deadline {self.config.timeout_ms}ms",
                result=None,
            )

        if "error" in container:
            return TimeoutResult(
                timed_out=True,
                elapsed_ms=elapsed,
                deadline_ms=self.config.timeout_ms,
                reason=str(container["error"]),
                result=None,
            )

        return TimeoutResult(
            timed_out=False,
            elapsed_ms=elapsed,
            deadline_ms=self.config.timeout_ms,
            reason=None,
            result=container.get("result"),
        )


@dataclass(frozen=True)
class RetryConfig:
    """Configuration for retry behavior."""

    max_attempts: int
    base_backoff_ms: Decimal
    backoff_multiplier: Decimal


@dataclass(frozen=True)
class RetryResult:
    """Result of retry execution."""

    attempts: int
    succeeded: bool
    final_error: str | None = None
    result: object = None


class RetryHandler:
    """Executes a callable, retrying on failure up to max_attempts."""

    def __init__(self, config: RetryConfig) -> None:
        self.config = config

    def run(self, func) -> RetryResult:
        """Run func with retries."""
        last_error: str | None = None
        result = None
        for attempt in range(1, self.config.max_attempts + 1):
            try:
                result = func()
                return RetryResult(
                    attempts=attempt,
                    succeeded=True,
                    final_error=None,
                    result=result,
                )
            except Exception as exc:  # noqa: BLE001 - retry on any exception
                last_error = str(exc)
                if attempt < self.config.max_attempts:
                    backoff_ms = self.config.base_backoff_ms * (
                        self.config.backoff_multiplier ** (attempt - 1)
                    )
                    time.sleep(float(backoff_ms) / 1000.0)
        return RetryResult(
            attempts=self.config.max_attempts,
            succeeded=False,
            final_error=last_error,
            result=None,
        )


@dataclass(frozen=True)
class FallbackConfig:
    """Configuration for fallback behavior."""

    primary: object
    fallback: object


@dataclass(frozen=True)
class FallbackResult:
    """Result of fallback execution."""

    source: str  # "primary" or "fallback"
    value: object


class FallbackHandler:
    """Executes primary callable; falls back to fallback on failure."""

    def __init__(self, config: FallbackConfig) -> None:
        self.config = config

    def run(self) -> FallbackResult:
        """Run primary, falling back on exception."""
        try:
            value = self.config.primary()
            return FallbackResult(source="primary", value=value)
        except Exception:  # noqa: BLE001 - fall back on any exception
            value = self.config.fallback()
            return FallbackResult(source="fallback", value=value)


@dataclass(frozen=True)
class SkipConfig:
    """Configuration for conditional skip."""

    skip: bool
    reason: str | None = None


@dataclass(frozen=True)
class SkipResult:
    """Result of skip evaluation."""

    skipped: bool
    reason: str | None = None


class SkipFilter:
    """Evaluates whether an operation should be skipped."""

    def __init__(self, config: SkipConfig) -> None:
        self.config = config

    def should_skip(self) -> SkipResult:
        """Return SkipResult based on config."""
        return SkipResult(skipped=self.config.skip, reason=self.config.reason)


@dataclass(frozen=True)
class ConflictConfig:
    """Configuration for conflict detection."""

    detect_conflicts: bool
    conflict_window_ms: Decimal


@dataclass(frozen=True)
class ConflictResult:
    """Result of conflict detection."""

    conflict: bool
    conflicting_ops: list[str]


class ConflictResolver:
    """Detects conflicts between operation sets within a time window."""

    def __init__(self, config: ConflictConfig) -> None:
        self.config = config

    def check(self, ops_a: list[str], ops_b: list[str]) -> ConflictResult:
        """Return ConflictResult indicating whether ops overlap."""
        conflicting = [op for op in ops_a if op in ops_b]
        conflict = bool(conflicting) and self.config.detect_conflicts
        return ConflictResult(conflict=conflict, conflicting_ops=conflicting)


@dataclass(frozen=True)
class ResourceAllocation:
    """Result of a resource allocation attempt."""

    allocated: bool
    resource: str
    remaining: dict


class ResourceRouter:
    """Routes jobs to resources with capacity checks."""

    def __init__(self, resources: dict[str, int]) -> None:
        self.resources = dict(resources)
        self._allocated: dict[str, dict[str, int]] = {}

    def allocate(self, job_id: str, demand: dict[str, int]) -> ResourceAllocation:
        """Attempt to allocate resources for a job."""
        for resource, needed in demand.items():
            available = self.resources.get(resource, 0)
            used = sum(a.get(resource, 0) for a in self._allocated.values())
            if available - used < needed:
                return ResourceAllocation(
                    allocated=False,
                    resource=resource,
                    remaining={r: self.resources.get(r, 0) for r in self.resources},
                )
        self._allocated[job_id] = dict(demand)
        remaining = {
            r: self.resources.get(r, 0) - sum(a.get(r, 0) for a in self._allocated.values())
            for r in self.resources
        }
        return ResourceAllocation(allocated=True, resource=next(iter(demand)), remaining=remaining)


@dataclass(frozen=True)
class OrchestrationResult:
    """Overall outcome of an orchestrated sequence."""

    success: bool
    steps: list[str]
    errors: list[str]


@dataclass(frozen=True)
class ExecutionResult:
    """Result of a single execution step."""

    step: str
    success: bool
    error: str | None = None


def execute_with_timeout(func, timeout_ms: Decimal, hard_limit_ms: Decimal) -> TimeoutResult:
    """Convenience: run func with a timeout."""
    return TimeoutHandler(TimeoutConfig(timeout_ms=timeout_ms, hard_limit_ms=hard_limit_ms)).run(
        func
    )


def retry_operation(
    func, max_attempts: int, base_backoff_ms: Decimal, backoff_multiplier: Decimal
) -> RetryResult:
    """Convenience: run func with retries."""
    return RetryHandler(
        RetryConfig(
            max_attempts=max_attempts,
            base_backoff_ms=base_backoff_ms,
            backoff_multiplier=backoff_multiplier,
        )
    ).run(func)


def route_resource(
    router: ResourceRouter, job_id: str, demand: dict[str, int]
) -> ResourceAllocation:
    """Convenience: route a job to resources via the router."""
    return router.allocate(job_id, demand)

"""Boundaries/concurrency/missing-input tests and risk audit events (schema.md section 7.7).

Deterministic risk boundary and audit service:
- Boundary validation: zero/negative/extreme inputs blocked at trust boundaries
- Missing input handling: None/null/empty inputs block operations rather than defaulting
- Concurrency safety: thread-safe access to shared risk state
- Risk audit events: immutable log of risk decisions (halt, resume, block, reject, resize)
- Audit event immutability: events cannot be modified after creation
- All Decimal arithmetic; no silent defaults for missing inputs
- Stdlib-only; no import-time network/MT5/database/model activity.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from threading import RLock


class BoundaryError(Exception):
    """Raised when a value violates boundary constraints."""


class MissingInputError(Exception):
    """Raised when a required input is missing/None/empty."""


@dataclass(frozen=True)
class AuditEvent:
    """Immutable audit event."""

    event_type: str
    reason: str
    detail: dict
    timestamp: float = field(default_factory=lambda: __import__("time").time())


class AuditEventLogger:
    """Immutable append-only log of risk audit events."""

    def __init__(self) -> None:
        self._events: list[AuditEvent] = []
        self._lock: RLock = RLock()

    def log_audit_event(
        self,
        event_type: str,
        reason: str,
        detail: dict,
    ) -> None:
        """Append an immutable audit event."""
        with self._lock:
            self._events.append(
                AuditEvent(
                    event_type=event_type,
                    reason=reason,
                    detail=dict(detail),
                )
            )

    def get_events(self) -> list[dict]:
        """Return a copy of all audit events (immutable snapshot)."""
        with self._lock:
            return [
                {
                    "event_type": e.event_type,
                    "reason": e.reason,
                    "detail": dict(e.detail),
                    "timestamp": e.timestamp,
                }
                for e in self._events
            ]


class ConcurrencySafeRiskService:
    """Thread-safe risk service for shared state access."""

    def __init__(self) -> None:
        self._decisions: list[dict] = []
        self._lock: RLock = RLock()

    def record_decision(
        self,
        decision_id: str,
        detail: dict,
    ) -> None:
        """Record a risk decision thread-safely."""
        with self._lock:
            self._decisions.append(
                {
                    "decision_id": decision_id,
                    "detail": dict(detail),
                }
            )

    def get_decisions(self) -> list[dict]:
        """Return a copy of all recorded decisions."""
        with self._lock:
            return [dict(d) for d in self._decisions]


def validate_boundary(
    name: str,
    value: Decimal,
    min_value: Decimal | None = None,
    max_value: Decimal | None = None,
) -> Decimal:
    """Validate a Decimal value against boundary constraints.

    Args:
        name: parameter name (for error messages)
        value: value to validate
        min_value: minimum allowed value (inclusive)
        max_value: maximum allowed value (inclusive)

    Returns the validated value.

    Raises BoundaryError if value is zero, negative, below min, or above max.
    """
    if value == Decimal(0) or value < Decimal(0):
        msg = f"{name} must be positive and non-zero, got {value}"
        if min_value is not None:
            msg += f" (minimum {min_value})"
        raise BoundaryError(msg)
    if min_value is not None and value < min_value:
        raise BoundaryError(f"{name} {value} below minimum {min_value}")
    if max_value is not None and value > max_value:
        raise BoundaryError(f"{name} {value} above maximum {max_value}")
    return value


def validate_not_missing(
    name: str,
    value,
):
    """Validate that a value is not missing (None or empty).

    Args:
        name: parameter name (for error messages)
        value: value to validate

    Returns the validated value.

    Raises MissingInputError if value is None or empty string.
    """
    if value is None:
        raise MissingInputError(f"{name} is missing (None)")
    if isinstance(value, str) and value == "":
        raise MissingInputError(f"{name} is missing (empty string)")
    return value


def audit_event(
    logger: AuditEventLogger,
    event_type: str,
    reason: str,
    detail: dict,
) -> None:
    """Log an audit event (convenience function)."""
    logger.log_audit_event(event_type, reason, detail)


# log_audit_event is an alias for audit_event, kept for API compatibility.
log_audit_event = audit_event

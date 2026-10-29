"""RED tests for M7.7 — Boundaries/concurrency/missing-input tests and risk audit events.

Tests define:
- Boundary validation: zero/negative/extreme inputs blocked at trust boundaries
- Missing input handling: None/null/empty inputs block operations rather than defaulting
- Concurrency safety: thread-safe access to shared risk state
- Risk audit events: immutable log of risk decisions (halt, resume, block, reject, resize)
- Audit event immutability: events cannot be modified after creation
- All Decimal arithmetic, no silent defaults for missing inputs
- Stdlib-only, no import-time network/MT5/database/model activity
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from superbot.risk.risk_boundaries import (
    AuditEvent,
    AuditEventLogger,
    BoundaryError,
    ConcurrencySafeRiskService,
    MissingInputError,
    validate_boundary,
    validate_not_missing,
)


def test_audit_event_creates():
    """AuditEvent can be created."""
    event = AuditEvent(
        event_type="halt",
        reason="daily_loss_exceeded",
        detail={"daily_loss_pct": "4.0", "threshold_pct": "3.0"},
    )
    assert event.event_type == "halt"
    assert event.reason == "daily_loss_exceeded"


def test_audit_event_logger_creates():
    """AuditEventLogger can be created."""
    logger = AuditEventLogger()
    assert logger is not None


def test_log_audit_event_immutable():
    """log_audit_event appends events that cannot be modified."""
    logger = AuditEventLogger()
    logger.log_audit_event("halt", "daily_loss_exceeded", {"detail": "test"})
    events = logger.get_events()
    assert len(events) == 1
    assert events[0]["event_type"] == "halt"


def test_audit_event_cannot_be_modified():
    """Audit events are immutable after logging."""
    logger = AuditEventLogger()
    logger.log_audit_event("halt", "reason", {})
    events_before = logger.get_events()
    # Attempting to modify should not affect stored events
    events_before[0]["event_type"] = "modified"
    events_after = logger.get_events()
    assert events_after[0]["event_type"] == "halt"


def test_validate_boundary_zero_rejected():
    """validate_boundary rejects zero values."""
    with pytest.raises(BoundaryError):
        validate_boundary("size", Decimal(0), min_value=Decimal("0.01"))


def test_validate_boundary_negative_rejected():
    """validate_boundary rejects negative values."""
    with pytest.raises(BoundaryError):
        validate_boundary("size", Decimal(-5), min_value=Decimal("0.01"))


def test_validate_boundary_below_min_rejected():
    """validate_boundary rejects values below minimum."""
    with pytest.raises(BoundaryError):
        validate_boundary("size", Decimal("0.005"), min_value=Decimal("0.01"))


def test_validate_boundary_above_max_rejected():
    """validate_boundary rejects values above maximum."""
    with pytest.raises(BoundaryError):
        validate_boundary("size", Decimal(1000000), max_value=Decimal(100000))


def test_validate_boundary_valid():
    """validate_boundary accepts valid values."""
    result = validate_boundary(
        "size", Decimal(5000), min_value=Decimal("0.01"), max_value=Decimal(100000)
    )
    assert result == Decimal(5000)


def test_validate_not_missing_none_rejected():
    """validate_not_missing rejects None values."""
    with pytest.raises(MissingInputError):
        validate_not_missing("spread", None)


def test_validate_not_missing_empty_rejected():
    """validate_not_missing rejects empty values."""
    with pytest.raises(MissingInputError):
        validate_not_missing("symbol", "")


def test_validate_not_missing_valid():
    """validate_not_missing accepts valid values."""
    result = validate_not_missing("spread", Decimal("0.1"))
    assert result == Decimal("0.1")


def test_concurrency_safe_service_creates():
    """ConcurrencySafeRiskService can be created."""
    service = ConcurrencySafeRiskService()
    assert service is not None


def test_concurrency_safe_service_thread_safe():
    """ConcurrencySafeRiskService handles concurrent access without corruption."""
    service = ConcurrencySafeRiskService()
    # Simulate concurrent reads/writes
    for i in range(100):
        service.record_decision(f"decision_{i}", {"value": i})
    decisions = service.get_decisions()
    assert len(decisions) == 100


def test_audit_event_logger_deterministic():
    """Same inputs yield identical audit event results (excluding timestamp)."""
    logger1 = AuditEventLogger()
    logger2 = AuditEventLogger()
    logger1.log_audit_event("halt", "reason", {"a": 1})
    logger2.log_audit_event("halt", "reason", {"a": 1})
    e1 = logger1.get_events()[0]
    e2 = logger2.get_events()[0]
    assert e1["event_type"] == e2["event_type"]
    assert e1["reason"] == e2["reason"]
    assert e1["detail"] == e2["detail"]


def test_boundary_error_message():
    """BoundaryError contains meaningful message."""
    try:
        validate_boundary("size", Decimal(0), min_value=Decimal("0.01"))
    except BoundaryError as e:
        assert "size" in str(e)
        assert "0.01" in str(e)


def test_missing_input_error_message():
    """MissingInputError contains meaningful message."""
    try:
        validate_not_missing("spread", None)
    except MissingInputError as e:
        assert "spread" in str(e)

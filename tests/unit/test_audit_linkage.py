"""RED tests for M8.3 — Append-only audit and correction linkage.

Tests define:
- AuditService: append-only audit log of events
- AuditEvent: immutable audit record with hash chain
- CorrectionLinkage: corrections linked to original events (not modifying them)
- Append-only: events cannot be modified or deleted after append
- Audit integrity: tampering detected via hash chain verification
- Correction creates a new event referencing the original event id
- Deterministic: same inputs yield identical results
- Stdlib-only, no import-time network/DB activity
"""

from __future__ import annotations

import pytest

from superbot.persistence.audit_linkage import (
    AuditCorrection,
    AuditEvent,
    AuditEventLogger,
    AuditIntegrityError,
    link_correction,
    verify_audit_chain,
)


def test_audit_event_creates():
    """AuditEvent can be created with event_type, detail, and previous hash."""
    event = AuditEvent(
        event_type="halt",
        detail={"daily_loss_pct": "4.0"},
        previous_hash="genesis",
    )
    assert event.event_type == "halt"
    assert event.detail == {"daily_loss_pct": "4.0"}
    assert event.previous_hash == "genesis"
    assert event.event_id is not None
    assert event.timestamp is not None


def test_audit_event_hash_chain():
    """AuditEvent computes its own hash from content + previous hash."""
    event = AuditEvent(event_type="start", detail={}, previous_hash="genesis")
    h1 = event.hash
    event2 = AuditEvent(event_type="halt", detail={}, previous_hash=h1)
    assert event2.previous_hash == h1
    assert event2.hash != h1


def test_audit_event_logger_creates():
    """AuditEventLogger can be created."""
    logger = AuditEventLogger()
    assert logger is not None


def test_append_audit_event_immutable():
    """append_audit_event appends events that cannot be modified."""
    logger = AuditEventLogger()
    logger.append_audit_event("halt", {"daily_loss_pct": "4.0"})
    events = logger.get_events()
    assert len(events) == 1
    assert events[0]["event_type"] == "halt"
    # Mutating the returned list should not affect stored events
    events[0]["event_type"] = "modified"
    events_after = logger.get_events()
    assert events_after[0]["event_type"] == "halt"


def test_append_audit_event_chain():
    """Each appended event links to the previous event's hash."""
    logger = AuditEventLogger()
    logger.append_audit_event("start", {})
    logger.append_audit_event("halt", {"daily_loss_pct": "4.0"})
    events = logger.get_events()
    assert (
        events[1]["previous_hash"] == events[0]["event_id"]
        or events[1]["previous_hash"] == events[0]["hash"]
    )


def test_verify_audit_chain_valid():
    """verify_audit_chain passes when chain is intact."""
    logger = AuditEventLogger()
    logger.append_audit_event("start", {})
    logger.append_audit_event("halt", {"daily_loss_pct": "4.0"})
    assert verify_audit_chain(logger.get_events()) is True


def test_verify_audit_chain_tampered():
    """verify_audit_chain fails when an event is tampered."""
    logger = AuditEventLogger()
    logger.append_audit_event("start", {})
    logger.append_audit_event("halt", {"daily_loss_pct": "4.0"})
    events = logger.get_events()
    events[0]["detail"] = {"tampered": True}
    assert verify_audit_chain(events) is False


def test_correction_linkage_creates():
    """AuditCorrection can be created linking correction to original."""
    correction = AuditCorrection(
        correction_id="corr_1",
        original_event_id="event_1",
        corrected_detail={"daily_loss_pct": "3.0"},
        reason="typo",
    )
    assert correction.original_event_id == "event_1"
    assert correction.corrected_detail == {"daily_loss_pct": "3.0"}


def test_link_correction():
    """link_correction creates a correction event linked to original."""
    logger = AuditEventLogger()
    logger.append_audit_event("halt", {"daily_loss_pct": "4.0"})
    events = logger.get_events()
    original_id = events[0]["event_id"]
    correction = link_correction(
        logger,
        original_event_id=original_id,
        corrected_detail={"daily_loss_pct": "3.0"},
        reason="typo fix",
    )
    assert correction.original_event_id == original_id
    assert correction.corrected_detail == {"daily_loss_pct": "3.0"}
    # Original event unchanged
    assert logger.get_events()[0]["detail"] == {"daily_loss_pct": "4.0"}


def test_link_correction_unknown_original_blocked():
    """link_correction raises when original event id doesn't exist."""
    logger = AuditEventLogger()
    with pytest.raises(AuditIntegrityError):
        link_correction(
            logger,
            original_event_id="nonexistent",
            corrected_detail={"daily_loss_pct": "3.0"},
            reason="typo fix",
        )


def test_correction_chain_integrity():
    """Correction events are part of the audit chain and verified."""
    logger = AuditEventLogger()
    logger.append_audit_event("halt", {"daily_loss_pct": "4.0"})
    link_correction(
        logger,
        original_event_id=logger.get_events()[0]["event_id"],
        corrected_detail={"daily_loss_pct": "3.0"},
        reason="typo fix",
    )
    assert verify_audit_chain(logger.get_events()) is True


def test_audit_linkage_deterministic():
    """Same inputs yield identical audit results."""
    logger1 = AuditEventLogger()
    logger2 = AuditEventLogger()
    logger1.append_audit_event("halt", {"daily_loss_pct": "4.0"})
    logger2.append_audit_event("halt", {"daily_loss_pct": "4.0"})
    e1 = logger1.get_events()[0]
    e2 = logger2.get_events()[0]
    assert e1["event_type"] == e2["event_type"]
    assert e1["detail"] == e2["detail"]

"""Append-only audit and correction linkage (schema.md section 8.3).

Deterministic audit service:
- Append-only audit log of risk decisions (halt, resume, block, reject, resize)
- Each event immutable with hash chain (event hash = hash(content + previous hash))
- Corrections create NEW events linked to original event id (never modify originals)
- Tampering detected via hash chain verification
- Stdlib-only; no import-time network/DB activity.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from time import time


def _sha256_hex(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


class AuditIntegrityError(Exception):
    """Raised when audit chain verification fails or original event missing."""


@dataclass(frozen=True)
class AuditEvent:
    """Immutable audit event with hash chain."""

    event_type: str
    detail: dict
    previous_hash: str
    event_id: str = field(init=False)
    timestamp: float = field(init=False)
    hash: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "event_id",
            _sha256_hex(f"{self.event_type}:{self.detail}:{self.previous_hash}:{time()}"),
        )
        object.__setattr__(self, "timestamp", time())
        object.__setattr__(self, "hash", self._compute_hash())

    def _compute_hash(self) -> str:
        return _sha256_hex(
            f"{self.event_type}:{self.detail}:{self.previous_hash}:{self.event_id}:{self.timestamp}"
        )


@dataclass(frozen=True)
class AuditCorrection:
    """Correction event linked to an original event (never modifies original)."""

    correction_id: str
    original_event_id: str
    corrected_detail: dict
    reason: str
    timestamp: float = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "timestamp", time())


class AuditEventLogger:
    """Append-only immutable audit event log with hash chain."""

    def __init__(self) -> None:
        self._events: list[AuditEvent] = []
        self._corrections: list[AuditCorrection] = []

    def append_audit_event(self, event_type: str, detail: dict) -> AuditEvent:
        """Append an immutable audit event linked to the previous event's hash."""
        previous_hash = self._events[-1].hash if self._events else "genesis"
        event = AuditEvent(
            event_type=event_type,
            detail=dict(detail),
            previous_hash=previous_hash,
        )
        self._events.append(event)
        return event

    def get_events(self) -> list[dict]:
        """Return a copy of all audit events (immutable snapshot)."""
        return [
            {
                "event_id": e.event_id,
                "event_type": e.event_type,
                "detail": dict(e.detail),
                "previous_hash": e.previous_hash,
                "hash": e.hash,
                "timestamp": e.timestamp,
            }
            for e in self._events
        ]

    def get_corrections(self) -> list[dict]:
        """Return a copy of all corrections (immutable snapshot)."""
        return [
            {
                "correction_id": c.correction_id,
                "original_event_id": c.original_event_id,
                "corrected_detail": dict(c.corrected_detail),
                "reason": c.reason,
                "timestamp": c.timestamp,
            }
            for c in self._corrections
        ]


def link_correction(
    logger: AuditEventLogger,
    original_event_id: str,
    corrected_detail: dict,
    reason: str,
) -> AuditCorrection:
    """Create a correction event linked to the original event (never modifies original).

    Args:
        logger: AuditEventLogger
        original_event_id: id of the original event being corrected
        corrected_detail: corrected detail dict
        reason: reason for the correction

    Returns AuditCorrection.

    Raises AuditIntegrityError if original event id doesn't exist.
    """
    event_ids = {e["event_id"] for e in logger.get_events()}
    if original_event_id not in event_ids:
        raise AuditIntegrityError(f"Original event {original_event_id} not found")
    correction = AuditCorrection(
        correction_id=_sha256_hex(f"corr:{original_event_id}:{time()}"),
        original_event_id=original_event_id,
        corrected_detail=dict(corrected_detail),
        reason=reason,
    )
    logger._corrections.append(correction)
    # Also append a correction event to the audit chain for integrity
    logger.append_audit_event(
        "correction",
        {
            "correction_id": correction.correction_id,
            "original_event_id": original_event_id,
            "corrected_detail": correction.corrected_detail,
            "reason": reason,
        },
    )
    return correction


def verify_audit_chain(events: list[dict]) -> bool:
    """Verify audit chain integrity: each event's previous_hash links to prior hash
    and each event's stored hash matches recomputing it from its content.

    Args:
        events: list of event dicts from get_events()

    Returns True if chain intact, False if tampered.
    """
    previous_hash = "genesis"
    for event in events:
        if event.get("previous_hash") != previous_hash:
            return False
        expected_hash = _sha256_hex(
            f"{event.get('event_type')}:{event.get('detail')}:{event.get('previous_hash')}:{event.get('event_id')}:{event.get('timestamp')}"
        )
        if event.get("hash") != expected_hash:
            return False
        previous_hash = event.get("hash", "")
    return True


def append_audit_event(
    logger: AuditEventLogger,
    event_type: str,
    detail: dict,
) -> AuditEvent:
    """Append an audit event (convenience function)."""
    return logger.append_audit_event(event_type, detail)


# CorrectionLinkage is an alias for link_correction, kept for API compatibility.
CorrectionLinkage = link_correction

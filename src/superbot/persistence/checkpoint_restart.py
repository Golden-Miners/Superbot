"""Checkpoint/crash restart reconciliation for jobs/signals/positions (schema.md section 8.5).

Deterministic checkpoint/restart service:
- Checkpoints recorded with sequence numbers and hash chain
- Crash recovery reconciles state from last committed checkpoint
- Job reconciliation: in-progress -> pending
- Signal reconciliation: sent -> pending
- Position reconciliation: open -> closed
- Stdlib-only; no import-time network/DB activity.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from time import time


def _sha256_hex(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CheckpointRecord:
    """Immutable checkpoint record."""

    checkpoint_id: str
    checkpoint_type: str  # "job", "signal", "position"
    payload: dict
    sequence: int
    previous_hash: str
    event_id: str = field(init=False)
    timestamp: float = field(init=False)
    hash: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "event_id",
            _sha256_hex(
                f"{self.checkpoint_type}:{self.payload}:{self.previous_hash}:{self.sequence}"
            ),
        )
        object.__setattr__(self, "timestamp", time())
        object.__setattr__(self, "hash", self._compute_hash())

    def _compute_hash(self) -> str:
        return _sha256_hex(
            f"{self.checkpoint_type}:{self.payload}:{self.previous_hash}:{self.sequence}:{self.event_id}"
        )


@dataclass(frozen=True)
class CrashReconciliation:
    """Result of crash reconciliation."""

    job_reconciliations: dict[str, str]
    signal_reconciliations: dict[str, str]
    position_reconciliations: dict[str, str]


@dataclass(frozen=True)
class JobReconciliation:
    job_id: str
    before: str
    after: str


@dataclass(frozen=True)
class SignalReconciliation:
    signal_id: str
    before: str
    after: str


@dataclass(frozen=True)
class PositionReconciliation:
    position_id: str
    before: str
    after: str


class CheckpointService:
    """Tracks checkpoints with sequence numbers and hash chain."""

    def __init__(self) -> None:
        self._checkpoints: dict[str, CheckpointRecord] = {}
        self._by_sequence: dict[int, str] = {}

    def register_checkpoint(self, record: CheckpointRecord) -> CheckpointRecord:
        """Register a checkpoint."""
        self._checkpoints[record.checkpoint_id] = record
        self._by_sequence[record.sequence] = record.checkpoint_id
        return record

    def get_checkpoint(self, checkpoint_id: str) -> CheckpointRecord | None:
        """Get a checkpoint by id."""
        return self._checkpoints.get(checkpoint_id)

    def get_checkpoints(self) -> list[dict]:
        """Return all checkpoints sorted by sequence, as dicts."""
        return [
            {
                "checkpoint_id": c.checkpoint_id,
                "checkpoint_type": c.checkpoint_type,
                "payload": dict(c.payload),
                "sequence": c.sequence,
                "previous_hash": c.previous_hash,
                "event_id": c.event_id,
                "timestamp": c.timestamp,
                "hash": c.hash,
            }
            for c in sorted(self._checkpoints.values(), key=lambda c: c.sequence)
        ]


def checkpoint(
    service: CheckpointService,
    checkpoint_id: str,
    checkpoint_type: str,
    payload: dict,
    sequence: int,
    previous_hash: str,
) -> CheckpointRecord:
    """Register a checkpoint (convenience function)."""
    return service.register_checkpoint(
        CheckpointRecord(
            checkpoint_id=checkpoint_id,
            checkpoint_type=checkpoint_type,
            payload=dict(payload),
            sequence=sequence,
            previous_hash=previous_hash,
        )
    )


def reconcile_crash(service: CheckpointService) -> CrashReconciliation:
    """Reconcile crash state from checkpoints.

    Jobs: in_progress -> pending
    Signals: sent -> pending
    Positions: open -> closed
    Other statuses unchanged.
    """
    job_reconciliations: dict[str, str] = {}
    signal_reconciliations: dict[str, str] = {}
    position_reconciliations: dict[str, str] = {}

    for c in service._checkpoints.values():
        payload = dict(c.payload)
        if c.checkpoint_type == "job":
            job_id = payload.get("job_id", c.checkpoint_id)
            before = payload.get("status", "unknown")
            after = "pending" if before == "in_progress" else before
            job_reconciliations[job_id] = after
        elif c.checkpoint_type == "signal":
            signal_id = payload.get("signal_id", c.checkpoint_id)
            before = payload.get("status", "unknown")
            after = "pending" if before == "sent" else before
            signal_reconciliations[signal_id] = after
        elif c.checkpoint_type == "position":
            position_id = payload.get("position_id", c.checkpoint_id)
            before = payload.get("status", "unknown")
            after = "closed" if before == "open" else before
            position_reconciliations[position_id] = after

    return CrashReconciliation(
        job_reconciliations=job_reconciliations,
        signal_reconciliations=signal_reconciliations,
        position_reconciliations=position_reconciliations,
    )


def verify_chain(events: list[dict]) -> bool:
    """Verify audit chain integrity.

    Args:
        events: list of checkpoint dicts from get_checkpoints()

    Returns True if chain intact, False if tampered.
    """
    previous_hash = "genesis"
    for event in events:
        if event.get("previous_hash") != previous_hash:
            return False
        expected_hash = _sha256_hex(
            f"{event.get('checkpoint_type')}:{event.get('payload')}:{event.get('previous_hash')}:{event.get('sequence')}:{event.get('event_id')}"
        )
        if event.get("hash") != expected_hash:
            return False
        previous_hash = event.get("hash", "")
    return True


# register_checkpoint is an alias for checkpoint, kept for API compatibility.
register_checkpoint = checkpoint

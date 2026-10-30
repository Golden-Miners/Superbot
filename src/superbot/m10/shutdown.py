"""M10.3 — Graceful shutdown/checkpoint, restart checks and resume guard.

Deterministic shutdown/resume service:
- ShutdownState: RUNNING, SHUTTING_DOWN, SHUTDOWN, RESUMING
- ShutdownManager: initiates graceful shutdown, drains in-flight jobs, blocks new work
- CheckpointRecord: saved state at a point in time (sequence, timestamp, payload hash)
- CheckpointService: create/restore checkpoints, hash chain verification
- RestartCheck: verifies system consistency before restart
- ResumeGuard: blocks resume if state is inconsistent or unsafe
- Stdlib-only; no import-time network/database activity.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum


class ShutdownState(str, Enum):
    """System lifecycle states."""

    RUNNING = "running"
    SHUTTING_DOWN = "shutting_down"
    SHUTDOWN = "shutdown"
    RESUMING = "resuming"


@dataclass(frozen=True)
class ShutdownResult:
    """Result of a shutdown/resume operation."""

    accepted: bool
    jobs_drained: int = 0
    state: str = ""
    reason: str | None = None


@dataclass(frozen=True)
class RestartCheckResult:
    """Result of a restart consistency check."""

    safe_to_restart: bool
    reasons: list[str]


@dataclass(frozen=True)
class ResumeResult:
    """Result of a resume evaluation."""

    safe: bool
    reasons: list[str]


@dataclass(frozen=True)
class CollectorResult:
    """Result of a collection/registration operation."""

    recorded: bool
    resource_id: str
    metric_name: str
    registered: bool = False


@dataclass(frozen=True)
class CheckpointRecord:
    """A saved checkpoint at a point in time."""

    sequence: int
    timestamp: datetime
    payload_hash: str
    previous_hash: str

    @property
    def hash_value(self) -> str:
        """Deterministic hash of this record's content."""
        content = (
            f"{self.sequence}|{self.timestamp.isoformat()}|{self.payload_hash}|{self.previous_hash}"
        )
        return hashlib.sha256(content.encode("utf-8")).hexdigest()


class ShutdownManager:
    """Manages graceful shutdown: transitions states, drains jobs, blocks new work."""

    def __init__(self) -> None:
        self.state: ShutdownState = ShutdownState.RUNNING
        self._in_flight: int = 0
        self._new_work_blocked: bool = False

    def initiate_shutdown(self) -> ShutdownResult:
        """Transition RUNNING -> SHUTTING_DOWN."""
        if self.state != ShutdownState.RUNNING:
            return ShutdownResult(
                accepted=False,
                jobs_drained=0,
                state=self.state.value,
                reason="already_shutting_down_or_shutdown",
            )
        self.state = ShutdownState.SHUTTING_DOWN
        self._new_work_blocked = True
        return ShutdownResult(accepted=True, jobs_drained=0, state=self.state.value)

    def submit_work(self, job_id: str) -> ShutdownResult:
        """Submit new work; rejected once shutting down."""
        if self._new_work_blocked:
            return ShutdownResult(
                accepted=False,
                jobs_drained=0,
                state=self.state.value,
                reason="shutting_down",
            )
        self._in_flight += 1
        return ShutdownResult(accepted=True, jobs_drained=0, state=self.state.value)

    def drain_jobs(self) -> ShutdownResult:
        """Wait for in-flight jobs to complete, then transition to SHUTDOWN."""
        if self.state != ShutdownState.SHUTTING_DOWN:
            return ShutdownResult(
                accepted=False,
                jobs_drained=self._in_flight,
                state=self.state.value,
                reason="not_shutting_down",
            )
        drained = self._in_flight
        self._in_flight = 0
        self.state = ShutdownState.SHUTDOWN
        return ShutdownResult(accepted=True, jobs_drained=drained, state=self.state.value)

    def resume_system(self) -> ShutdownResult:
        """Transition SHUTDOWN -> RESUMING -> RUNNING."""
        if self.state != ShutdownState.SHUTDOWN:
            return ShutdownResult(
                accepted=False,
                jobs_drained=0,
                state=self.state.value,
                reason="not_shutdown",
            )
        self.state = ShutdownState.RESUMING
        self.state = ShutdownState.RUNNING
        self._new_work_blocked = False
        return ShutdownResult(accepted=True, jobs_drained=0, state=self.state.value)


class CheckpointRecordStore:
    """In-memory store of checkpoint records with hash chain."""

    def __init__(self) -> None:
        self._records: list[CheckpointRecord] = []
        self._sequence_counter = 0

    def add(self, record: CheckpointRecord) -> None:
        """Append a record to the chain."""
        self._records.append(record)
        self._sequence_counter = max(self._sequence_counter, record.sequence)

    def get_latest(self) -> CheckpointRecord | None:
        """Return the most recent record, or None."""
        return self._records[-1] if self._records else None

    def verify_chain(self) -> bool:
        """Verify the hash chain is unbroken."""
        for i in range(1, len(self._records)):
            if self._records[i].previous_hash != self._records[i - 1].hash_value:
                return False
        return True

    def __len__(self) -> int:
        return len(self._records)


class CheckpointService:
    """Service for creating and restoring checkpoints with hash-chain integrity."""

    def __init__(self) -> None:
        self._store = CheckpointRecordStore()

    def register_checkpoint(
        self,
        sequence: int,
        payload: dict,
        previous_hash: str,
    ) -> CheckpointRecord:
        """Register a new checkpoint record."""
        payload_json = json.dumps(payload, sort_keys=True)
        payload_hash = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
        record = CheckpointRecord(
            sequence=sequence,
            timestamp=datetime.now(UTC),
            payload_hash=payload_hash,
            previous_hash=previous_hash,
        )
        self._store.add(record)
        return record

    def restore_checkpoint(self) -> CheckpointRecord | None:
        """Restore the latest checkpoint record."""
        return self._store.get_latest()

    def verify_chain(self) -> bool:
        """Verify the checkpoint hash chain is unbroken."""
        return self._store.verify_chain()


class RestartCheck:
    """Verifies system consistency before restart."""

    def perform(
        self,
        checkpoint_valid: bool,
        pending_jobs: int,
    ) -> RestartCheckResult:
        """Return whether it is safe to restart."""
        reasons: list[str] = []
        if not checkpoint_valid:
            reasons.append("checkpoint chain is corrupt or missing")
        if pending_jobs > 0:
            reasons.append(f"{pending_jobs} pending jobs not yet drained")
        return RestartCheckResult(safe_to_restart=len(reasons) == 0, reasons=reasons)


class ResumeGuard:
    """Guards resume: blocks unless system is SHUTDOWN and restart check passes."""

    def evaluate(
        self,
        state: ShutdownState,
        restart_ok: bool,
    ) -> ResumeResult:
        """Return whether it is safe to resume."""
        reasons: list[str] = []
        if state != ShutdownState.SHUTDOWN:
            reasons.append(f"system is {state.value}, not shutdown")
        if not restart_ok:
            reasons.append("restart check failed")
        return ResumeResult(safe=len(reasons) == 0, reasons=reasons)


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------


def create_shutdown_manager() -> ShutdownManager:
    """Create a ShutdownManager."""
    return ShutdownManager()


def shutdown_system() -> ShutdownResult:
    """Convenience: initiate shutdown on a fresh manager."""
    return create_shutdown_manager().initiate_shutdown()


def initiate_shutdown() -> ShutdownResult:
    """Convenience alias for shutdown_system."""
    return shutdown_system()


def drain_jobs(manager: ShutdownManager) -> ShutdownResult:
    """Convenience: drain jobs on a manager."""
    return manager.drain_jobs()


def register_checkpoint(
    service: CheckpointService,
    sequence: int,
    payload: dict,
    previous_hash: str,
) -> CollectorResult:
    """Convenience: register a checkpoint."""
    service.register_checkpoint(sequence, payload, previous_hash)
    return CollectorResult(recorded=True, resource_id="", metric_name="", registered=True)


# Alias for brevity.
checkpoint = register_checkpoint


def restore_checkpoint(service: CheckpointService) -> CheckpointRecord | None:
    """Convenience: restore the latest checkpoint."""
    return service.restore_checkpoint()


def perform_restart_check(checkpoint_valid: bool, pending_jobs: int) -> RestartCheckResult:
    """Convenience: perform a restart check."""
    return RestartCheck().perform(checkpoint_valid, pending_jobs)


def verify_chain(service: CheckpointService) -> bool:
    """Convenience: verify a checkpoint service's hash chain."""
    return service.verify_chain()


def is_safe_to_resume(state: ShutdownState, restart_ok: bool) -> ResumeResult:
    """Convenience: evaluate resume safety."""
    return ResumeGuard().evaluate(state, restart_ok)


def resume_system(manager: ShutdownManager) -> ShutdownResult:
    """Convenience: resume a manager."""
    return manager.resume_system()

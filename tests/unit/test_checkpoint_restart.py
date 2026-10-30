"""RED tests for M8.5 — Checkpoint/crash restart reconciliation for jobs/signals/positions.

Tests define:
- CheckpointService: records job/signal/position checkpoints with sequence numbers
- CheckpointRecord: immutable checkpoint with id, type, payload, sequence, previous hash
- Crash recovery: reconcile state from last committed checkpoint
- Job reconciliation: reconcile job state after crash (in-progress -> pending)
- Signal reconciliation: reconcile signal state (sent -> pending)
- Position reconciliation: reconcile position state (open -> closed)
- Append-only checkpoint log with hash chain for tamper detection
- Stdlib-only, no import-time network/DB activity
"""

from __future__ import annotations

from superbot.persistence.checkpoint_restart import (
    CheckpointRecord,
    CheckpointService,
    CrashReconciliation,
    JobReconciliation,
    PositionReconciliation,
    SignalReconciliation,
    reconcile_crash,
    verify_chain,
)


def test_checkpoint_record_creates():
    """CheckpointRecord can be created."""
    record = CheckpointRecord(
        checkpoint_id="ck_1",
        checkpoint_type="job",
        payload={"job_id": "j1", "status": "running"},
        sequence=1,
        previous_hash="genesis",
    )
    assert record.checkpoint_id == "ck_1"
    assert record.checkpoint_type == "job"
    assert record.payload["status"] == "running"
    assert record.sequence == 1
    assert record.previous_hash == "genesis"


def test_checkpoint_service_creates():
    """CheckpointService can be created."""
    service = CheckpointService()
    assert service is not None


def test_register_checkpoint():
    """register_checkpoint records a checkpoint."""
    service = CheckpointService()
    record = CheckpointRecord(
        checkpoint_id="ck_1",
        checkpoint_type="job",
        payload={"job_id": "j1"},
        sequence=1,
        previous_hash="genesis",
    )
    service.register_checkpoint(record)
    assert service.get_checkpoint("ck_1") is not None


def test_checkpoint_hash_chain():
    """Each checkpoint's hash links to previous hash."""
    service = CheckpointService()
    r1 = service.register_checkpoint(
        CheckpointRecord(
            checkpoint_id="ck_1",
            checkpoint_type="job",
            payload={"job_id": "j1"},
            sequence=1,
            previous_hash="genesis",
        )
    )
    r2 = service.register_checkpoint(
        CheckpointRecord(
            checkpoint_id="ck_2",
            checkpoint_type="signal",
            payload={"signal_id": "s1"},
            sequence=2,
            previous_hash=r1.hash,
        )
    )
    assert r2.previous_hash == r1.hash
    assert r2.hash != r1.hash


def test_crash_reconciliation_jobs():
    """crash_reconciliation reconciles in-progress jobs to pending."""
    service = CheckpointService()
    service.register_checkpoint(
        CheckpointRecord(
            checkpoint_id="ck_1",
            checkpoint_type="job",
            payload={"job_id": "j1", "status": "in_progress"},
            sequence=1,
            previous_hash="genesis",
        )
    )
    result = reconcile_crash(service)
    assert result.job_reconciliations["j1"] == "pending"


def test_crash_reconciliation_signals():
    """crash_reconciliation reconciles sent signals to pending."""
    service = CheckpointService()
    service.register_checkpoint(
        CheckpointRecord(
            checkpoint_id="ck_1",
            checkpoint_type="signal",
            payload={"signal_id": "s1", "status": "sent"},
            sequence=1,
            previous_hash="genesis",
        )
    )
    result = reconcile_crash(service)
    assert result.signal_reconciliations["s1"] == "pending"


def test_crash_reconciliation_positions():
    """crash_reconciliation reconciles open positions to closed."""
    service = CheckpointService()
    service.register_checkpoint(
        CheckpointRecord(
            checkpoint_id="ck_1",
            checkpoint_type="position",
            payload={"position_id": "p1", "status": "open"},
            sequence=1,
            previous_hash="genesis",
        )
    )
    result = reconcile_crash(service)
    assert result.position_reconciliations["p1"] == "closed"


def test_crash_reconciliation_completed():
    """crash_reconciliation leaves completed jobs unchanged."""
    service = CheckpointService()
    service.register_checkpoint(
        CheckpointRecord(
            checkpoint_id="ck_1",
            checkpoint_type="job",
            payload={"job_id": "j1", "status": "completed"},
            sequence=1,
            previous_hash="genesis",
        )
    )
    result = reconcile_crash(service)
    assert result.job_reconciliations["j1"] == "completed"


def test_checkpoint_service_deterministic():
    """Same inputs yield identical checkpoint results."""
    s1 = CheckpointService()
    s2 = CheckpointService()
    r1 = s1.register_checkpoint(
        CheckpointRecord(
            checkpoint_id="ck_1",
            checkpoint_type="job",
            payload={"job_id": "j1"},
            sequence=1,
            previous_hash="genesis",
        )
    )
    r2 = s2.register_checkpoint(
        CheckpointRecord(
            checkpoint_id="ck_1",
            checkpoint_type="job",
            payload={"job_id": "j1"},
            sequence=1,
            previous_hash="genesis",
        )
    )
    assert r1.hash == r2.hash


def test_verify_chain_valid():
    """verify_chain passes when chain is intact."""
    service = CheckpointService()
    service.register_checkpoint(
        CheckpointRecord(
            checkpoint_id="ck_1",
            checkpoint_type="job",
            payload={"job_id": "j1"},
            sequence=1,
            previous_hash="genesis",
        )
    )
    service.register_checkpoint(
        CheckpointRecord(
            checkpoint_id="ck_2",
            checkpoint_type="signal",
            payload={"signal_id": "s1"},
            sequence=2,
            previous_hash=service.get_checkpoint("ck_1").hash,
        )
    )
    assert verify_chain(service.get_checkpoints()) is True


def test_verify_chain_tampered():
    """verify_chain fails when an event is tampered."""
    service = CheckpointService()
    service.register_checkpoint(
        CheckpointRecord(
            checkpoint_id="ck_1",
            checkpoint_type="job",
            payload={"job_id": "j1"},
            sequence=1,
            previous_hash="genesis",
        )
    )
    service.register_checkpoint(
        CheckpointRecord(
            checkpoint_id="ck_2",
            checkpoint_type="signal",
            payload={"signal_id": "s1"},
            sequence=2,
            previous_hash=service.get_checkpoint("ck_1").hash,
        )
    )
    events = service.get_checkpoints()
    events[0]["payload"] = {"job_id": "tampered"}
    assert verify_chain(events) is False


def test_job_reconciliation_creates():
    """JobReconciliation can be created."""
    jr = JobReconciliation(job_id="j1", before="in_progress", after="pending")
    assert jr.job_id == "j1"
    assert jr.before == "in_progress"
    assert jr.after == "pending"


def test_signal_reconciliation_creates():
    """SignalReconciliation can be created."""
    sr = SignalReconciliation(signal_id="s1", before="sent", after="pending")
    assert sr.signal_id == "s1"
    assert sr.before == "sent"
    assert sr.after == "pending"


def test_position_reconciliation_creates():
    """PositionReconciliation can be created."""
    pr = PositionReconciliation(position_id="p1", before="open", after="closed")
    assert pr.position_id == "p1"
    assert pr.before == "open"
    assert pr.after == "closed"


def test_crash_reconciliation_creates():
    """CrashReconciliation can be created."""
    cr = CrashReconciliation(
        job_reconciliations={"j1": "pending"},
        signal_reconciliations={"s1": "pending"},
        position_reconciliations={"p1": "closed"},
    )
    assert cr.job_reconciliations["j1"] == "pending"

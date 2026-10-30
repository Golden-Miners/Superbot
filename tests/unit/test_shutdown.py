"""RED tests for M10.3 — Graceful shutdown/checkpoint, restart checks and resume guard.

Tests define:
- ShutdownState: RUNNING, SHUTTING_DOWN, SHUTDOWN, RESUMING
- ShutdownManager: initiates graceful shutdown, drains in-flight jobs, blocks new work
- CheckpointRecord: saved state at a point in time (sequence, timestamp, payload hash)
- CheckpointService: create/checkpoint restore, hash chain verification
- RestartCheck: verifies system consistency before restart (checkpoint integrity, pending jobs)
- ResumeGuard: blocks resume if state is inconsistent or unsafe
- ShutdownResult: accepted, jobs_drained, state, reason
- Deterministic: same inputs -> identical results
- Stdlib-only, no import-time network/database activity
"""

from __future__ import annotations

from datetime import datetime

from superbot.m10.shutdown import (
    CheckpointRecord,
    CheckpointService,
    RestartCheck,
    ResumeGuard,
    ShutdownManager,
    ShutdownResult,
    ShutdownState,
    create_shutdown_manager,
    drain_jobs,
    is_safe_to_resume,
    perform_restart_check,
    register_checkpoint,
    restore_checkpoint,
    resume_system,
    shutdown_system,
)


def test_shutdown_state_enum():
    """ShutdownState defines all lifecycle states."""
    assert ShutdownState.RUNNING.value == "running"
    assert ShutdownState.SHUTTING_DOWN.value == "shutting_down"
    assert ShutdownState.SHUTDOWN.value == "shutdown"
    assert ShutdownState.RESUMING.value == "resuming"


def test_shutdown_manager_creates():
    """ShutdownManager can be created."""
    manager = ShutdownManager()
    assert manager.state == ShutdownState.RUNNING


def test_initiate_shutdown():
    """initiate_shutdown transitions RUNNING -> SHUTTING_DOWN."""
    manager = ShutdownManager()
    result = manager.initiate_shutdown()
    assert result.accepted is True
    assert manager.state == ShutdownState.SHUTTING_DOWN


def test_shutdown_blocks_new_work():
    """Once shutting down, new work is rejected."""
    manager = ShutdownManager()
    manager.initiate_shutdown()
    result = manager.submit_work("job_1")
    assert result.accepted is False
    assert result.reason == "shutting_down"


def test_drain_jobs():
    """drain_jobs waits for in-flight jobs to complete then transitions to SHUTDOWN."""
    manager = ShutdownManager()
    manager.initiate_shutdown()
    result = manager.drain_jobs()
    assert result.jobs_drained >= 0
    assert manager.state == ShutdownState.SHUTDOWN


def test_shutdown_result_creates():
    """ShutdownResult stores accepted, jobs_drained, state, reason."""
    result = ShutdownResult(accepted=True, jobs_drained=3, state="shutdown", reason=None)
    assert result.accepted is True
    assert result.jobs_drained == 3
    assert result.state == "shutdown"


def test_checkpoint_record_creates():
    """CheckpointRecord stores sequence, timestamp, payload_hash, previous_hash."""
    record = CheckpointRecord(
        sequence=1,
        timestamp=datetime(2026, 10, 28, 9, 0, 0),
        payload_hash="abc123",
        previous_hash="genesis",
    )
    assert record.sequence == 1
    assert record.payload_hash == "abc123"
    assert record.previous_hash == "genesis"


def test_checkpoint_service_creates():
    """CheckpointService can be created."""
    service = CheckpointService()
    assert service is not None


def test_register_and_restore_checkpoint():
    """register_checkpoint saves state; restore_checkpoint retrieves latest."""
    service = CheckpointService()
    record = service.register_checkpoint(
        sequence=1,
        payload={"jobs": 5, "positions": 2},
        previous_hash="genesis",
    )
    assert record.sequence == 1
    restored = service.restore_checkpoint()
    assert restored is not None
    assert restored.sequence == 1


def test_checkpoint_hash_chain():
    """Each checkpoint's previous_hash links to the prior record's hash."""
    service = CheckpointService()
    r1 = service.register_checkpoint(sequence=1, payload={"a": 1}, previous_hash="genesis")
    r2 = service.register_checkpoint(sequence=2, payload={"b": 2}, previous_hash=r1.hash_value)
    assert r2.previous_hash == r1.hash_value


def test_verify_chain_valid():
    """verify_chain returns True for an unbroken hash chain."""
    service = CheckpointService()
    r1 = service.register_checkpoint(sequence=1, payload={"a": 1}, previous_hash="genesis")
    service.register_checkpoint(sequence=2, payload={"b": 2}, previous_hash=r1.hash_value)
    assert service.verify_chain() is True


def test_verify_chain_tampered():
    """verify_chain returns False if a record's hash is tampered."""
    service = CheckpointService()
    service.register_checkpoint(sequence=1, payload={"a": 1}, previous_hash="genesis")
    service.register_checkpoint(sequence=2, payload={"b": 2}, previous_hash="wrong_hash")
    assert service.verify_chain() is False


def test_restart_check_creates():
    """RestartCheck can be created."""
    check = RestartCheck()
    assert check is not None


def test_perform_restart_check_pass():
    """perform_restart_check passes when checkpoint chain valid and no pending jobs."""
    check = RestartCheck()
    result = check.perform(checkpoint_valid=True, pending_jobs=0)
    assert result.safe_to_restart is True
    assert result.reasons == []


def test_perform_restart_check_fail_corrupt():
    """perform_restart_check fails when checkpoint chain is corrupt."""
    check = RestartCheck()
    result = check.perform(checkpoint_valid=False, pending_jobs=0)
    assert result.safe_to_restart is False
    assert any("checkpoint" in r.lower() for r in result.reasons)


def test_perform_restart_check_fail_pending_jobs():
    """perform_restart_check fails when pending jobs exist."""
    check = RestartCheck()
    result = check.perform(checkpoint_valid=True, pending_jobs=3)
    assert result.safe_to_restart is False
    assert any("pending" in r.lower() for r in result.reasons)


def test_resume_guard_creates():
    """ResumeGuard can be created."""
    guard = ResumeGuard()
    assert guard is not None


def test_is_safe_to_resume_true():
    """is_safe_to_resume returns True when system is SHUTDOWN and restart check passes."""
    guard = ResumeGuard()
    result = guard.evaluate(state=ShutdownState.SHUTDOWN, restart_ok=True)
    assert result.safe is True


def test_is_safe_to_resume_false_running():
    """is_safe_to_resume returns False when system is RUNNING (not shut down)."""
    guard = ResumeGuard()
    result = guard.evaluate(state=ShutdownState.RUNNING, restart_ok=True)
    assert result.safe is False


def test_is_safe_to_resume_false_restart_not_ok():
    """is_safe_to_resume returns False when restart check fails."""
    guard = ResumeGuard()
    result = guard.evaluate(state=ShutdownState.SHUTDOWN, restart_ok=False)
    assert result.safe is False


def test_resume_system():
    """resume_system transitions SHUTDOWN -> RESUMING -> RUNNING."""
    manager = ShutdownManager()
    manager.initiate_shutdown()
    manager.drain_jobs()
    result = manager.resume_system()
    assert result.accepted is True
    assert manager.state == ShutdownState.RUNNING


def test_resume_system_blocks_if_not_shutdown():
    """resume_system rejects when not in SHUTDOWN state."""
    manager = ShutdownManager()
    result = manager.resume_system()
    assert result.accepted is False
    assert result.reason == "not_shutdown"


def test_shutdown_system_function():
    """shutdown_system convenience function works."""
    result = shutdown_system()
    assert result.accepted is True


def test_drain_jobs_function():
    """drain_jobs convenience function works."""
    manager = ShutdownManager()
    manager.initiate_shutdown()
    result = drain_jobs(manager)
    assert result.jobs_drained >= 0


def test_register_checkpoint_function():
    """register_checkpoint convenience function works."""
    service = CheckpointService()
    result = register_checkpoint(service, sequence=1, payload={"x": 1}, previous_hash="genesis")
    assert result.registered is True


def test_restore_checkpoint_function():
    """restore_checkpoint convenience function works."""
    service = CheckpointService()
    service.register_checkpoint(sequence=1, payload={"x": 1}, previous_hash="genesis")
    result = restore_checkpoint(service)
    assert result is not None
    assert result.sequence == 1


def test_perform_restart_check_function():
    """perform_restart_check convenience function works."""
    result = perform_restart_check(checkpoint_valid=True, pending_jobs=0)
    assert result.safe_to_restart is True


def test_is_safe_to_resume_function():
    """is_safe_to_resume convenience function works."""
    result = is_safe_to_resume(ShutdownState.SHUTDOWN, True)
    assert result.safe is True


def test_resume_system_function():
    """resume_system convenience function works."""
    manager = ShutdownManager()
    manager.initiate_shutdown()
    manager.drain_jobs()
    result = resume_system(manager)
    assert result.accepted is True


def test_create_shutdown_manager_function():
    """create_shutdown_manager convenience function works."""
    manager = create_shutdown_manager()
    assert manager.state == ShutdownState.RUNNING


def test_shutdown_deterministic():
    """Same inputs yield identical shutdown results."""
    m1 = ShutdownManager()
    m2 = ShutdownManager()
    r1 = m1.initiate_shutdown()
    r2 = m2.initiate_shutdown()
    assert r1.accepted == r2.accepted
    assert m1.state == m2.state


def test_checkpoint_deterministic():
    """Same inputs yield identical checkpoint records."""
    s1 = CheckpointService()
    s2 = CheckpointService()
    r1 = s1.register_checkpoint(sequence=1, payload={"a": 1}, previous_hash="genesis")
    r2 = s2.register_checkpoint(sequence=1, payload={"a": 1}, previous_hash="genesis")
    assert r1.sequence == r2.sequence
    assert r1.payload_hash == r2.payload_hash

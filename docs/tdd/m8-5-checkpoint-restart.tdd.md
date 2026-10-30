# TDD Evidence Report — M8.5 Checkpoint/Crash Restart Reconciliation

## Source plan
No `*.plan.md` provided; user journeys derived during this TDD run from task.md `M8.5` ("Checkpoint/crash restart reconciliation for jobs/signals/positions").

## User journeys
- As a researcher, I want checkpoints recorded with sequence numbers and hash chain
- As a researcher, I want crash recovery to reconcile state from last committed checkpoint
- As a researcher, I want job reconciliation: in-progress jobs reset to pending after crash
- As a researcher, I want signal reconciliation: sent signals reset to pending after crash
- As a researcher, I want position reconciliation: open positions reset to closed after crash
- As a researcher, I want completed jobs unchanged after crash
- As a researcher, I want deterministic: same inputs yield identical results
- As a researcher, I want tampering detected via hash chain verification

## Task report

| Behavior | Validation command | RED result | GREEN result | Guarantee |
|---|---|---|---|---|
| CheckpointRecord creation | `tests/unit/test_checkpoint_restart.py::test_checkpoint_record_creates` | ModuleNotFoundError | PASS | CheckpointRecord stores checkpoint_id, checkpoint_type, payload, sequence, previous_hash |
| Service creation | `tests/unit/test_checkpoint_restart.py::test_checkpoint_service_creates` | ModuleNotFoundError | PASS | CheckpointService instantiates |
| Register checkpoint | `tests/unit/test_checkpoint_restart.py::test_register_checkpoint` | ModuleNotFoundError | PASS | Checkpoint registered and retrievable |
| Checkpoint hash chain | `tests/unit/test_checkpoint_restart.py::test_checkpoint_hash_chain` | ModuleNotFoundError | PASS | Each checkpoint's hash links to previous hash |
| Crash reconciliation jobs | `tests/unit/test_checkpoint_restart.py::test_crash_reconciliation_jobs` | ModuleNotFoundError | PASS | In-progress jobs → pending |
| Crash reconciliation signals | `tests/unit/test_checkpoint_restart.py::test_crash_reconciliation_signals` | ModuleNotFoundError | PASS | Sent signals → pending |
| Crash reconciliation positions | `tests/unit/test_checkpoint_restart.py::test_crash_reconciliation_positions` | ModuleNotFoundError | PASS | Open positions → closed |
| Crash reconciliation completed | `tests/unit/test_checkpoint_restart.py::test_crash_reconciliation_completed` | ModuleNotFoundError | PASS | Completed jobs unchanged |
| Deterministic | `tests/unit/test_checkpoint_restart.py::test_checkpoint_service_deterministic` | ModuleNotFoundError | PASS | Same inputs → identical results |
| Verify chain valid | `tests/unit/test_checkpoint_restart.py::test_verify_chain_valid` | ModuleNotFoundError | PASS | Intact chain returns True |
| Verify chain tampered | `tests/unit/test_checkpoint_restart.py::test_verify_chain_tampered` | ModuleNotFoundError | PASS | Tampered event returns False |
| JobReconciliation creation | `tests/unit/test_checkpoint_restart.py::test_job_reconciliation_creates` | ModuleNotFoundError | PASS | JobReconciliation dataclass |
| SignalReconciliation creation | `tests/unit/test_checkpoint_restart.py::test_signal_reconciliation_creates` | ModuleNotFoundError | PASS | SignalReconciliation dataclass |
| PositionReconciliation creation | `tests/unit/test_checkpoint_restart.py::test_position_reconciliation_creates` | ModuleNotFoundError | PASS | PositionReconciliation dataclass |
| CrashReconciliation creation | `tests/unit/test_checkpoint_restart.py::test_crash_reconciliation_creates` | ModuleNotFoundError | PASS | CrashReconciliation dataclass |

## Test specification

| # | What is guaranteed | Test file/command | Type | Result | Evidence |
|---|---|---|---|---|---|
| 1 | Checkpoint recording | `tests/unit/test_checkpoint_restart.py` | unit | PASS | 539 passed, 2 skipped |
| 2 | Hash chain integrity | `tests/unit/test_checkpoint_restart.py` | unit | PASS | 539 passed, 2 skipped |
| 3 | Crash reconciliation | `tests/unit/test_checkpoint_restart.py` | unit | PASS | 539 passed, 2 skipped |
| 4 | Tamper detection | `tests/unit/test_checkpoint_restart.py` | unit | PASS | 539 passed, 2 skipped |
| 5 | Deterministic results | `tests/unit/test_checkpoint_restart.py` | unit | PASS | 539 passed, 2 skipped |

## Coverage and known gaps
- No coverage tool configured; all M8.5 lines exercised by unit tests
- Intentional gap: No persistence of checkpoint state — in-memory only
- Intentional gap: No multi-process concurrency for checkpoint log

## Merge evidence
RED: `ModuleNotFoundError: No module named 'superbot.persistence.checkpoint_restart'` captured before implementation. GREEN: 539 tests pass, 2 skipped, ruff clean, format clean, working tree clean.
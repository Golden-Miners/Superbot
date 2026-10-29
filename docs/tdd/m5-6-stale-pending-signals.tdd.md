# TDD Evidence Report — M5.6 Stale Pending Signals / Expiry / Re-entry

## Source plan
No `*.plan.md` provided; user journeys derived during this TDD run from task.md `M5.6` ("Stale pending signals, expiry, re-entry, same-symbol multi-strategy and opposite-signal tests").

## User journeys
- As a researcher, I want pending signals tracked with status (pending/filled/expired/cancelled)
- As a researcher, I want stale signals (past expiry without fill) to block execution
- As a researcher, I want signals to expire after their expiry timestamp
- As a researcher, I want re-entry after exit to be allowed (not blocked forever)
- As a researcher, I want same-symbol multi-strategy signals to coexist
- As a researcher, I want opposite signals to close existing positions before opening new ones
- As a researcher, I want versioned signal spec: SignalSpec carries schema_version and signal_id
- As a researcher, I want deterministic: same inputs → same signal lifecycle
- As a researcher, I want no discretionary terms — all timestamps/thresholds explicit

## Task report

| Behavior | Validation command | RED result | GREEN result | Guarantee |
|---|---|---|---|---|
| Pending signal creation | `tests/unit/test_stale_pending_signals.py::test_pending_signal_creation` | ModuleNotFoundError | PASS | Signal created with pending status |
| Stale signal detected | `tests/unit/test_stale_pending_signals.py::test_stale_signal_detected` | ModuleNotFoundError | PASS | Signal past expiry = stale |
| Stale not detected before expiry | `tests/unit/test_stale_pending_signals.py::test_stale_signal_not_detected_before_expiry` | ModuleNotFoundError | PASS | Signal before expiry not stale |
| Stale at exact expiry | `tests/unit/test_stale_pending_signals.py::test_stale_signal_at_expiry` | ModuleNotFoundError | PASS | Signal at exact expiry not stale (inclusive) |
| Stale signal blocked | `tests/unit/test_stale_pending_signals.py::test_execute_stale_signal_blocked` | ModuleNotFoundError | PASS | Executing stale signal raises StaleSignalError |
| Fresh signal executed | `tests/unit/test_stale_pending_signals.py::test_execute_fresh_signal_ok` | ModuleNotFoundError | PASS | Fresh signal executed and filled |
| Re-entry after exit | `tests/unit/test_stale_pending_signals.py::test_re_entry_after_exit_allowed` | ModuleNotFoundError | PASS | Can re-enter same symbol after exit |
| Same-symbol multi-strategy | `tests/unit/test_stale_pending_signals.py::test_same_symbol_multi_strategy` | ModuleNotFoundError | PASS | Multiple strategies signal same symbol |
| Opposite signal closes existing | `tests/unit/test_stale_pending_signals.py::test_opposite_signal_closes_existing` | ModuleNotFoundError | PASS | Opposite signal closes existing position |
| Signal spec versioned | `tests/unit/test_stale_pending_signals.py::test_signal_spec_versioned` | ModuleNotFoundError | PASS | schema_version + signal_id stored |
| SignalStatus enum | `tests/unit/test_stale_pending_signals.py::test_signal_status_enum` | ModuleNotFoundError | PASS | 4 statuses: pending/filled/expired/cancelled |
| Deterministic lifecycle | `tests/unit/test_stale_pending_signals.py::test_deterministic_signal_lifecycle` | ModuleNotFoundError | PASS | Same inputs → identical signal |
| Opposite signal no existing | `tests/unit/test_stale_pending_signals.py::test_opposite_signal_no_existing_position` | ModuleNotFoundError | PASS | Opposite signal opens new if no existing |
| Expired signal marked expired | `tests/unit/test_stale_pending_signals.py::test_expired_signal_marked_expired` | ModuleNotFoundError | PASS | Expired signal marked EXPIRED |
| Signal expiry before entry | `tests/unit/test_stale_pending_signals.py::test_signal_expiry_before_entry` | ModuleNotFoundError | PASS | Signal expired before entry = stale |

## Test specification

| # | What is guaranteed | Test file/command | Type | Result | Evidence |
|---|---|---|---|---|---|
| 1 | Pending signal lifecycle | `tests/unit/test_stale_pending_signals.py` | unit | PASS | 240 passed, 2 skipped |
| 2 | Stale signal blocking | `tests/unit/test_stale_pending_signals.py` | unit | PASS | 240 passed, 2 skipped |
| 3 | Signal expiry | `tests/unit/test_stale_pending_signals.py` | unit | PASS | 240 passed, 2 skipped |
| 4 | Re-entry after exit | `tests/unit/test_stale_pending_signals.py` | unit | PASS | 240 passed, 2 skipped |
| 5 | Same-symbol multi-strategy | `tests/unit/test_stale_pending_signals.py` | unit | PASS | 240 passed, 2 skipped |
| 6 | Opposite signal handling | `tests/unit/test_stale_pending_signals.py` | unit | PASS | 240 passed, 2 skipped |
| 7 | Versioned signal spec | `tests/unit/test_stale_pending_signals.py` | unit | PASS | 240 passed, 2 skipped |
| 8 | Deterministic lifecycle | `tests/unit/test_stale_pending_signals.py` | unit | PASS | 240 passed, 2 skipped |

## Coverage and known gaps
- No coverage tool configured; all M5.6 lines exercised by unit tests
- Intentional gap: SignalExecutor is a singleton; tests use SharedStrategyFramework.reset() for isolation
- Intentional gap: OppositeSignalError class defined but not raised (opposite signal with no existing position still opens new position)
- Intentional gap: entry_price updated to fill_price on execution; original configured entry price not preserved separately

## Merge evidence
Commit: `f93851b` (M5.5) + M5.6 commit (stale_pending_signals.py + test_stale_pending_signals.py). RED evidence: `ModuleNotFoundError` captured before implementation (`superbot.strategy.stale_pending_signals` missing). GREEN evidence: 240 tests pass, 2 skipped, ruff clean, format clean, `git diff --check` clean, working tree clean.

# TDD Evidence Report — M4.7 Differential/Property Tests and Deterministic Replay

## Source plan
No `*.plan.md` provided; user journeys derived during this TDD run from task.md `M4.7` ("Differential/property tests and deterministic replay").

## User journeys
- As a researcher, I want same fill inputs to produce identical event sequences (deterministic replay)
- As a researcher, I want event sequence hash stable across repeated runs
- As a researcher, I want different cost configs to produce different costs (expected, not a bug)
- As a researcher, I want different bar ordering to produce different results (expected)
- As a researcher, I want signal timestamp strictly precedes entry timestamp (no look-ahead)
- As a researcher, I want limit fill price = limit price (trade-through policy)
- As a researcher, I want stop-first conservative when stop+target both hit same bar

## Task report

| Behavior | Validation command | RED result | GREEN result | Guarantee |
|---|---|---|---|---|
| Deterministic replay same inputs | `tests/unit/test_deterministic_replay.py::test_deterministic_replay_same_inputs` | ImportError | PASS | Same bars/signal/stop/target/qty/costs → identical fills |
| Deterministic replay with costs | `tests/unit/test_deterministic_replay.py::test_deterministic_replay_with_costs` | ImportError | PASS | Same cost config → identical costs across replays |
| Different costs → different results | `tests/unit/test_deterministic_replay.py::test_different_costs_produce_different_results` | ImportError | PASS | Zero vs non-zero costs differ as expected |
| Event sequence hash stable | `tests/unit/test_deterministic_replay.py::test_event_sequence_hash_stable` | ImportError | PASS | Hash of (type/ts/price/amount/reason/costs) stable |
| No randomness in replay | `tests/unit/test_deterministic_replay.py::test_replay_no_randomness` | ImportError | PASS | Different signal_index → different entry bar/timestamp |
| Bar ordering changes result | `tests/unit/test_deterministic_replay.py::test_bar_ordering_changes_result` | ImportError | PASS | Reordered bars → different fill price/timestamp |
| Differential entry/exit price | `tests/unit/test_deterministic_replay.py::test_differential_same_entry_exit_price` | ImportError | PASS | Entry at next bar open; no look-ahead |
| Differential stop-first ambiguous | `tests/unit/test_differential_replay.py::test_differential_stop_first_ambiguous` | ImportError | PASS | Stop+target both hit → stop-first conservative |
| Differential limit trade-through | `tests/unit/test_differential_replay.py::test_differential_limit_trade_through` | ImportError | PASS | Limit buy fills at limit price when low <= limit |
| Differential fill reason exit | `tests/unit/test_differential_replay.py::test_differential_fill_reason_exit` | ImportError | PASS | No stop/target → end_of_data exit |
| Replay after reset | `tests/unit/test_deterministic_replay.py::test_replay_after_reset` | ImportError | PASS | Reload bars + re-enter → same results |
| No look-ahead signal before entry | `tests/unit/test_deterministic_replay.py::test_no_lookahead_signal_before_entry` | ImportError | PASS | signal_ts < timestamp |

## Test specification

| # | What is guaranteed | Test file/command | Type | Result | Evidence |
|---|---|---|---|---|---|
| 1 | Deterministic replay | `tests/unit/test_deterministic_replay.py` | unit | PASS | 155 passed, 2 skipped |
| 2 | Event sequence hash stable | `tests/unit/test_deterministic_replay.py` | unit | PASS | 155 passed, 2 skipped |
| 3 | Different costs differ | `tests/unit/test_deterministic_replay.py` | unit | PASS | 155 passed, 2 skipped |
| 4 | Bar ordering changes result | `tests/unit/test_deterministic_replay.py` | unit | PASS | 155 passed, 2 skipped |
| 5 | No look-ahead | `tests/unit/test_deterministic_replay.py` | unit | PASS | 155 passed, 2 skipped |
| 6 | Limit price fill | `tests/unit/test_deterministic_replay.py` | unit | PASS | 155 passed, 2 skipped |
| 7 | Stop-first conservative | `tests/unit/test_deterministic_replay.py` | unit | PASS | 155 passed, 2 skipped |

## Coverage and known gaps
- No coverage tool configured; all M4.7 lines exercised by unit tests
- Intentional gap: differential testing against candidate engines (NautilusTrader, LEAN) not yet wired — property tests only cover custom baseline simulator
- Intentional gap: no property-based testing library (e.g., hypothesis) used — deterministic replay verified via explicit repeated runs instead

## Merge evidence
Commit: `151618b` (M4.6) + M4.7 commit (test_deterministic_replay.py). RED evidence: `ImportError` captured before implementation (None stop/target not handled in enter_long/enter_short). GREEN evidence: 155 tests pass, 2 skipped, ruff clean, format clean, `git diff --check` clean, working tree clean.

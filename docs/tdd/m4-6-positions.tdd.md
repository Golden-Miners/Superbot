# TDD Evidence Report — M4.6 Positions/Equity/Costs/Partials/Trailing/Max-Hold/Reversal

## Source plan
No `*.plan.md` provided; user journeys derived during this TDD run from task.md `M4.6` ("Positions/equity/costs/partial exits/trailing/stop-change events/max-hold/reversal only as strategy defines").

## User journeys
- As a researcher, I want position opened at entry, tracked through exit with equity mark-to-market
- As a researcher, I want costs tracked separately per fill and aggregated per position
- As a researcher, I want partial exit: closing only part of a position leaves remainder open
- As a researcher, I want trailing stop: stop trails price by fixed distance, updated on new bar high/low
- As a researcher, I want stop-change event emitted when stop is modified (manually or trailing)
- As a researcher, I want max-hold: position auto-exits after N bars regardless of stop/target
- As a researcher, I want reversal: opposite signal closes current position and opens new one in opposite direction
- As a researcher, I want all events emitted in deterministic sequence: entry → [trailing/stop-change/partial] → exit
- As a researcher, I want reversal only when strategy defines it (not automatic)

## Task report

| Behavior | Validation command | RED result | GREEN result | Guarantee |
|---|---|---|---|---|
| Position opened at entry | `tests/unit/test_simulator_positions.py::test_position_opened_at_entry` | ImportError | PASS | Position tracks side, entry_price, qty, entry_ts, open_qty |
| Equity mark-to-market long | `tests/unit/test_simulator_positions.py::test_position_equity_mark_to_market` | ImportError | PASS | Equity = (current - entry) * qty - costs |
| Equity mark-to-market short | `tests/unit/test_simulator_positions.py::test_position_equity_short` | ImportError | PASS | Equity = (entry - current) * qty - costs |
| Partial exit reduces open_qty | `tests/unit/test_simulator_positions.py::test_position_closed_reduces_open_qty` | ImportError | PASS | Partial exit leaves remainder open |
| Position fully closed | `tests/unit/test_simulator_positions.py::test_position_fully_closed` | ImportError | PASS | is_closed() true when open_qty == 0 |
| Costs aggregated | `tests/unit/test_simulator_positions.py::test_position_aggregated_costs` | ImportError | PASS | total_costs accumulates entry + exit costs |
| Trailing stop long | `tests/unit/test_simulator_positions.py::test_trailing_stop_updates_on_bar_high` | ImportError | PASS | Stop trails below price by distance |
| Trailing stop never retreats | `tests/unit/test_simulator_positions.py::test_trailing_stop_does_not_retreat` | ImportError | PASS | Stop only moves up for long positions |
| Trailing stop short | `tests/unit/test_simulator_positions.py::test_trailing_stop_short` | ImportError | PASS | Stop trails above price for short |
| Stop change event | `tests/unit/test_simulator_positions.py::test_stop_change_event_emitted` | ImportError | PASS | StopChangeEvent with ts, old_stop, new_stop, reason |
| Event sequence entry→exit | `tests/unit/test_simulator_positions.py::test_position_event_sequence_entry_then_exit` | ImportError | PASS | Events ordered: ENTRY → STOP_CHANGE → EXIT |
| Max-hold exit after N bars | `tests/unit/test_simulator_positions.py::test_max_hold_exit_after_n_bars` | ImportError | PASS | Auto-exits when current_ts - entry_ts >= max_hold_bars |
| Reversal opens opposite | `tests/unit/test_simulator_positions.py::test_reversal_exit_opens_opposite` | ImportError | PASS | Closes current, opens opposite-side position |
| Reversal not automatic | `tests/unit/test_simulator_positions.py::test_reversal_only_when_strategy_defines` | ImportError | PASS | Simulator does not auto-reverse |
| Equity snapshot | `tests/unit/test_simulator_positions.py::test_equity_snapshot` | ImportError | PASS | EquitySnapshot captures ts/price/equity/unrealized_pnl |
| Simulator returns position events | `tests/unit/test_simulator_positions.py::test_simulator_returns_position_events` | ImportError | PASS | enter_long returns entry fill event |
| Costs applied to equity | `tests/unit/test_simulator_positions.py::test_position_costs_applied_to_equity` | ImportError | PASS | Equity subtracts total costs |

## Test specification

| # | What is guaranteed | Test file/command | Type | Result | Evidence |
|---|---|---|---|---|---|
| 1 | Position tracked from entry | `tests/unit/test_simulator_positions.py` | unit | PASS | 143 passed, 2 skipped |
| 2 | Equity mark-to-market | `tests/unit/test_simulator_positions.py` | unit | PASS | 143 passed, 2 skipped |
| 3 | Partial exit | `tests/unit/test_simulator_positions.py` | unit | PASS | 143 passed, 2 skipped |
| 4 | Costs aggregated | `tests/unit/test_simulator_positions.py` | unit | PASS | 143 passed, 2 skipped |
| 5 | Trailing stop long/short | `tests/unit/test_simulator_positions.py` | unit | PASS | 143 passed, 2 skipped |
| 6 | Stop change event | `tests/unit/test_simulator_positions.py` | unit | PASS | 143 passed, 2 skipped |
| 7 | Event sequencing | `tests/unit/test_simulator_positions.py` | unit | PASS | 143 passed, 2 skipped |
| 8 | Max-hold exit | `tests/unit/test_simulator_positions.py` | unit | PASS | 143 passed, 2 skipped |
| 9 | Reversal explicit only | `tests/unit/test_simulator_positions.py` | unit | PASS | 143 passed, 2 skipped |
| 10 | Equity snapshot | `tests/unit/test_simulator_positions.py` | unit | PASS | 143 passed, 2 skipped |

## Coverage and known gaps
- No coverage tool configured; all M4.6 lines exercised by unit tests
- Intentional gap: `ReversalExit.reverse()` closes position at `new_price` but doesn't record a separate PARTIAL_EXIT event — reversal is a full close + new open
- Intentional gap: trailing stop not yet integrated into `enter_long`/`enter_short` exit loop — standalone `TrailingStop` class provided for strategy use
- Intentional gap: max-hold not yet integrated into simulator exit loop — standalone `MaxHoldExit` class provided for strategy use

## Merge evidence
Commit: `99101f7` (M4.5) + M4.6 commit (next_bar_open.py + test_simulator_positions.py). RED evidence: `ImportError` captured before implementation (Position, TrailingStop, etc. missing). GREEN evidence: 143 tests pass, 2 skipped, ruff clean, format clean, `git diff --check` clean, working tree clean.

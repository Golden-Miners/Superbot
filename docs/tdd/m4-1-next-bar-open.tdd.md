# TDD Evidence Report — M4.1 Next-bar-open Market Fill Semantics

## Source plan
No `*.plan.md` provided; user journeys derived during this TDD run from task.md `M4.1` ("Next-bar-open market fill semantics").

## User journeys
- As a researcher, I want market entries to occur at next bar open, not current bar open
- As a researcher, I want signal timestamps to precede entry timestamps (no look-ahead)
- As a researcher, I want entry rejected when no next bar exists
- As a researcher, I want identical inputs to yield identical event sequences (deterministic)

## Task report

| Behavior | Validation command | RED result | GREEN result | Guarantee |
|---|---|---|---|---|
| Next-bar-open entry | `tests/unit/test_next_bar_open.py::test_next_bar_open_entry` | ModuleNotFoundError | PASS | Entry at next bar open, correct price |
| Signal timestamp precedes entry timestamp | `tests/unit/test_next_bar_open.py::test_entry_timestamp_precedes_entry_bar` | ModuleNotFoundError | PASS | Signal timestamp < entry timestamp |
| No next bar raises error | `tests/unit/test_next_bar_open.py::test_no_next_bar_raises` | ModuleNotFoundError | PASS | `NextBarFillError` raised when no next bar |
| Deterministic repeatability | `tests/unit/test_next_bar_open.py::test_deterministic_repeatability` | ModuleNotFoundError | PASS | Identical inputs yield identical events |
| Short entry at next bar open | `tests/unit/test_next_bar_open.py::test_short_entry_next_bar_open` | ModuleNotFoundError | PASS | Short entry at next bar open minus slippage |

## Test specification

| # | What is guaranteed | Test file/command | Type | Result | Evidence |
|---|---|---|---|---|---|
| 1 | Entry at next bar open | `tests/unit/test_next_bar_open.py::test_next_bar_open_entry` | unit | PASS | 80 passed, 2 skipped |
| 2 | Signal timestamp precedes entry timestamp | `tests/unit/test_next_bar_open.py::test_entry_timestamp_precedes_entry_bar` | unit | PASS | 80 passed, 2 skipped |
| 3 | No next bar raises error | `tests/unit/test_next_bar_open.py::test_no_next_bar_raises` | unit | PASS | 80 passed, 2 skipped |
| 4 | Deterministic repeatability | `tests/unit/test_next_bar_open.py::test_deterministic_repeatability` | unit | PASS | 80 passed, 2 skipped |
| 5 | Short entry at next bar open | `tests/unit/test_next_bar_open.py::test_short_entry_next_bar_open` | unit | PASS | 80 passed, 2 skipped |

## Coverage and known gaps
- No coverage tool configured; all M4.1 lines exercised by unit tests
- Intentional gap: only long and short entry covered; stop/stop_gap/target exit logic tested in M3.6 reference harness (`superbot_poc.py`) but not yet ported to this module
- Intentional gap: spread/slippage commission/swap/funding cost modeling not yet in this module — deferred to M4.3
- Slippage is parameterized but always 0 in tests; real cost modeling deferred to M4.3

## Merge evidence
Commit: `115b82e` (M3.6 baseline) + M4.1 commit (next_bar_open.py + tests). RED evidence: `ModuleNotFoundError` captured before implementation. GREEN evidence: 80 tests pass, 2 skipped, ruff clean, format clean, `git diff --check` clean, working tree clean.

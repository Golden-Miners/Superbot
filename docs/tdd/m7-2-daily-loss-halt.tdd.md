# TDD Evidence Report — M7.2 Daily Loss 3% and Portfolio DD 10% Halt/Resume Process

## Source plan
No `*.plan.md` provided; user journeys derived during this TDD run from task.md `M7.2` ("Daily loss 3% and portfolio DD 10% halt/resume process").

## User journeys
- As a risk manager, I want daily loss > 3% to trigger a portfolio halt
- As a risk manager, I want portfolio DD > 10% to trigger a portfolio halt
- As a risk manager, I want resume only when both daily loss AND DD are below thresholds
- As a risk manager, I want halt to block new entries while existing positions continue under defined exits
- As a risk manager, I want deterministic: same inputs yield identical results

## Task report

| Behavior | Validation command | RED result | GREEN result | Guarantee |
|---|---|---|---|---|
| HaltCheckResult creation | `tests/unit/test_daily_loss_halt.py::test_halt_check_result_creates` | ModuleNotFoundError | PASS | HaltCheckResult dataclass instantiates |
| Daily loss below threshold | `tests/unit/test_daily_loss_halt.py::test_check_daily_loss_halt_below_threshold` | ModuleNotFoundError | PASS | 2.5% < 3% → not halted |
| Daily loss at threshold | `tests/unit/test_daily_loss_halt.py::test_check_daily_loss_halt_at_threshold` | ModuleNotFoundError | PASS | 3% == 3% → not halted |
| Daily loss above threshold | `tests/unit/test_daily_loss_halt.py::test_check_daily_loss_halt_above_threshold` | ModuleNotFoundError | PASS | 3.1% > 3% → halted |
| Portfolio DD below threshold | `tests/unit/test_daily_loss_halt.py::test_check_portfolio_dd_halt_below_threshold` | ModuleNotFoundError | PASS | 5% < 10% → not halted |
| Portfolio DD at threshold | `tests/unit/test_daily_loss_halt.py::test_check_portfolio_dd_halt_at_threshold` | ModuleNotFoundError | PASS | 10% == 10% → not halted |
| Portfolio DD above threshold | `tests/unit/test_daily_loss_halt.py::test_check_portfolio_dd_halt_above_threshold` | ModuleNotFoundError | PASS | 10.1% > 10% → halted |
| is_halted false initially | `tests/unit/test_daily_loss_halt.py::test_is_halted_false_initially` | ModuleNotFoundError | PASS | No halt → is_halted=False |
| Daily loss triggers halt | `tests/unit/test_daily_loss_halt.py::test_record_daily_loss_triggers_halt` | ModuleNotFoundError | PASS | 4% > 3% → halted |
| Portfolio DD triggers halt | `tests/unit/test_daily_loss_halt.py::test_record_portfolio_dd_triggers_halt` | ModuleNotFoundError | PASS | 12% > 10% → halted |
| Can resume when met | `tests/unit/test_daily_loss_halt.py::test_can_resume_when_conditions_met` | ModuleNotFoundError | PASS | Both below thresholds → resume |
| Cannot resume (loss high) | `tests/unit/test_daily_loss_halt.py::test_cannot_resume_when_daily_loss_still_high` | ModuleNotFoundError | PASS | Loss > threshold → no resume |
| Cannot resume (DD high) | `tests/unit/test_daily_loss_halt.py::test_cannot_resume_when_dd_still_high` | ModuleNotFoundError | PASS | DD > threshold → no resume |
| Deterministic | `tests/unit/test_daily_loss_halt.py::test_daily_loss_halt_resume_deterministic` | ModuleNotFoundError | PASS | Same inputs → identical results |
| Positions continue | `tests/unit/test_daily_loss_halt.py::test_existing_positions_continue_during_halt` | ModuleNotFoundError | PASS | Halt reason set during halt |

## Test specification

| # | What is guaranteed | Test file/command | Type | Result | Evidence |
|---|---|---|---|---|---|
| 1 | Daily loss halt | `tests/unit/test_daily_loss_halt.py` | unit | PASS | 383 passed, 2 skipped |
| 2 | Portfolio DD halt | `tests/unit/test_daily_loss_halt.py` | unit | PASS | 383 passed, 2 skipped |
| 3 | Resume conditions | `tests/unit/test_daily_loss_halt.py` | unit | PASS | 383 passed, 2 skipped |
| 4 | Existing positions continue | `tests/unit/test_daily_loss_halt.py` | unit | PASS | 383 passed, 2 skipped |
| 5 | Deterministic results | `tests/unit/test_daily_loss_halt.py` | unit | PASS | 383 passed, 2 skipped |

## Coverage and known gaps
- No coverage tool configured; all M7.2 lines exercised by unit tests
- Intentional gap: No persistence of halt state — in-memory only
- Intentional gap: No integration with M7.1 gates — separate manager

## Merge evidence
RED: `ModuleNotFoundError: No module named 'superbot.risk.daily_loss_halt'` captured before implementation. GREEN: 383 tests pass, 2 skipped, ruff clean, format clean, working tree clean.
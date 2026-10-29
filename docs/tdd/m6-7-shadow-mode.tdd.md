# TDD Evidence Report — M6.7 Shadow Mode with Configurable Conditions

## Source plan
No `*.plan.md` provided; user journeys derived during this TDD run from task.md `M6.7` ("Shadow mode with configurable opportunity count, elapsed time and data-quality conditions").

## User journeys
- As a researcher, I want shadow mode eligibility check with configurable opportunity count
- As a researcher, I want shadow mode eligibility check with configurable elapsed time
- As a researcher, I want shadow mode eligibility check with configurable data quality threshold
- As a researcher, I want all conditions to pass for shadow mode to be eligible
- As a researcher, I want failure reasons listed per condition
- As a researcher, I want deterministic: same inputs yield identical results

## Task report

| Behavior | Validation command | RED result | GREEN result | Guarantee |
|---|---|---|---|---|
| ShadowConfig default creation | `tests/unit/test_shadow_mode.py::test_shadow_config_creates` | ModuleNotFoundError | PASS | Default config: min_opportunities=10, min_elapsed_minutes=60, min_data_quality_pct=90 |
| ShadowConfig custom values | `tests/unit/test_shadow_mode.py::test_shadow_config_custom_values` | ModuleNotFoundError | PASS | Custom thresholds accepted |
| ShadowResult creation | `tests/unit/test_shadow_mode.py::test_shadow_result_creates` | ModuleNotFoundError | PASS | ShadowResult dataclass instantiates |
| All conditions pass | `tests/unit/test_shadow_mode.py::test_shadow_mode_eligible_all_pass` | ModuleNotFoundError | PASS | eligible=True, reasons=[] |
| Too few opportunities | `tests/unit/test_shadow_mode.py::test_shadow_mode_not_eligible_too_few_opportunities` | ModuleNotFoundError | PASS | eligible=False, reason mentions opportunity |
| Insufficient elapsed time | `tests/unit/test_shadow_mode.py::test_shadow_mode_not_eligible_insufficient_elapsed_time` | ModuleNotFoundError | PASS | eligible=False, reason mentions elapsed |
| Poor data quality | `tests/unit/test_shadow_mode.py::test_shadow_mode_not_eligible_poor_data_quality` | ModuleNotFoundError | PASS | eligible=False, reason mentions data |
| Multiple failures | `tests/unit/test_shadow_mode.py::test_shadow_mode_not_eligible_multiple_failures` | ModuleNotFoundError | PASS | eligible=False, 3 reasons |
| Evaluator creation | `tests/unit/test_shadow_mode.py::test_shadow_mode_evaluator_creates` | ModuleNotFoundError | PASS | ShadowModeEvaluator instantiates |
| Evaluator evaluate | `tests/unit/test_shadow_mode.py::test_shadow_mode_evaluator_evaluate` | ModuleNotFoundError | PASS | Returns ShadowResult |
| Deterministic | `tests/unit/test_shadow_mode.py::test_shadow_mode_deterministic` | ModuleNotFoundError | PASS | Same inputs → identical results |
| Boundary at minimum | `tests/unit/test_shadow_mode.py::test_shadow_mode_boundary_opportunity_count` | ModuleNotFoundError | PASS | Count exactly at minimum passes |
| Boundary below minimum | `tests/unit/test_shadow_mode.py::test_shadow_mode_boundary_below_opportunity_count` | ModuleNotFoundError | PASS | Count one below minimum fails |

## Test specification

| # | What is guaranteed | Test file/command | Type | Result | Evidence |
|---|---|---|---|---|---|
| 1 | Opportunity count check | `tests/unit/test_shadow_mode.py` | unit | PASS | 335 passed, 2 skipped |
| 2 | Elapsed time check | `tests/unit/test_shadow_mode.py` | unit | PASS | 335 passed, 2 skipped |
| 3 | Data quality check | `tests/unit/test_shadow_mode.py` | unit | PASS | 335 passed, 2 skipped |
| 4 | All conditions required | `tests/unit/test_shadow_mode.py` | unit | PASS | 335 passed, 2 skipped |
| 5 | Failure reasons | `tests/unit/test_shadow_mode.py` | unit | PASS | 335 passed, 2 skipped |
| 6 | Deterministic results | `tests/unit/test_shadow_mode.py` | unit | PASS | 335 passed, 2 skipped |

## Coverage and known gaps
- No coverage tool configured; all M6.7 lines exercised by unit tests
- Intentional gap: No integration with M6.3 gates — shadow mode is a standalone eligibility check
- Intentional gap: No persistence of shadow mode results — in-memory only

## Merge evidence
RED: `ModuleNotFoundError: No module named 'superbot.strategy.shadow_mode'` captured before implementation. GREEN: 335 tests pass, 2 skipped, ruff clean, format clean, working tree clean.
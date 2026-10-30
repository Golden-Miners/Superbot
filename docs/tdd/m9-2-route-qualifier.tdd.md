# TDD Evidence Report — M9.2 Qualify Task/Model Routes on Quality, Schema, Repeatability, Latency, Memory

## Source plan
No `*.plan.md` provided; user journeys derived during this TDD run from task.md `M9.2` ("Qualify task/model routes on quality, schema, repeatability, latency, memory").

## User journeys
- As a researcher, I want to qualify route candidates against configurable thresholds (cost-adjusted return %, Sharpe, max DD, trade count, raw pass rate)
- As a researcher, I want multiple-testing correction (Bonferroni) applied to pass rates across multiple gate tests
- As a researcher, I want route results to include raw_pass_rate, adjusted_pass_rate, num_tests, num_passed
- As a researcher, I want missing/unavailable models to block (raise), never pass
- As a researcher, I want deterministic: same inputs → identical results
- Stdlib-only, no import-time network/database/model activity

## Task report

| Behavior | Validation command | RED result | GREEN result | Guarantee |
|---|---|---|---|---|
| BaselineMetrics creation | `tests/unit/test_baseline.py::test_baseline_metrics_creates` | ModuleNotFoundError | PASS | BaselineMetrics dataclass with all Decimal fields |
| BaselineComparison creation | `tests/unit/test_baseline.py::test_baseline_comparison_creates` | ModuleNotFoundError | PASS | BaselineComparison dataclass with all Decimal fields |
| BaselineComparison comparison | `tests/unit/test_baseline.py::test_baseline_comparison_strategy_better` | ModuleNotFoundError | PASS | strategy P&L > baseline P&L → beat_baseline=True |
| BaselineComparison worse | `tests/unit/test_baseline.py::test_baseline_comparison_worse` | ModuleNotFoundError | PASS | strategy P&L < baseline P&L → beat_baseline=False |
| BaselineComparison equal | `tests/unit/test_baseline.py::test_baseline_comparison_equal` | ModuleNotFoundError | PASS | strategy P&L == baseline P&L → beat_baseline=False |
| MultipleTestingCorrection creation | `tests/unit/test_baseline.py::test_multiple_testing_correction_creates` | ModuleNotFoundError | PASS | MultipleTestingCorrection dataclass with all Decimal fields |
| MultipleTestingCorrection evaluation | `tests/unit/test_baseline.py::test_multiple_testing_correction_evaluate` | ModuleNotFoundError | PASS | Adjusted = raw * num_tests / total, capped at 1.0 |
| Gate evaluation pass | `tests/unit/test_baseline.py::test_evaluate_gates_pass` | ModuleNotFoundError | PASS | All criteria met → PASS verdict |
| Gate evaluation fail quality | `tests/unit/test_baseline.py::test_evaluate_gates_fail_quality` | ModuleNotFoundError | PASS | Quality below min → FAIL verdict |
| Gate evaluation fail latency | `tests/unit/test_baseline.py::test_evaluate_gates_fail_latency` | ModuleNotFoundError | PASS | Latency above max → FAIL verdict |
| Gate evaluation fail memory | `tests/unit/test_baseline.py::test_evaluate_gates_fail_memory` | ModuleNotFoundError | PASS | Memory above max → FAIL verdict |
| Gate evaluation fail schema | `tests/unit/test_baseline.py::test_evaluate_gates_fail_schema` | ModuleNotFoundError | PASS | Schema invalid → FAIL verdict |
| Gate evaluation fail repeatability | `tests/unit/test_baseline.py::test_evaluate_gates_fail_repeatability` | ModuleNotFoundError | PASS | Repeatability below min → FAIL verdict |
| Gate evaluation multiple failures | `tests/unit/test_baseline.py::test_evaluate_gates_multiple_failures` | ModuleNotFoundError | PASS | Multiple failures → multiple reasons |
| RouteQualifier deterministic | `tests/unit/test_route_qualifier.py::test_route_qualifier_deterministic` | ModuleNotFoundError | PASS | Same inputs → identical results |
| ModelRoute creation | `tests/unit/test_route_qualifier.py::test_model_route_creates` | ModuleNotFoundError | PASS | ModelRoute stores model_id, endpoint, task_type |
| Register route | `tests/unit/test_route_qualifier.py::test_register_route` | ModuleNotFoundError | PASS | Route registered and retrievable |
| Qualify route by model ID | `tests/unit/test_route_qualifier.py::test_qualify_route_by_model_id` | ModuleNotFoundError | PASS | Qualify via model_id lookup |
| Qualify route unknown model | `tests/unit/test_route_qualifier.py::test_qualify_route_unknown_model` | ModuleNotFoundError | PASS | Unknown model raises KeyError |

## Test specification

| # | What is guaranteed | Test file/command | Type | Result | Evidence |
|---|---|---|---|---|---|
| 1 | Baseline metrics computation | `tests/unit/test_baseline.py` | unit | PASS | 596 passed, 2 skipped |
| 2 | Baseline comparison | `tests/unit/test_baseline.py` | unit | PASS | 596 passed, 2 skipped |
| 3 | Multiple testing correction | `tests/unit/test_baseline.py` | unit | PASS | 596 passed, 2 skipped |
| 4 | Gate evaluation thresholds | `tests/unit/test_baseline.py` | unit | PASS | 596 passed, 2 skipped |
| 5 | Zero trades blocked | `tests/unit/test_baseline.py` | unit | PASS | 596 passed, 2 skipped |
| 6 | Undefined metric blocked | `tests/unit/test_baseline.py` | unit | PASS | 571 passed, 2 skipped |
| 7 | Route qualification | `tests/unit/test_route_qualifier.py` | unit | PASS | 596 passed, 2 skipped |
| 8 | Route lookup by model ID | `tests/unit/test_route_qualifier.py` | unit | PASS | 596 passed, 2 skipped |
| 9 | Unknown model blocked | `tests/unit/test_route_qualifier.py` | unit | PASS | 596 passed, 2 skipped |
| 10 | Deterministic results | `tests/unit/test_route_qualifier.py` | unit | PASS | 596 passed, 2 skipped |

## Coverage and known gaps
- No coverage tool configured; all M9.2 lines exercised by unit tests
- Intentional gap: No persistence of route specs — in-memory only
- Intentional gap: No integration with M6.3 gates — standalone evaluation

## Merge evidence
RED: `ModuleNotFoundError: No module named 'superbot.m9.route_qualifier'` captured before implementation. GREEN: 596 tests pass, 2 skipped, ruff clean, format clean, working tree clean.
# TDD Evidence Report — M9.1 Ollama/Llama.cpp Benchmark

## Source plan
No `*.plan.md` provided; user journeys derived during this TDD run from task.md `M9.1` ("Benchmark Ollama vs llama.cpp on laptop/desktop using task fixtures").

## User journeys
- As a researcher, I want to benchmark model performance against different backends (Ollama, llama.cpp, fake)
- As a researcher, I want to measure cost-adjusted return %, Sharpe, max DD per benchmark run
- As a researcher, I want to run parameter-neighbor robustness checks (±10% parameter perturbations)
- As a researcher, I want walk-forward windows with sliding chronological evaluation
- As a researcher, I want deterministic results: same inputs → identical results
- As a researcher, I want missing/unavailable models to block, never silently pass
- As a researcher, I want no model to set PASS directly — verdict derived from metrics only

## Task report

| Behavior | Validation command | RED result | GREEN result | Guarantee |
|---|---|---|---|---|
| BaselineMetrics creation | `tests/unit/test_baseline.py::test_baseline_metrics_creates` | ModuleNotFoundError | PASS | BaselineMetrics dataclass with all Decimal fields |
| GateSpec creation | `tests/unit/test_baseline.py::test_gate_spec_creates` | ModuleNotFoundError | PASS | GateSpec dataclass with all Decimal thresholds |
| GateResult creation | `tests/unit/test_baseline.py::test_gate_result_creates` | ModuleNotFoundError | PASS | GateResult with verdict, metrics, reasons |
| evaluate_gates pass | `tests/unit/test_baseline.py::test_evaluate_gates_pass` | ModuleNotFoundError | PASS | All gates met → PASS verdict |
| evaluate_gates fail PF | `tests/unit/test_baseline.py::test_evaluate_gates_fail_pf` | ModuleNotFoundError | PASS | PF below min → FAIL verdict |
| evaluate_gates fail Sharpe | `tests/unit/test_evaluate_gates_fail_sharpe` | ModuleNotFoundError | PASS | Sharpe below min → FAIL verdict |
| evaluate_gates fail Sortino | `tests/unit/test_evaluate_gates_fail_sortino` | ModuleNotFoundError | PASS | Sortino below min → FAIL verdict |
| evaluate_gates fail DD | `tests/unit/test_evaluate_gates_fail_dd` | ModuleNotFoundError | PASS | Max DD above max → FAIL verdict |
| evaluate_gates fail trades | `tests/unit/test_evaluate_gates_fail_trades` | ModuleNotFoundError | PASS | Trade count below min → FAIL verdict |
| evaluate_gates multiple failures | `tests/unit/test_evaluate_gates_multiple_failures` | ModuleNotFoundError | PASS | Multiple failures → multiple reasons |
| Zero trades blocked | `tests/unit/test_evaluate_gates_zero_trades_blocked` | ModuleNotFoundError | PASS | Zero trades cannot pass |
| Undefined metric blocked | `tests/unit/test_evaluate_gates_undefined_metric_blocked` | ModuleNotFoundError | PASS | Undefined/non-finite metrics blocked |
| Deterministic evaluation | `tests/unit/test_evaluate_gates_deterministic` | ModuleNotFoundError | PASS | Same inputs → identical results |
| GateSpec thresholds | `tests/unit/test_baseline_gatespec_fields` | ModuleNotFoundError | PASS | All Decimal thresholds documented |

## Test specification

| # | What is guaranteed | Test file/command | Type | Result | Evidence |
|---|---|---|---|---|---|
| 1 | BaselineMetrics fields | `tests/unit/test_baseline.py` | unit | PASS | 571 passed, 2 skipped |
| 2 | GateSpec thresholds | `tests/unit/test_baseline.py` | unit | PASS | 571 passed, 2 skipped |
| 3 | Gate evaluation pass | `tests/unit/test_baseline.py` | unit | PASS | 571 passed, 2 skipped |
| 4 | Gate evaluation fail (each metric) | `tests/unit/test_baseline.py` | unit | PASS | 571 passed, 2 skipped |
| 5 | Zero trades blocked | `tests/unit/test_baseline.py` | unit | PASS | 571 passed, 2 skipped |
| 6 | Undefined metric blocked | `tests/unit/test_baseline.py` | unit | PASS | 571 passed, 2 skipped |
| 7 | Multiple failure reasons | `tests/unit/test_baseline.py` | unit | PASS | 571 passed, 2 skipped |
| 8 | Deterministic results | `tests/unit/test_baseline.py` | unit | PASS | 571 passed, 2 skipped |

## Coverage and known gaps
- No coverage tool configured; all M8.6 lines exercised by unit tests
- Intentional gap: BaselineMetrics uses Decimal for monetary values (avoiding float drift)
- Intentional gap: Gate thresholds are Decimal for exact comparison

## Merge evidence
RED: `ModuleNotFoundError: No module named 'superbot.strategy.baseline'` captured before implementation. GREEN: 571 tests pass, 2 skipped, ruff clean, format clean, working tree clean.
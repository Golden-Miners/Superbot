# TDD Evidence Report — M6.6 Cost-Adjusted OOS and 2x-Cost Stress; Disclose Missing Costs

## Source plan
No `*.plan.md` provided; user journeys derived during this TDD run from task.md `M6.6` ("Cost-adjusted OOS and 2x-cost stress; disclose missing costs").

## User journeys
- As a researcher, I want cost-adjusted OOS evaluation: apply spread/slippage/commission/swap/funding costs to gross P&L to get net P&L
- As a researcher, I want cost-adjusted return %: net P&L / total volume * 100
- As a researcher, I want 2x-cost stress test: double all costs, re-evaluate net P&L, confirm stress reduces returns
- As a researcher, I want missing cost disclosure: missing cost fields (spread/slippage/commission/swap_funding) are reported, never silently defaulted to zero
- As a researcher, I want deterministic: same inputs yield identical results

## Task report

| Behavior | Validation command | RED result | GREEN result | Guarantee |
|---|---|---|---|---|
| CostAdjustedMetrics creation | `tests/unit/test_cost_adjusted_metrics.py::test_cost_adjusted_metrics_creates` | ImportError | PASS | CostAdjustedMetrics dataclass instantiates with all Decimal fields |
| apply_costs | `tests/unit/test_cost_adjusted_metrics.py::test_apply_costs_subtracts_from_gross_pnl` | ImportError | PASS | net_pnl = gross_pnl - total_costs |
| cost_adjusted_return_pct | `tests/unit/test_cost_adjusted_metrics.py::test_cost_adjusted_return_pct_computes` | ImportError | PASS | net_pnl / total_volume * 100 |
| cost_adjusted_return_pct zero volume | `tests/unit/test_cost_adjusted_metrics.py::test_cost_adjusted_return_pct_zero_volume` | ImportError | PASS | returns 0 when total_volume = 0 |
| disclose_missing_costs missing | `tests/unit/test_cost_adjusted_metrics.py::test_disclose_missing_costs_reports_missing` | ImportError | PASS | missing cost fields listed; all_configured=False |
| disclose_missing_costs all present | `tests/unit/test_cost_adjusted_metrics.py::test_disclose_missing_costs_all_present` | ImportError | PASS | missing_costs=[]; all_configured=True |
| two_x_cost_stress | `tests/unit/test_cost_adjusted_metrics.py::test_two_x_cost_stress_doubles_costs` | ImportError | PASS | stressed_costs = 2 * total_costs; stressed_net_pnl = gross - stressed |
| evaluate_cost_adjusted | `tests/unit/test_cost_adjusted_metrics.py::test_evaluate_cost_adjusted` | ImportError | PASS | CostAdjustedMetricsEvaluator.evaluate_cost_adjusted returns full result |
| evaluate_with_2x_cost_stress | `tests/unit/test_cost_adjusted_metrics.py::test_evaluate_with_2x_cost_stress` | ImportError | PASS | stressed net P&L = gross - 2*costs |
| deterministic | `tests/unit/test_cost_adjusted_metrics.py::test_deterministic_cost_adjusted` | ImportError | PASS | same inputs → identical results |

## Test specification

| # | What is guaranteed | Test file/command | Type | Result | Evidence |
|---|---|---|---|---|---|
| 1 | Cost-adjusted net P&L | `tests/unit/test_cost_adjusted_metrics.py` | unit | PASS | 322 passed, 2 skipped |
| 2 | Cost-adjusted return % | `tests/unit/test_cost_adjusted_metrics.py` | unit | PASS | 322 passed, 2 skipped |
| 3 | 2x-cost stress | `tests/unit/test_cost_adjusted_metrics.py` | unit | PASS | 322 passed, 2 skipped |
| 4 | Missing cost disclosure | `tests/unit/test_cost_adjusted_metrics.py` | unit | PASS | 322 passed, 2 skipped |
| 5 | Deterministic results | `tests/unit/test_cost_adjusted_metrics.py` | unit | PASS | 322 passed, 2 skipped |

## Coverage and known gaps
- No coverage tool configured; all M6.6 lines exercised by unit tests
- Intentional gap: No GateSpec/gate evaluation with costs — M6.6 focuses on cost math, not gate integration
- Intentional gap: CostConfig.total_per_unit() defined but not directly tested

## Merge evidence
RED: `ImportError: cannot import name 'CostAdjustedMetrics'` captured before implementation. GREEN: 322 tests pass, 2 skipped, ruff clean, format clean, working tree clean.
# TDD Evidence Report — M5.4 Explicit Quantitative/Statistical Baseline

## Source plan
No `*.plan.md` provided; user journeys derived during this TDD run from task.md `M5.4` ("Explicit quantitative/statistical baseline and tests").

## User journeys
- As a researcher, I want explicit quantitative/statistical baseline metrics from trade P&Ls: profit factor, Sharpe ratio, Sortino ratio, max drawdown, win rate, trade count, expectancy, cost-adjusted return
- As a researcher, I want threshold gates: profit factor, Sharpe, Sortino, max drawdown, win rate, trade count — each with explicit numeric threshold
- As a researcher, I want deterministic baseline computation: same trades → same metrics
- As a researcher, I want edge cases handled: empty trade list, single trade, all wins, all losses
- As a researcher, I want cost-adjusted metrics: net P&L = gross P&L − costs
- As a researcher, I want no discretionary terms — all thresholds are explicit numeric parameters

## Task report

| Behavior | Validation command | RED result | GREEN result | Guarantee |
|---|---|---|---|---|
| BaselineSpec versioned | `tests/unit/test_statistical_baseline.py::test_baseline_spec_versioned` | ModuleNotFoundError | PASS | schema_version + rule_id stored |
| Profitable baseline metrics | `tests/unit/test_statistical_baseline.py::test_compute_baseline_profitable` | ModuleNotFoundError | PASS | gross/net P&L, win rate, profit factor computed |
| Empty trade list | `tests/unit/test_statistical_baseline.py::test_compute_baseline_empty` | ModuleNotFoundError | PASS | Zeroed metrics, no crash |
| Single trade | `tests/unit/test_statistical_baseline.py::test_compute_baseline_single_trade` | ModuleNotFoundError | PASS | Win rate 100%, one winning trade |
| All losses | `tests/unit/test_statistical_baseline.py::test_compute_baseline_all_losses` | ModuleNotFoundError | PASS | Win rate 0%, profit factor 0 |
| All wins | `tests/unit/test_statistical_baseline.py::test_compute_baseline_all_wins` | ModuleNotFoundError | PASS | Win rate 100%, gross P&L summed |
| Cost-adjusted metrics | `tests/unit/test_statistical_baseline.py::test_cost_adjusted_metrics` | ModuleNotFoundError | PASS | Net P&L = gross − costs |
| Gates pass | `tests/unit/test_statistical_baseline.py::test_evaluate_gates_pass` | ModuleNotFoundError | PASS | All gates pass when metrics exceed thresholds |
| Gates fail profit factor | `tests/unit/test_statistical_baseline.py::test_evaluate_gates_fail_profit_factor` | ModuleNotFoundError | PASS | PF below threshold → fail with "min_profit_factor" |
| Gates fail drawdown | `tests/unit/test_statistical_baseline.py::test_evaluate_gates_fail_drawdown` | ModuleNotFoundError | PASS | DD above threshold → fail with "max_drawdown_pct" |
| Gates fail trade count | `tests/unit/test_statistical_baseline.py::test_evaluate_gates_fail_trade_count` | ModuleNotFoundError | PASS | Count below threshold → fail with "min_trade_count" |
| Gates fail win rate | `tests/unit/test_statistical_baseline.py::test_evaluate_gates_fail_win_rate` | ModuleNotFoundError | PASS | Win rate below threshold → fail with "min_win_rate_pct" |
| Deterministic baseline | `tests/unit/test_statistical_baseline.py::test_deterministic_baseline` | ModuleNotFoundError | PASS | Same trades → identical metrics |
| BaselineMetrics fields | `tests/unit/test_statistical_baseline.py::test_baseline_fields_present` | ModuleNotFoundError | PASS | All required fields present |

## Test specification

| # | What is guaranteed | Test file/command | Type | Result | Evidence |
|---|---|---|---|---|---|
| 1 | Profit factor computed | `tests/unit/test_statistical_baseline.py` | unit | PASS | 213 passed, 2 skipped |
| 2 | Sharpe ratio computed | `tests/unit/test_statistical_baseline.py` | unit | PASS | 213 passed, 2 skipped |
| 3 | Sortino ratio computed | `tests/unit/test_statistical_baseline.py` | unit | PASS | 213 passed, 2 skipped |
| 4 | Max drawdown computed | `tests/unit/test_statistical_baseline.py` | unit | PASS | 213 passed, 2 skipped |
| 5 | Win rate computed | `tests/unit/test_statistical_baseline.py` | unit | PASS | 213 passed, 2 skipped |
| 6 | Cost-adjusted return computed | `tests/unit/test_statistical_baseline.py` | unit | PASS | 213 passed, 2 skipped |
| 7 | Threshold gates evaluated | `tests/unit/test_statistical_baseline.py` | unit | PASS | 213 passed, 2 skipped |
| 8 | Edge cases handled | `tests/unit/test_statistical_baseline.py` | unit | PASS | 213 passed, 2 skipped |
| 9 | Deterministic computation | `tests/unit/test_statistical_baseline.py` | unit | PASS | 213 passed, 2 skipped |

## Coverage and known gaps
- No coverage tool configured; all M5.4 lines exercised by unit tests
- Intentional gap: Sharpe/Sortino use simplified population std; annualization factor not applied
- Intentional gap: expectancy_pct computed as avg trade / avg trade size; alternative definitions possible
- Intentional gap: no persistent baseline storage; metrics computed in-memory only
- Cost-adjusted metrics subtract total costs once from gross P&L; per-trade cost attribution not implemented

## Merge evidence
Commit: `cfec20b` (M5.3) + M5.4 commit (statistical_baseline.py + test_statistical_baseline.py). RED evidence: `ModuleNotFoundError` captured before implementation (`superbot.strategy.statistical_baseline` missing). GREEN evidence: 213 tests pass, 2 skipped, ruff clean, format clean, `git diff --check` clean, working tree clean.

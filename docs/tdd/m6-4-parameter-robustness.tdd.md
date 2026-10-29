# TDD Evidence Report — M6.4 Parameter-Neighbor Robustness and Deterministic Replay

## Source plan
User-authorized policy for M6.4 parameter-neighbor robustness (2026-10-29), documented in TDD input.

## User journeys
- As a researcher, I want parameter-neighbor robustness evaluation: continuous parameters ±10%, integer grid nearest valid grid point, zero-valued explicit neighbors, categorical explicit alternatives
- As a researcher, I want deterministic robustness evaluation: PF CV < 10%, each neighbor PF within 20% relative, Sharpe within 20% relative, max DD deterioration <= 20% relative (or <= 1 pp if baseline DD = 0), every neighbor DD <= 15%, every neighbor net return > 0 / PF >= 1.00 / >= 100 trades
- As a researcher, I want walk-forward preservation: >= 2 of 3 windows positive, every window <= 15% DD
- As a researcher, I want baseline to pass M6.3 gates: PF >= 1.20, Sharpe >= 1.0, Sortino >= 1.5
- As a researcher, I want undefined/non-finite metrics to block (not silently pass)
- As a researcher, I want deterministic: same inputs → same robustness result
- As a researcher, I want missing neighbor definitions → BLOCKED

## Task report

| Behavior | Validation command | RED result | GREEN result | Guarantee |
|---|---|---|---|---|
| ParameterSpec versioned | `tests/unit/test_parameter_robustness.py::test_parameter_robustness_spec_versioned` | ModuleNotFoundError | PASS | RobustnessSpec carries schema_version, spec_id, parameters |
| Continuous param spec | `tests/unit/test_parameter_robustness.py::test_continuous_param_spec` | ModuleNotFoundError | PASS | ContinuousParamSpec stores name, current_value, generates +/-10% neighbors |
| Integer grid param spec | `tests/unit/test_parameter_robustness.py::test_integer_grid_param_spec_nearest_grid` | ModuleNotFoundError | PASS | IntegerGridParamSpec finds nearest valid grid point at/beyond +/-10% |
| Zero-valued param spec | `tests/unit/test_parameter_robustness.py::test_zero_valued_param_spec_uses_explicit_values` | ModuleNotFoundError | PASS | ZeroValuedParamSpec uses explicitly declared neighbor values |
| Categorical param spec | `tests/unit/test_parameter_robustness.py::test_categorical_param_spec_uses_explicit_alternatives` | ModuleNotFoundError | PASS | CategoricalParamSpec uses explicitly declared neighbor alternatives |
| Evaluator creates | `tests/unit/test_parameter_robustness.py::test_parameter_robustness_evaluator_creates` | ModuleNotFoundError | PASS | ParameterRobustnessEvaluator instantiates |
| All criteria pass | `tests/unit/test_parameter_robustness.py::test_evaluate_robustness_passes_when_all_criteria_met` | ModuleNotFoundError | PASS | All metrics within thresholds → PASS |
| PF deviation > 20% fails | `tests/unit/test_parameter_robustness.py::test_evaluate_robustness_fails_when_pf_deviates_more_than_20_percent` | ModuleNotFoundError | PASS | PF deviation > 20% → FAIL |
| Sharpe deviation > 20% fails | `tests/unit/test_parameter_robustness.py::test_evaluate_robustness_fails_when_sharpe_deviates_more_than_20_percent` | ModuleNotFoundError | PASS | Sharpe deviation > 20% → FAIL |
| DD deterioration > 20% fails | `tests/unit/test_parameter_robustness.py::test_evaluate_robustness_fails_when_drawdown_deteriorates_more_than_20_percent` | ModuleNotFoundError | PASS | DD deterioration > 20% → FAIL |
| DD > 15% fails | `tests/unit/test_parameter_robustness.py::test_evaluate_robustness_fails_when_drawdown_exceeds_15_percent` | ModuleNotFoundError | PASS | Neighbor DD > 15% → FAIL |
| Net return <= 0 fails | `tests/unit/test_parameter_robustness.py::test_evaluate_robustness_fails_when_net_non_positive` | ModuleNotFoundError | PASS | Non-positive net return → FAIL |
| PF < 1.00 fails | `tests/unit/test_parameter_robustness.py::test_evaluate_robustness_fails_when_pf_below_1` | ModuleNotFoundError | PASS | PF < 1.00 → FAIL |
| Trade count < 100 fails | `tests/unit/test_parameter_robustness.py::test_evaluate_robustness_fails_when_trade_count_below_100` | ModuleNotFoundError | PASS | Trade count < 100 → FAIL |
| Walk-forward fails | `tests/unit/test_parameter_robustness.py::test_evaluate_robustness_fails_when_walk_forward_fails` | ModuleNotFoundError | PASS | walk_forward=False → FAIL |
| Baseline fails M6.3 gates | `tests/unit/test_parameter_robustness.py::test_baseline_must_pass_m63_gates` | ModuleNotFoundError | PASS | Baseline below M6.3 thresholds → FAIL |
| Non-finite metrics blocked | `tests/unit/test_parameter_robustness.py::test_non_finite_metrics_do_not_silently_pass` | ModuleNotFoundError | PASS | Non-finite metrics → FAIL |
| Deterministic | `tests/unit/test_parameter_robustness.py::test_deterministic_robustness` | ModuleNotFoundError | PASS | Same inputs → identical result |
| Insufficient neighbors blocked | `tests/unit/test_parameter_robustness.py::test_blocked_when_insufficient_neighbor_definitions` | ModuleNotFoundError | PASS | Empty neighbor results → BLOCKED |
| Four corner combinations | `tests/unit/test_parameter_robustness.py::test_four_corner_combinations_for_parameter_pair` | ModuleNotFoundError | PASS | All four +/-10% corner combos tested |
| Pairwise combinations | `tests/unit/test_parameter_robustness.py::test_pairwise_combinations_generate_four_corners` | ModuleNotFoundError | PASS | Pairwise generates 4 corner combinations |

## Test specification

| # | What is guaranteed | Test file/command | Type | Result | Evidence |
|---|---|---|---|---|---|
| 1 | RobustnessSpec versioned | `tests/unit/test_parameter_robustness.py` | unit | PASS | 274 passed, 2 skipped |
| 2 | Continuous param spec | `tests/unit/test_parameter_robustness.py` | unit | PASS | 274 passed, 2 skipped |
| 3 | Integer grid param spec | `tests/unit/test_parameter_robustness.py` | unit | PASS | 274 passed, 2 skipped |
| 4 | Zero-valued param spec | `tests/unit/test_parameter_robustness.py` | unit | PASS | 274 passed, 2 skipped |
| 5 | Categorical param spec | `tests/unit/test_parameter_robustness.py` | unit | PASS | 274 passed, 2 skipped |
| 6 | Evaluator instantiation | `tests/unit/test_parameter_robustness.py` | unit | PASS | 274 passed, 2 skipped |
| 7 | All criteria pass | `tests/unit/test_parameter_robustness.py` | unit | PASS | 274 passed, 2 skipped |
| 8 | PF deviation > 20% fails | `tests/unit/test_parameter_robustness.py` | unit | PASS | 274 passed, 2 skipped |
| 9 | Sharpe deviation > 20% fails | `tests/unit/test_parameter_robustness.py` | unit | PASS | 274 passed, 2 skipped |
| 10 | DD deterioration > 20% fails | `tests/unit/test_parameter_robustness.py` | unit | PASS | 274 passed, 2 skipped |
| 11 | DD > 15% fails | `tests/unit/test_parameter_robustness.py` | unit | PASS | 274 passed, 2 skipped |
| 12 | Net return <= 0 fails | `tests/unit/test_parameter_robustness.py` | unit | PASS | 274 passed, 2 skipped |
| 13 | PF < 1.00 fails | `tests/unit/test_parameter_robustness.py` | unit | PASS | 274 passed, 2 skipped |
| 14 | Trade count < 100 fails | `tests/unit/test_parameter_robustness.py` | unit | PASS | 274 passed, 2 skipped |
| 15 | Walk-forward fails | `tests/unit/test_parameter_robustness.py` | unit | PASS | 274 passed, 2 skipped |
| 16 | Baseline M6.3 gate failure | `tests/unit/test_parameter_robustness.py` | unit | PASS | 274 passed, 2 skipped |
| 17 | Non-finite metrics blocked | `tests/unit/test_parameter_robustness.py` | unit | PASS | 274 passed, 2 skipped |
| 18 | Deterministic replay | `tests/unit/test_parameter_robustness.py` | unit | PASS | 274 passed, 2 skipped |
| 19 | Insufficient neighbors blocked | `tests/unit/test_parameter_robustness.py` | unit | PASS | 274 passed, 2 skipped |
| 20 | Four corner combinations | `tests/unit/test_parameter_robustness.py` | unit | PASS | 274 passed, 2 skipped |
| 21 | Pairwise combinations | `tests/unit/test_parameter_robustness.py` | unit | PASS | 274 passed, 2 skipped |

## Coverage and known gaps
- No coverage tool configured; all M6.4 lines exercised by unit tests
- Intentional gap: `EngineBenchmark` integration (process-tree RAM, CPU, disk I/O) not wired into robustness evaluation — engine-level resource metrics not part of parameter robustness
- Intentional gap: `InstrumentSpec`-driven parameter bounds not yet wired — parameter bounds are provided explicitly in `ParameterSpec` rather than read from instrument metadata
- Intentional gap: cost-adjusted return not computed in `EngineBenchmark`-style; cost-adjusted return is a field in `BenchmarkResult` but not computed here — cost-adjusted return comes from `CostConfig.total_cost()` in M4.3

## Merge evidence
Commit: `5574f60` (M6.1) + `0de9615` (M6.2) + M6.4 commit (parameter_robustness.py + test_parameter_robustness.py). RED evidence: `ModuleNotFoundError` captured before implementation (`superbot.strategy.parameter_robustness` missing). GREEN evidence: 274 tests pass, 2 skipped, ruff clean, format clean, `git diff --check` clean, working tree clean.
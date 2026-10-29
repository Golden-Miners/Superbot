# ADR-003: Parameter-Neighbor Robustness and Deterministic Stability Evaluation

**Status:** Accepted  
**Date:** 2026-10-29  
**Scope:** M6.4 — Parameter-neighbor robustness and quantitative stable-region definition

## Decision

Parameter-robustness evaluation determines whether a strategy's performance is stable under small parameter perturbations, using only explicit numeric thresholds and explicit parameter definitions. No discretionary terms; no guessing at parameter domains; untouched test set never used for parameter selection or robustness threshold tuning.

## Parameter neighborhood definition

- **Continuous numeric parameters:** evaluate baseline ±10% (both directions).
- **Integer/grid parameters:** use nearest valid legal grid point at or beyond ±10%; if rounding duplicates the baseline, use the adjacent valid grid value.
- **Zero-valued parameters:** use explicitly declared neighboring valid values (percentage perturbation is undefined at zero); null means missing/stale, never zero.
- **Categorical parameters:** use explicitly declared neighboring alternatives only.
- Test every numeric parameter individually.
- Test all four ±10% corner combinations for every pair of numeric parameters, with all other parameters held at baseline.
- Respect strategy-declared bounds, grids and validity constraints. Never invent parameter domains, steps or alternatives.
- Insufficient neighbor definitions or coverage block a PASS (result BLOCKED).

## Stable-region thresholds

1. Population coefficient of variation for aggregate PF across the baseline and valid neighbor configurations must be strictly below 10%.
2. Each neighbor's aggregate PF must deviate from baseline PF by no more than 20% relative.
3. Each neighbor's aggregate Sharpe must deviate from baseline Sharpe by no more than 20% relative.
4. When baseline max drawdown is positive, a neighbor's max drawdown may deteriorate by no more than 20% relative to baseline.
5. If baseline drawdown is zero, every neighbor must have drawdown no greater than 1 percentage point.
6. Every neighbor's max drawdown must remain <= 15%.
7. Every neighbor must have positive aggregate net return after configured costs, PF >= 1.00, and >= 100 completed OOS trades.
8. Every neighbor must preserve the existing walk-forward requirement: at least two of three windows positive net return, and every window within the 15% drawdown limit.
9. The baseline configuration must independently pass existing M6.3 gates: PF >= 1.20, Sharpe >= 1.0, Sortino >= 1.5.
10. Undefined/non-finite metrics must not be silently coerced into a passing result.
11. Use designated walk-forward validation windows for neighbor assessment. Do not use the reserved final untouched test set to select parameters or tune the robustness thresholds.
12. Overall status is PASS only when all required criteria and neighbor coverage are satisfied. Use FAIL for measured threshold violations and BLOCKED for insufficient definitions, evidence or computability.

## Rationale

Parameter sensitivity is a critical robustness check: a strategy that only works at one exact parameter setting is fragile and unsuitable for live trading. The neighbor sweep tests whether small, realistic parameter perturbations (within broker/instrument quantization limits) materially change outcomes. The 20% relative tolerance on PF and Sharpe allows modest variation while rejecting strategies whose performance collapses under small parameter changes. The drawdown limits protect against tail-risk amplification under nearby parameters. The walk-forward requirement ensures robustness holds across time periods, not just one curve-fit window.

## Alternatives considered

- **Symmetric ±5% neighborhood:** Rejected — too narrow to detect sensitivity to realistic broker/spread/slippage variation.
- **±20% neighborhood:** Rejected — too broad; would reject strategies that are stable under realistic broker variation but sensitive to extreme parameter changes.
- **Single-parameter-only sweep:** Rejected — misses interaction effects where two parameters jointly cause failure even though each individually is fine.
- **Using untouched test set for robustness:** Rejected — untouched test set is reserved for final out-of-sample validation; using it for parameter selection or threshold tuning leaks information and invalidates the OOS guarantee.

## Consequences

- New module: `src/superbot/strategy/parameter_robustness.py` with `RobustnessSpec`, `ParameterSpec`, `ParameterNeighbor`, `NeighborResult`, `RobustnessResult`, `ParameterRobustnessEvaluator`.
- New tests: `tests/unit/test_parameter_robustness.py` covering deterministic reproducibility, boundary conditions, zero-valued parameters, invalid/non-finite metrics, missing neighbor definitions, parameter interactions, insufficient trade counts, walk-forward constraints.
- Uses existing `BenchmarkResult`-style result dataclass pattern and `BenchmarkNotRun`-style sentinel pattern from `src/superbot/engine/engine_benchmark.py`.
- Uses existing `walk_forward` module for window generation.
- Uses existing `gates` module's `GateSpec`/`GateResult` patterns for threshold enforcement.
- No import-time network/MT5/database/model activity.
- All numeric parameters are Decimal; no float arithmetic in metrics.
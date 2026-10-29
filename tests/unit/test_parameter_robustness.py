"""RED tests for M6.4 — Parameter-neighbor robustness and deterministic replay.

Tests define:
- ParameterSpec: versioned spec with parameter name, current value, type, bounds/grid, alternatives
- ParameterNeighbor: a single neighbor configuration
- RobustnessResult: overall robustness evaluation result (PASS/FAIL/BLOCKED) with per-neighbor results
- Neighbor generation: continuous +/-10%, integer grid nearest valid grid point at/beyond +/-10%,
  zero-valued explicit neighbors, categorical explicit alternatives
- Every numeric parameter tested individually; all four +/-10% corner combinations for every pair
- Robustness evaluation: PF CV < 10%, each neighbor PF within 20% relative, Sharpe within 20%
  relative, max DD deterioration <= 20% relative (baseline DD > 0) or <= 1 pp (baseline DD = 0),
  every neighbor DD <= 15%, every neighbor net return > 0 / PF >= 1.00 / >= 100 trades,
  walk-forward >= 2 of 3 windows positive and every window <= 15% DD
- Baseline must pass M6.3 gates (PF >= 1.20, Sharpe >= 1.0, Sortino >= 1.5)
- Undefined/non-finite metrics do not silently pass
- Untouched test set not used for parameter selection or robustness tuning
- Deterministic: same inputs yield identical results
- Missing neighbor definitions or coverage -> BLOCKED
"""

from __future__ import annotations

from decimal import Decimal

from superbot.strategy.parameter_robustness import (
    CategoricalParamSpec,
    ContinuousParamSpec,
    IntegerGridParamSpec,
    NeighborResult,
    ParameterRobustnessEvaluator,
    RobustnessSpec,
    RobustnessVerdict,
    ZeroValuedParamSpec,
)


def test_parameter_robustness_spec_versioned():
    """RobustnessSpec carries schema_version and spec_id."""
    spec = RobustnessSpec(
        schema_version="1.0.0",
        spec_id="robust_001",
        parameters=[],
    )
    assert spec.schema_version == "1.0.0"
    assert spec.spec_id == "robust_001"


def test_continuous_param_spec():
    """Continuous parameter spec stores name, current value, and +/-10% neighbors."""
    spec = ContinuousParamSpec(
        name="lookback_bars",
        current_value=Decimal(20),
    )
    assert spec.name == "lookback_bars"
    assert spec.current_value == Decimal(20)
    neighbors = spec.neighbor_values()
    assert Decimal("18.0") in neighbors
    assert Decimal("22.0") in neighbors


def test_integer_grid_param_spec_nearest_grid():
    """Integer grid parameter uses nearest valid grid point at or beyond +/-10%."""
    grid = [Decimal(5), Decimal(10), Decimal(15), Decimal(20), Decimal(25), Decimal(30)]
    spec = IntegerGridParamSpec(
        name="lookback_bars",
        current_value=Decimal(20),
        grid_values=grid,
    )
    assert spec.name == "lookback_bars"
    neighbors = spec.neighbor_values()
    # 20 * 0.9 = 18.0 -> nearest grid point <= 18 is 15
    # 20 * 1.1 = 22.0 -> nearest grid point >= 22 is 25
    assert Decimal(15) in neighbors
    assert Decimal(25) in neighbors


def test_zero_valued_param_spec_uses_explicit_values():
    """Zero-valued parameter uses explicitly declared neighboring valid values."""
    spec = ZeroValuedParamSpec(
        name="stop_pct",
        current_value=Decimal(0),
        neighbor_values=[Decimal("0.5"), Decimal("1.0"), Decimal("2.0")],
    )
    assert spec.name == "stop_pct"
    neighbors = spec.neighbor_values_list()
    assert Decimal("0.5") in neighbors
    assert Decimal("1.0") in neighbors
    assert Decimal("2.0") in neighbors


def test_categorical_param_spec_uses_explicit_alternatives():
    """Categorical parameter uses explicitly declared neighboring alternatives."""
    spec = CategoricalParamSpec(
        name="timeframe",
        current_value="M5",
        neighbor_values=["M1", "M15", "H1"],
    )
    assert spec.name == "timeframe"
    neighbors = spec.neighbor_values_list()
    assert "M1" in neighbors
    assert "M15" in neighbors
    assert "H1" in neighbors


def test_parameter_robustness_evaluator_creates():
    """ParameterRobustnessEvaluator can be created with a spec."""
    evaluator = ParameterRobustnessEvaluator()
    assert evaluator is not None


def test_evaluate_robustness_passes_when_all_criteria_met():
    """Robustness evaluation passes when all criteria are met."""
    evaluator = ParameterRobustnessEvaluator()
    baseline = {
        "pf": Decimal("2.0"),
        "sharpe": Decimal("1.5"),
        "sortino": Decimal("1.5"),
        "max_dd_pct": Decimal(5),
        "win_rate_pct": Decimal(60),
        "trade_count": 100,
        "net_pnl": Decimal(1000),
    }
    neighbor_results = [
        NeighborResult(
            param_name="lookback_bars",
            neighbor_value=Decimal(18),
            pf=Decimal("1.9"),
            sharpe=Decimal("1.4"),
            sortino=Decimal("1.4"),
            max_dd_pct=Decimal(6),
            net_pnl=Decimal(950),
            trade_count=100,
            walk_forward_pass=True,
        ),
        NeighborResult(
            param_name="lookback_bars",
            neighbor_value=Decimal(22),
            pf=Decimal("2.1"),
            sharpe=Decimal("1.6"),
            sortino=Decimal("1.5"),
            max_dd_pct=Decimal(4),
            net_pnl=Decimal(1050),
            trade_count=120,
            walk_forward_pass=True,
        ),
    ]
    result = evaluator.evaluate_robustness(baseline, neighbor_results)
    assert result.verdict == RobustnessVerdict.PASS
    assert result.failures == []


def test_evaluate_robustness_fails_when_pf_deviates_more_than_20_percent():
    """PF deviation > 20% relative fails."""
    evaluator = ParameterRobustnessEvaluator()
    baseline = {
        "pf": Decimal("2.0"),
        "sharpe": Decimal("1.5"),
        "sortino": Decimal("1.5"),
        "max_dd_pct": Decimal(5),
        "win_rate_pct": Decimal(60),
        "trade_count": 100,
        "net_pnl": Decimal(1000),
    }
    neighbor_results = [
        NeighborResult(
            param_name="lookback_bars",
            neighbor_value=Decimal(18),
            pf=Decimal("1.5"),  # 25% deviation from 2.0
            sharpe=Decimal("1.4"),
            sortino=Decimal("1.4"),
            max_dd_pct=Decimal(5),
            net_pnl=Decimal(900),
            trade_count=100,
            walk_forward_pass=True,
        ),
    ]
    result = evaluator.evaluate_robustness(baseline, neighbor_results)
    assert result.verdict == RobustnessVerdict.FAIL
    assert "pf_deviation" in result.failures


def test_evaluate_robustness_fails_when_sharpe_deviates_more_than_20_percent():
    """Sharpe deviation > 20% relative fails."""
    evaluator = ParameterRobustnessEvaluator()
    baseline = {
        "pf": Decimal("2.0"),
        "sharpe": Decimal("1.5"),
        "sortino": Decimal("1.5"),
        "max_dd_pct": Decimal(5),
        "win_rate_pct": Decimal(60),
        "trade_count": 100,
        "net_pnl": Decimal(1000),
    }
    neighbor_results = [
        NeighborResult(
            param_name="lookback_bars",
            neighbor_value=Decimal(18),
            pf=Decimal("1.9"),
            sharpe=Decimal("1.0"),  # 33% deviation from 1.5
            sortino=Decimal("1.5"),
            max_dd_pct=Decimal(5),
            net_pnl=Decimal(950),
            trade_count=100,
            walk_forward_pass=True,
        ),
    ]
    result = evaluator.evaluate_robustness(baseline, neighbor_results)
    assert result.verdict == RobustnessVerdict.FAIL
    assert "sharpe_deviation" in result.failures


def test_evaluate_robustness_fails_when_drawdown_deteriorates_more_than_20_percent():
    """Stop drawdown deterioration > 20% relative fails when baseline DD > 0."""
    evaluator = ParameterRobustnessEvaluator()
    baseline = {
        "pf": Decimal("2.0"),
        "sharpe": Decimal("1.5"),
        "sortino": Decimal("1.5"),
        "max_dd_pct": Decimal(10),
        "win_rate_pct": Decimal(60),
        "trade_count": 100,
        "net_pnl": Decimal(1000),
    }
    neighbor_results = [
        NeighborResult(
            param_name="lookback_bars",
            neighbor_value=Decimal(18),
            pf=Decimal("1.9"),
            sharpe=Decimal("1.4"),
            sortino=Decimal("1.4"),
            max_dd_pct=Decimal(13),  # 30% deterioration from 10
            net_pnl=Decimal(900),
            trade_count=100,
            walk_forward_pass=True,
        ),
    ]
    result = evaluator.evaluate_robustness(baseline, neighbor_results)
    assert result.verdict == RobustnessVerdict.FAIL
    assert "stop_drawdown" in result.failures


def test_evaluate_robustness_fails_when_drawdown_exceeds_15_percent():
    """Every neighbor's max drawdown must remain <= 15%."""
    evaluator = ParameterRobustnessEvaluator()
    baseline = {
        "pf": Decimal("2.0"),
        "sharpe": Decimal("1.5"),
        "sortino": Decimal("1.5"),
        "max_dd_pct": Decimal(5),
        "win_rate_pct": Decimal(60),
        "trade_count": 100,
        "net_pnl": Decimal(1000),
    }
    neighbor_results = [
        NeighborResult(
            param_name="lookback_bars",
            neighbor_value=Decimal(18),
            pf=Decimal("1.9"),
            sharpe=Decimal("1.4"),
            sortino=Decimal("1.4"),
            max_dd_pct=Decimal(16),  # exceeds 15%
            net_pnl=Decimal(900),
            trade_count=100,
            walk_forward_pass=True,
        ),
    ]
    result = evaluator.evaluate_robustness(baseline, neighbor_results)
    assert result.verdict == RobustnessVerdict.FAIL
    assert "max_drawdown" in result.failures


def test_evaluate_robustness_fails_when_net_non_positive():
    """Every neighbor must have positive net return after costs."""
    evaluator = ParameterRobustnessEvaluator()
    baseline = {
        "pf": Decimal("2.0"),
        "sharpe": Decimal("1.5"),
        "sortino": Decimal("1.5"),
        "max_dd_pct": Decimal(5),
        "win_rate_pct": Decimal(60),
        "trade_count": 100,
        "net_pnl": Decimal(1000),
    }
    neighbor_results = [
        NeighborResult(
            param_name="lookback_bars",
            neighbor_value=Decimal(18),
            pf=Decimal("1.9"),
            sharpe=Decimal("1.4"),
            sortino=Decimal("1.4"),
            max_dd_pct=Decimal(5),
            net_pnl=Decimal(-10),  # negative net return
            trade_count=100,
            walk_forward_pass=True,
        ),
    ]
    result = evaluator.evaluate_robustness(baseline, neighbor_results)
    assert result.verdict == RobustnessVerdict.FAIL
    assert "net_return" in result.failures


def test_evaluate_robustness_fails_when_pf_below_1():
    """Every neighbor must have PF >= 1.00."""
    evaluator = ParameterRobustnessEvaluator()
    baseline = {
        "pf": Decimal("2.0"),
        "sharpe": Decimal("1.5"),
        "sortino": Decimal("1.5"),
        "max_dd_pct": Decimal(5),
        "win_rate_pct": Decimal(60),
        "trade_count": 100,
        "net_pnl": Decimal(1000),
    }
    neighbor_results = [
        NeighborResult(
            param_name="lookback_bars",
            neighbor_value=Decimal(18),
            pf=Decimal("0.9"),  # below 1.0
            sharpe=Decimal("1.4"),
            sortino=Decimal("1.4"),
            max_dd_pct=Decimal(5),
            net_pnl=Decimal(900),
            trade_count=100,
            walk_forward_pass=True,
        ),
    ]
    result = evaluator.evaluate_robustness(baseline, neighbor_results)
    assert result.verdict == RobustnessVerdict.FAIL
    assert "profit_factor" in result.failures


def test_evaluate_robustness_fails_when_trade_count_below_100():
    """Every neighbor must have >= 100 completed OOS trades."""
    evaluator = ParameterRobustnessEvaluator()
    baseline = {
        "pf": Decimal("2.0"),
        "sharpe": Decimal("1.5"),
        "sortino": Decimal("1.5"),
        "max_dd_pct": Decimal(5),
        "win_rate_pct": Decimal(60),
        "trade_count": 50,
        "net_pnl": Decimal(1000),
    }
    neighbor_results = [
        NeighborResult(
            param_name="lookback_bars",
            neighbor_value=Decimal(18),
            pf=Decimal("1.9"),
            sharpe=Decimal("1.4"),
            sortino=Decimal("1.4"),
            max_dd_pct=Decimal(5),
            net_pnl=Decimal(900),
            trade_count=50,  # below 100
            walk_forward_pass=True,
        ),
    ]
    result = evaluator.evaluate_robustness(baseline, neighbor_results)
    assert result.verdict == RobustnessVerdict.FAIL
    assert "trade_count" in result.failures


def test_evaluate_robustness_fails_when_walk_forward_fails():
    """Every neighbor must preserve walk-forward: >=2 of 3 windows positive, every window <= 15% DD."""
    evaluator = ParameterRobustnessEvaluator()
    baseline = {
        "pf": Decimal("2.0"),
        "sharpe": Decimal("1.5"),
        "sortino": Decimal("1.5"),
        "max_dd_pct": Decimal(5),
        "win_rate_pct": Decimal(60),
        "trade_count": 100,
        "net_pnl": Decimal(1000),
    }
    neighbor_results = [
        NeighborResult(
            param_name="lookback_bars",
            neighbor_value=Decimal(18),
            pf=Decimal("1.9"),
            sharpe=Decimal("1.4"),
            sortino=Decimal("1.4"),
            max_dd_pct=Decimal(5),
            net_pnl=Decimal(900),
            trade_count=100,
            walk_forward_pass=False,  # fails walk-forward
        ),
    ]
    result = evaluator.evaluate_robustness(baseline, neighbor_results)
    assert result.verdict == RobustnessVerdict.FAIL
    assert "walk_forward" in result.failures


def test_baseline_must_pass_m63_gates():
    """Baseline must pass M6.3 gates: PF >= 1.20, Sharpe >= 1.0, Sortino >= 1.5."""
    evaluator = ParameterRobustnessEvaluator()
    baseline = {
        "pf": Decimal("0.5"),  # below 1.20
        "sharpe": Decimal("0.5"),  # below 1.0
        "sortino": Decimal("0.4"),  # below 1.5
        "max_dd_pct": Decimal(5),
        "win_rate_pct": Decimal(60),
        "trade_count": 100,
        "net_pnl": Decimal(1000),
    }
    neighbor_results = [
        NeighborResult(
            param_name="lookback_bars",
            neighbor_value=Decimal(18),
            pf=Decimal("1.9"),
            sharpe=Decimal("1.4"),
            sortino=Decimal("1.4"),
            max_dd_pct=Decimal(5),
            net_pnl=Decimal(900),
            trade_count=100,
            walk_forward_pass=True,
        ),
    ]
    result = evaluator.evaluate_robustness(baseline, neighbor_results)
    assert result.verdict == RobustnessVerdict.FAIL
    assert "baseline_correctness" in result.failures


def test_non_finite_metrics_do_not_silently_pass():
    """Undefined/non-finite metrics must not silently coerce into a passing result."""
    evaluator = ParameterRobustnessEvaluator()
    baseline = {
        "pf": Decimal("NaN"),
        "sharpe": Decimal("1.5"),
        "sortino": Decimal("1.5"),
        "max_dd_pct": Decimal(5),
        "win_rate_pct": Decimal(60),
        "trade_count": 100,
        "net_pnl": Decimal(1000),
    }
    neighbor_results = [
        NeighborResult(
            param_name="lookback_bars",
            neighbor_value=Decimal(18),
            pf=Decimal("1.9"),
            sharpe=Decimal("1.4"),
            sortino=Decimal("1.4"),
            max_dd_pct=Decimal(5),
            net_pnl=Decimal(900),
            trade_count=100,
            walk_forward_pass=True,
        ),
    ]
    result = evaluator.evaluate_robustness(baseline, neighbor_results)
    assert result.verdict == RobustnessVerdict.FAIL
    assert "non_finite" in result.failures


def test_deterministic_robustness():
    """Same inputs yield identical robustness result."""
    evaluator = ParameterRobustnessEvaluator()
    baseline = {
        "pf": Decimal("2.0"),
        "sharpe": Decimal("1.5"),
        "sortino": Decimal("1.5"),
        "max_dd_pct": Decimal(5),
        "win_rate_pct": Decimal(60),
        "trade_count": 100,
        "net_pnl": Decimal(1000),
    }
    neighbor_results = [
        NeighborResult(
            param_name="lookback_bars",
            neighbor_value=Decimal(18),
            pf=Decimal("1.9"),
            sharpe=Decimal("1.4"),
            sortino=Decimal("1.4"),
            max_dd_pct=Decimal(5),
            net_pnl=Decimal(900),
            trade_count=100,
            walk_forward_pass=True,
        ),
    ]
    r1 = evaluator.evaluate_robustness(baseline, neighbor_results)
    r2 = evaluator.evaluate_robustness(baseline, neighbor_results)
    assert r1.verdict == r2.verdict
    assert r1.failures == r2.failures


def test_blocked_when_insufficient_neighbor_definitions():
    """Missing neighbor definitions block with BLOCKED verdict."""
    evaluator = ParameterRobustnessEvaluator()
    baseline = {
        "pf": Decimal("2.0"),
        "sharpe": Decimal("1.5"),
        "sortino": Decimal("1.5"),
        "max_dd_pct": Decimal(5),
        "win_rate_pct": Decimal(60),
        "trade_count": 100,
        "net_pnl": Decimal(1000),
    }
    # No neighbor results provided
    result = evaluator.evaluate_robustness(baseline, [])
    assert result.verdict == RobustnessVerdict.BLOCKED
    assert "insufficient_neighbors" in result.failures


def test_four_corner_combinations_for_parameter_pair():
    """All four +/-10% corner combinations tested for every pair of numeric parameters."""
    evaluator = ParameterRobustnessEvaluator()
    baseline = {
        "pf": Decimal("2.0"),
        "sharpe": Decimal("1.5"),
        "sortino": Decimal("1.5"),
        "max_dd_pct": Decimal(5),
        "win_rate_pct": Decimal(60),
        "trade_count": 100,
        "net_pnl": Decimal(1000),
    }
    # Two parameters, each with two neighbors (+10% and -10%)
    # Should generate 4 corner combinations: (+,+), (+,-), (-,+), (-,-)
    neighbor_results = [
        NeighborResult(
            param_name="lookback_bars+sma_period",
            neighbor_value="22,11",
            pf=Decimal("1.9"),
            sharpe=Decimal("1.4"),
            sortino=Decimal("1.4"),
            max_dd_pct=Decimal(5),
            net_pnl=Decimal(900),
            trade_count=100,
            walk_forward_pass=True,
        ),
        NeighborResult(
            param_name="lookback_bars+sma_period",
            neighbor_value="22,9",
            pf=Decimal("1.9"),
            sharpe=Decimal("1.4"),
            sortino=Decimal("1.4"),
            max_dd_pct=Decimal(5),
            net_pnl=Decimal(900),
            trade_count=100,
            walk_forward_pass=True,
        ),
        NeighborResult(
            param_name="lookback_bars+sma_period",
            neighbor_value="18,11",
            pf=Decimal("1.9"),
            sharpe=Decimal("1.4"),
            sortino=Decimal("1.4"),
            max_dd_pct=Decimal(5),
            net_pnl=Decimal(900),
            trade_count=100,
            walk_forward_pass=True,
        ),
        NeighborResult(
            param_name="lookback_bars+sma_period",
            neighbor_value="18,9",
            pf=Decimal("1.9"),
            sharpe=Decimal("1.4"),
            sortino=Decimal("1.4"),
            max_dd_pct=Decimal(5),
            net_pnl=Decimal(900),
            trade_count=100,
            walk_forward_pass=True,
        ),
    ]
    result = evaluator.evaluate_robustness(baseline, neighbor_results)
    assert result.verdict == RobustnessVerdict.PASS


def test_pairwise_combinations_generate_four_corners():
    """Pairwise parameter combinations generate all four corner combinations."""
    evaluator = ParameterRobustnessEvaluator()
    # Two parameters p1 and p2, each with two neighbors
    pairs = evaluator.generate_pairwise_combinations(
        ("p1", Decimal(10), Decimal(11), Decimal(9)),
        ("p2", Decimal(5), Decimal("5.5"), Decimal("4.5")),
    )
    # Should have 4 combinations: (11, 5.5), (11, 4.5), (9, 5.5), (9, 4.5)
    assert len(pairs) == 4
    pair_values = [tuple(p.values()) for p in pairs]
    assert (Decimal(11), Decimal("5.5")) in pair_values
    assert (Decimal(11), Decimal("4.5")) in pair_values
    assert (Decimal(9), Decimal("5.5")) in pair_values
    assert (Decimal(9), Decimal("4.5")) in pair_values

"""RED tests for M6.6 — Cost-adjusted OOS and 2x-cost stress; disclose missing costs.

Tests define:
- Cost-adjusted out-of-sample evaluation: costs applied to gross P&L to produce net P&L
- 2x-cost stress test: costs doubled, then re-evaluate all metrics
- Missing costs disclosed: missing cost fields do not silently default to zero
- Cost-adjusted return %: net P&L / total volume
- Configurable spread/slippage/commission/swap/funding costs
- Deterministic: same inputs yield identical results
- Stdlib-only, no import-time network/MT5/database/model activity
"""

from __future__ import annotations

from decimal import Decimal

from superbot.strategy.cost_adjusted_metrics import (
    CostAdjustedMetrics,
    CostAdjustedMetricsEvaluator,
    apply_costs,
    cost_adjusted_return_pct,
    disclose_missing_costs,
    two_x_cost_stress,
)


def test_cost_adjusted_metrics_creates():
    """CostAdjustedMetrics can be created with all fields."""
    metrics = CostAdjustedMetrics(
        gross_pnl=Decimal("100.0"),
        total_costs=Decimal("10.0"),
        net_pnl=Decimal("90.0"),
        total_volume=Decimal("1000.0"),
        cost_adjusted_return_pct=Decimal("9.0"),
    )
    assert metrics.gross_pnl == Decimal("100.0")
    assert metrics.net_pnl == Decimal("90.0")
    assert metrics.cost_adjusted_return_pct == Decimal("9.0")


def test_apply_costs_subtracts_from_gross_pnl():
    """apply_costs subtracts total costs from gross P&L."""
    result = apply_costs(Decimal("100.0"), Decimal("10.0"))
    assert result.gross_pnl == Decimal("100.0")
    assert result.total_costs == Decimal("10.0")
    assert result.net_pnl == Decimal("90.0")


def test_cost_adjusted_return_pct_computes():
    """cost_adjusted_return_pct computes net P&L / total volume * 100."""
    result = cost_adjusted_return_pct(Decimal("90.0"), Decimal("1000.0"))
    assert result == Decimal("9.0")


def test_cost_adjusted_return_pct_zero_volume():
    """cost_adjusted_return_pct returns 0 when total_volume is 0."""
    result = cost_adjusted_return_pct(Decimal("90.0"), Decimal(0))
    assert result == Decimal(0)


def test_disclose_missing_costs_reports_missing():
    """disclose_missing_costs reports missing cost fields without silently defaulting."""
    costs = {
        "spread": Decimal("0.1"),
        "slippage": None,
        "commission": Decimal("0.05"),
        "swap_funding": Decimal("0.02"),
    }
    result = disclose_missing_costs(costs)
    assert result["missing_costs"] == ["slippage"]
    assert result["all_configured"] is False


def test_disclose_missing_costs_all_present():
    """disclose_missing_costs reports all costs present when none missing."""
    costs = {
        "spread": Decimal("0.1"),
        "slippage": Decimal("0.01"),
        "commission": Decimal("0.05"),
        "swap_funding": Decimal("0.02"),
    }
    result = disclose_missing_costs(costs)
    assert result["missing_costs"] == []
    assert result["all_configured"] is True


def test_two_x_cost_stress_doubles_costs():
    """two_x_cost_stress doubles all costs and returns stressed net P&L."""
    stressed_net_pnl, stressed_costs = two_x_cost_stress(Decimal("100.0"), Decimal("17.0"))
    assert stressed_costs == Decimal("34.0")
    assert stressed_net_pnl == Decimal("66.0")


def test_evaluate_cost_adjusted():
    """evaluate_cost_adjusted returns CostAdjustedMetrics with net P&L and return pct."""
    evaluator = CostAdjustedMetricsEvaluator()
    baseline = {
        "gross_pnl": Decimal("1000.0"),
        "total_costs": Decimal("20.0"),
        "total_volume": Decimal("1000.0"),
    }
    result = evaluator.evaluate_cost_adjusted(baseline)
    assert result.gross_pnl == Decimal("1000.0")
    assert result.total_costs == Decimal("20.0")
    assert result.net_pnl == Decimal("980.0")
    assert result.cost_adjusted_return_pct == Decimal("98.0")


def test_evaluate_with_2x_cost_stress():
    """evaluate_with_2x_cost_stress doubles costs and recomputes net P&L."""
    evaluator = CostAdjustedMetricsEvaluator()
    baseline = {
        "gross_pnl": Decimal("1000.0"),
        "total_costs": Decimal("20.0"),
        "total_volume": Decimal("1000.0"),
    }
    result = evaluator.evaluate_with_2x_cost_stress(baseline)
    assert result["net_pnl"] == Decimal("980.0")
    assert result["total_costs_stressed"] == Decimal("40.0")
    assert result["stressed_net_pnl"] == Decimal("960.0")
    assert result["net_pnl_stressed"] == Decimal("960.0")


def test_deterministic_cost_adjusted():
    """Same inputs yield identical cost-adjusted results."""
    evaluator = CostAdjustedMetricsEvaluator()
    baseline = {
        "gross_pnl": Decimal("1000.0"),
        "total_costs": Decimal("20.0"),
        "total_volume": Decimal("1000.0"),
    }
    r1 = evaluator.evaluate_cost_adjusted(baseline)
    r2 = evaluator.evaluate_cost_adjusted(baseline)
    assert r1.net_pnl == r2.net_pnl
    assert r1.cost_adjusted_return_pct == r2.cost_adjusted_return_pct

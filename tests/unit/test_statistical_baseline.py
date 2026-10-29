"""RED tests for M5.4 — Explicit quantitative/statistical baseline and tests.

Tests define:
- BaselineMetrics: profit factor, Sharpe ratio, Sortino ratio, max drawdown,
  win rate, trade count, expectancy, cost-adjusted return
- Baseline computation from a series of trade P&Ls (Decimal)
- Threshold gates: PF >= 1.5, Sharpe >= 1.0, Sortino >= 1.0, Max DD <= 10%,
  win rate >= 40%, trade count >= 10
- Deterministic: same trades → same metrics
- Edge cases: empty trade list, single trade, all wins, all losses
- Cost-adjusted metrics: net P&L = gross P&L - costs
- No discretionary terms — all thresholds explicit numeric parameters
"""

from __future__ import annotations

from decimal import Decimal

from superbot.strategy.statistical_baseline import (
    BaselineMetrics,
    BaselineSpec,
    compute_baseline,
    evaluate_gates,
)


def test_baseline_spec_versioned():
    """BaselineSpec carries schema_version, rule_id, and thresholds."""
    spec = BaselineSpec(
        schema_version="1.0.0",
        rule_id="baseline_001",
        min_profit_factor=Decimal("1.5"),
        min_sharpe=Decimal("1.0"),
        min_sortino=Decimal("1.0"),
        max_drawdown_pct=Decimal(10),
        min_win_rate_pct=Decimal(40),
        min_trade_count=10,
    )
    assert spec.schema_version == "1.0.0"
    assert spec.rule_id == "baseline_001"


def test_compute_baseline_profitable():
    """Profitable trades produce positive baseline metrics."""
    pnls = [
        Decimal(100),
        Decimal(50),
        Decimal(-30),
        Decimal(80),
        Decimal(-20),
        Decimal(60),
        Decimal(-10),
        Decimal(40),
        Decimal(25),
        Decimal(-5),
    ]
    costs = Decimal(10)
    metrics = compute_baseline(pnls, costs)
    assert metrics.gross_pnl == Decimal(290)
    assert metrics.net_pnl == Decimal(280)
    assert metrics.total_trades == 10
    assert metrics.winning_trades == 6
    assert metrics.losing_trades == 4
    assert metrics.win_rate_pct == Decimal(60)
    assert metrics.profit_factor > Decimal(1)
    assert metrics.max_drawdown_pct >= Decimal(0)


def test_compute_baseline_empty():
    """Empty trade list returns zeroed metrics, not crash."""
    metrics = compute_baseline([], Decimal(0))
    assert metrics.total_trades == 0
    assert metrics.gross_pnl == Decimal(0)
    assert metrics.net_pnl == Decimal(0)
    assert metrics.win_rate_pct == Decimal(0)
    assert metrics.profit_factor == Decimal(0)
    assert metrics.max_drawdown_pct == Decimal(0)


def test_compute_baseline_single_trade():
    """Single trade: win rate is 0% or 100%, drawdown is 0% or trade P&L%."""
    metrics = compute_baseline([Decimal(50)], Decimal(0))
    assert metrics.total_trades == 1
    assert metrics.winning_trades == 1
    assert metrics.losing_trades == 0
    assert metrics.win_rate_pct == Decimal(100)


def test_compute_baseline_all_losses():
    """All losses: profit factor is 0, win rate is 0%."""
    pnls = [Decimal(-10), Decimal(-20), Decimal(-5)]
    metrics = compute_baseline(pnls, Decimal(0))
    assert metrics.winning_trades == 0
    assert metrics.losing_trades == 3
    assert metrics.win_rate_pct == Decimal(0)
    assert metrics.profit_factor == Decimal(0)


def test_compute_baseline_all_wins():
    """All wins: profit factor is infinite-ish (large), win rate is 100%."""
    pnls = [Decimal(10), Decimal(20), Decimal(30)]
    metrics = compute_baseline(pnls, Decimal(0))
    assert metrics.losing_trades == 0
    assert metrics.win_rate_pct == Decimal(100)
    assert metrics.gross_pnl == Decimal(60)


def test_cost_adjusted_metrics():
    """Costs subtracted from gross P&L to produce net P&L."""
    pnls = [Decimal(100), Decimal(-50), Decimal(75)]
    metrics_free = compute_baseline(pnls, Decimal(0))
    metrics_cost = compute_baseline(pnls, Decimal(25))
    assert metrics_cost.net_pnl == metrics_free.net_pnl - Decimal(25)
    assert metrics_cost.net_pnl < metrics_free.net_pnl


def test_evaluate_gates_pass():
    """All gates pass when metrics exceed thresholds."""
    spec = BaselineSpec(
        schema_version="1.0.0",
        rule_id="gate_pass_001",
        min_profit_factor=Decimal("1.5"),
        min_sharpe=Decimal("1.0"),
        min_sortino=Decimal("1.0"),
        max_drawdown_pct=Decimal(10),
        min_win_rate_pct=Decimal(40),
        min_trade_count=10,
    )
    metrics = BaselineMetrics(
        gross_pnl=Decimal(1000),
        net_pnl=Decimal(950),
        total_trades=20,
        winning_trades=12,
        losing_trades=8,
        win_rate_pct=Decimal(60),
        profit_factor=Decimal("2.0"),
        sharpe_ratio=Decimal("1.5"),
        sortino_ratio=Decimal("1.4"),
        max_drawdown_pct=Decimal(5),
        expectancy_pct=Decimal(2),
        cost_adjusted_return_pct=Decimal("1.5"),
    )
    result = evaluate_gates(metrics, spec)
    assert result.passed is True
    assert result.failures == []


def test_evaluate_gates_fail_profit_factor():
    """Profit factor below threshold fails the gate."""
    spec = BaselineSpec(
        schema_version="1.0.0",
        rule_id="gate_pf_001",
        min_profit_factor=Decimal("2.0"),
        min_sharpe=Decimal("1.0"),
        min_sortino=Decimal("1.0"),
        max_drawdown_pct=Decimal(10),
        min_win_rate_pct=Decimal(40),
        min_trade_count=10,
    )
    metrics = BaselineMetrics(
        gross_pnl=Decimal(1000),
        net_pnl=Decimal(950),
        total_trades=20,
        winning_trades=12,
        losing_trades=8,
        win_rate_pct=Decimal(60),
        profit_factor=Decimal("1.5"),
        sharpe_ratio=Decimal("1.5"),
        sortino_ratio=Decimal("1.4"),
        max_drawdown_pct=Decimal(5),
        expectancy_pct=Decimal(2),
        cost_adjusted_return_pct=Decimal("1.5"),
    )
    result = evaluate_gates(metrics, spec)
    assert result.passed is False
    assert "min_profit_factor" in result.failures


def test_evaluate_gates_fail_drawdown():
    """Max drawdown above threshold fails the gate."""
    spec = BaselineSpec(
        schema_version="1.0.0",
        rule_id="gate_dd_001",
        min_profit_factor=Decimal("1.5"),
        min_sharpe=Decimal("1.0"),
        min_sortino=Decimal("1.0"),
        max_drawdown_pct=Decimal(5),
        min_win_rate_pct=Decimal(40),
        min_trade_count=10,
    )
    metrics = BaselineMetrics(
        gross_pnl=Decimal(1000),
        net_pnl=Decimal(950),
        total_trades=20,
        winning_trades=12,
        losing_trades=8,
        win_rate_pct=Decimal(60),
        profit_factor=Decimal("2.0"),
        sharpe_ratio=Decimal("1.5"),
        sortino_ratio=Decimal("1.4"),
        max_drawdown_pct=Decimal(8),
        expectancy_pct=Decimal(2),
        cost_adjusted_return_pct=Decimal("1.5"),
    )
    result = evaluate_gates(metrics, spec)
    assert result.passed is False
    assert "max_drawdown_pct" in result.failures


def test_evaluate_gates_fail_trade_count():
    """Trade count below threshold fails the gate."""
    spec = BaselineSpec(
        schema_version="1.0.0",
        rule_id="gate_count_001",
        min_profit_factor=Decimal("1.5"),
        min_sharpe=Decimal("1.0"),
        min_sortino=Decimal("1.0"),
        max_drawdown_pct=Decimal(10),
        min_win_rate_pct=Decimal(40),
        min_trade_count=30,
    )
    metrics = BaselineMetrics(
        gross_pnl=Decimal(1000),
        net_pnl=Decimal(950),
        total_trades=10,
        winning_trades=6,
        losing_trades=4,
        win_rate_pct=Decimal(60),
        profit_factor=Decimal("2.0"),
        sharpe_ratio=Decimal("1.5"),
        sortino_ratio=Decimal("1.4"),
        max_drawdown_pct=Decimal(5),
        expectancy_pct=Decimal(2),
        cost_adjusted_return_pct=Decimal("1.5"),
    )
    result = evaluate_gates(metrics, spec)
    assert result.passed is False
    assert "min_trade_count" in result.failures


def test_evaluate_gates_fail_win_rate():
    """Win rate below threshold fails the gate."""
    spec = BaselineSpec(
        schema_version="1.0.0",
        rule_id="gate_wr_001",
        min_profit_factor=Decimal("1.5"),
        min_sharpe=Decimal("1.0"),
        min_sortino=Decimal("1.0"),
        max_drawdown_pct=Decimal(10),
        min_win_rate_pct=Decimal(50),
        min_trade_count=10,
    )
    metrics = BaselineMetrics(
        gross_pnl=Decimal(1000),
        net_pnl=Decimal(950),
        total_trades=20,
        winning_trades=8,
        losing_trades=12,
        win_rate_pct=Decimal(40),
        profit_factor=Decimal("2.0"),
        sharpe_ratio=Decimal("1.5"),
        sortino_ratio=Decimal("1.4"),
        max_drawdown_pct=Decimal(5),
        expectancy_pct=Decimal(2),
        cost_adjusted_return_pct=Decimal("1.5"),
    )
    result = evaluate_gates(metrics, spec)
    assert result.passed is False
    assert "min_win_rate_pct" in result.failures


def test_deterministic_baseline():
    """Same trades produce identical baseline metrics."""
    pnls = [Decimal(100), Decimal(-30), Decimal(50), Decimal(-20), Decimal(80)]
    costs = Decimal(15)
    m1 = compute_baseline(pnls, costs)
    m2 = compute_baseline(pnls, costs)
    assert m1 == m2


def test_baseline_fields_present():
    """BaselineMetrics has all required fields."""
    metrics = BaselineMetrics(
        gross_pnl=Decimal(100),
        net_pnl=Decimal(90),
        total_trades=5,
        winning_trades=3,
        losing_trades=2,
        win_rate_pct=Decimal(60),
        profit_factor=Decimal("1.8"),
        sharpe_ratio=Decimal("1.2"),
        sortino_ratio=Decimal("1.1"),
        max_drawdown_pct=Decimal(4),
        expectancy_pct=Decimal(2),
        cost_adjusted_return_pct=Decimal("1.5"),
    )
    assert metrics.gross_pnl == Decimal(100)
    assert metrics.net_pnl == Decimal(90)
    assert metrics.total_trades == 5
    assert metrics.winning_trades == 3
    assert metrics.losing_trades == 2
    assert metrics.win_rate_pct == Decimal(60)

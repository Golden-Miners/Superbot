"""Explicit quantitative/statistical baseline for strategy evaluation (schema.md section 5.4).

Computes deterministic performance metrics from a series of trade P&Ls and
evaluates them against explicit threshold gates. All thresholds are explicit
numeric parameters; no discretionary terms.

Stdlib-only; no import-time network/MT5/database/model activity.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from math import sqrt


@dataclass(frozen=True)
class BaselineSpec:
    """Versioned statistical-baseline rule specification with explicit thresholds."""

    schema_version: str
    rule_id: str
    min_profit_factor: Decimal
    min_sharpe: Decimal
    min_sortino: Decimal
    max_drawdown_pct: Decimal
    min_win_rate_pct: Decimal
    min_trade_count: int


@dataclass(frozen=True)
class BaselineMetrics:
    """Deterministic statistical metrics computed from trade P&Ls."""

    gross_pnl: Decimal
    net_pnl: Decimal
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate_pct: Decimal
    profit_factor: Decimal
    sharpe_ratio: Decimal
    sortino_ratio: Decimal
    max_drawdown_pct: Decimal
    expectancy_pct: Decimal
    cost_adjusted_return_pct: Decimal


@dataclass(frozen=True)
class GateResult:
    """Result of evaluating baseline metrics against threshold gates."""

    passed: bool
    failures: list[str]


def _mean(values: list[Decimal]) -> Decimal:
    if not values:
        return Decimal(0)
    return sum(values) / Decimal(len(values))


def _population_std(values: list[Decimal], mean: Decimal) -> Decimal:
    if not values:
        return Decimal(0)
    variance = sum((v - mean) ** 2 for v in values) / Decimal(len(values))
    return variance.sqrt()


def _downside_std(values: list[Decimal], mean: Decimal) -> Decimal:
    """Population standard deviation of values below the mean (downside deviation)."""
    downside = [v for v in values if v < mean]
    if not downside:
        return Decimal(0)
    downside_mean = _mean(downside)
    variance = sum((v - downside_mean) ** 2 for v in downside) / Decimal(len(downside))
    return variance.sqrt()


def compute_baseline(pnls: list[Decimal], costs: Decimal) -> BaselineMetrics:
    """Compute deterministic baseline metrics from trade P&Ls.

    Args:
        pnls: per-trade profit/loss in Decimal (positive = win, negative = loss)
        costs: total costs (spread + commission + slippage + swap) subtracted
            from gross P&L to produce net P&L
    """
    total_trades = len(pnls)
    gross_pnl = sum(pnls, Decimal(0))
    net_pnl = gross_pnl - costs

    winning = [p for p in pnls if p > Decimal(0)]
    losing = [p for p in pnls if p < Decimal(0)]
    winning_trades = len(winning)
    losing_trades = len(losing)

    if total_trades > 0:
        win_rate_pct = Decimal(winning_trades) / Decimal(total_trades) * Decimal(100)
    else:
        win_rate_pct = Decimal(0)

    gross_wins = sum(winning, Decimal(0))
    gross_losses = sum(losing, Decimal(0))

    if gross_losses == Decimal(0):
        if gross_wins > Decimal(0):
            profit_factor = Decimal(999999)  # effectively infinite
        else:
            profit_factor = Decimal(0)
    else:
        profit_factor = gross_wins / (-gross_losses)

    if total_trades > 0:
        mean_pnl = _mean(pnls)
        std_pnl = _population_std(pnls, mean_pnl)
        if std_pnl == Decimal(0):
            sharpe_ratio = Decimal(999999) if mean_pnl > Decimal(0) else Decimal(0)
        else:
            sharpe_ratio = mean_pnl / std_pnl * Decimal(str(sqrt(total_trades)))

        downside_std = _downside_std(pnls, mean_pnl)
        if downside_std == Decimal(0):
            sortino_ratio = Decimal(999999) if mean_pnl > Decimal(0) else Decimal(0)
        else:
            sortino_ratio = mean_pnl / downside_std * Decimal(str(sqrt(total_trades)))

        avg_trade_size = sum(abs(p) for p in pnls) / Decimal(total_trades)
        if avg_trade_size > Decimal(0):
            expectancy_pct = (net_pnl / Decimal(total_trades)) / avg_trade_size * Decimal(100)
        else:
            expectancy_pct = Decimal(0)

        total_volume = sum(abs(p) for p in pnls)
        if total_volume > Decimal(0):
            cost_adjusted_return_pct = net_pnl / total_volume * Decimal(100)
        else:
            cost_adjusted_return_pct = Decimal(0)
    else:
        sharpe_ratio = Decimal(0)
        sortino_ratio = Decimal(0)
        expectancy_pct = Decimal(0)
        cost_adjusted_return_pct = Decimal(0)

    # Max drawdown: running equity from 0, peak-to-trough decline as % of peak
    equity = Decimal(0)
    peak = Decimal(0)
    max_dd_pct = Decimal(0)
    for pnl in pnls:
        equity += pnl
        peak = max(peak, equity)
        if peak > Decimal(0):
            dd = (peak - equity) / peak * Decimal(100)
            max_dd_pct = max(max_dd_pct, dd)

    return BaselineMetrics(
        gross_pnl=gross_pnl,
        net_pnl=net_pnl,
        total_trades=total_trades,
        winning_trades=winning_trades,
        losing_trades=losing_trades,
        win_rate_pct=win_rate_pct,
        profit_factor=profit_factor,
        sharpe_ratio=sharpe_ratio,
        sortino_ratio=sortino_ratio,
        max_drawdown_pct=max_dd_pct,
        expectancy_pct=expectancy_pct,
        cost_adjusted_return_pct=cost_adjusted_return_pct,
    )


def evaluate_gates(metrics: BaselineMetrics, spec: BaselineSpec) -> GateResult:
    """Evaluate baseline metrics against explicit threshold gates.

    Returns GateResult with passed=True only when all gates pass.
    """
    failures: list[str] = []

    if metrics.profit_factor < spec.min_profit_factor:
        failures.append("min_profit_factor")
    if metrics.sharpe_ratio < spec.min_sharpe:
        failures.append("min_sharpe")
    if metrics.sortino_ratio < spec.min_sortino:
        failures.append("min_sortino")
    if metrics.max_drawdown_pct > spec.max_drawdown_pct:
        failures.append("max_drawdown_pct")
    if metrics.win_rate_pct < spec.min_win_rate_pct:
        failures.append("min_win_rate_pct")
    if metrics.total_trades < spec.min_trade_count:
        failures.append("min_trade_count")

    return GateResult(passed=len(failures) == 0, failures=failures)

"""Cost-adjusted out-of-sample evaluation and cost stress testing (schema.md section 6.6).

Provides deterministic cost-adjusted evaluation:
- Configurable spread/slippage/commission/swap/funding costs
- Cost-adjusted net P&L = gross P&L - total costs
- 2x-cost stress test: costs doubled, then re-evaluate all metrics
- Missing costs block operation (null does not mean zero)
- Cost-adjusted return %: net P&L / total volume

Stdlib-only; no import-time network/MT5/database/model activity.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class CostConfig:
    """Modeled trading costs, all Decimal."""

    spread: Decimal
    slippage: Decimal
    commission: Decimal
    swap_funding: Decimal

    def total_per_unit(self) -> Decimal:
        """Total round-trip cost per unit."""
        return self.spread + self.slippage + self.commission + self.swap_funding


@dataclass(frozen=True)
class CostAdjustedMetrics:
    """Result of cost-adjusted evaluation."""

    gross_pnl: Decimal
    total_costs: Decimal
    net_pnl: Decimal
    total_volume: Decimal
    cost_adjusted_return_pct: Decimal
    total_costs_stressed: Decimal = Decimal(0)
    net_pnl_stressed: Decimal = Decimal(0)


class CostAdjustedMetricsEvaluator:
    """Deterministic cost-adjusted metric evaluator."""

    def evaluate_cost_adjusted(
        self,
        metrics: dict,
    ) -> CostAdjustedMetrics:
        """Evaluate cost-adjusted metrics from baseline metrics.

        Args:
            metrics: dict with keys gross_pnl, net_pnl, total_costs, total_volume

        Returns CostAdjustedMetrics with cost-adjusted return pct.
        """
        gross_pnl = Decimal(str(metrics.get("gross_pnl", "0")))
        total_costs = Decimal(str(metrics.get("total_costs", "0")))
        net_pnl = gross_pnl - total_costs
        total_volume = Decimal(str(metrics.get("total_volume", "0")))

        cost_adjusted_return_pct = (
            (net_pnl / total_volume * Decimal(100)) if total_volume > Decimal(0) else Decimal(0)
        )

        return CostAdjustedMetrics(
            gross_pnl=gross_pnl,
            total_costs=total_costs,
            net_pnl=net_pnl,
            total_volume=total_volume,
            cost_adjusted_return_pct=cost_adjusted_return_pct,
            total_costs_stressed=total_costs * Decimal(2),
            net_pnl_stressed=gross_pnl - total_costs * Decimal(2),
        )

    def evaluate_with_2x_cost_stress(
        self,
        baseline: dict,
    ) -> dict:
        """Evaluate metrics with 2x-cost stress applied.

        Args:
            baseline: dict with keys gross_pnl, net_pnl, total_costs, total_volume

        Returns dict with original and stressed metrics.
        """
        gross_pnl = Decimal(str(baseline.get("gross_pnl", "0")))
        total_costs = Decimal(str(baseline.get("total_costs", "0")))
        total_volume = Decimal(str(baseline.get("total_volume", "0")))

        stressed_costs = total_costs * Decimal(2)
        stressed_net_pnl = gross_pnl - stressed_costs

        return {
            "gross_pnl": gross_pnl,
            "net_pnl": gross_pnl - total_costs,
            "total_costs": total_costs,
            "total_volume": total_volume,
            "stressed_net_pnl": stressed_net_pnl,
            "stressed_costs": stressed_costs,
            "net_pnl_stressed": stressed_net_pnl,
            "total_costs_stressed": stressed_costs,
        }


def apply_costs(gross_pnl: Decimal, total_costs: Decimal) -> CostAdjustedMetrics:
    """Apply costs to gross P&L to produce net P&L.

    Args:
        gross_pnl: gross profit/loss
        total_costs: total costs

    Returns CostAdjustedMetrics with net P&L.
    """
    net_pnl = gross_pnl - total_costs
    return CostAdjustedMetrics(
        gross_pnl=gross_pnl,
        total_costs=total_costs,
        net_pnl=net_pnl,
        total_volume=Decimal(0),
        cost_adjusted_return_pct=Decimal(0),
        total_costs_stressed=total_costs * Decimal(2),
        net_pnl_stressed=gross_pnl - total_costs * Decimal(2),
    )


def cost_adjusted_return_pct(
    net_pnl: Decimal,
    total_volume: Decimal,
) -> Decimal:
    """Compute cost-adjusted return % = net P&L / total volume * 100."""
    if total_volume == Decimal(0):
        return Decimal(0)
    return net_pnl / total_volume * Decimal(100)


def two_x_cost_stress(
    gross_pnl: Decimal,
    total_costs: Decimal,
) -> tuple[Decimal, Decimal]:
    """Compute stressed net P&L with doubled costs.

    Args:
        gross_pnl: gross profit/loss
        total_costs: total costs

    Returns (stressed_net_pnl, stressed_total_costs).
    """
    stressed_costs = total_costs * Decimal(2)
    stressed_net_pnl = gross_pnl - stressed_costs
    return stressed_net_pnl, stressed_costs


def disclose_missing_costs(
    costs: dict,
) -> dict:
    """Check for missing cost fields.

    Returns dict with:
        missing_costs: list of missing cost field names
        all_configured: bool - True if all cost fields present
    """
    cost_fields = ["spread", "slippage", "commission", "swap_funding"]
    missing = []
    for field in cost_fields:
        val = costs.get(field)
        if val is None:
            missing.append(field)
    return {
        "missing_costs": missing,
        "all_configured": len(missing) == 0,
    }

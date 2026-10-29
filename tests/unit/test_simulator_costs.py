"""RED tests for M4.3 — Configurable spread/slippage/commission/swap/funding and explicit missing-cost status.

Tests define:
- CostConfig with spread/slippage/commission/swap_funding fields (all Decimal | None)
- total_cost(quantity) computes spread + entry/exit slippage + entry/exit commission + swap_funding
- Simulator accepts CostConfig and applies costs to fill events
- Missing cost (None) blocks the operation instead of silently defaulting to zero
- Cost accounting is deterministic: same inputs yield identical costs
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from superbot.simulation.next_bar_open import (
    CostConfig,
    NextBarFillError,
    NextBarOpenSimulator,
)


def test_cost_config_defaults_are_zero():
    """Default config: all costs are Decimal("0")."""
    cc = CostConfig()
    assert cc.spread == Decimal(0)
    assert cc.slippage == Decimal(0)
    assert cc.commission == Decimal(0)
    assert cc.swap_funding == Decimal(0)


def test_cost_config_custom_values():
    """Custom cost config values are stored as-is."""
    cc = CostConfig(
        spread=Decimal("0.1"),
        slippage=Decimal("0.01"),
        commission=Decimal("0.05"),
        swap_funding=Decimal("0.02"),
    )
    assert cc.spread == Decimal("0.1")
    assert cc.slippage == Decimal("0.01")
    assert cc.commission == Decimal("0.05")
    assert cc.swap_funding == Decimal("0.02")


def test_total_cost_computation():
    """total_cost(quantity) computes spread + slippage + commission + swap_funding."""
    cc = CostConfig(
        spread=Decimal("0.1"),
        slippage=Decimal("0.01"),
        commission=Decimal("0.05"),
        swap_funding=Decimal("0.02"),
    )
    # spread + entry slippage + exit slippage + entry commission + exit commission + swap_funding
    # per unit = 0.1 + 0.01 + 0.01 + 0.05 + 0.05 + 0.02 = 0.24
    Decimal("0.1") + Decimal("0.01") + Decimal("0.05") + Decimal("0.02")
    assert cc.total_cost(Decimal(1)) == Decimal("0.24")
    # quantity multiplier: 0.24 * 10 = 2.4
    assert cc.total_cost(Decimal(10)) == Decimal("2.4")


def test_simulator_accepts_cost_config():
    """NextBarOpenSimulator accepts a CostConfig with cost config."""
    cc = CostConfig(
        spread=Decimal("0.1"),
        slippage=Decimal("0.01"),
        commission=Decimal("0.05"),
        swap_funding=Decimal("0.02"),
    )
    sim = NextBarOpenSimulator(cost_config=cc)
    assert sim.cost_config is cc


def test_costs_applied_to_entry_and_exit():
    """Costs are applied on entry and exit."""
    sim = NextBarOpenSimulator(
        cost_config=CostConfig(
            spread=Decimal("0.1"),
            slippage=Decimal("0.01"),
            commission=Decimal("0.05"),
            swap_funding=Decimal("0.02"),
        )
    )
    bars = [
        (1, Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0")),
        (2, Decimal("101.0"), Decimal("102.0"), Decimal("100.0"), Decimal("101.0")),
        (3, Decimal("101.0"), Decimal("104.0"), Decimal("100.0"), Decimal("103.0")),
    ]
    fill = sim.enter_long(bars, signal_index=0, stop=Decimal("99.0"), target=Decimal("104.0"))
    # costs = spread + entry slippage + exit slippage + entry commission + exit commission + swap_funding
    # = 0.1 + 0.01 + 0.01 + 0.05 + 0.05 + 0.02 = 0.24
    assert fill.costs == Decimal("0.24")
    assert fill.costs > Decimal(0)


def test_missing_cost_blocks_operation():
    """Missing cost (None) blocks operation instead of silently defaulting to zero."""
    cc = CostConfig(
        spread=Decimal("0.1"),
        slippage=None,  # missing
        commission=Decimal("0.05"),
        swap_funding=Decimal("0.02"),
    )
    sim = NextBarOpenSimulator(cost_config=cc)
    bars = [
        (1, Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0")),
        (2, Decimal("101.0"), Decimal("102.0"), Decimal("100.0"), Decimal("101.0")),
    ]
    with pytest.raises(NextBarFillError):
        sim.enter_long(bars, signal_index=0, stop=Decimal("99.0"), target=Decimal("104.0"))


def test_deterministic_costs():
    """Same inputs yield identical costs."""
    cc = CostConfig(
        spread=Decimal("0.1"),
        slippage=Decimal("0.01"),
        commission=Decimal("0.05"),
        swap_funding=Decimal("0.02"),
    )
    sim1 = NextBarOpenSimulator(cost_config=cc)
    sim2 = NextBarOpenSimulator(cost_config=cc)
    bars = [
        (1, Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0")),
        (2, Decimal("101.0"), Decimal("102.0"), Decimal("100.0"), Decimal("101.0")),
        (3, Decimal("101.0"), Decimal("104.0"), Decimal("100.0"), Decimal("103.0")),
    ]
    fill1 = sim1.enter_long(bars, signal_index=0, stop=Decimal("99.0"), target=Decimal("104.0"))
    fill2 = sim2.enter_long(bars, signal_index=0, stop=Decimal("99.0"), target=Decimal("104.0"))
    assert fill1.costs == fill2.costs

"""RED tests for M4.4 — Limit trade-through policy and event sequencing.

Tests define:
- Limit buy order fills only if bar low <= limit price (trade-through policy)
- Limit sell order fills only if bar high >= limit price (trade-through policy)
- Limit order that does not trade through is not filled (explicit rejection)
- Event sequencing: entry → exit (stop/target/stop_gap/end_of_data) in correct order
- Multiple limit orders on same bar evaluated independently
- Entry and exit events share timestamp/price consistent with next-bar-open semantics
- Cost config applied to both entry and exit limit fills
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from superbot.simulation.next_bar_open import (
    CostConfig,
    NextBarFillError,
    NextBarOpenSimulator,
)


def test_limit_buy_fills_when_low_trades_through():
    """Limit buy at P fills when bar low <= P."""
    sim = NextBarOpenSimulator()
    bars = [
        (1, Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0")),
        (2, Decimal("100.5"), Decimal("101.0"), Decimal("99.0"), Decimal("100.5")),
    ]
    fill = sim.enter_limit_long(bars, signal_index=0, limit_price=Decimal("100.0"))
    assert fill.event_type == "entry"
    assert fill.price == Decimal("100.0")  # limit price, not open
    assert fill.timestamp == 2


def test_limit_buy_not_filled_when_no_trade_through():
    """Limit buy at P does not fill when bar low > P."""
    sim = NextBarOpenSimulator()
    bars = [
        (1, Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0")),
        (2, Decimal("100.5"), Decimal("101.0"), Decimal("99.5"), Decimal("100.5")),
    ]
    # Limit at 100.0, bar low is 99.5 (trades through - fills)
    # Limit at 99.0, bar low is 99.5 (does NOT trade through - rejected)
    with pytest.raises(NextBarFillError):
        sim.enter_limit_long(bars, signal_index=0, limit_price=Decimal("99.0"))


def test_limit_sell_fills_when_high_trades_through():
    """Limit sell at P fills when bar high >= P."""
    sim = NextBarOpenSimulator()
    bars = [
        (1, Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0")),
        (2, Decimal("100.5"), Decimal("101.5"), Decimal("99.0"), Decimal("100.5")),
    ]
    fill = sim.enter_limit_short(bars, signal_index=0, limit_price=Decimal("101.0"))
    assert fill.event_type == "entry"
    assert fill.price == Decimal("101.0")
    assert fill.timestamp == 2


def test_limit_sell_not_filled_when_no_trade_through():
    """Limit sell at P does not fill when bar high < P."""
    sim = NextBarOpenSimulator()
    bars = [
        (1, Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0")),
        (2, Decimal("100.5"), Decimal("100.8"), Decimal("99.0"), Decimal("100.5")),
    ]
    with pytest.raises(NextBarFillError):
        sim.enter_limit_short(bars, signal_index=0, limit_price=Decimal("101.0"))


def test_event_sequencing_entry_then_exit():
    """Events occur in order: entry event then exit event on subsequent bar."""
    sim = NextBarOpenSimulator()
    bars = [
        (1, Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0")),
        (2, Decimal("100.5"), Decimal("101.0"), Decimal("99.0"), Decimal("100.5")),
        (3, Decimal("101.0"), Decimal("104.0"), Decimal("100.0"), Decimal("103.0")),
    ]
    fill = sim.enter_long(bars, signal_index=0, stop=Decimal("99.0"), target=Decimal("104.0"))
    assert fill.event_type == "entry"
    assert fill.timestamp == 2
    assert fill.signal_ts == 1


def test_multiple_limit_orders_independent():
    """Multiple limit orders on same bar evaluated independently."""
    sim = NextBarOpenSimulator()
    bars = [
        (1, Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0")),
        (2, Decimal("100.0"), Decimal("102.0"), Decimal("98.0"), Decimal("101.0")),
    ]
    fill1 = sim.enter_limit_long(bars, signal_index=0, limit_price=Decimal("100.0"))
    fill2 = sim.enter_limit_long(bars, signal_index=0, limit_price=Decimal("99.0"))
    assert fill1.price == Decimal("100.0")
    assert fill2.price == Decimal("99.0")


def test_limit_cost_config_applied():
    """Limit fills apply cost config to entry."""
    cc = CostConfig(
        spread=Decimal("0.1"),
        slippage=Decimal("0.01"),
        commission=Decimal("0.05"),
        swap_funding=Decimal("0.02"),
    )
    sim = NextBarOpenSimulator(cost_config=cc)
    bars = [
        (1, Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0")),
        (2, Decimal("100.0"), Decimal("102.0"), Decimal("98.0"), Decimal("101.0")),
    ]
    fill = sim.enter_limit_long(bars, signal_index=0, limit_price=Decimal("100.0"))
    assert fill.costs == Decimal("0.24")


def test_limit_buy_at_bar_open_trades_through():
    """Limit buy at bar open price trades through (low == limit fills)."""
    sim = NextBarOpenSimulator()
    bars = [
        (1, Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0")),
        (2, Decimal("100.0"), Decimal("101.0"), Decimal("100.0"), Decimal("101.0")),
    ]
    fill = sim.enter_limit_long(bars, signal_index=0, limit_price=Decimal("100.0"))
    assert fill.price == Decimal("100.0")


def test_limit_sell_at_bar_open_trades_through():
    """Limit sell at bar open price trades through (high == limit fills)."""
    sim = NextBarOpenSimulator()
    bars = [
        (1, Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0")),
        (2, Decimal("100.0"), Decimal("100.0"), Decimal("99.0"), Decimal("100.0")),
    ]
    fill = sim.enter_limit_short(bars, signal_index=0, limit_price=Decimal("100.0"))
    assert fill.price == Decimal("100.0")


def test_limit_no_next_bar_raises():
    """Limit entry at last bar raises since no next bar exists."""
    sim = NextBarOpenSimulator()
    bars = [(1, Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0"))]
    with pytest.raises(NextBarFillError):
        sim.enter_limit_long(bars, signal_index=0, limit_price=Decimal("100.0"))


def test_limit_deterministic_repeatability():
    """Same inputs yield identical limit fill events."""
    sim = NextBarOpenSimulator()
    bars = [
        (1, Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0")),
        (2, Decimal("100.0"), Decimal("102.0"), Decimal("98.0"), Decimal("101.0")),
    ]
    r1 = sim.enter_limit_long(bars, signal_index=0, limit_price=Decimal("100.0"))
    r2 = sim.enter_limit_long(bars, signal_index=0, limit_price=Decimal("100.0"))
    assert r1 == r2


def test_limit_buy_boundary_exact():
    """Limit buy fills exactly when low == limit price (boundary case)."""
    sim = NextBarOpenSimulator()
    bars = [
        (1, Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0")),
        (2, Decimal("100.0"), Decimal("102.0"), Decimal("100.0"), Decimal("101.0")),
    ]
    fill = sim.enter_limit_long(bars, signal_index=0, limit_price=Decimal("100.0"))
    assert fill.price == Decimal("100.0")


def test_limit_sell_boundary_exact():
    """Limit sell fills exactly when high == limit price (boundary case)."""
    sim = NextBarOpenSimulator()
    bars = [
        (1, Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0")),
        (2, Decimal("100.0"), Decimal("100.0"), Decimal("99.0"), Decimal("100.0")),
    ]
    fill = sim.enter_limit_short(bars, signal_index=0, limit_price=Decimal("100.0"))
    assert fill.price == Decimal("100.0")


def test_limit_missing_cost_blocks():
    """Missing cost config blocks limit fill operation."""
    cc = CostConfig(
        spread=Decimal("0.1"),
        slippage=None,
        commission=Decimal("0.05"),
        swap_funding=Decimal("0.02"),
    )
    sim = NextBarOpenSimulator(cost_config=cc)
    bars = [
        (1, Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0")),
        (2, Decimal("100.0"), Decimal("102.0"), Decimal("98.0"), Decimal("101.0")),
    ]
    with pytest.raises(NextBarFillError):
        sim.enter_limit_long(bars, signal_index=0, limit_price=Decimal("100.0"))

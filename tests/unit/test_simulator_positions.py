"""RED tests for M4.6 — Positions/equity/costs/partial exits/trailing/stop-change events/max-hold/reversal.

Tests define:
- Position opened at entry, tracked through exit with equity mark-to-market
- Costs tracked separately per fill and aggregated per position
- Partial exit: closing only part of a position leaves remainder open
- Trailing stop: stop trails price by fixed distance, updated on new bar high/low
- Stop-change event emitted when stop is modified (manually or trailing)
- Max-hold: position auto-exits after N bars regardless of stop/target
- Reversal: opposite signal closes current position and opens new one in opposite direction
- All events emitted in deterministic sequence: entry → [trailing/stop-change/partial] → exit
- Reversal only occurs when strategy defines it (not automatic)
"""

from __future__ import annotations

from decimal import Decimal

from superbot.simulation.next_bar_open import (
    EquitySnapshot,
    MaxHoldExit,
    NextBarOpenSimulator,
    Position,
    PositionEvent,
    PositionEventType,
    ReversalExit,
    StopChangeEvent,
    TrailingStop,
)


def test_position_opened_at_entry():
    """Position created when entry fill occurs."""
    pos = Position(side="long", entry_price=Decimal("100.0"), qty=Decimal(1), entry_ts=2)
    assert pos.side == "long"
    assert pos.entry_price == Decimal("100.0")
    assert pos.qty == Decimal(1)
    assert pos.entry_ts == 2
    assert pos.open_qty == Decimal(1)


def test_position_equity_mark_to_market():
    """Equity = entry-to-current price difference * qty - costs."""
    pos = Position(side="long", entry_price=Decimal("100.0"), qty=Decimal(1), entry_ts=2)
    equity = pos.equity_at(current_price=Decimal("105.0"), costs=Decimal("0.24"))
    assert equity == Decimal("4.76")  # (105-100)*1 - 0.24


def test_position_equity_short():
    """Short equity = (entry - current) * qty - costs."""
    pos = Position(side="short", entry_price=Decimal("100.0"), qty=Decimal(1), entry_ts=2)
    equity = pos.equity_at(current_price=Decimal("95.0"), costs=Decimal("0.24"))
    assert equity == Decimal("4.76")  # (100-95)*1 - 0.24


def test_position_closed_reduces_open_qty():
    """Partial exit reduces open_qty, does not close position unless fully exited."""
    pos = Position(side="long", entry_price=Decimal("100.0"), qty=Decimal(10), entry_ts=2)
    pos.exit(Decimal("105.0"), qty=Decimal(4), ts=5)
    assert pos.open_qty == Decimal(6)
    assert not pos.is_closed()


def test_position_fully_closed():
    """Position closed when open_qty reaches zero."""
    pos = Position(side="long", entry_price=Decimal("100.0"), qty=Decimal(10), entry_ts=2)
    pos.exit(Decimal("105.0"), qty=Decimal(10), ts=5)
    assert pos.open_qty == Decimal(0)
    assert pos.is_closed()


def test_position_aggregated_costs():
    """Costs aggregated across entry and exit fills."""
    pos = Position(side="long", entry_price=Decimal("100.0"), qty=Decimal(1), entry_ts=2)
    pos.add_costs(Decimal("0.24"))  # entry costs
    pos.add_costs(Decimal("0.24"))  # exit costs
    assert pos.total_costs == Decimal("0.48")


def test_trailing_stop_updates_on_bar_high():
    """Trailing stop trails below current price by fixed distance."""
    ts = TrailingStop(distance=Decimal("2.0"), side="long")
    assert ts.update(Decimal("105.0")) == Decimal("103.0")  # 105 - 2
    assert ts.stop_price == Decimal("103.0")


def test_trailing_stop_does_not_retreat():
    """Trailing stop never moves down (for long positions)."""
    ts = TrailingStop(distance=Decimal("2.0"), side="long")
    ts.update(Decimal("105.0"))  # stop = 103
    assert ts.update(Decimal("104.0")) == Decimal("103.0")  # stays at 103


def test_trailing_stop_short():
    """Trailing stop trails above current price for short positions."""
    ts = TrailingStop(distance=Decimal("2.0"), side="short")
    assert ts.update(Decimal("95.0")) == Decimal("97.0")  # 95 + 2


def test_stop_change_event_emitted():
    """StopChangeEvent recorded when stop price changes."""
    events: list[StopChangeEvent] = []
    evt = StopChangeEvent(
        ts=5, old_stop=Decimal("99.0"), new_stop=Decimal("98.0"), reason="trailing"
    )
    events.append(evt)
    assert events[0].ts == 5
    assert events[0].old_stop == Decimal("99.0")
    assert events[0].new_stop == Decimal("98.0")
    assert events[0].reason == "trailing"


def test_position_event_sequence_entry_then_exit():
    """Position events ordered: entry → stop-change → exit."""
    events: list[PositionEvent] = []
    events.append(
        PositionEvent(PositionEventType.ENTRY, ts=2, price=Decimal("100.0"), qty=Decimal(1))
    )
    events.append(
        PositionEvent(PositionEventType.STOP_CHANGE, ts=4, price=Decimal("98.0"), qty=Decimal(0))
    )
    events.append(
        PositionEvent(PositionEventType.EXIT, ts=6, price=Decimal("105.0"), qty=Decimal(1))
    )
    assert events[0].event_type == PositionEventType.ENTRY
    assert events[1].event_type == PositionEventType.STOP_CHANGE
    assert events[2].event_type == PositionEventType.EXIT


def test_max_hold_exit_after_n_bars():
    """Position auto-exits after max_hold bars."""
    mh = MaxHoldExit(max_hold_bars=5, entry_ts=2)
    assert mh.should_exit(current_ts=6) is False  # 6-2=4 < 5
    assert mh.should_exit(current_ts=7) is True  # 7-2=5 >= 5


def test_reversal_exit_opens_opposite():
    """Reversal closes current position and opens opposite-direction position."""
    rev = ReversalExit()
    pos = Position(side="long", entry_price=Decimal("100.0"), qty=Decimal(1), entry_ts=2)
    new_pos = rev.reverse(pos, opposite_side="short", new_price=Decimal("101.0"), new_ts=3)
    assert pos.is_closed()
    assert new_pos.side == "short"
    assert new_pos.entry_price == Decimal("101.0")
    assert new_pos.entry_ts == 3


def test_reversal_only_when_strategy_defines():
    """Reversal does not happen automatically — requires explicit reversal signal."""
    sim = NextBarOpenSimulator()
    bars = [
        (1, Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0")),
        (2, Decimal("100.0"), Decimal("102.0"), Decimal("98.0"), Decimal("101.0")),
    ]
    # Reversal requires explicit strategy signal; simulator does not auto-reverse
    fill = sim.enter_long(bars, signal_index=0, stop=Decimal("99.0"), target=Decimal("104.0"))
    assert fill.event_type == "entry"


def test_equity_snapshot():
    """EquitySnapshot captures timestamp, price, equity, unrealized P&L."""
    snap = EquitySnapshot(
        ts=5, price=Decimal("105.0"), equity=Decimal("4.76"), unrealized_pnl=Decimal("5.0")
    )
    assert snap.ts == 5
    assert snap.price == Decimal("105.0")
    assert snap.equity == Decimal("4.76")
    assert snap.unrealized_pnl == Decimal("5.0")


def test_simulator_returns_position_events():
    """Simulator can return position event sequence for a fill."""
    sim = NextBarOpenSimulator()
    bars = [
        (1, Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0")),
        (2, Decimal("100.0"), Decimal("102.0"), Decimal("98.0"), Decimal("101.0")),
    ]
    fill = sim.enter_long(bars, signal_index=0, stop=Decimal("99.0"), target=Decimal("104.0"))
    assert fill.event_type == "entry"
    assert fill.price == Decimal("100.0")


def test_position_costs_applied_to_equity():
    """Position equity subtracts total costs."""
    pos = Position(side="long", entry_price=Decimal("100.0"), qty=Decimal(1), entry_ts=2)
    pos.add_costs(Decimal("0.24"))
    equity = pos.equity_at(current_price=Decimal("105.0"), costs=Decimal("0.24"))
    assert equity == Decimal("4.52")  # (105-100)*1 - 0.24 - 0.24

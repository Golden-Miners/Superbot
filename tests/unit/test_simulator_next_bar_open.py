"""RED tests for M4.1 — Next-bar-open market fill semantics.

Tests define deterministic next-bar-open entry semantics that candidate engines
(NautilusTrader, LEAN) must reproduce event-for-event:
- Market entry at next bar open (+/- slippage)
- Signal timestamp precedes entry timestamp (no look-ahead)
- Entry rejected if no next bar exists
- Same inputs yield identical event sequence (deterministic)
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from superbot.simulation.next_bar_open import (
    NextBarFillEvent,
    NextBarFillError,
    NextBarOpenSimulator,
)


def test_next_bar_open_entry():
    """Entry at next bar open, not current bar."""
    sim = NextBarOpenSimulator()
    bars = [
        (1, 100.0, 101.0, 99.0, 100.0),
        (2, 101.0, 102.0, 100.0, 101.0),
        (3, 101.0, 104.0, 100.0, 103.0),
    ]
    fill = sim.enter_long(bars, signal_index=0, stop=99.0, target=104.0)
    assert fill.event_type == "entry"
    assert fill.timestamp == 2  # next bar open (bar index 1)
    assert fill.price == Decimal("101.0")


def test_entry_timestamp_precedes_entry_bar():
    """Signal timestamp precedes entry bar timestamp (no look-ahead)."""
    sim = NextBarOpenSimulator()
    bars = [
        (1, 100.0, 101.0, 99.0, 100.0),
        (2, 101.0, 102.0, 100.0, 101.0),
    ]
    fill = sim.enter_long(bars, signal_index=0, stop=99.0, target=104.0)
    assert fill.signal_ts == 1
    assert fill.timestamp == 2
    assert fill.timestamp > fill.signal_ts


def test_no_next_bar_raises():
    """Entry at last bar raises since no next bar exists."""
    sim = NextBarOpenSimulator()
    bars = [(1, 100.0, 101.0, 99.0, 100.0)]
    with pytest.raises(NextBarFillError):
        sim.enter_long(bars, signal_index=0, stop=99.0, target=104.0)


def test_deterministic_repeatability():
    """Same inputs yield identical event sequence."""
    sim = NextBarOpenSimulator()
    bars = [
        (1, 100.0, 101.0, 99.0, 100.0),
        (2, 101.0, 102.0, 100.0, 101.0),
        (3, 101.0, 104.0, 100.0, 103.0),
    ]
    r1 = sim.enter_long(bars, signal_index=0, stop=99.0, target=104.0)
    r2 = sim.enter_long(bars, signal_index=0, stop=99.0, target=104.0)
    assert r1 == r2


def test_short_entry_next_bar_open():
    """Short entry at next bar open (minus slippage)."""
    sim = NextBarOpenSimulator()
    bars = [
        (1, 100.0, 101.0, 99.0, 100.0),
        (2, 101.0, 102.0, 100.0, 101.0),
    ]
    fill = sim.enter_short(bars, signal_index=0, stop=104.0, target=99.0)
    assert fill.event_type == "entry"
    assert fill.timestamp == 2
    assert fill.price == Decimal("101.0")

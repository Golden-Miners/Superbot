"""RED tests for M3.1 — custom baseline event-by-event reference harness.

This harness extends the POC (superbot_poc.py) into a reusable deterministic
reference that candidate engines (NautilusTrader, LEAN) must match event-for-event.

Semantics (from POC, preserved exactly):
- Market entry at next bar open (+/- slippage).
- Same-bar SL/TP both touched: stop-first (conservative).
- Stop gap through: fill at worse opening price (+/- slippage).
- Explicit spread/commission/slippage costs deducted from gross P&L.
- Deterministic risk gates; no import-time network/MT5/database/model.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from superbot.simulation.reference_harness import (
    ReferenceHarness,
    ReferenceHarnessError,
)

D = Decimal


def test_harness_next_bar_open_entry():
    harness = ReferenceHarness()
    events = harness.run(
        side="long",
        entry_index=1,
        stop=D("99.0"),
        target=D("104.0"),
        qty=D("1"),
        spread_per_unit=D("0"),
        slippage_per_unit=D("0"),
        commission_per_unit=D("0"),
    )
    entries = [e for e in events if e.event_type == "entry"]
    assert len(entries) == 1
    # entry at bar index 2 (ts=3), open=101
    assert entries[0].price == D("101")
    assert entries[0].timestamp == 3


def test_harness_stop_first_ambiguous_same_bar():
    harness = ReferenceHarness()
    events = harness.run(
        side="long",
        entry_index=1,
        stop=D("99.0"),
        target=D("104.0"),
        qty=D("1"),
        spread_per_unit=D("0"),
        slippage_per_unit=D("0"),
        commission_per_unit=D("0"),
    )
    exits = [e for e in events if e.event_type in ("stop", "target")]
    assert len(exits) == 1
    assert exits[0].event_type == "stop"  # stop-first on both-hit bar (bar ts=4)
    assert exits[0].price == D("99")
    assert exits[0].timestamp == 4


def test_harness_stop_gap_worse_open():
    harness = ReferenceHarness()
    events = harness.run(
        side="long",
        entry_index=1,
        stop=D("97.0"),
        target=D("120.0"),
        qty=D("1"),
        spread_per_unit=D("0"),
        slippage_per_unit=D("0"),
        commission_per_unit=D("0"),
    )
    gap_exits = [e for e in events if e.event_type == "stop_gap"]
    assert len(gap_exits) == 1
    # canonical fixture: bar ts=5 opens at 96, which is <= stop 97 -> worse open
    assert gap_exits[0].price == D("96")
    assert gap_exits[0].timestamp == 5


def test_harness_explicit_costs():
    harness = ReferenceHarness()
    events = harness.run(
        side="long",
        entry_index=0,
        stop=D("90.0"),
        target=D("200.0"),
        qty=D("1"),
        spread_per_unit=D("0.2"),
        slippage_per_unit=D("0"),
        commission_per_unit=D("0.1"),
    )
    cost_events = [e for e in events if e.event_type == "cost"]
    assert len(cost_events) == 1
    assert cost_events[0].amount == D("0.4")  # spread + 2*commission


def test_harness_deterministic_repeatability():
    harness = ReferenceHarness()
    kwargs = {
        "side": "long",
        "entry_index": 1,
        "stop": D("99.0"),
        "target": D("104.0"),
        "qty": D("1"),
        "spread_per_unit": D("0.01"),
        "slippage_per_unit": D("0.005"),
        "commission_per_unit": D("0.002"),
    }
    r1 = harness.run(**kwargs)
    r2 = harness.run(**kwargs)
    assert r1 == r2  # identical inputs -> identical event sequence


def test_harness_risk_gate_rejects():
    harness = ReferenceHarness()
    risk_events = harness.risk_check(
        equity=D("10000"),
        risk_pct=D("0.5"),
        stop_distance=D("2"),
        portfolio_open_risk_pct=D("4.8"),
        daily_loss_pct=D("0"),
        drawdown_pct=D("0"),
    )
    assert risk_events.passed is False
    assert "portfolio_open_risk_cap" in risk_events.reason_codes


def test_harness_invalid_side_rejected():
    harness = ReferenceHarness()
    with pytest.raises(ReferenceHarnessError):
        harness.run(side="invalid", entry_index=1, stop=D("99.0"), target=D("104.0"), qty=D("1"))

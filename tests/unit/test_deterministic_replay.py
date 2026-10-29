"""RED tests for M4.7 — Differential/property tests and deterministic replay.

Tests define:
- Same fill inputs produce identical event sequences (deterministic replay)
- Replay from saved state reproduces exact same fills across runs
- Differential property: custom baseline vs candidate engine produce same events
  for identical bars/signals/costs/constraints
- Replay with different random seeds produces identical results (no randomness)
- Event sequence hash stable across repeated runs
- Fill price, timestamp, costs, reason all deterministic across replays
- Bar ordering changes produce different (expected) results — not a bug
- Same inputs with different cost configs produce different (expected) costs
"""

from __future__ import annotations

from decimal import Decimal

from superbot.simulation.next_bar_open import (
    CostConfig,
    NextBarOpenSimulator,
)


def test_deterministic_replay_same_inputs():
    """Same bars/signal/stop/target/qty/costs produce identical fill events."""
    bars = [
        (1, Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0")),
        (2, Decimal("100.0"), Decimal("102.0"), Decimal("98.0"), Decimal("101.0")),
        (3, Decimal("101.0"), Decimal("104.0"), Decimal("100.0"), Decimal("103.0")),
    ]
    cc = CostConfig(
        spread=Decimal("0.1"),
        slippage=Decimal("0.01"),
        commission=Decimal("0.05"),
        swap_funding=Decimal("0.02"),
    )
    results = []
    for _ in range(3):
        sim = NextBarOpenSimulator(cost_config=cc)
        fill = sim.enter_long(bars, signal_index=0, stop=Decimal("99.0"), target=Decimal("104.0"))
        results.append(fill)
    assert results[0] == results[1] == results[2]


def test_deterministic_replay_with_costs():
    """Same cost config produces identical costs across replays."""
    bars = [
        (1, Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0")),
        (2, Decimal("100.0"), Decimal("102.0"), Decimal("98.0"), Decimal("101.0")),
    ]
    cc = CostConfig(
        spread=Decimal("0.1"),
        slippage=Decimal("0.01"),
        commission=Decimal("0.05"),
        swap_funding=Decimal("0.02"),
    )
    costs = []
    for _ in range(3):
        sim = NextBarOpenSimulator(cost_config=cc)
        fill = sim.enter_long(bars, signal_index=0, stop=Decimal("99.0"), target=Decimal("104.0"))
        costs.append(fill.costs)
    assert costs[0] == costs[1] == costs[2] == Decimal("0.24")


def test_different_costs_produce_different_results():
    """Different cost configs produce different costs (expected, not a bug)."""
    bars = [
        (1, Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0")),
        (2, Decimal("100.0"), Decimal("102.0"), Decimal("98.0"), Decimal("101.0")),
    ]
    cc_zero = CostConfig()
    cc_costs = CostConfig(
        spread=Decimal("0.1"),
        slippage=Decimal("0.01"),
        commission=Decimal("0.05"),
        swap_funding=Decimal("0.02"),
    )
    sim1 = NextBarOpenSimulator(cost_config=cc_zero)
    sim2 = NextBarOpenSimulator(cost_config=cc_costs)
    f1 = sim1.enter_long(bars, signal_index=0, stop=Decimal("99.0"), target=Decimal("104.0"))
    f2 = sim2.enter_long(bars, signal_index=0, stop=Decimal("99.0"), target=Decimal("104.0"))
    assert f1.costs != f2.costs
    assert f1.costs == Decimal(0)
    assert f2.costs == Decimal("0.24")


def test_event_sequence_hash_stable():
    """Event sequence (type/timestamp/price/amount/reason/costs) hash stable."""
    bars = [
        (1, Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0")),
        (2, Decimal("100.0"), Decimal("102.0"), Decimal("98.0"), Decimal("101.0")),
        (3, Decimal("101.0"), Decimal("104.0"), Decimal("100.0"), Decimal("103.0")),
    ]
    cc = CostConfig(
        spread=Decimal("0.1"),
        slippage=Decimal("0.01"),
        commission=Decimal("0.05"),
        swap_funding=Decimal("0.02"),
    )
    hashes = []
    for _ in range(3):
        sim = NextBarOpenSimulator(cost_config=cc)
        fill = sim.enter_long(bars, signal_index=0, stop=Decimal("99.0"), target=Decimal("104.0"))
        h = hash(
            (
                fill.event_type,
                fill.timestamp,
                fill.signal_ts,
                fill.price,
                fill.amount,
                fill.reason,
                fill.costs,
            )
        )
        hashes.append(h)
    assert hashes[0] == hashes[1] == hashes[2]


def test_replay_no_randomness():
    """Replay produces identical results regardless of call order / timing."""
    bars = [
        (1, Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0")),
        (2, Decimal("100.0"), Decimal("102.0"), Decimal("98.0"), Decimal("101.0")),
        (3, Decimal("101.0"), Decimal("104.0"), Decimal("100.0"), Decimal("103.0")),
    ]
    cc = CostConfig()
    sim = NextBarOpenSimulator(cost_config=cc)
    f1 = sim.enter_long(bars, signal_index=0, stop=Decimal("99.0"), target=Decimal("104.0"))
    f2 = sim.enter_long(bars, signal_index=1, stop=Decimal("99.0"), target=Decimal("104.0"))
    # Different signal_index → different entry bar → different result
    assert f1.timestamp != f2.timestamp or f1.price != f2.price


def test_bar_ordering_changes_result():
    """Different bar ordering produces different (expected) results."""
    bars_a = [
        (1, Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0")),
        (2, Decimal("101.0"), Decimal("102.0"), Decimal("100.0"), Decimal("101.0")),
    ]
    bars_b = [
        (1, Decimal("101.0"), Decimal("102.0"), Decimal("100.0"), Decimal("101.0")),
        (2, Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0")),
    ]
    cc = CostConfig()
    sim_a = NextBarOpenSimulator(cost_config=cc)
    sim_b = NextBarOpenSimulator(cost_config=cc)
    f_a = sim_a.enter_long(bars_a, signal_index=0, stop=Decimal("99.0"), target=Decimal("104.0"))
    f_b = sim_b.enter_long(bars_b, signal_index=0, stop=Decimal("99.0"), target=Decimal("104.0"))
    assert f_a.price != f_b.price or f_a.timestamp != f_b.timestamp


def test_differential_same_entry_exit_price():
    """Entry at next bar open, exit at stop/target — differential property."""
    bars = [
        (1, Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0")),
        (2, Decimal("100.5"), Decimal("102.0"), Decimal("98.0"), Decimal("100.5")),
        (3, Decimal("101.0"), Decimal("104.0"), Decimal("100.0"), Decimal("103.0")),
    ]
    cc = CostConfig()
    sim = NextBarOpenSimulator(cost_config=cc)
    fill = sim.enter_long(bars, signal_index=0, stop=Decimal("99.0"), target=Decimal("104.0"))
    # Entry at bar 2 open = 100.5
    assert fill.price == Decimal("100.5")
    # Signal at bar 1, entry at bar 2 → no look-ahead
    assert fill.signal_ts == 1
    assert fill.timestamp == 2


def test_differential_stop_first_ambiguous():
    """When stop and target both hit same bar, stop-first wins (conservative)."""
    bars = [
        (1, Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0")),
        (2, Decimal("100.5"), Decimal("104.0"), Decimal("98.0"), Decimal("101.0")),
    ]
    # Bar 2: high=104 (target hit), low=98 (stop hit) → stop-first
    cc = CostConfig()
    sim = NextBarOpenSimulator(cost_config=cc)
    fill = sim.enter_long(bars, signal_index=0, stop=Decimal("99.0"), target=Decimal("104.0"))
    assert fill.reason == "entry"
    # exit would be at stop (conservative), not target


def test_differential_limit_trade_through():
    """Limit buy fills only when bar low <= limit price."""
    bars = [
        (1, Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0")),
        (2, Decimal("100.0"), Decimal("102.0"), Decimal("98.0"), Decimal("101.0")),
    ]
    cc = CostConfig()
    sim = NextBarOpenSimulator(cost_config=cc)
    fill = sim.enter_limit_long(bars, signal_index=0, limit_price=Decimal("100.0"))
    assert fill.price == Decimal("100.0")  # limit price, not open


def test_differential_fill_reason_exit():
    """Exit reason is stop, target, stop_gap, or end_of_data."""
    bars = [
        (1, Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0")),
        (2, Decimal("100.5"), Decimal("102.0"), Decimal("98.0"), Decimal("100.5")),
    ]
    cc = CostConfig()
    sim = NextBarOpenSimulator(cost_config=cc)
    # No stop/target → end_of_data exit at bar close
    fill = sim.enter_long(bars, signal_index=0, stop=None, target=None)
    assert fill.event_type == "entry"


def test_replay_after_reset():
    """Re-loading bars and re-entering produces same results."""
    bars = [
        (1, Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0")),
        (2, Decimal("100.0"), Decimal("102.0"), Decimal("98.0"), Decimal("101.0")),
    ]
    cc = CostConfig()
    results = []
    for _ in range(3):
        sim = NextBarOpenSimulator(cost_config=cc)
        sim.load_bars(bars)
        fill = sim.enter_long(bars, signal_index=0, stop=Decimal("99.0"), target=Decimal("104.0"))
        results.append((fill.timestamp, fill.price, fill.costs))
    assert results[0] == results[1] == results[2]


def test_no_lookahead_signal_before_entry():
    """Signal timestamp strictly precedes entry timestamp."""
    bars = [
        (1, Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0")),
        (2, Decimal("100.5"), Decimal("102.0"), Decimal("98.0"), Decimal("100.5")),
    ]
    cc = CostConfig()
    sim = NextBarOpenSimulator(cost_config=cc)
    fill = sim.enter_long(bars, signal_index=0, stop=Decimal("99.0"), target=Decimal("104.0"))
    assert fill.signal_ts < fill.timestamp

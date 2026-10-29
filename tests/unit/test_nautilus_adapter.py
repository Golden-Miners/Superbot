"""RED tests for M3.3 — NautilusTrader engine POC adapter.

Tests define:
- NautilusTrader adapter raises NautilusTraderNotInstalled when package absent
- Adapter runs equivalence acceptance using M3.2 canonical fixture/costs
- Correctness gate passes for NautilusTrader (next-bar-open entry, stop-first)
- Same fixtures/rules/costs/splits as M3.2 equivalence framework

Adapter under test requires nautilus_trader installed in isolated env.
"""

from __future__ import annotations

from decimal import Decimal

from superbot.engine.equivalence import CostConvention, EquivalenceFixture
from superbot.engine.nautilus_adapter import (
    NautilusTraderAdapter,
)


def test_nautilus_adapter_instantiates():
    """Adapter instantiates when nautilus_trader is available."""
    adapter = NautilusTraderAdapter()
    assert adapter is not None


def test_cost_convention_applies_to_trade():
    """M3.2 cost convention totals spread+slippage+commission+swap."""
    cc = CostConvention(
        spread_per_unit=Decimal("0.1"),
        slippage_per_unit=Decimal("0.01"),
        commission_per_unit=Decimal("0.05"),
        swap_funding_per_unit=Decimal("0.02"),
    )
    expected = (
        Decimal("0.1") * Decimal(10)
        + Decimal("0.01") * Decimal(10) * 2
        + Decimal("0.05") * Decimal(10) * 2
        + Decimal("0.02") * Decimal(10)
    )
    assert cc.total_cost(Decimal(10)) == expected


def test_equivalence_fixture_canonical_has_ten_bars():
    """M3.2 canonical equivalence fixture has 10 bars."""
    fx = EquivalenceFixture.canonical()
    assert len(fx.bars) == 10
    assert fx.bars[0].ts == 1
    assert fx.bars[-1].ts == 10


def test_adapter_runs_equivalence_and_passes_correctness_gate():
    """Adapter runs equivalence on NautilusTrader and passes correctness gate."""
    adapter = NautilusTraderAdapter()
    fx = EquivalenceFixture.canonical()
    cc = CostConvention.default()
    result = adapter.run_equivalence(fx, cc)
    assert result.engine == "nautilus_trader"
    assert result.fixture == "canonical_10bar"
    assert result.correctness_gate_passed is True
    assert result.event_count > 0

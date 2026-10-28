"""RED tests for M3.2 — equivalence fixtures, strategy rules, cost conventions,
acceptance tests for engine POC comparison.

Defines the standardized POC protocol: same inputs/rules/costs/splits across
candidate engines (custom baseline, NautilusTrader, LEAN). Machine-testable
strategy rules; explicit cost conventions; correctness-gate acceptance tests.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from superbot.engine.equivalence import (
    AcceptanceResult,
    CostConvention,
    EquivalenceFixture,
    StrategyRule,
    UnknownStrategyRuleError,
    run_equivalence_acceptance,
)


def test_equivalence_fixture_has_known_bars():
    fx = EquivalenceFixture.canonical()
    assert len(fx.bars) == 10
    assert fx.bars[0].ts == 1
    assert fx.bars[-1].ts == 10


def test_cost_convention_defaults():
    cc = CostConvention.default()
    assert cc.spread_per_unit == Decimal(0)
    assert cc.slippage_per_unit == Decimal(0)
    assert cc.commission_per_unit == Decimal(0)
    assert cc.swap_funding_per_unit == Decimal(0)


def test_cost_convention_applies_to_trade():
    cc = CostConvention(
        spread_per_unit=Decimal("0.2"),
        slippage_per_unit=Decimal("0.01"),
        commission_per_unit=Decimal("0.1"),
        swap_funding_per_unit=Decimal("0.05"),
    )
    qty = Decimal(2)
    # spread + entry/exit slippage + entry/exit commission + swap funding
    expected = (
        Decimal("0.2") * qty
        + Decimal("0.01") * qty * 2
        + Decimal("0.1") * qty * 2
        + Decimal("0.05") * qty
    )
    assert cc.total_cost(qty) == expected


def test_strategy_rule_machine_testable_fields():
    rule = StrategyRule(
        name="trend_pullback_v1",
        family="trend_pullback",
        entry_condition="close > sma(20) and close < sma(50)",
        exit_condition="close < sma(20) or close > sma(50)",
        stop_condition="low <= entry * 0.98",
        target_condition="high >= entry * 1.04",
        parameters={"sma_fast": 20, "sma_slow": 50},
    )
    assert rule.family == "trend_pullback"
    assert rule.parameters == {"sma_fast": 20, "sma_slow": 50}


def test_run_acceptance_passes_for_baseline():
    result = run_equivalence_acceptance("custom_baseline")
    assert isinstance(result, AcceptanceResult)
    assert result.passed is True
    assert result.correctness_gate_passed is True
    assert result.event_count > 0


def test_run_acceptance_unknown_engine_raises():
    with pytest.raises(UnknownStrategyRuleError):
        run_equivalence_acceptance("nonexistent_engine")

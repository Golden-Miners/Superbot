"""RED tests for M7.4 — Tier multipliers (0.25/0.50/0.75/1.00), monthly review, max 10% relative increase.

Tests define:
- TierMultiplierService: manages tier multipliers per strategy
- Fixed tier multipliers: 0.25, 0.50, 0.75, 1.00
- Monthly review: tracks review cadence, last/next review dates
- Max 10% relative increase: multiplier cannot increase by more than 10% relative per review
- Numeric tier criteria remain OPEN: service does not assume specific criteria for tier assignment
- Deterministic: same inputs yield identical results
- Stdlib-only, no import-time network/MT5/database/model activity
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from superbot.risk.tier_multiplier import (
    TierMultiplier,
    TierMultiplierResult,
    TierMultiplierService,
)


def test_tier_multiplier_creates():
    """TierMultiplier can be created with valid multiplier values."""
    tm = TierMultiplier(multiplier=Decimal("0.25"))
    assert tm.multiplier == Decimal("0.25")


def test_tier_multiplier_valid_values():
    """Tier multipliers restricted to 0.25, 0.50, 0.75, 1.00."""
    for expected in [Decimal("0.25"), Decimal("0.50"), Decimal("0.75"), Decimal("1.00")]:
        tm = TierMultiplier(multiplier=expected)
        assert tm.multiplier == expected


def test_tier_multiplier_service_creates():
    """TierMultiplierService can be created."""
    service = TierMultiplierService()
    assert service is not None


def test_get_tier_multiplier_default():
    """get_tier_multiplier returns default 1.00 for unknown strategy."""
    service = TierMultiplierService()
    result = service.get_tier_multiplier("unknown_strategy")
    assert result.multiplier == Decimal("1.00")


def test_assign_tier_multiplier():
    """assign_tier_multiplier sets a tier multiplier for a strategy."""
    service = TierMultiplierService()
    result = service.assign_tier_multiplier("strategy_a", Decimal("0.50"))
    assert result.multiplier == Decimal("0.50")
    assert service.get_tier_multiplier("strategy_a").multiplier == Decimal("0.50")


def test_assign_tier_multiplier_invalid_value():
    """assign_tier_multiplier rejects invalid multiplier values."""
    service = TierMultiplierService()
    with pytest.raises(ValueError):
        service.assign_tier_multiplier("strategy_a", Decimal("0.30"))


def test_review_tier_monthly_cadence():
    """review_tier enforces monthly review cadence."""
    service = TierMultiplierService()
    service.assign_tier_multiplier("strategy_a", Decimal("0.50"))
    last_review = date(2026, 9, 1)
    service.set_last_review("strategy_a", last_review)
    # Next review should be ~1 month later
    nr = service.next_review_date("strategy_a")
    assert nr is not None
    assert nr > last_review


def test_max_10_percent_relative_increase():
    """review_tier enforces max 10% relative increase per review, snaps down to valid tier."""
    service = TierMultiplierService()
    service.assign_tier_multiplier("strategy_a", Decimal("0.50"))
    # Attempt to increase to 0.75 = 50% relative increase, exceeds 10% cap
    # Capped at 0.50 * 1.10 = 0.55, snapped down to nearest valid tier = 0.50
    result = service.review_tier("strategy_a", Decimal("0.75"))
    assert result.multiplier == Decimal("0.50")


def test_max_10_percent_relative_increase_blocked():
    """review_tier blocks increases exceeding 10% relative; snaps down to valid tier."""
    service = TierMultiplierService()
    service.assign_tier_multiplier("strategy_a", Decimal("0.50"))
    # Target 0.75 = +50% relative, exceeds 10% cap; snapped down to nearest valid <= cap(0.55) = 0.50
    result = service.review_tier("strategy_a", Decimal("0.75"))
    assert result.multiplier == Decimal("0.50")


def test_decrease_always_allowed():
    """review_tier allows decreases regardless of 10% cap."""
    service = TierMultiplierService()
    service.assign_tier_multiplier("strategy_a", Decimal("1.00"))
    result = service.review_tier("strategy_a", Decimal("0.50"))
    assert result.multiplier == Decimal("0.50")


def test_tier_criteria_remain_open():
    """Service does not assume specific numeric tier criteria (OPEN)."""
    service = TierMultiplierService()
    # No built-in criteria; tiers must be explicitly assigned
    result = service.get_tier_multiplier("new_strategy")
    assert result.multiplier == Decimal("1.00")  # default, not auto-assigned


def test_tier_multiplier_deterministic():
    """Same inputs yield identical tier multiplier results."""
    s1 = TierMultiplierService()
    s2 = TierMultiplierService()
    s1.assign_tier_multiplier("s", Decimal("0.75"))
    s2.assign_tier_multiplier("s", Decimal("0.75"))
    assert s1.get_tier_multiplier("s").multiplier == s2.get_tier_multiplier("s").multiplier


def test_tier_multiplier_result_creates():
    """TierMultiplierResult can be created."""
    result = TierMultiplierResult(
        strategy_name="strategy_a",
        multiplier=Decimal("0.75"),
        previous_multiplier=Decimal("0.50"),
        review_date=date(2026, 9, 1),
    )
    assert result.multiplier == Decimal("0.75")


def test_next_review_date_none_when_unreviewed():
    """next_review_date returns None for unreviewed strategy."""
    service = TierMultiplierService()
    assert service.next_review_date("unreviewed") is None

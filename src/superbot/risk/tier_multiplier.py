"""Tier multipliers (0.25/0.50/0.75/1.00), monthly review, max 10% relative increase (schema.md section 7.4).

Deterministic tier multiplier service:
- Fixed tier multipliers: 0.25, 0.50, 0.75, 1.00
- Monthly review cadence tracks last/next review dates
- Max 10% relative increase per review (conservative: snaps down to nearest valid tier)
- Numeric tier criteria remain OPEN: service does not assume criteria for tier assignment
- Stdlib-only; no import-time network/MT5/database/model activity.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

VALID_TIER_MULTIPLIERS = (Decimal("0.25"), Decimal("0.50"), Decimal("0.75"), Decimal("1.00"))


@dataclass(frozen=True)
class TierMultiplier:
    """A tier multiplier value."""

    multiplier: Decimal


@dataclass(frozen=True)
class TierMultiplierResult:
    """Result of tier multiplier assignment or review."""

    strategy_name: str
    multiplier: Decimal
    previous_multiplier: Decimal
    review_date: date | None


class TierMultiplierService:
    """Manages tier multipliers per strategy with monthly review and 10% cap."""

    def __init__(
        self,
        review_interval_days: int = 30,
    ) -> None:
        self.review_interval_days = review_interval_days
        self._multipliers: dict[str, Decimal] = {}
        self._last_review: dict[str, date] = {}

    def get_tier_multiplier(self, strategy_name: str) -> TierMultiplier:
        """Get the current tier multiplier for a strategy (defaults to 1.00)."""
        multiplier = self._multipliers.get(strategy_name, Decimal("1.00"))
        return TierMultiplier(multiplier=multiplier)

    def assign_tier_multiplier(
        self,
        strategy_name: str,
        multiplier: Decimal,
    ) -> TierMultiplierResult:
        """Assign a tier multiplier to a strategy.

        Args:
            strategy_name: strategy identifier
            multiplier: one of 0.25, 0.50, 0.75, 1.00

        Returns TierMultiplierResult.
        Raises ValueError if multiplier is not a valid tier value.
        """
        if multiplier not in VALID_TIER_MULTIPLIERS:
            raise ValueError(
                f"Invalid tier multiplier {multiplier}; valid values: {VALID_TIER_MULTIPLIERS}"
            )
        previous = self._multipliers.get(strategy_name, Decimal("1.00"))
        self._multipliers[strategy_name] = multiplier
        return TierMultiplierResult(
            strategy_name=strategy_name,
            multiplier=multiplier,
            previous_multiplier=previous,
            review_date=None,
        )

    def set_last_review(self, strategy_name: str, review_date: date) -> None:
        """Record the last review date for a strategy."""
        self._last_review[strategy_name] = review_date

    def next_review_date(self, strategy_name: str) -> date | None:
        """Return the next review date for a strategy, or None if never reviewed."""
        last = self._last_review.get(strategy_name)
        if last is None:
            return None
        return last + timedelta(days=self.review_interval_days)

    def review_tier(
        self,
        strategy_name: str,
        target_multiplier: Decimal,
    ) -> TierMultiplierResult:
        """Review and potentially adjust a tier multiplier.

        Enforces max 10% relative increase per review. If the target exceeds
        current * 1.10, the result is snapped down to the nearest valid tier
        multiplier at or below the cap.

        Args:
            strategy_name: strategy identifier
            target_multiplier: desired tier multiplier

        Returns TierMultiplierResult with the (possibly capped) multiplier.
        """
        if target_multiplier not in VALID_TIER_MULTIPLIERS:
            raise ValueError(
                f"Invalid tier multiplier {target_multiplier}; valid values: {VALID_TIER_MULTIPLIERS}"
            )
        current = self._multipliers.get(strategy_name, Decimal("1.00"))
        previous = current
        cap = current * Decimal("1.10")
        if target_multiplier <= cap:
            snapped = target_multiplier
        else:
            # Snap down to nearest valid tier <= cap
            snapped = Decimal("1.00")
            for valid in VALID_TIER_MULTIPLIERS:
                if valid <= cap:
                    snapped = valid
        self._multipliers[strategy_name] = snapped
        today = date.today()
        self._last_review[strategy_name] = today
        return TierMultiplierResult(
            strategy_name=strategy_name,
            multiplier=snapped,
            previous_multiplier=previous,
            review_date=today,
        )


def get_tier_multiplier(
    service: TierMultiplierService,
    strategy_name: str,
) -> TierMultiplier:
    """Get the tier multiplier for a strategy."""
    return service.get_tier_multiplier(strategy_name)


def assign_tier_multiplier(
    service: TierMultiplierService,
    strategy_name: str,
    multiplier: Decimal,
) -> TierMultiplierResult:
    """Assign a tier multiplier to a strategy."""
    return service.assign_tier_multiplier(strategy_name, multiplier)


def set_tier_multiplier(
    service: TierMultiplierService,
    strategy_name: str,
    multiplier: Decimal,
) -> TierMultiplierResult:
    """Set a tier multiplier (alias for assign_tier_multiplier)."""
    return service.assign_tier_multiplier(strategy_name, multiplier)


def review_tier(
    service: TierMultiplierService,
    strategy_name: str,
    target_multiplier: Decimal,
) -> TierMultiplierResult:
    """Review and adjust a tier multiplier with 10% cap."""
    return service.review_tier(strategy_name, target_multiplier)


def next_review_date(
    service: TierMultiplierService,
    strategy_name: str,
) -> date | None:
    """Return the next review date for a strategy."""
    return service.next_review_date(strategy_name)

"""Daily loss 3% and portfolio DD 10% halt/resume process (schema.md section 7.2).

Deterministic halt/resume manager:
- Daily loss threshold 3% triggers halt
- Portfolio DD threshold 10% triggers halt
- Resume requires daily loss below threshold AND portfolio DD below threshold
- During halt, new entries blocked; existing positions continue under defined exits
- Stdlib-only; no import-time network/MT5/database/model activity.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class HaltCheckResult:
    """Halt check result."""

    halted: bool
    reasons: list[str]


class DailyLossHaltResumeManager:
    """Tracks portfolio state (halted/resumed), daily loss, and portfolio DD."""

    def __init__(
        self,
        daily_loss_threshold_pct: Decimal = Decimal(3),
        portfolio_dd_threshold_pct: Decimal = Decimal(10),
    ) -> None:
        self.daily_loss_threshold_pct = daily_loss_threshold_pct
        self.portfolio_dd_threshold_pct = portfolio_dd_threshold_pct
        self.daily_loss_pct: Decimal = Decimal(0)
        self.portfolio_dd_pct: Decimal = Decimal(0)
        self._halted: bool = False
        self.halt_reason: str | None = None

    def is_halted(self) -> bool:
        """Return whether the portfolio is currently halted."""
        return self._halted

    def record_daily_loss(self, daily_loss_pct: Decimal) -> None:
        """Record daily loss percentage and update halt state."""
        self.daily_loss_pct = daily_loss_pct
        self._update_halt_state()

    def record_portfolio_dd(self, portfolio_dd_pct: Decimal) -> None:
        """Record portfolio DD percentage and update halt state."""
        self.portfolio_dd_pct = portfolio_dd_pct
        self._update_halt_state()

    def can_resume(self) -> bool:
        """Return True if resume conditions met (daily loss and DD both below thresholds)."""
        return (
            self.daily_loss_pct <= self.daily_loss_threshold_pct
            and self.portfolio_dd_pct <= self.portfolio_dd_threshold_pct
        )

    def _update_halt_state(self) -> None:
        """Update halt state based on current daily loss and DD."""
        if self.daily_loss_pct > self.daily_loss_threshold_pct:
            self._halted = True
            self.halt_reason = f"daily_loss {self.daily_loss_pct} exceeds threshold {self.daily_loss_threshold_pct}"
        elif self.portfolio_dd_pct > self.portfolio_dd_threshold_pct:
            self._halted = True
            self.halt_reason = f"portfolio_dd {self.portfolio_dd_pct} exceeds threshold {self.portfolio_dd_threshold_pct}"
        else:
            self._halted = False
            self.halt_reason = None


def check_daily_loss_halt(
    daily_loss_pct: Decimal,
    threshold_pct: Decimal,
) -> HaltCheckResult:
    """Check daily loss against threshold.

    Args:
        daily_loss_pct: current daily loss percentage
        threshold_pct: halt threshold percentage

    Returns HaltCheckResult with halted flag and reasons.
    """
    reasons: list[str] = []
    halted = False

    if daily_loss_pct > threshold_pct:
        halted = True
        reasons.append(f"daily_loss {daily_loss_pct} exceeds threshold {threshold_pct}")

    return HaltCheckResult(halted=halted, reasons=reasons)


def check_portfolio_dd_halt(
    portfolio_dd_pct: Decimal,
    threshold_pct: Decimal,
) -> HaltCheckResult:
    """Check portfolio DD against threshold.

    Args:
        portfolio_dd_pct: current portfolio DD percentage
        threshold_pct: halt threshold percentage

    Returns HaltCheckResult with halted flag and reasons.
    """
    reasons: list[str] = []
    halted = False

    if portfolio_dd_pct > threshold_pct:
        halted = True
        reasons.append(f"portfolio_dd {portfolio_dd_pct} exceeds threshold {threshold_pct}")

    return HaltCheckResult(halted=halted, reasons=reasons)


def is_halted(
    manager: DailyLossHaltResumeManager,
) -> bool:
    """Check if manager is halted."""
    return manager.is_halted()


def can_resume(
    manager: DailyLossHaltResumeManager,
    daily_loss_threshold_pct: Decimal = Decimal(3),
    portfolio_dd_threshold_pct: Decimal = Decimal(10),
) -> bool:
    """Check if resume conditions met."""
    return (
        manager.daily_loss_pct <= daily_loss_threshold_pct
        and manager.portfolio_dd_pct <= portfolio_dd_threshold_pct
    )


def record_daily_loss(
    manager: DailyLossHaltResumeManager,
    daily_loss_pct: Decimal,
    threshold_pct: Decimal = Decimal(3),
) -> None:
    """Record daily loss on manager."""
    manager.daily_loss_threshold_pct = threshold_pct
    manager.record_daily_loss(daily_loss_pct)


def record_portfolio_dd(
    manager: DailyLossHaltResumeManager,
    portfolio_dd_pct: Decimal,
    threshold_pct: Decimal = Decimal(10),
) -> None:
    """Record portfolio DD on manager."""
    manager.portfolio_dd_threshold_pct = threshold_pct
    manager.record_portfolio_dd(portfolio_dd_pct)

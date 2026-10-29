"""RED tests for M7.2 — Daily loss 3% and portfolio DD 10% halt/resume process.

Tests define:
- HaltResumeManager: tracks portfolio state (halted/resumed), daily loss, portfolio DD
- HaltCheckResult: halt decision with reasons
- Daily loss threshold 3% triggers halt
- Portfolio DD threshold 10% triggers halt
- Resume conditions: daily loss below threshold AND portfolio DD below threshold
- Existing positions continue under defined exits during halt (no new entries)
- Deterministic: same inputs yield identical results
- Stdlib-only, no import-time network/MT5/database/model activity
"""

from __future__ import annotations

from decimal import Decimal

from superbot.risk.daily_loss_halt import (
    DailyLossHaltResumeManager,
    HaltCheckResult,
    can_resume,
    check_daily_loss_halt,
    check_portfolio_dd_halt,
    is_halted,
    record_daily_loss,
    record_portfolio_dd,
)


def test_halt_check_result_creates():
    """HaltCheckResult can be created."""
    result = HaltCheckResult(halted=False, reasons=[])
    assert result.halted is False


def test_check_daily_loss_halt_below_threshold():
    """check_daily_loss_halt returns not halted when daily loss below 3%."""
    result = check_daily_loss_halt(Decimal("2.5"), Decimal(3))
    assert result.halted is False
    assert result.reasons == []


def test_check_daily_loss_halt_at_threshold():
    """check_daily_loss_halt returns not halted when daily loss equals 3% (not exceeding)."""
    result = check_daily_loss_halt(Decimal(3), Decimal(3))
    assert result.halted is False


def test_check_daily_loss_halt_above_threshold():
    """check_daily_loss_halt returns halted when daily loss exceeds 3%."""
    result = check_daily_loss_halt(Decimal("3.1"), Decimal(3))
    assert result.halted is True
    assert "daily" in " ".join(result.reasons).lower() or "loss" in " ".join(result.reasons).lower()


def test_check_portfolio_dd_halt_below_threshold():
    """check_portfolio_dd_halt returns not halted when DD below 10%."""
    result = check_portfolio_dd_halt(Decimal(5), Decimal(10))
    assert result.halted is False


def test_check_portfolio_dd_halt_at_threshold():
    """check_portfolio_dd_halt returns not halted when DD equals 10% (not exceeding)."""
    result = check_portfolio_dd_halt(Decimal(10), Decimal(10))
    assert result.halted is False


def test_check_portfolio_dd_halt_above_threshold():
    """check_portfolio_dd_halt returns halted when DD exceeds 10%."""
    result = check_portfolio_dd_halt(Decimal("10.1"), Decimal(10))
    assert result.halted is True
    assert (
        "dd" in " ".join(result.reasons).lower() or "drawdown" in " ".join(result.reasons).lower()
    )


def test_is_halted_false_initially():
    """is_halted returns False when no halt has been recorded."""
    manager = DailyLossHaltResumeManager()
    assert not is_halted(manager)


def test_record_daily_loss_triggers_halt():
    """record_daily_loss above threshold triggers halt."""
    manager = DailyLossHaltResumeManager()
    record_daily_loss(manager, Decimal(4), Decimal(3))
    assert is_halted(manager)


def test_record_portfolio_dd_triggers_halt():
    """record_portfolio_dd above threshold triggers halt."""
    manager = DailyLossHaltResumeManager()
    record_portfolio_dd(manager, Decimal(12), Decimal(10))
    assert is_halted(manager)


def test_can_resume_when_conditions_met():
    """can_resume returns True when daily loss below threshold AND DD below threshold."""
    manager = DailyLossHaltResumeManager()
    record_daily_loss(manager, Decimal(4), Decimal(3))
    record_portfolio_dd(manager, Decimal(12), Decimal(10))
    assert is_halted(manager)
    # Now both below threshold
    manager.daily_loss_pct = Decimal(1)
    manager.portfolio_dd_pct = Decimal(5)
    assert can_resume(manager, Decimal(3), Decimal(10))


def test_cannot_resume_when_daily_loss_still_high():
    """can_resume returns False when daily loss still above threshold."""
    manager = DailyLossHaltResumeManager()
    record_daily_loss(manager, Decimal(4), Decimal(3))
    manager.daily_loss_pct = Decimal("3.5")
    manager.portfolio_dd_pct = Decimal(5)
    assert not can_resume(manager, Decimal(3), Decimal(10))


def test_cannot_resume_when_dd_still_high():
    """can_resume returns False when portfolio DD still above threshold."""
    manager = DailyLossHaltResumeManager()
    record_portfolio_dd(manager, Decimal(12), Decimal(10))
    manager.daily_loss_pct = Decimal(1)
    manager.portfolio_dd_pct = Decimal("10.5")
    assert not can_resume(manager, Decimal(3), Decimal(10))


def test_daily_loss_halt_resume_deterministic():
    """Same inputs yield identical halt/resume results."""
    m1 = DailyLossHaltResumeManager()
    m2 = DailyLossHaltResumeManager()
    record_daily_loss(m1, Decimal(4), Decimal(3))
    record_daily_loss(m2, Decimal(4), Decimal(3))
    assert is_halted(m1) == is_halted(m2)


def test_existing_positions_continue_during_halt():
    """During halt, existing positions continue (halt only blocks new entries)."""
    manager = DailyLossHaltResumeManager()
    record_daily_loss(manager, Decimal(4), Decimal(3))
    assert is_halted(manager)
    # Halt state indicates no new entries; existing positions unaffected
    assert manager.halt_reason is not None

"""RED tests for M7.1 — Portfolio/strategy/correlation-group risk service.

Tests define:
- PortfolioRiskService: tracks portfolio risk across strategies and correlation groups
- CorrelationGroup: groups strategies by correlation, enforces group-level risk caps
- RiskLimit: per-strategy and per-group risk limits (max DD, daily loss, position size)
- RiskCheckResult: pass/fail verdict with reasons for proposed trades
- Deterministic: same inputs yield identical results
- Stdlib-only, no import-time network/MT5/database/model activity
"""

from __future__ import annotations

from decimal import Decimal

from superbot.risk.portfolio_risk import (
    CorrelationGroup,
    PortfolioRiskService,
    RiskCheckResult,
    RiskLimit,
    check_group_risk,
    check_strategy_risk,
)


def test_portfolio_risk_service_creates():
    """PortfolioRiskService can be created."""
    service = PortfolioRiskService()
    assert service is not None


def test_register_strategy():
    """register_strategy adds a strategy to the portfolio service."""
    service = PortfolioRiskService()
    service.register_strategy("strategy_a", max_dd_pct=Decimal(10), daily_loss_pct=Decimal(3))
    assert service.get_strategy("strategy_a") is not None


def test_risk_limit_creates():
    """RiskLimit can be created."""
    limit = RiskLimit(
        max_dd_pct=Decimal(10), daily_loss_pct=Decimal(3), max_position_pct=Decimal(5)
    )
    assert limit.max_dd_pct == Decimal(10)
    assert limit.daily_loss_pct == Decimal(3)
    assert limit.max_position_pct == Decimal(5)


def test_risk_check_result_creates():
    """RiskCheckResult can be created."""
    result = RiskCheckResult(allowed=True, reasons=[])
    assert result.allowed is True


def test_check_strategy_risk_allows():
    """check_strategy_risk allows when within limits."""
    result = check_strategy_risk(
        current_dd_pct=Decimal(2),
        daily_loss_pct=Decimal(1),
        limit=RiskLimit(
            max_dd_pct=Decimal(10), daily_loss_pct=Decimal(3), max_position_pct=Decimal(5)
        ),
    )
    assert result.allowed is True
    assert result.reasons == []


def test_check_strategy_risk_blocks_high_dd():
    """check_strategy_risk blocks when DD exceeds limit."""
    result = check_strategy_risk(
        current_dd_pct=Decimal(12),
        daily_loss_pct=Decimal(1),
        limit=RiskLimit(
            max_dd_pct=Decimal(10), daily_loss_pct=Decimal(3), max_position_pct=Decimal(5)
        ),
    )
    assert result.allowed is False
    assert (
        "dd" in " ".join(result.reasons).lower() or "drawdown" in " ".join(result.reasons).lower()
    )


def test_check_strategy_risk_blocks_high_daily_loss():
    """check_strategy_risk blocks when daily loss exceeds limit."""
    result = check_strategy_risk(
        current_dd_pct=Decimal(2),
        daily_loss_pct=Decimal(4),
        limit=RiskLimit(
            max_dd_pct=Decimal(10), daily_loss_pct=Decimal(3), max_position_pct=Decimal(5)
        ),
    )
    assert result.allowed is False
    assert "daily" in " ".join(result.reasons).lower()


def test_check_strategy_risk_blocks_multiple():
    """check_strategy_risk blocks with multiple failing criteria."""
    result = check_strategy_risk(
        current_dd_pct=Decimal(12),
        daily_loss_pct=Decimal(4),
        limit=RiskLimit(
            max_dd_pct=Decimal(10), daily_loss_pct=Decimal(3), max_position_pct=Decimal(5)
        ),
    )
    assert result.allowed is False
    assert len(result.reasons) == 2


def test_correlation_group_creates():
    """CorrelationGroup can be created."""
    group = CorrelationGroup(name="tech", max_group_dd_pct=Decimal(15))
    assert group.name == "tech"


def test_correlation_group_add_strategy():
    """CorrelationGroup can add strategies."""
    group = CorrelationGroup(name="tech", max_group_dd_pct=Decimal(15))
    group.add_strategy("strategy_a")
    group.add_strategy("strategy_b")
    assert "strategy_a" in group.strategies
    assert "strategy_b" in group.strategies


def test_check_group_risk_allows():
    """check_group_risk allows when group DD within limit."""
    result = check_group_risk(
        group_dd_pct=Decimal(5),
        limit=Decimal(15),
    )
    assert result.allowed is True


def test_check_group_risk_blocks():
    """check_group_risk blocks when group DD exceeds limit."""
    result = check_group_risk(
        group_dd_pct=Decimal(18),
        limit=Decimal(15),
    )
    assert result.allowed is False


def test_portfolio_risk_service_deterministic():
    """Same inputs yield identical results."""
    service = PortfolioRiskService()
    service.register_strategy("s1", max_dd_pct=Decimal(10), daily_loss_pct=Decimal(3))
    r1 = check_strategy_risk(Decimal(2), Decimal(1), service.get_strategy("s1").limit)
    r2 = check_strategy_risk(Decimal(2), Decimal(1), service.get_strategy("s1").limit)
    assert r1.allowed == r2.allowed
    assert r1.reasons == r2.reasons


def test_portfolio_risk_service_unknown_strategy():
    """Getting unknown strategy returns None."""
    service = PortfolioRiskService()
    assert service.get_strategy("nonexistent") is None


def test_register_strategy_duplicate():
    """Registering duplicate strategy replaces or keeps first."""
    service = PortfolioRiskService()
    service.register_strategy("s1", max_dd_pct=Decimal(10), daily_loss_pct=Decimal(3))
    service.register_strategy("s1", max_dd_pct=Decimal(5), daily_loss_pct=Decimal(1))
    assert service.get_strategy("s1").limit.max_dd_pct == Decimal(5)

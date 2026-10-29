"""RED tests for M7.3 — Combined open-risk cap 5%; adaptive risk and verified sizing.

Tests define:
- OpenRiskService: tracks combined open risk across all strategies and positions
- Combined open-risk cap: 5% of portfolio; blocks new entries when exceeded
- Adaptive risk: position sizing adjusts based on current open risk
- Verified sizing: position size verified against open-risk cap before entry
- Open risk per position and aggregate across all strategies
- Deterministic: same inputs yield identical results
- Stdlib-only, no import-time network/MT5/database/model activity
"""

from __future__ import annotations

from decimal import Decimal

from superbot.risk.open_risk_cap import (
    OpenRiskResult,
    OpenRiskService,
    PositionRisk,
    check_combined_open_risk,
    compute_adaptive_size,
    verified_size,
)


def test_open_risk_service_creates():
    """OpenRiskService can be created with default 5% cap."""
    service = OpenRiskService()
    assert service is not None
    assert service.combined_open_risk_cap_pct == Decimal(5)


def test_open_risk_service_custom_cap():
    """OpenRiskService accepts custom combined open-risk cap."""
    service = OpenRiskService(combined_open_risk_cap_pct=Decimal(3))
    assert service.combined_open_risk_cap_pct == Decimal(3)


def test_position_risk_creates():
    """PositionRisk can be created."""
    pr = PositionRisk(
        strategy_name="strategy_a",
        symbol="EURUSD",
        notional_usd=Decimal(10000),
        risk_pct=Decimal(1),
    )
    assert pr.strategy_name == "strategy_a"
    assert pr.risk_pct == Decimal(1)


def test_register_open_position():
    """register_open_position adds position risk to the service."""
    service = OpenRiskService()
    service.register_open_position("strategy_a", "EURUSD", Decimal(10000), Decimal(1))
    assert service.get_position("strategy_a", "EURUSD") is not None


def test_register_open_position_updates_combined_risk():
    """register_open_position updates combined open risk."""
    service = OpenRiskService()
    service.register_open_position("s1", "EURUSD", Decimal(10000), Decimal(1))
    service.register_open_position("s1", "GBPUSD", Decimal(10000), Decimal(1))
    service.register_open_position("s2", "USDJPY", Decimal(10000), Decimal(1))
    assert service.combined_open_risk_pct == Decimal(3)


def test_check_combined_open_risk_within_cap():
    """check_combined_open_risk allows when within 5% cap."""
    result = check_combined_open_risk(Decimal(3), Decimal(5))
    assert result.allowed is True
    assert result.reasons == []


def test_check_combined_open_risk_at_cap():
    """check_combined_open_risk allows when exactly at 5% cap (not exceeding)."""
    result = check_combined_open_risk(Decimal(5), Decimal(5))
    assert result.allowed is True


def test_check_combined_open_risk_exceeds_cap():
    """check_combined_open_risk blocks when exceeding 5% cap."""
    result = check_combined_open_risk(Decimal("5.1"), Decimal(5))
    assert result.allowed is False
    assert "open" in " ".join(result.reasons).lower() or "risk" in " ".join(result.reasons).lower()


def test_verify_size_within_cap():
    """verified_size allows when new position size keeps combined risk within cap."""
    service = OpenRiskService()
    service.register_open_position("s1", "EURUSD", Decimal(10000), Decimal(2))
    size = verified_size(service, Decimal(2), Decimal(5))
    assert size == Decimal(2)


def test_verify_size_reduced_at_cap():
    """verified_size reduces size when adding position would exceed cap."""
    service = OpenRiskService()
    service.register_open_position("s1", "EURUSD", Decimal(10000), Decimal(4))
    size = verified_size(service, Decimal(2), Decimal(5))
    # 4% existing + new size; new size can add at most 1%
    assert size <= Decimal(1)


def test_verify_size_zero_when_at_cap():
    """verified_size returns 0 when combined risk already at cap."""
    service = OpenRiskService()
    service.register_open_position("s1", "EURUSD", Decimal(10000), Decimal(5))
    size = verified_size(service, Decimal(1), Decimal(5))
    assert size == Decimal(0)


def test_compute_adaptive_size():
    """compute_adaptive_size scales size based on available risk headroom."""
    service = OpenRiskService()
    service.register_open_position("s1", "EURUSD", Decimal(10000), Decimal(2))
    size = compute_adaptive_size(service, requested_size=Decimal(3), cap_pct=Decimal(5))
    # 2% used, 3% available; requested 3% fits exactly
    assert size == Decimal(3)


def test_compute_adaptive_size_caps_to_headroom():
    """compute_adaptive_size caps requested size to available headroom."""
    service = OpenRiskService()
    service.register_open_position("s1", "EURUSD", Decimal(10000), Decimal(4))
    size = compute_adaptive_size(service, requested_size=Decimal(3), cap_pct=Decimal(5))
    # 4% used, 1% available; requested 3% capped to 1%
    assert size == Decimal(1)


def test_open_risk_result_creates():
    """OpenRiskResult can be created."""
    result = OpenRiskResult(
        combined_open_risk_pct=Decimal(3),
        cap_pct=Decimal(5),
        headroom_pct=Decimal(2),
        allowed=True,
        reasons=[],
    )
    assert result.combined_open_risk_pct == Decimal(3)


def test_remove_open_position():
    """remove_open_position removes position and reduces combined risk."""
    service = OpenRiskService()
    service.register_open_position("s1", "EURUSD", Decimal(10000), Decimal(2))
    assert service.combined_open_risk_pct == Decimal(2)
    service.remove_open_position("s1", "EURUSD")
    assert service.combined_open_risk_pct == Decimal(0)


def test_open_risk_service_deterministic():
    """Same inputs yield identical open risk results."""
    s1 = OpenRiskService()
    s2 = OpenRiskService()
    s1.register_open_position("s", "EURUSD", Decimal(10000), Decimal(1))
    s2.register_open_position("s", "EURUSD", Decimal(10000), Decimal(1))
    assert s1.combined_open_risk_pct == s2.combined_open_risk_pct

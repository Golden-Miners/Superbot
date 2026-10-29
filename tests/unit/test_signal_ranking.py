"""RED tests for M7.6 — Competing signal ranking, reserve/capacity, group limits, resize/reject semantics.

Tests define:
- SignalRankingService: ranks competing signals by score
- Signal: signal with symbol, side, score, size
- ReserveCapacityService: tracks reserve/capacity for signal execution
- GroupLimitService: enforces group-level limits (max signals per group, max risk per group)
- ResizeRejectSemantics: resize or reject signals when limits breached
- Rank-based selection: highest score signals selected first
- Capacity enforcement: total size cannot exceed reserve capacity
- Group limits: per-group signal count and risk caps
- Resize: reduce signal size to fit within remaining capacity
- Reject: reject signal entirely when cannot fit
- Deterministic: same inputs yield identical results
- Stdlib-only, no import-time network/MT5/database/model activity
"""

from __future__ import annotations

from decimal import Decimal

from superbot.risk.signal_ranking import (
    GroupLimit,
    GroupLimitService,
    RankedSignal,
    ReserveCapacityService,
    ResizeRejectDecision,
    ResizeRejectSemantics,
    Signal,
    SignalRankingService,
    allocate_capacity,
    check_group_limits,
    rank_signals,
    resize_or_reject,
)


def test_signal_creates():
    """Signal can be created."""
    signal = Signal(
        symbol="EURUSD",
        side="long",
        score=Decimal("0.85"),
        size=Decimal(10000),
    )
    assert signal.symbol == "EURUSD"
    assert signal.side == "long"
    assert signal.score == Decimal("0.85")
    assert signal.size == Decimal(10000)


def test_signal_ranking_service_creates():
    """SignalRankingService can be created."""
    service = SignalRankingService()
    assert service is not None


def test_rank_signals_by_score_descending():
    """rank_signals returns signals sorted by score descending."""
    signals = [
        Signal("EURUSD", "long", Decimal("0.5"), Decimal(1000)),
        Signal("GBPUSD", "short", Decimal("0.9"), Decimal(1000)),
        Signal("USDJPY", "long", Decimal("0.7"), Decimal(1000)),
    ]
    ranked = rank_signals(signals)
    scores = [s.score for s in ranked]
    assert scores == sorted(scores, reverse=True)


def test_ranked_signal_creates():
    """RankedSignal can be created."""
    rs = RankedSignal(
        symbol="EURUSD",
        side="long",
        score=Decimal("0.85"),
        size=Decimal(10000),
        rank=1,
    )
    assert rs.rank == 1


def test_reserve_capacity_service_creates():
    """ReserveCapacityService can be created with total capacity."""
    service = ReserveCapacityService(total_capacity=Decimal(100000))
    assert service.total_capacity == Decimal(100000)


def test_allocate_capacity_within_reserve():
    """allocate_capacity allocates when total size within reserve capacity."""
    service = ReserveCapacityService(total_capacity=Decimal(100000))
    signals = [
        Signal("EURUSD", "long", Decimal("0.9"), Decimal(30000)),
        Signal("GBPUSD", "short", Decimal("0.8"), Decimal(40000)),
        Signal("USDJPY", "long", Decimal("0.7"), Decimal(20000)),
    ]
    result = allocate_capacity(service, signals)
    assert result.allocated is True
    assert result.total_allocated == Decimal(90000)


def test_allocate_capacity_exceeds_reserve():
    """allocate_capacity rejects when total size exceeds reserve capacity."""
    service = ReserveCapacityService(total_capacity=Decimal(100000))
    signals = [
        Signal("EURUSD", "long", Decimal("0.9"), Decimal(60000)),
        Signal("GBPUSD", "short", Decimal("0.8"), Decimal(60000)),
    ]
    result = allocate_capacity(service, signals)
    assert result.allocated is False


def test_reserve_capacity_remaining():
    """ReserveCapacityService tracks remaining capacity after allocation."""
    service = ReserveCapacityService(total_capacity=Decimal(100000))
    service.allocate(Decimal(30000))
    assert service.remaining_capacity == Decimal(70000)


def test_group_limit_service_creates():
    """GroupLimitService can be created."""
    service = GroupLimitService()
    assert service is not None


def test_group_limit_creates():
    """GroupLimit can be created."""
    gl = GroupLimit(
        group_name="tech",
        max_signals=5,
        max_risk_pct=Decimal(10),
    )
    assert gl.group_name == "tech"
    assert gl.max_signals == 5
    assert gl.max_risk_pct == Decimal(10)


def test_add_group_limit():
    """GroupLimitService can add group limits."""
    service = GroupLimitService()
    service.add_group_limit("tech", Decimal(5), Decimal(10))
    assert service.get_group_limit("tech") is not None


def test_check_group_limits_within_limits():
    """check_group_limits passes when signal count and risk within limits."""
    service = GroupLimitService()
    service.add_group_limit("tech", Decimal(5), Decimal(5000))
    signals = [
        Signal("AAPL", "long", Decimal("0.8"), Decimal(1000)),
        Signal("MSFT", "long", Decimal("0.7"), Decimal(1000)),
    ]
    result = check_group_limits(service, "tech", signals)
    assert result.passed is True


def test_check_group_limits_exceeds_signal_count():
    """check_group_limits fails when signal count exceeds max_signals."""
    service = GroupLimitService()
    service.add_group_limit("tech", Decimal(2), Decimal(10))
    signals = [
        Signal("AAPL", "long", Decimal("0.8"), Decimal(1000)),
        Signal("MSFT", "long", Decimal("0.7"), Decimal(1000)),
        Signal("GOOG", "long", Decimal("0.6"), Decimal(1000)),
    ]
    result = check_group_limits(service, "tech", signals)
    assert result.passed is False


def test_check_group_limits_exceeds_risk():
    """check_group_limits fails when total risk exceeds max_risk_pct."""
    service = GroupLimitService()
    service.add_group_limit("tech", Decimal(10), Decimal(5))
    signals = [
        Signal("AAPL", "long", Decimal("0.8"), Decimal(4000)),
        Signal("MSFT", "long", Decimal("0.7"), Decimal(2000)),
    ]
    result = check_group_limits(service, "tech", signals)
    assert result.passed is False


def test_resize_reject_semantics_creates():
    """ResizeRejectSemantics can be created."""
    service = ResizeRejectSemantics()
    assert service is not None


def test_resize_or_reject_resize():
    """resize_or_reject resizes signal to fit within remaining capacity."""
    service = ResizeRejectSemantics()
    signal = Signal("EURUSD", "long", Decimal("0.8"), Decimal(10000))
    result = resize_or_reject(service, signal, Decimal(5000))
    assert result.decision == "resize"
    assert result.resized_size == Decimal(5000)


def test_resize_or_reject_reject():
    """resize_or_reject rejects signal when minimum size not met."""
    service = ResizeRejectSemantics(min_size=Decimal(1000))
    signal = Signal("EURUSD", "long", Decimal("0.8"), Decimal(10000))
    result = resize_or_reject(service, signal, Decimal(500))
    assert result.decision == "reject"


def test_resize_reject_decision_creates():
    """ResizeRejectDecision can be created."""
    rd = ResizeRejectDecision(
        decision="resize",
        original_size=Decimal(10000),
        resized_size=Decimal(5000),
    )
    assert rd.decision == "resize"


def test_signal_ranking_deterministic():
    """Same inputs yield identical ranking results."""
    signals = [
        Signal("EURUSD", "long", Decimal("0.5"), Decimal(1000)),
        Signal("GBPUSD", "short", Decimal("0.9"), Decimal(1000)),
    ]
    r1 = rank_signals(signals)
    r2 = rank_signals(signals)
    assert [s.symbol for s in r1] == [s.symbol for s in r2]

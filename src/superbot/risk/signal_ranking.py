"""Competing signal ranking, reserve/capacity, group limits, resize/reject semantics (schema.md section 7.6).

Deterministic signal ranking and risk allocation service:
- Ranks competing signals by score (highest first)
- Reserve/capacity: total allocated size cannot exceed reserve capacity
- Group limits: per-group max signal count and max risk pct
- Resize/reject: resize signal to fit remaining capacity, or reject when below min size
- All Decimal arithmetic; thresholds are explicit inputs (never guessed)
- Stdlib-only; no import-time network/MT5/database/model activity.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Signal:
    """A trading signal."""

    symbol: str
    side: str  # "long" or "short"
    score: Decimal
    size: Decimal


@dataclass(frozen=True)
class RankedSignal:
    """A signal with its rank."""

    symbol: str
    side: str
    score: Decimal
    size: Decimal
    rank: int


@dataclass(frozen=True)
class GroupLimit:
    """Group-level limit configuration."""

    group_name: str
    max_signals: int
    max_risk_pct: Decimal


@dataclass(frozen=True)
class GroupLimitResult:
    """Group limit check result."""

    passed: bool
    reasons: list[str]


@dataclass(frozen=True)
class ResizeRejectDecision:
    """Resize/reject decision."""

    decision: str  # "resize" or "reject"
    original_size: Decimal
    resized_size: Decimal


@dataclass(frozen=True)
class AllocationResult:
    """Capacity allocation result."""

    allocated: bool
    total_allocated: Decimal
    remaining_capacity: Decimal


class SignalRankingService:
    """Ranks competing signals by score."""

    def rank_signals(
        self,
        signals: list[Signal],
    ) -> list[RankedSignal]:
        """Rank signals by score descending.

        Args:
            signals: list of Signal objects

        Returns list of RankedSignal sorted by score descending (highest first).
        """
        sorted_signals = sorted(signals, key=lambda s: s.score, reverse=True)
        return [
            RankedSignal(
                symbol=s.symbol,
                side=s.side,
                score=s.score,
                size=s.size,
                rank=i + 1,
            )
            for i, s in enumerate(sorted_signals)
        ]


class ReserveCapacityService:
    """Tracks reserve/capacity for signal execution."""

    def __init__(
        self,
        total_capacity: Decimal,
    ) -> None:
        self.total_capacity = total_capacity
        self._allocated: Decimal = Decimal(0)

    def allocate(
        self,
        size: Decimal,
    ) -> bool:
        """Attempt to allocate size from remaining capacity.

        Returns True if allocation succeeded (remaining capacity sufficient).
        """
        if self._allocated + size > self.total_capacity:
            return False
        self._allocated += size
        return True

    @property
    def remaining_capacity(self) -> Decimal:
        """Remaining reserve capacity."""
        return self.total_capacity - self._allocated

    @property
    def allocated_capacity(self) -> Decimal:
        """Currently allocated capacity."""
        return self._allocated


class GroupLimitService:
    """Enforces group-level limits (max signal count, max risk pct)."""

    def __init__(
        self,
    ) -> None:
        self._limits: dict[str, GroupLimit] = {}

    def add_group_limit(
        self,
        group_name: str,
        max_signals: int,
        max_risk_pct: Decimal,
    ) -> None:
        """Add a group limit (OPEN configuration input)."""
        self._limits[group_name] = GroupLimit(
            group_name=group_name,
            max_signals=max_signals,
            max_risk_pct=max_risk_pct,
        )

    def get_group_limit(
        self,
        group_name: str,
    ) -> GroupLimit | None:
        """Get group limit by name."""
        return self._limits.get(group_name)


class ResizeRejectSemantics:
    """Resize or reject signals when capacity limits breached."""

    def __init__(
        self,
        min_size: Decimal = Decimal(0),
    ) -> None:
        self.min_size = min_size

    def resize_or_reject(
        self,
        signal: Signal,
        available_capacity: Decimal,
    ) -> ResizeRejectDecision:
        """Decide whether to resize or reject a signal.

        Args:
            signal: the signal to size
            available_capacity: remaining capacity available

        Returns ResizeRejectDecision with decision "resize" or "reject".
        """
        if available_capacity >= signal.size:
            return ResizeRejectDecision(
                decision="resize",
                original_size=signal.size,
                resized_size=signal.size,
            )
        if available_capacity >= self.min_size:
            return ResizeRejectDecision(
                decision="resize",
                original_size=signal.size,
                resized_size=available_capacity,
            )
        return ResizeRejectDecision(
            decision="reject",
            original_size=signal.size,
            resized_size=Decimal(0),
        )


def rank_signals(
    signals: list[Signal],
) -> list[RankedSignal]:
    """Rank signals by score descending (convenience function)."""
    return SignalRankingService().rank_signals(signals)


def allocate_capacity(
    service: ReserveCapacityService,
    signals: list[Signal],
) -> AllocationResult:
    """Allocate capacity for ranked signals.

    Allocates signals in order until capacity exhausted.
    Returns AllocationResult with allocated flag (True only if ALL signals fit
    within reserve capacity) and totals.
    """
    total = Decimal(0)
    all_allocated = True
    for signal in signals:
        if service.allocate(signal.size):
            total += signal.size
        else:
            all_allocated = False
            break
    return AllocationResult(
        allocated=all_allocated,
        total_allocated=total,
        remaining_capacity=service.remaining_capacity,
    )


def check_group_limits(
    service: GroupLimitService,
    group_name: str,
    signals: list[Signal],
) -> GroupLimitResult:
    """Check group limits against signals.

    Args:
        service: GroupLimitService with configured limits
        group_name: group to check
        signals: signals in the group

    Returns GroupLimitResult with passed flag and reasons.
    """
    limit = service.get_group_limit(group_name)
    if limit is None:
        return GroupLimitResult(
            passed=True,
            reasons=[],
        )
    reasons: list[str] = []
    passed = True

    if len(signals) > limit.max_signals:
        passed = False
        reasons.append(f"signal count {len(signals)} exceeds max_signals {limit.max_signals}")

    total_risk = sum((s.size for s in signals), Decimal(0))
    if total_risk > limit.max_risk_pct:
        passed = False
        reasons.append(f"total risk {total_risk} exceeds max_risk_pct {limit.max_risk_pct}")

    return GroupLimitResult(
        passed=passed,
        reasons=reasons,
    )


def resize_or_reject(
    service: ResizeRejectSemantics,
    signal: Signal,
    available_capacity: Decimal,
) -> ResizeRejectDecision:
    """Resize or reject a signal (convenience function)."""
    return service.resize_or_reject(signal, available_capacity)

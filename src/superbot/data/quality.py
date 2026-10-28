"""Data-quality validation for collections of OHLCV bars (M2.2).

Validates chronology, duplicates, gaps, staleness, suspicious prices, and
availability timestamps. Collection-level checks report problems; individual
bar correctness is enforced by OHLCVBar (schema.md section 3).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from superbot.contracts.ohlcv import (
    InvalidOHLCVError,
    OHLCVBar,
    Timeframe,
)


@dataclass(frozen=True)
class GapReport:
    has_gaps: bool
    gaps: list[tuple[datetime, datetime]] = field(default_factory=list)


@dataclass(frozen=True)
class FreshnessReport:
    is_stale: bool
    stale_bars: list[datetime] = field(default_factory=list)


@dataclass(frozen=True)
class PriceReport:
    has_suspicious: bool
    suspicious: list[datetime] = field(default_factory=list)


def _utc_now() -> datetime:
    return datetime.now(tz=UTC)


def validate_chronology(bars: Iterable[OHLCVBar]) -> None:
    """Reject bars whose open times are not strictly increasing."""
    previous: int | None = None
    for bar in bars:
        current = int(bar.bar_open_utc.timestamp())
        if previous is not None and current <= previous:
            raise InvalidOHLCVError(
                "chronology violated: bar at "
                f"{bar.bar_open_utc} is not after previous bar at "
                f"{datetime.fromtimestamp(previous, tz=UTC)}"
            )
        previous = current


def validate_no_duplicates(bars: Iterable[OHLCVBar]) -> None:
    """Reject bars with duplicate open times."""
    seen: set[int] = set()
    for bar in bars:
        key = int(bar.bar_open_utc.timestamp())
        if key in seen:
            raise InvalidOHLCVError(f"duplicate bar open time: {bar.bar_open_utc}")
        seen.add(key)


def validate_gaps(bars: Iterable[OHLCVBar], timeframe: Timeframe) -> GapReport:
    """Flag gaps larger than one expected interval between consecutive bars.

    Does not reject; callers decide whether gaps block work.
    """
    sorted_bars = sorted(bars, key=lambda b: b.bar_open_utc)
    delta = _timeframe_delta(timeframe)
    gaps: list[tuple[datetime, datetime]] = []
    previous: datetime | None = None
    for bar in sorted_bars:
        if previous is not None:
            expected = previous + delta
            if bar.bar_open_utc > expected:
                gaps.append((expected, bar.bar_open_utc))
        previous = bar.bar_open_utc
    return GapReport(has_gaps=len(gaps) > 0, gaps=gaps)


def validate_freshness(
    bars: Iterable[OHLCVBar], max_age: timedelta, now: datetime | None = None
) -> FreshnessReport:
    """Flag bars whose available_at_utc is older than max_age."""
    reference = now if now is not None else _utc_now()
    stale: list[datetime] = []
    for bar in bars:
        if bar.available_at_utc is None:
            continue
        if reference - bar.available_at_utc > max_age:
            stale.append(bar.bar_open_utc)
    return FreshnessReport(is_stale=len(stale) > 0, stale_bars=stale)


def validate_prices(bars: Iterable[OHLCVBar]) -> PriceReport:
    """Flag bars with non-positive open/high/low/close prices."""
    suspicious: list[datetime] = []
    for bar in bars:
        for value in (bar.open, bar.high, bar.low, bar.close):
            if value <= 0:
                suspicious.append(bar.bar_open_utc)
                break
    return PriceReport(has_suspicious=len(suspicious) > 0, suspicious=suspicious)


def validate_availability(bars: Iterable[OHLCVBar]) -> None:
    """Reject bars missing an availability timestamp."""
    for bar in bars:
        if bar.available_at_utc is None:
            raise InvalidOHLCVError(f"missing available_at_utc for bar at {bar.bar_open_utc}")


def _timeframe_delta(timeframe: Timeframe) -> timedelta:
    return {
        Timeframe.M5: timedelta(minutes=5),
        Timeframe.M15: timedelta(minutes=15),
        Timeframe.H1: timedelta(hours=1),
        Timeframe.H4: timedelta(hours=4),
    }[timeframe]

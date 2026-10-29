"""Trend-following / pullback strategy rule contract (schema.md section 5.2).

Provides deterministic trend detection and pullback signal generation.
All thresholds are explicit numeric parameters; no discretionary terms.
Stdlib-only; no import-time network/MT5/database/model activity.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class TrendDirection(str, Enum):
    UPTREND = "uptrend"
    DOWNTREND = "downtrend"
    RANGING = "ranging"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class TrendSpec:
    """Versioned trend-detection rule specification."""

    schema_version: str
    rule_id: str
    lookback_bars: int
    ma_period: int


@dataclass(frozen=True)
class PullbackSpec:
    """Versioned pullback-detection rule specification."""

    schema_version: str
    rule_id: str
    min_depth_pct: Decimal
    max_depth_pct: Decimal
    require_bounce: bool


@dataclass(frozen=True)
class PullbackSignal:
    """A deterministic pullback entry signal."""

    signal_type: str  # "entry_long" | "entry_short"
    entry_price: Decimal
    stop_price: Decimal
    depth_pct: Decimal


def detect_trend(
    bars: list[tuple[int, Decimal, Decimal, Decimal, Decimal]],
    spec: TrendSpec,
) -> TrendDirection:
    """Detect trend direction over the lookback window.

    UPTREND: higher highs and higher lows across the window.
    DOWNTREND: lower highs and lower lows across the window.
    RANGING: neither.
    UNKNOWN: fewer bars than lookback.
    """
    if len(bars) < spec.lookback_bars:
        return TrendDirection.UNKNOWN

    window = bars[-spec.lookback_bars :]

    higher_highs = all(window[i][2] >= window[i - 1][2] for i in range(1, len(window)))
    higher_lows = all(window[i][3] >= window[i - 1][3] for i in range(1, len(window)))
    lower_highs = all(window[i][2] <= window[i - 1][2] for i in range(1, len(window)))
    lower_lows = all(window[i][3] <= window[i - 1][3] for i in range(1, len(window)))

    if higher_highs and higher_lows:
        return TrendDirection.UPTREND
    if lower_highs and lower_lows:
        return TrendDirection.DOWNTREND
    return TrendDirection.RANGING


def detect_pullback(
    bars: list[tuple[int, Decimal, Decimal, Decimal, Decimal]],
    trend: TrendDirection,
    trend_spec: TrendSpec,
    pullback_spec: PullbackSpec,
) -> PullbackSignal | None:
    """Detect a pullback entry signal in the direction of the trend.

    Uptrend pullback: price retraces from recent high toward trend-start low,
    depth within [min_depth_pct, max_depth_pct], then bounces (close > low).
    Downtrend pullback: price retraces from recent low toward trend-start high,
    depth within range, then bounces down (close < high).
    """
    if trend not in (TrendDirection.UPTREND, TrendDirection.DOWNTREND):
        return None
    if len(bars) < trend_spec.lookback_bars + 1:
        return None

    # Historical bars only — exclude current (pullback) bar from trend/impulse
    history = bars[:-1]
    window = history[-trend_spec.lookback_bars :]
    current_bar = bars[-1]
    current_close = Decimal(str(current_bar[4]))
    current_high = Decimal(str(current_bar[2]))
    current_low = Decimal(str(current_bar[3]))

    if trend == TrendDirection.UPTREND:
        trend_start_low = min(Decimal(str(b[3])) for b in window)
        recent_high = max(Decimal(str(b[2])) for b in window)
        impulse = recent_high - trend_start_low
        if impulse <= Decimal(0):
            return None
        retracement = recent_high - current_low
        depth_pct = (retracement / impulse) * Decimal(100)
        if not (pullback_spec.min_depth_pct <= depth_pct <= pullback_spec.max_depth_pct):
            return None
        if pullback_spec.require_bounce and current_close <= current_low:
            return None
        entry_price = current_close
        stop_price = trend_start_low
    else:  # DOWNTREND
        trend_start_high = max(Decimal(str(b[2])) for b in window)
        recent_low = min(Decimal(str(b[3])) for b in window)
        impulse = trend_start_high - recent_low
        if impulse <= Decimal(0):
            return None
        retracement = current_high - recent_low
        depth_pct = (retracement / impulse) * Decimal(100)
        if not (pullback_spec.min_depth_pct <= depth_pct <= pullback_spec.max_depth_pct):
            return None
        if pullback_spec.require_bounce and current_close >= current_high:
            return None
        entry_price = current_close
        stop_price = trend_start_high

    return PullbackSignal(
        signal_type=("entry_long" if trend == TrendDirection.UPTREND else "entry_short"),
        entry_price=entry_price,
        stop_price=stop_price,
        depth_pct=depth_pct,
    )


def trend_following_entry(
    bars: list[tuple[int, Decimal, Decimal, Decimal, Decimal]],
    trend_spec: TrendSpec,
    pullback_spec: PullbackSpec,
) -> PullbackSignal | None:
    """Combine trend detection + pullback detection into an entry signal.

    Returns an entry_long signal in an uptrend pullback, or entry_short in a
    downtrend pullback. Returns None when no valid setup exists.
    """
    trend = detect_trend(bars[:-1], trend_spec)
    if trend == TrendDirection.UNKNOWN:
        return None
    return detect_pullback(bars, trend, trend_spec, pullback_spec)

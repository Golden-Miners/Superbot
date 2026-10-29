"""Liquidity-sweep / market-structure strategy contract (schema.md section 5.3).

Precise BOS (Break of Structure) and CHOCH (Change of Character) definitions,
plus liquidity-sweep detection. OB (Order Block) and FVG (Fair Value Gap) are
deferred until precise rule acceptance and are NOT implemented here.

Stdlib-only; no import-time network/MT5/database/model activity.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class BOSDirection(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"


class CHOCHDirection(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"


@dataclass(frozen=True)
class StructureSpec:
    """Versioned market-structure rule specification."""

    schema_version: str
    rule_id: str
    lookback_bars: int


@dataclass(frozen=True)
class StructureEvent:
    """A single structure event (BOS or CHOCH)."""

    ts: int  # bar open timestamp (UTC epoch ms)
    direction: str  # BOSDirection.* | CHOCHDirection.*
    break_level: Decimal  # price level that was broken


@dataclass(frozen=True)
class LiquiditySweep:
    """A liquidity sweep: wick breaches a level but close rejects it."""

    ts: int
    direction: str  # "bullish" | "bearish"
    swept_level: Decimal  # level that was swept


@dataclass(frozen=True)
class StructureState:
    """Current market-structure state."""

    swing_high: Decimal
    swing_low: Decimal
    current_trend: str  # "uptrend" | "downtrend" | "ranging"


def _swing_points(
    bars: list[tuple[int, Decimal, Decimal, Decimal, Decimal]],
    lookback: int,
) -> tuple[Decimal, Decimal]:
    """Return (swing_high, swing_low) over the lookback window."""
    window = bars[-lookback:]
    swing_high = max(Decimal(str(b[2])) for b in window)
    swing_low = min(Decimal(str(b[3])) for b in window)
    return swing_high, swing_low


def detect_bos(
    bars: list[tuple[int, Decimal, Decimal, Decimal, Decimal]],
    spec: StructureSpec,
) -> list[StructureEvent]:
    """Detect Break of Structure events.

    Bullish BOS: close breaks above prior swing high.
    Bearish BOS: close breaks below prior swing low.
    """
    if len(bars) < spec.lookback_bars + 1:
        return []

    history = bars[:-1]
    current_bar = bars[-1]
    current_close = Decimal(str(current_bar[4]))
    current_ts = int(current_bar[0])

    swing_high, swing_low = _swing_points(history, spec.lookback_bars)

    events: list[StructureEvent] = []
    if current_close > swing_high:
        events.append(
            StructureEvent(
                ts=current_ts,
                direction=BOSDirection.BULLISH,
                break_level=swing_high,
            )
        )
    if current_close < swing_low:
        events.append(
            StructureEvent(
                ts=current_ts,
                direction=BOSDirection.BEARISH,
                break_level=swing_low,
            )
        )
    return events


def detect_choch(
    bars: list[tuple[int, Decimal, Decimal, Decimal, Decimal]],
    spec: StructureSpec,
) -> list[StructureEvent]:
    """Detect Change of Character events.

    Bullish CHOCH: in downtrend, close breaks above prior swing high.
    Bearish CHOCH: in uptrend, close breaks below prior swing low.
    Uses the same break logic as BOS but interpreted as trend reversal
    based on the prevailing trend direction.
    """
    if len(bars) < spec.lookback_bars + 1:
        return []

    history = bars[:-1]
    current_bar = bars[-1]
    current_close = Decimal(str(current_bar[4]))
    current_ts = int(current_bar[0])

    swing_high, swing_low = _swing_points(history, spec.lookback_bars)

    # Determine prevailing trend from history
    history_closes = [Decimal(str(b[4])) for b in history]
    if len(history_closes) >= 2:
        prev_close = history_closes[-1]
        first_close = history_closes[0]
        if prev_close > first_close:
            prevailing = "uptrend"
        elif prev_close < first_close:
            prevailing = "downtrend"
        else:
            prevailing = "ranging"
    else:
        prevailing = "ranging"

    events: list[StructureEvent] = []
    if prevailing == "downtrend" and current_close > swing_high:
        events.append(
            StructureEvent(
                ts=current_ts,
                direction=CHOCHDirection.BULLISH,
                break_level=swing_high,
            )
        )
    if prevailing == "uptrend" and current_close < swing_low:
        events.append(
            StructureEvent(
                ts=current_ts,
                direction=CHOCHDirection.BEARISH,
                break_level=swing_low,
            )
        )
    return events


def detect_liquidity_sweep(
    bars: list[tuple[int, Decimal, Decimal, Decimal, Decimal]],
    spec: StructureSpec,
) -> list[LiquiditySweep]:
    """Detect liquidity sweeps: wick breaches a level but close rejects it.

    Bullish sweep: low breaches swing low but close closes above it.
    Bearish sweep: high breaches swing high but close closes below it.
    """
    if len(bars) < spec.lookback_bars + 1:
        return []

    history = bars[:-1]
    current_bar = bars[-1]
    current_ts = int(current_bar[0])
    Decimal(str(current_bar[1]))
    current_high = Decimal(str(current_bar[2]))
    current_low = Decimal(str(current_bar[3]))
    current_close = Decimal(str(current_bar[4]))

    swing_high, swing_low = _swing_points(history, spec.lookback_bars)

    sweeps: list[LiquiditySweep] = []
    # Bullish sweep: wick below swing low, close above it
    if current_low < swing_low and current_close > swing_low:
        sweeps.append(
            LiquiditySweep(
                ts=current_ts,
                direction="bullish",
                swept_level=swing_low,
            )
        )
    # Bearish sweep: wick above swing high, close below it
    if current_high > swing_high and current_close < swing_high:
        sweeps.append(
            LiquiditySweep(
                ts=current_ts,
                direction="bearish",
                swept_level=swing_high,
            )
        )
    return sweeps


def get_structure_state(
    bars: list[tuple[int, Decimal, Decimal, Decimal, Decimal]],
    spec: StructureSpec,
) -> StructureState:
    """Return current swing high, swing low, and prevailing trend."""
    if len(bars) < spec.lookback_bars:
        raise ValueError(f"insufficient bars: {len(bars)} < lookback {spec.lookback_bars}")

    window = bars[-spec.lookback_bars :]
    swing_high = max(Decimal(str(b[2])) for b in window)
    swing_low = min(Decimal(str(b[3])) for b in window)

    closes = [Decimal(str(b[4])) for b in window]
    if closes[-1] > closes[0]:
        trend = "uptrend"
    elif closes[-1] < closes[0]:
        trend = "downtrend"
    else:
        trend = "ranging"

    return StructureState(
        swing_high=swing_high,
        swing_low=swing_low,
        current_trend=trend,
    )

"""RED tests for M5.3 — Liquidity-sweep/structure strategy; precise BOS/CHOCH definitions.

Tests define:
- Bullish BOS: price breaks above prior swing high with close above it
- Bearish BOS: price breaks below prior swing low with close below it
- Bullish CHOCH: in downtrend, price breaks above prior swing high (trend reversal)
- Bearish CHOCH: in uptrend, price breaks below prior swing low (trend reversal)
- Liquidity sweep: wick breaches a level but close rejects it (false breakout)
- Structure state machine tracks swing highs/lows and emits BOS/CHOCH events
- Versioned rule spec: StructureSpec carries schema_version, rule_id, lookback_bars
- Deterministic: same inputs yield identical structure events
- No discretionary terms: all thresholds explicit numeric parameters
- OB/FVG deferred until precise rule acceptance (not tested here)
"""

from __future__ import annotations

from decimal import Decimal

from superbot.strategy.structure_liquidity import (
    BOSDirection,
    CHOCHDirection,
    StructureSpec,
    detect_bos,
    detect_choch,
    detect_liquidity_sweep,
    get_structure_state,
)


def test_bullish_bos():
    """Price breaks above prior swing high with close above = bullish BOS."""
    bars = [
        (1, Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0")),
        (2, Decimal("101.0"), Decimal("103.0"), Decimal("100.0"), Decimal("102.0")),
        (3, Decimal("102.0"), Decimal("104.0"), Decimal("101.0"), Decimal("103.0")),
        # Swing high at bar 3 = 104.0
        (4, Decimal("103.0"), Decimal("105.0"), Decimal("102.5"), Decimal("104.5")),
    ]
    spec = StructureSpec(
        schema_version="1.0.0",
        rule_id="bos_bullish_001",
        lookback_bars=3,
    )
    events = detect_bos(bars, spec)
    assert len(events) == 1
    assert events[0].direction == BOSDirection.BULLISH
    assert events[0].break_level == Decimal("104.0")


def test_bearish_bos():
    """Price breaks below prior swing low with close below = bearish BOS."""
    bars = [
        (1, Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0")),
        (2, Decimal("99.0"), Decimal("100.0"), Decimal("98.0"), Decimal("98.0")),
        (3, Decimal("98.0"), Decimal("99.0"), Decimal("97.0"), Decimal("97.0")),
        # Swing low at bar 3 = 97.0
        (4, Decimal("97.0"), Decimal("98.0"), Decimal("96.0"), Decimal("96.5")),
    ]
    spec = StructureSpec(
        schema_version="1.0.0",
        rule_id="bos_bearish_001",
        lookback_bars=3,
    )
    events = detect_bos(bars, spec)
    assert len(events) == 1
    assert events[0].direction == BOSDirection.BEARISH
    assert events[0].break_level == Decimal("97.0")


def test_no_bos_when_close_does_not_break():
    """Wick breaches but close does not break = no BOS (liquidity sweep instead)."""
    bars = [
        (1, Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0")),
        (2, Decimal("101.0"), Decimal("103.0"), Decimal("100.0"), Decimal("102.0")),
        (3, Decimal("102.0"), Decimal("104.0"), Decimal("101.0"), Decimal("103.0")),
        # Wick above 104.0 but close below = no BOS
        (4, Decimal("103.0"), Decimal("105.0"), Decimal("102.5"), Decimal("103.5")),
    ]
    spec = StructureSpec(
        schema_version="1.0.0",
        rule_id="bos_none_001",
        lookback_bars=3,
    )
    events = detect_bos(bars, spec)
    assert len(events) == 0


def test_bullish_choch():
    """In downtrend, price breaks above prior swing high = bullish CHOCH."""
    bars = [
        (1, Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("99.0")),
        (2, Decimal("99.0"), Decimal("100.0"), Decimal("98.0"), Decimal("98.0")),
        (3, Decimal("98.0"), Decimal("99.0"), Decimal("97.0"), Decimal("97.0")),
        # Downtrend, swing high resistance at bar 1 = 101.0
        (4, Decimal("97.0"), Decimal("102.0"), Decimal("96.0"), Decimal("101.5")),
    ]
    spec = StructureSpec(
        schema_version="1.0.0",
        rule_id="choch_bullish_001",
        lookback_bars=3,
    )
    events = detect_choch(bars, spec)
    assert len(events) == 1
    assert events[0].direction == CHOCHDirection.BULLISH
    assert events[0].break_level == Decimal("101.0")


def test_bearish_choch():
    """In uptrend, price breaks below prior swing low = bearish CHOCH."""
    bars = [
        (1, Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("101.0")),
        (2, Decimal("101.0"), Decimal("102.0"), Decimal("100.0"), Decimal("101.0")),
        (3, Decimal("101.0"), Decimal("103.0"), Decimal("100.0"), Decimal("102.0")),
        # Uptrend, swing low support at bar 1 = 99.0
        (4, Decimal("102.0"), Decimal("103.0"), Decimal("98.0"), Decimal("98.5")),
    ]
    spec = StructureSpec(
        schema_version="1.0.0",
        rule_id="choch_bearish_001",
        lookback_bars=3,
    )
    events = detect_choch(bars, spec)
    assert len(events) == 1
    assert events[0].direction == CHOCHDirection.BEARISH
    assert events[0].break_level == Decimal("99.0")


def test_liquidity_sweep_bullish():
    """Wick breaches below swing low but close rejects above = bullish liquidity sweep."""
    bars = [
        (1, Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0")),
        (2, Decimal("101.0"), Decimal("103.0"), Decimal("100.0"), Decimal("102.0")),
        # Swing low = 99.0
        (3, Decimal("102.0"), Decimal("104.0"), Decimal("98.0"), Decimal("103.0")),
    ]
    spec = StructureSpec(
        schema_version="1.0.0",
        rule_id="sweep_bullish_001",
        lookback_bars=2,
    )
    sweeps = detect_liquidity_sweep(bars, spec)
    assert len(sweeps) == 1
    assert sweeps[0].direction == "bullish"  # swept below, closed above
    assert sweeps[0].swept_level == Decimal("99.0")


def test_liquidity_sweep_bearish():
    """Wick breaches above swing high but close rejects below = bearish liquidity sweep."""
    bars = [
        (1, Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0")),
        (2, Decimal("100.0"), Decimal("102.0"), Decimal("99.0"), Decimal("101.0")),
        # Swing high = 102.0
        (3, Decimal("101.0"), Decimal("103.0"), Decimal("100.5"), Decimal("101.0")),
    ]
    spec = StructureSpec(
        schema_version="1.0.0",
        rule_id="sweep_bearish_001",
        lookback_bars=2,
    )
    sweeps = detect_liquidity_sweep(bars, spec)
    assert len(sweeps) == 1
    assert sweeps[0].direction == "bearish"  # swept above, closed below
    assert sweeps[0].swept_level == Decimal("102.0")


def test_no_liquidity_sweep_when_close_breaks():
    """Close actually breaks level = BOS/CHOCH, not liquidity sweep."""
    bars = [
        (1, Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0")),
        (2, Decimal("101.0"), Decimal("103.0"), Decimal("100.0"), Decimal("102.0")),
        (3, Decimal("102.0"), Decimal("104.0"), Decimal("101.0"), Decimal("104.5")),
    ]
    spec = StructureSpec(
        schema_version="1.0.0",
        rule_id="sweep_none_001",
        lookback_bars=2,
    )
    sweeps = detect_liquidity_sweep(bars, spec)
    assert len(sweeps) == 0


def test_structure_state_swing_highs_lows():
    """get_structure_state tracks swing highs and lows."""
    bars = [
        (1, Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0")),
        (2, Decimal("101.0"), Decimal("103.0"), Decimal("100.0"), Decimal("102.0")),
        (3, Decimal("102.0"), Decimal("104.0"), Decimal("101.0"), Decimal("103.0")),
    ]
    spec = StructureSpec(
        schema_version="1.0.0",
        rule_id="state_001",
        lookback_bars=3,
    )
    state = get_structure_state(bars, spec)
    assert state.swing_high == Decimal("104.0")
    assert state.swing_low == Decimal("99.0")
    assert state.current_trend == "uptrend"


def test_structure_spec_versioned():
    """StructureSpec carries schema_version and rule_id."""
    spec = StructureSpec(
        schema_version="1.0.0",
        rule_id="struct_ver_001",
        lookback_bars=20,
    )
    assert spec.schema_version == "1.0.0"
    assert spec.rule_id == "struct_ver_001"


def test_deterministic_structure():
    """Same inputs yield identical structure events."""
    bars = [
        (1, Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0")),
        (2, Decimal("101.0"), Decimal("103.0"), Decimal("100.0"), Decimal("102.0")),
        (3, Decimal("102.0"), Decimal("104.0"), Decimal("101.0"), Decimal("103.0")),
        (4, Decimal("103.0"), Decimal("105.0"), Decimal("102.5"), Decimal("104.5")),
    ]
    spec = StructureSpec(
        schema_version="1.0.0",
        rule_id="struct_det_001",
        lookback_bars=3,
    )
    e1 = detect_bos(bars, spec)
    e2 = detect_bos(bars, spec)
    assert e1 == e2


def test_insufficient_bars_no_events():
    """Fewer bars than lookback returns no structure events."""
    bars = [
        (1, Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0")),
        (2, Decimal("101.0"), Decimal("102.0"), Decimal("100.0"), Decimal("101.0")),
    ]
    spec = StructureSpec(
        schema_version="1.0.0",
        rule_id="struct_insuff_001",
        lookback_bars=5,
    )
    events = detect_bos(bars, spec)
    assert len(events) == 0
    events = detect_choch(bars, spec)
    assert len(events) == 0
    sweeps = detect_liquidity_sweep(bars, spec)
    assert len(sweeps) == 0

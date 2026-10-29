"""RED tests for M5.2 — Trend-following/pullback definition and tests.

Tests define:
- Trend detection: higher highs and higher lows = uptrend; lower highs and lower lows = downtrend
- Ranging market: neither higher highs/higher lows nor lower highs/lower lows
- Pullback detection: in uptrend, price retraces toward support then bounces
- Pullback depth quantified as percentage of prior impulse move
- Trend-following entry: long in uptrend on pullback to support; short in downtrend on pullback to resistance
- Trend must be confirmed over lookback window (not single bar)
- Versioned rule schema: TrendSpec and PullbackSpec carry schema_version and rule_id
- Same inputs yield identical trend/pullback signals (deterministic)
- Insufficient bars return UNKNOWN trend / no pullback signal
- No discretionary terms: all thresholds are explicit numeric parameters
"""

from __future__ import annotations

from decimal import Decimal

from superbot.strategy.trend_following import (
    PullbackSpec,
    TrendDirection,
    TrendSpec,
    detect_pullback,
    detect_trend,
    trend_following_entry,
)


def test_uptrend_higher_highs_higher_lows():
    """Higher highs and higher lows over lookback = uptrend."""
    bars = [
        (1, Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0")),
        (2, Decimal("101.0"), Decimal("103.0"), Decimal("100.0"), Decimal("102.0")),
        (3, Decimal("102.0"), Decimal("104.0"), Decimal("101.0"), Decimal("103.0")),
        (4, Decimal("103.0"), Decimal("105.0"), Decimal("102.0"), Decimal("104.0")),
        (5, Decimal("104.0"), Decimal("106.0"), Decimal("103.0"), Decimal("105.0")),
    ]
    spec = TrendSpec(
        schema_version="1.0.0",
        rule_id="trend_uptrend_001",
        lookback_bars=5,
        ma_period=3,
    )
    trend = detect_trend(bars, spec)
    assert trend == TrendDirection.UPTREND


def test_downtrend_lower_highs_lower_lows():
    """Lower highs and lower lows over lookback = downtrend."""
    bars = [
        (1, Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("99.0")),
        (2, Decimal("99.0"), Decimal("100.0"), Decimal("98.0"), Decimal("98.0")),
        (3, Decimal("98.0"), Decimal("99.0"), Decimal("97.0"), Decimal("97.0")),
        (4, Decimal("97.0"), Decimal("98.0"), Decimal("96.0"), Decimal("96.0")),
        (5, Decimal("96.0"), Decimal("97.0"), Decimal("95.0"), Decimal("95.0")),
    ]
    spec = TrendSpec(
        schema_version="1.0.0",
        rule_id="trend_downtrend_001",
        lookback_bars=5,
        ma_period=3,
    )
    trend = detect_trend(bars, spec)
    assert trend == TrendDirection.DOWNTREND


def test_ranging_market():
    """Neither HH/HL nor LH/LL = ranging."""
    bars = [
        (1, Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0")),
        (2, Decimal("102.0"), Decimal("103.0"), Decimal("99.0"), Decimal("101.0")),
        (3, Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0")),
        (4, Decimal("102.0"), Decimal("103.0"), Decimal("99.0"), Decimal("101.0")),
        (5, Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0")),
    ]
    spec = TrendSpec(
        schema_version="1.0.0",
        rule_id="trend_ranging_001",
        lookback_bars=5,
        ma_period=3,
    )
    trend = detect_trend(bars, spec)
    assert trend == TrendDirection.RANGING


def test_insufficient_bars_unknown():
    """Fewer bars than lookback returns UNKNOWN trend."""
    bars = [
        (1, Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0")),
        (2, Decimal("101.0"), Decimal("102.0"), Decimal("100.0"), Decimal("101.0")),
    ]
    spec = TrendSpec(
        schema_version="1.0.0",
        rule_id="trend_insufficient_001",
        lookback_bars=5,
        ma_period=3,
    )
    trend = detect_trend(bars, spec)
    assert trend == TrendDirection.UNKNOWN


def test_pullback_in_uptrend():
    """In uptrend, price retraces to support then bounces = pullback long signal."""
    bars = [
        (1, Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0")),
        (2, Decimal("101.0"), Decimal("103.0"), Decimal("100.0"), Decimal("102.0")),
        (3, Decimal("102.0"), Decimal("104.0"), Decimal("101.0"), Decimal("103.0")),
        (4, Decimal("103.0"), Decimal("105.0"), Decimal("102.0"), Decimal("104.0")),
        (5, Decimal("104.0"), Decimal("106.0"), Decimal("103.0"), Decimal("105.0")),
        # Pullback: price retraces toward prior swing low (101.0) but stays above it
        (6, Decimal("105.0"), Decimal("105.5"), Decimal("102.0"), Decimal("102.5")),
    ]
    trend_spec = TrendSpec(
        schema_version="1.0.0",
        rule_id="trend_pullback_001",
        lookback_bars=5,
        ma_period=3,
    )
    pullback_spec = PullbackSpec(
        schema_version="1.0.0",
        rule_id="pullback_long_001",
        min_depth_pct=Decimal(10),
        max_depth_pct=Decimal(60),
        require_bounce=True,
    )
    signal = detect_pullback(bars, TrendDirection.UPTREND, trend_spec, pullback_spec)
    assert signal is not None
    assert signal.signal_type == "entry_long"
    assert signal.entry_price is not None
    assert signal.stop_price is not None


def test_no_pullback_in_ranging():
    """Ranging market produces no pullback signal."""
    bars = [
        (1, Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0")),
        (2, Decimal("102.0"), Decimal("103.0"), Decimal("99.0"), Decimal("101.0")),
        (3, Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0")),
    ]
    trend_spec = TrendSpec(
        schema_version="1.0.0",
        rule_id="trend_no_pullback_001",
        lookback_bars=3,
        ma_period=2,
    )
    pullback_spec = PullbackSpec(
        schema_version="1.0.0",
        rule_id="pullback_none_001",
        min_depth_pct=Decimal(10),
        max_depth_pct=Decimal(60),
        require_bounce=True,
    )
    signal = detect_pullback(bars, TrendDirection.RANGING, trend_spec, pullback_spec)
    assert signal is None


def test_pullback_depth_out_of_range():
    """Pullback deeper than max_depth_pct or shallower than min_depth_pct = no signal."""
    bars = [
        (1, Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0")),
        (2, Decimal("101.0"), Decimal("103.0"), Decimal("100.0"), Decimal("102.0")),
        (3, Decimal("102.0"), Decimal("104.0"), Decimal("101.0"), Decimal("103.0")),
        (4, Decimal("103.0"), Decimal("105.0"), Decimal("102.0"), Decimal("104.0")),
        (5, Decimal("104.0"), Decimal("106.0"), Decimal("103.0"), Decimal("105.0")),
        # Deep pullback: retraces below prior swing low
        (6, Decimal("105.0"), Decimal("105.5"), Decimal("99.0"), Decimal("100.0")),
    ]
    trend_spec = TrendSpec(
        schema_version="1.0.0",
        rule_id="trend_deep_001",
        lookback_bars=5,
        ma_period=3,
    )
    pullback_spec = PullbackSpec(
        schema_version="1.0.0",
        rule_id="pullback_deep_001",
        min_depth_pct=Decimal(10),
        max_depth_pct=Decimal(30),  # shallow only
        require_bounce=True,
    )
    signal = detect_pullback(bars, TrendDirection.UPTREND, trend_spec, pullback_spec)
    assert signal is None


def test_trend_following_entry_long():
    """trend_following_entry: long in uptrend on pullback."""
    bars = [
        (1, Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0")),
        (2, Decimal("101.0"), Decimal("103.0"), Decimal("100.0"), Decimal("102.0")),
        (3, Decimal("102.0"), Decimal("104.0"), Decimal("101.0"), Decimal("103.0")),
        (4, Decimal("103.0"), Decimal("105.0"), Decimal("102.0"), Decimal("104.0")),
        (5, Decimal("104.0"), Decimal("106.0"), Decimal("103.0"), Decimal("105.0")),
        (6, Decimal("105.0"), Decimal("105.5"), Decimal("102.0"), Decimal("102.5")),
    ]
    trend_spec = TrendSpec(
        schema_version="1.0.0",
        rule_id="tf_entry_long_001",
        lookback_bars=5,
        ma_period=3,
    )
    pullback_spec = PullbackSpec(
        schema_version="1.0.0",
        rule_id="tf_pullback_long_001",
        min_depth_pct=Decimal(10),
        max_depth_pct=Decimal(60),
        require_bounce=True,
    )
    signal = trend_following_entry(bars, trend_spec, pullback_spec)
    assert signal is not None
    assert signal.signal_type == "entry_long"
    assert signal.entry_price is not None


def test_trend_following_entry_short():
    """trend_following_entry: short in downtrend on pullback to resistance."""
    bars = [
        (1, Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0")),
        (2, Decimal("99.0"), Decimal("100.0"), Decimal("98.0"), Decimal("98.0")),
        (3, Decimal("98.0"), Decimal("99.0"), Decimal("97.0"), Decimal("97.0")),
        (4, Decimal("97.0"), Decimal("98.0"), Decimal("96.0"), Decimal("96.0")),
        (5, Decimal("96.0"), Decimal("97.0"), Decimal("95.0"), Decimal("95.0")),
        # Pullback up toward resistance
        (6, Decimal("95.0"), Decimal("97.5"), Decimal("94.5"), Decimal("96.0")),
    ]
    trend_spec = TrendSpec(
        schema_version="1.0.0",
        rule_id="tf_entry_short_001",
        lookback_bars=5,
        ma_period=3,
    )
    pullback_spec = PullbackSpec(
        schema_version="1.0.0",
        rule_id="tf_pullback_short_001",
        min_depth_pct=Decimal(10),
        max_depth_pct=Decimal(60),
        require_bounce=True,
    )
    signal = trend_following_entry(bars, trend_spec, pullback_spec)
    assert signal is not None
    assert signal.signal_type == "entry_short"
    assert signal.entry_price is not None


def test_trend_following_no_entry_ranging():
    """trend_following_entry: no signal in ranging market."""
    bars = [
        (1, Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0")),
        (2, Decimal("102.0"), Decimal("103.0"), Decimal("99.0"), Decimal("101.0")),
        (3, Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0")),
    ]
    trend_spec = TrendSpec(
        schema_version="1.0.0",
        rule_id="tf_none_001",
        lookback_bars=3,
        ma_period=2,
    )
    pullback_spec = PullbackSpec(
        schema_version="1.0.0",
        rule_id="tf_pullback_none_001",
        min_depth_pct=Decimal(10),
        max_depth_pct=Decimal(60),
        require_bounce=True,
    )
    signal = trend_following_entry(bars, trend_spec, pullback_spec)
    assert signal is None


def test_trend_spec_versioned():
    """TrendSpec carries schema_version and rule_id."""
    spec = TrendSpec(
        schema_version="1.0.0",
        rule_id="trend_ver_001",
        lookback_bars=10,
        ma_period=5,
    )
    assert spec.schema_version == "1.0.0"
    assert spec.rule_id == "trend_ver_001"


def test_pullback_spec_versioned():
    """PullbackSpec carries schema_version and rule_id."""
    spec = PullbackSpec(
        schema_version="1.0.0",
        rule_id="pullback_ver_001",
        min_depth_pct=Decimal(25),
        max_depth_pct=Decimal(50),
        require_bounce=True,
    )
    assert spec.schema_version == "1.0.0"
    assert spec.rule_id == "pullback_ver_001"


def test_deterministic_trend():
    """Same inputs yield identical trend detection."""
    bars = [
        (1, Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0")),
        (2, Decimal("101.0"), Decimal("103.0"), Decimal("100.0"), Decimal("102.0")),
        (3, Decimal("102.0"), Decimal("104.0"), Decimal("101.0"), Decimal("103.0")),
    ]
    spec = TrendSpec(
        schema_version="1.0.0",
        rule_id="trend_det_001",
        lookback_bars=3,
        ma_period=2,
    )
    t1 = detect_trend(bars, spec)
    t2 = detect_trend(bars, spec)
    assert t1 == t2


def test_deterministic_pullback():
    """Same inputs yield identical pullback signal."""
    bars = [
        (1, Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0")),
        (2, Decimal("101.0"), Decimal("103.0"), Decimal("100.0"), Decimal("102.0")),
        (3, Decimal("102.0"), Decimal("104.0"), Decimal("101.0"), Decimal("103.0")),
        (4, Decimal("103.0"), Decimal("105.0"), Decimal("102.0"), Decimal("104.0")),
        (5, Decimal("104.0"), Decimal("106.0"), Decimal("103.0"), Decimal("105.0")),
        (6, Decimal("105.0"), Decimal("105.5"), Decimal("101.5"), Decimal("102.0")),
    ]
    trend_spec = TrendSpec(
        schema_version="1.0.0",
        rule_id="pullback_det_001",
        lookback_bars=5,
        ma_period=3,
    )
    pullback_spec = PullbackSpec(
        schema_version="1.0.0",
        rule_id="pullback_det_002",
        min_depth_pct=Decimal(10),
        max_depth_pct=Decimal(60),
        require_bounce=True,
    )
    s1 = detect_pullback(bars, TrendDirection.UPTREND, trend_spec, pullback_spec)
    s2 = detect_pullback(bars, TrendDirection.UPTREND, trend_spec, pullback_spec)
    assert s1 == s2

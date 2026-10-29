"""RED tests for M6.2 — >=3 walk-forward windows and metric-accounting tests.

Tests define:
- WalkForwardSpec: n_windows (>=3), train_bars, val_bars, test_bars, gap_bars, step_bars
- generate_windows: produces >=3 walk-forward windows sliding across data chronologically
- Each window: train < val < test chronologically, no overlap
- Metric accounting: track metrics per window (PF, Sharpe, Sortino, max DD, trade count)
- Window determinism: same inputs → same windows
- Metric aggregation: mean/std across windows
- Failure accounting: windows failing gates counted
- Walk-forward stability: metrics not wildly divergent across windows
- Versioned spec: WalkForwardSpec carries schema_version, spec_id
- No discretionary terms: all thresholds explicit numeric values
- Deterministic: same inputs → same result
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from superbot.data.walk_forward import (
    MetricAccounting,
    WalkForwardSpec,
    check_stability,
    generate_windows,
)


def test_walk_forward_spec_versioned():
    """WalkForwardSpec carries schema_version and spec_id."""
    spec = WalkForwardSpec(
        schema_version="1.0.0",
        spec_id="wf_001",
        n_windows=4,
        train_bars=20,
        val_bars=5,
        test_bars=5,
        gap_bars=2,
        step_bars=10,
    )
    assert spec.schema_version == "1.0.0"
    assert spec.spec_id == "wf_001"


def test_generate_windows_min_3_windows():
    """Must produce at least 3 walk-forward windows."""
    bars = [d for d in range(1, 61)]
    spec = WalkForwardSpec(
        schema_version="1.0.0",
        spec_id="wf_min3",
        n_windows=3,
        train_bars=10,
        val_bars=3,
        test_bars=3,
        gap_bars=1,
        step_bars=10,
    )
    windows = generate_windows(bars, spec)
    assert len(windows) >= 3


def test_windows_chronological():
    """Each window: train < val < test chronologically."""
    bars = [d for d in range(1, 61)]
    spec = WalkForwardSpec(
        schema_version="1.0.0",
        spec_id="wf_chrono",
        n_windows=3,
        train_bars=10,
        val_bars=3,
        test_bars=3,
        gap_bars=1,
        step_bars=10,
    )
    windows = generate_windows(bars, spec)
    for w in windows:
        assert w.train_ts[-1] < w.val_ts[0]
        assert w.val_ts[-1] < w.test_ts[0]


def test_windows_no_overlap_within_window():
    """No timestamp appears in more than one split within a window."""
    bars = [d for d in range(1, 61)]
    spec = WalkForwardSpec(
        schema_version="1.0.0",
        spec_id="wf_no_overlap",
        n_windows=3,
        train_bars=10,
        val_bars=3,
        test_bars=3,
        gap_bars=1,
        step_bars=10,
    )
    windows = generate_windows(bars, spec)
    for w in windows:
        all_ts = set(w.train_ts) | set(w.val_ts) | set(w.test_ts)
        assert len(all_ts) == len(w.train_ts) + len(w.val_ts) + len(w.test_ts)


def test_windows_slide_forward():
    """Each subsequent window starts after the previous window's start."""
    bars = [d for d in range(1, 61)]
    spec = WalkForwardSpec(
        schema_version="1.0.0",
        spec_id="wf_slide",
        n_windows=3,
        train_bars=10,
        val_bars=3,
        test_bars=3,
        gap_bars=1,
        step_bars=10,
    )
    windows = generate_windows(bars, spec)
    for i in range(1, len(windows)):
        assert windows[i].train_ts[0] > windows[i - 1].train_ts[0]


def test_metric_accounting():
    """Metric accounting tracks metrics per window."""
    accounting = MetricAccounting()
    accounting.add_window(
        "w1",
        pf=Decimal("2.0"),
        sharpe=Decimal("1.5"),
        sortino=Decimal("1.4"),
        max_dd_pct=Decimal(5),
        trade_count=10,
    )
    accounting.add_window(
        "w2",
        pf=Decimal("1.8"),
        sharpe=Decimal("1.2"),
        sortino=Decimal("1.1"),
        max_dd_pct=Decimal(7),
        trade_count=8,
    )
    metrics = accounting.summary()
    assert metrics.pf_mean == Decimal("1.9")
    assert metrics.sharpe_mean == Decimal("1.35")
    assert metrics.max_dd_max == Decimal(7)
    assert metrics.trade_count_total == 18


def test_check_stability_pass():
    """Stability check passes when metrics are consistent across windows."""
    accounting = MetricAccounting()
    accounting.add_window(
        "w1",
        pf=Decimal("2.0"),
        sharpe=Decimal("1.5"),
        sortino=Decimal("1.4"),
        max_dd_pct=Decimal(5),
        trade_count=10,
    )
    accounting.add_window(
        "w2",
        pf=Decimal("1.9"),
        sharpe=Decimal("1.4"),
        sortino=Decimal("1.3"),
        max_dd_pct=Decimal(5),
        trade_count=9,
    )
    accounting.add_window(
        "w3",
        pf=Decimal("2.1"),
        sharpe=Decimal("1.6"),
        sortino=Decimal("1.5"),
        max_dd_pct=Decimal(6),
        trade_count=11,
    )
    result = check_stability(accounting)
    assert result.stable is True
    assert result.pf_cv_pct < Decimal(10)


def test_check_stability_fail_high_variance():
    """Stability check fails when metrics vary too much across windows."""
    accounting = MetricAccounting()
    accounting.add_window(
        "w1",
        pf=Decimal("3.0"),
        sharpe=Decimal("2.0"),
        sortino=Decimal("1.8"),
        max_dd_pct=Decimal(2),
        trade_count=20,
    )
    accounting.add_window(
        "w2",
        pf=Decimal("0.5"),
        sharpe=Decimal("0.1"),
        sortino=Decimal("0.05"),
        max_dd_pct=Decimal(25),
        trade_count=2,
    )
    result = check_stability(accounting)
    assert result.stable is False


def test_deterministic_windows():
    """Same inputs yield identical windows."""
    bars = [d for d in range(1, 61)]
    spec = WalkForwardSpec(
        schema_version="1.0.0",
        spec_id="wf_det",
        n_windows=3,
        train_bars=10,
        val_bars=3,
        test_bars=3,
        gap_bars=1,
        step_bars=10,
    )
    w1 = generate_windows(bars, spec)
    w2 = generate_windows(bars, spec)
    assert w1 == w2


def test_insufficient_bars_raises():
    """Fewer bars than required raises ValueError."""
    bars = [d for d in range(1, 11)]
    spec = WalkForwardSpec(
        schema_version="1.0.0",
        spec_id="wf_insuff",
        n_windows=3,
        train_bars=10,
        val_bars=3,
        test_bars=3,
        gap_bars=1,
        step_bars=10,
    )
    with pytest.raises(ValueError):
        generate_windows(bars, spec)


def test_n_windows_min_3():
    """Must have at least 3 windows."""
    [d for d in range(1, 61)]
    with pytest.raises(ValueError):
        WalkForwardSpec(
            schema_version="1.0.0",
            spec_id="wf_min",
            n_windows=2,
            train_bars=10,
            val_bars=3,
            test_bars=3,
            gap_bars=1,
            step_bars=10,
        )

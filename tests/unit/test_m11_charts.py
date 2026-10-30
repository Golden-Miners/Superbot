"""RED tests for M11.2 — Plotly chart generation for the data explorer surface.

Covers: OHLCV candlestick chart with volume subplot, source/freshness labels,
optional deterministic overlays labeled by definition/version, and
never-implying-live behavior.
"""

from __future__ import annotations

from superbot.m11.charts import ohlcv_chart, overlay_line


def test_ohlcv_chart_returns_plotly_figure():
    """ohlcv_chart returns a Plotly Figure with candlestick + volume."""
    fig = ohlcv_chart(
        symbol="XAUUSD",
        timeframe="M5",
        ohlcv=[
            {"t": "2024-01-15T10:00:00+00:00", "o": 2650.0, "h": 2655.0, "l": 2648.0, "c": 2653.0, "v": 100},
            {"t": "2024-01-15T10:05:00+00:00", "o": 2653.0, "h": 2658.0, "l": 2652.0, "c": 2656.0, "v": 120},
        ],
    )
    assert fig is not None
    # Has a candlestick trace and a volume trace
    trace_types = [t.type for t in fig.data]
    assert "candlestick" in trace_types
    assert "bar" in trace_types or "scatter" in trace_types


def test_ohlcv_chart_labels_source_and_not_live():
    """Chart annotations state the source and that data is not live broker data."""
    fig = ohlcv_chart(
        symbol="XAUUSD",
        timeframe="M5",
        ohlcv=[
            {"t": "2024-01-15T10:00:00+00:00", "o": 2650.0, "h": 2655.0, "l": 2648.0, "c": 2653.0, "v": 100},
        ],
        source="synthetic_fixture",
    )
    annotations = fig.layout.annotations or []
    texts = [a.text for a in annotations]
    assert any("synthetic" in (t or "").lower() for t in texts)
    assert any("not live" in (t or "").lower() for t in texts)


def test_overlay_line_labeled_by_definition_version():
    """overlay_line returns a scatter trace labeled by definition and version."""
    trace = overlay_line(
        name="ema_fast",
        definition="ema(10)",
        version="v1",
        x=["2024-01-15T10:00:00+00:00"],
        y=[2652.0],
    )
    assert trace.name == "ema_fast"
    assert trace.legendgroup == "ema(10) v1"
    assert "ema(10)" in trace.hovertemplate


def test_ohlcv_chart_includes_overlays():
    """Chart includes provided overlays as additional traces."""
    fig = ohlcv_chart(
        symbol="XAUUSD",
        timeframe="M5",
        ohlcv=[
            {"t": "2024-01-15T10:00:00+00:00", "o": 2650.0, "h": 2655.0, "l": 2648.0, "c": 2653.0, "v": 100},
        ],
        overlays=[overlay_line("ema_fast", "ema(10)", "v1", ["2024-01-15T10:00:00+00:00"], [2652.0])],
    )
    names = [t.name for t in fig.data]
    assert "ema_fast" in names


def test_ohlcv_chart_timeframe_and_symbol_in_title():
    """Chart title includes symbol and timeframe."""
    fig = ohlcv_chart(
        symbol="BTCUSD",
        timeframe="H1",
        ohlcv=[
            {"t": "2024-01-15T10:00:00+00:00", "o": 100.0, "h": 105.0, "l": 99.0, "c": 102.0, "v": 10},
        ],
    )
    title = fig.layout.title.text if fig.layout.title else ""
    assert "BTCUSD" in title
    assert "H1" in title

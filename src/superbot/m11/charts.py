"""M11.2 — Plotly chart generation for the market/data explorer surface.

Deterministic offline charting: OHLCV candlestick with volume subplot,
optional overlays labeled by definition/version, and source/freshness
annotations that never imply live broker data.
"""

from __future__ import annotations

import plotly.graph_objects as go
from plotly.subplots import make_subplots


def overlay_line(
    name: str,
    definition: str,
    version: str,
    x: list[str],
    y: list[float],
) -> go.Scatter:
    """Return a scatter trace for a deterministic overlay.

    Labeled by definition and version so overlays are traceable to their
    source definition (design.md §2 Market/data explorer).
    """
    return go.Scatter(
        x=x,
        y=y,
        mode="lines",
        name=name,
        legendgroup=f"{definition} {version}",
        hovertemplate=(
            f"{name}<br>"
            f"definition: {definition}<br>"
            f"version: {version}<br>"
            "x: %{x}<br>"
            "y: %{y:.4f}<extra></extra>"
        ),
        line={"width": 1},
    )


def ohlcv_chart(
    symbol: str,
    timeframe: str,
    ohlcv: list[dict],
    source: str = "synthetic_fixture",
    overlays: list[go.Scatter] | None = None,
) -> go.Figure:
    """Build an OHLCV candlestick chart with a volume subplot.

    Args:
        symbol: instrument symbol.
        timeframe: bar timeframe (M5, M15, H1, H4).
        ohlcv: list of dicts with t, o, h, l, c, v.
        source: data source label (synthetic_fixture / imported_history /
            broker_feed).
        overlays: optional overlay traces (e.g. indicators).

    Returns a Plotly Figure. Annotations state the source and that data is
    not live broker data.
    """
    times = [row["t"] for row in ohlcv]
    opens = [row["o"] for row in ohlcv]
    highs = [row["h"] for row in ohlcv]
    lows = [row["l"] for row in ohlcv]
    closes = [row["c"] for row in ohlcv]
    volumes = [row["v"] for row in ohlcv]

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.7, 0.3],
        subplot_titles=(f"{symbol} {timeframe} OHLCV", "Volume"),
    )

    fig.add_trace(
        go.Candlestick(
            x=times,
            open=opens,
            high=highs,
            low=lows,
            close=closes,
            name="price",
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Bar(x=times, y=volumes, name="volume", marker_color="rgba(0,128,255,0.3)"),
        row=2,
        col=1,
    )

    for overlay in overlays or []:
        fig.add_trace(overlay, row=1, col=1)

    fig.update_layout(
        title_text=f"{symbol} {timeframe} — {source}",
        showlegend=True,
        height=600,
        xaxis_rangeslider_visible=False,
        annotations=[
            {
                "x": 0.0,
                "y": 1.02,
                "xref": "paper",
                "yref": "paper",
                "text": f"source: {source} — not live broker data",
                "showarrow": False,
                "font": {"size": 10},
            }
        ],
        margin={"l": 60, "r": 20, "t": 60, "b": 60},
    )

    fig.update_yaxes(title_text="price", row=1, col=1)
    fig.update_yaxes(title_text="volume", row=2, col=1)

    return fig

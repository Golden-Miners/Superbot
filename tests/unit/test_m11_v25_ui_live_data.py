"""RED tests for V2.5 — Connect Streamlit UI to live MT5 data.

Covers:
- render_overview shows MT5 connectivity status (healthy/blocked), not NOT_PROBED
- render_data_explorer shows live OHLCV bars from MT5 provider, not synthetic fixtures
- source_label returns broker_feed label, not synthetic_fixture
- All dashboard surfaces labeled broker_feed, never synthetic/fixture

No live trading authorized. Read-only market data only.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from superbot.contracts.ohlcv import QualityStatus
from superbot.m11.mt5_data_provider import DataState
from superbot.m11.ui import (
    render_data_explorer,
    render_overview,
    source_label,
)


class FakeMT5DataProvider:
    """Fake MT5DataProvider for testing without a live terminal."""

    def __init__(self):
        self.connect_called = False
        self.disconnect_called = False

    def connect(self):
        self.connect_called = True
        return True

    def disconnect(self):
        self.disconnect_called = True

    def is_connected(self):
        return True

    def get_tick(self, symbol):
        return type("TickData", (), {
            "symbol": symbol,
            "broker_symbol": "GOLD.i#",
            "bid": 3875.75,
            "ask": 3875.99,
            "last": 3875.87,
            "volume": 1.0,
            "timestamp_utc": datetime.now(tz=UTC),
            "source": "broker_feed",
            "data_state": DataState.LIVE,
        })()

    def get_ohlcv(self, symbol, timeframe, count=100):
        return [
            type("OHLCVBar", (), {
                "instrument_id": symbol,
                "provider_symbol": "GOLD.i#",
                "timeframe": timeframe,
                "bar_open_utc": datetime.now(tz=UTC),
                "open": Decimal("3875.75"),
                "high": Decimal("3875.99"),
                "low": Decimal("3875.50"),
                "close": Decimal("3875.90"),
                "volume": Decimal("1.0"),
                "quality_status": QualityStatus.VALID,
                "source": "broker_feed",
            })()
        ]

    def get_symbol_spec(self, symbol):
        return None


# --- RED tests ---


def test_source_label_returns_broker_feed():
    """source_label should label broker_feed data, not synthetic_fixture."""
    result = source_label("broker_feed")
    assert result == "broker feed — read-only, not live orders"
    assert result != "synthetic fixture — not live broker data"


def test_render_overview_shows_mt5_connected():
    """Overview surface should show MT5 as connected, not NOT_PROBED."""
    provider = FakeMT5DataProvider()
    ui = FakeUI()
    render_overview(ui=ui, mt5_data_provider=provider)
    ui_output = ui.output
    assert "connected" in ui_output.lower() or "healthy" in ui_output.lower()
    # mt5_readonly specifically should not show NOT_PROBED
    assert "mt5_readonly: not_probed" not in ui_output.lower()


def test_render_data_explorer_shows_live_data():
    """Data explorer should show live OHLCV bars from MT5, not synthetic fixtures."""
    provider = FakeMT5DataProvider()
    ui = FakeUI()
    render_data_explorer(ui=ui, mt5_data_provider=provider)
    ui_output = ui.output
    assert "broker feed" in ui_output.lower()
    assert "synthetic" not in ui_output.lower()


# --- Fake UI for testing ---


class FakeUI:
    """Fake Streamlit-like UI object for testing render functions."""

    def __init__(self):
        self.output = ""

    def title(self, text):
        self.output += f"TITLE: {text}\n"

    def subheader(self, text):
        self.output += f"SUBHEADER: {text}\n"

    def write(self, text):
        self.output += f"WRITE: {text}\n"

    def metric(self, label, value):
        self.output += f"METRIC: {label}={value}\n"

    def plotly_chart(self, fig):
        self.output += "CHART: plotly\n"

    def write_text(self, text):
        self.output += f"WRITE: {text}\n"

    def caption(self, text):
        self.output += f"CAPTION: {text}\n"

    def __getattr__(self, name):
        # Catch-all for any streamlit method we didn't define
        def method(*args, **kwargs):
            self.output += f"CALL: {name}({args}, {kwargs})\n"
        return method

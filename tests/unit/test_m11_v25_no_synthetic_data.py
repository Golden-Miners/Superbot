"""RED tests for V2 — Eliminate synthetic production dashboard state across all 8 surfaces.

Covers:
- render_overview: does not show synthetic jobs/strategies as live data
- render_data_explorer: already shows broker_feed, verify no synthetic fallback
- render_research_queue: labeled synthetic_fixture, not live
- render_strategy_workbench: labeled synthetic_fixture, not live
- render_validation_experiments: labeled synthetic_fixture, not live
- render_portfolio_risk: does NOT show hardcoded fake values when no live data
- render_audit_library: labeled synthetic_fixture, not live
- render_settings_profiles: labeled synthetic_fixture, not live

No live trading authorized. Read-only market data only.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from superbot.contracts.ohlcv import QualityStatus
from superbot.m11.mt5_data_provider import DataState, MT5DataProvider
from superbot.m11.ui import (
    render_audit_library,
    render_data_explorer,
    render_overview,
    render_portfolio_risk,
    render_research_queue,
    render_settings_profiles,
    render_strategy_workbench,
    render_validation_experiments,
    source_label,
)


# --- Fake MT5DataProvider for testing without a live terminal ---
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
        from superbot.m11.mt5_data_provider import DataState, TickData

        return TickData(
            symbol=symbol,
            broker_symbol="GOLD.i#",
            bid=3875.75,
            ask=3875.99,
            last=3875.87,
            volume=1.0,
            timestamp_utc=datetime.now(tz=UTC),
            source="broker_feed",
            data_state=DataState.LIVE,
        )

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
        def method(*args, **kwargs):
            self.output += f"CALL: {name}({args}, {kwargs})\n"
        return method


# --- RED tests ---


def test_source_label_returns_broker_feed():
    """source_label should label broker_feed data, not synthetic_fixture."""
    result = source_label("broker_feed")
    assert result == "broker feed — read-only, not live orders"
    assert result != "synthetic fixture — not live broker data"


def test_source_label_returns_synthetic_fixture():
    """source_label should label synthetic_fixture data explicitly."""
    result = source_label("synthetic_fixture")
    assert result == "synthetic fixture — not live broker data"


def test_render_overview_shows_mt5_connected():
    """Overview surface should show MT5 as connected, not NOT_PROBED."""
    provider = FakeMT5DataProvider()
    ui = FakeUI()
    render_overview(ui=ui, mt5_data_provider=provider)
    ui_output = ui.output
    assert "connected" in ui_output.lower() or "healthy" in ui_output.lower()
    assert "mt5_readonly: not_probed" not in ui_output.lower()


def test_render_overview_no_synthetic_jobs():
    """Overview surface should not show synthetic job data as live."""
    provider = FakeMT5DataProvider()
    ui = FakeUI()
    render_overview(ui=ui, mt5_data_provider=provider)
    ui_output = ui.output
    # Should not show synthetic job count as if it were live data
    assert "jobs" not in ui_output.lower() or "synthetic" in ui_output.lower()


def test_render_data_explorer_shows_live_data():
    """Data explorer should show live OHLCV bars from MT5, not synthetic fixtures."""
    provider = FakeMT5DataProvider()
    ui = FakeUI()
    render_data_explorer(ui=ui, mt5_data_provider=provider)
    ui_output = ui.output
    assert "broker feed" in ui_output.lower()
    assert "synthetic" not in ui_output.lower()


def test_render_research_queue_shows_synthetic_label():
    """Research queue should be labeled as synthetic_fixture, not live."""
    ui = FakeUI()
    render_research_queue(ui=ui)
    ui_output = ui.output.lower()
    assert "synthetic fixture" in ui_output or "internal_simulation" in ui_output
    assert "broker feed" not in ui_output or "not live" in ui_output


def test_render_research_queue_no_live_market_data():
    """Research queue should not present job data as live broker market data."""
    ui = FakeUI()
    render_research_queue(ui=ui)
    ui_output = ui.output.lower()
    assert ui_output.count("live broker") == ui_output.count("not live broker")


def test_render_strategy_workbench_shows_synthetic_label():
    """Strategy workbench should be labeled as synthetic_fixture, not live."""
    ui = FakeUI()
    render_strategy_workbench(ui=ui)
    ui_output = ui.output.lower()
    assert "synthetic fixture" in ui_output or "internal_simulation" in ui_output


def test_render_strategy_workbench_no_live_market_data():
    """Strategy workbench should not present strategy data as live broker data."""
    ui = FakeUI()
    render_strategy_workbench(ui=ui)
    ui_output = ui.output.lower()
    assert ui_output.count("live broker") == ui_output.count("not live broker")


def test_render_validation_experiments_shows_synthetic_label():
    """Validation experiments should be labeled as synthetic_fixture, not live."""
    ui = FakeUI()
    render_validation_experiments(ui=ui)
    ui_output = ui.output.lower()
    assert "synthetic fixture" in ui_output or "internal_simulation" in ui_output


def test_render_validation_experiments_no_live_market_data():
    """Validation experiments should not present experiment data as live broker data."""
    ui = FakeUI()
    render_validation_experiments(ui=ui)
    ui_output = ui.output.lower()
    assert ui_output.count("live broker") == ui_output.count("not live broker")


def test_render_portfolio_risk_no_hardcoded_values():
    """Portfolio/risk should not show hardcoded fake values when no live data."""
    ui = FakeUI()
    render_portfolio_risk(ui=ui)
    ui_output = ui.output.lower()
    # Should not show hardcoded exposure/P&L/drawdown as if live
    assert "265.00" not in ui_output
    assert "120.00" not in ui_output
    assert "0.8%" not in ui_output
    assert "1.2%" not in ui_output


def test_render_portfolio_risk_shows_unavailable_when_no_data():
    """Portfolio/risk should show UNAVAILABLE/STALE/BLOCKED when no live data."""
    ui = FakeUI()
    render_portfolio_risk(ui=ui)
    ui_output = ui.output.lower()
    assert "unavailable" in ui_output or "stale" in ui_output or "blocked" in ui_output


def test_render_audit_library_shows_synthetic_label():
    """Audit library should be labeled as synthetic_fixture, not live."""
    ui = FakeUI()
    render_audit_library(ui=ui)
    ui_output = ui.output.lower()
    assert "synthetic fixture" in ui_output or "internal_simulation" in ui_output


def test_render_audit_library_no_live_market_data():
    """Audit library should not present audit data as live broker data."""
    ui = FakeUI()
    render_audit_library(ui=ui)
    ui_output = ui.output.lower()
    assert ui_output.count("live broker") == ui_output.count("not live broker")


def test_render_settings_profiles_shows_synthetic_label():
    """Settings/profiles should be labeled as synthetic_fixture, not live."""
    ui = FakeUI()
    render_settings_profiles(ui=ui)
    ui_output = ui.output.lower()
    assert "synthetic fixture" in ui_output or "internal_simulation" in ui_output


def test_render_settings_profiles_no_live_market_data():
    """Settings/profiles should not present profile data as live broker data."""
    ui = FakeUI()
    render_settings_profiles(ui=ui)
    ui_output = ui.output.lower()
    assert ui_output.count("live broker") == ui_output.count("not live broker")


# --- TDD flow tests ---
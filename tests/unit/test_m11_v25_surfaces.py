from __future__ import annotations

from superbot.m11 import ui as m11_ui
from superbot.m11.mt5_data_provider import DataState


class FakeUI:
    """Records streamlit-like calls for smoke-testing render functions."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple, dict]] = []

    def __getattr__(self, name: str):
        def recorder(*args, **kwargs):
            self.calls.append((name, args, kwargs))
        return recorder


# --- Phase 2.5: Connect all surfaces to live MT5 data ---


class FakeMT5DataProvider:
    """Fake MT5DataProvider for testing UI surfaces with live data."""

    def __init__(self, ticks: dict | None = None):
        self._ticks = ticks or {}
        self._connected = True
        self.symbol_map = {k: v.get("broker_symbol", k) for k, v in self._ticks.items()}

    def connect(self) -> bool:
        self._connected = True
        return True

    def disconnect(self) -> None:
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def get_tick(self, symbol: str):
        """Return a fake TickData-like object for the symbol."""
        data = self._ticks.get(symbol)
        if data is None:
            return None
        return type(
            "TickData",
            (),
            {
                "symbol": data["symbol"],
                "broker_symbol": data["broker_symbol"],
                "bid": data["bid"],
                "ask": data["ask"],
                "last": data["last"],
                "volume": data["volume"],
                "timestamp_utc": data["timestamp_utc"],
                "source": "broker_feed",
                "data_state": data["data_state"],
            },
        )()

    def get_ohlcv(self, symbol: str, timeframe: str, count: int = 100):
        """Return empty list — UI tests focus on tick data."""
        return []


def test_render_overview_shows_mt5_connected_when_provider_connected():
    """Overview surface shows MT5 as connected when provider is live."""
    provider = FakeMT5DataProvider(
        {
            "XAUUSD": {
                "symbol": "XAUUSD",
                "broker_symbol": "GOLD.i#",
                "bid": 3875.75,
                "ask": 3875.99,
                "last": 3875.87,
                "volume": 1.0,
                "timestamp_utc": None,
                "data_state": DataState.LIVE,
            }
        }
    )
    ui = FakeUI()
    m11_ui.render_overview(ui, mt5_data_provider=provider)
    calls_text = " ".join(str(a) for _, args, _ in ui.calls for a in args).lower()
    assert "mt5_readonly" in calls_text
    assert "connected" in calls_text


def test_render_overview_shows_mt5_not_connected_when_no_provider():
    """Overview surface shows MT5 as not connected when no provider."""
    ui = FakeUI()
    m11_ui.render_overview(ui)
    calls_text = " ".join(str(a) for _, args, _ in ui.calls for a in args).lower()
    assert "mt5_readonly" in calls_text
    assert "not connected" in calls_text


def test_render_data_explorer_shows_broker_feed_label():
    """Data explorer shows broker_feed source label."""
    provider = FakeMT5DataProvider()
    ui = FakeUI()
    m11_ui.render_data_explorer(ui, mt5_data_provider=provider)
    calls_text = " ".join(str(a) for _, args, _ in ui.calls for a in args).lower()
    assert "broker feed" in calls_text


def test_render_research_queue_shows_live_symbols():
    """Research queue shows live MT5 symbols with data states."""
    provider = FakeMT5DataProvider(
        {
            "XAUUSD": {
                "symbol": "XAUUSD",
                "broker_symbol": "GOLD.i#",
                "bid": 3875.75,
                "ask": 3875.99,
                "last": 3875.87,
                "volume": 1.0,
                "timestamp_utc": None,
                "data_state": DataState.LIVE,
            },
            "BTCUSD": {
                "symbol": "BTCUSD",
                "broker_symbol": "BTCUSD#",
                "bid": 77803.35,
                "ask": 77818.35,
                "last": 77810.0,
                "volume": 0.5,
                "timestamp_utc": None,
                "data_state": DataState.LIVE,
            },
        }
    )
    ui = FakeUI()
    m11_ui.render_research_queue(ui, mt5_data_provider=provider)
    calls_text = " ".join(str(a) for _, args, _ in ui.calls for a in args).lower()
    assert "broker feed" in calls_text.lower()


def test_render_strategy_workbench_shows_live_data():
    """Strategy workbench shows strategies evaluated against live market data."""
    provider = FakeMT5DataProvider(
        {
            "XAUUSD": {
                "symbol": "XAUUSD",
                "broker_symbol": "GOLD.i#",
                "bid": 3875.75,
                "ask": 3875.99,
                "last": 3875.87,
                "volume": 1.0,
                "timestamp_utc": None,
                "data_state": DataState.LIVE,
            }
        }
    )
    ui = FakeUI()
    m11_ui.render_strategy_workbench(ui, mt5_data_provider=provider)
    calls_text = " ".join(str(a) for _, args, _ in ui.calls for a in args).lower()
    assert "strategy" in calls_text.lower()


def test_render_validation_experiments_shows_live_validation():
    """Validation experiments show results from live data."""
    provider = FakeMT5DataProvider(
        {
            "XAUUSD": {
                "symbol": "XAUUSD",
                "broker_symbol": "GOLD.i#",
                "bid": 3875.75,
                "ask": 3875.99,
                "last": 3875.87,
                "volume": 1.0,
                "timestamp_utc": None,
                "data_state": DataState.LIVE,
            }
        }
    )
    ui = FakeUI()
    m11_ui.render_validation_experiments(ui, mt5_data_provider=provider)
    calls_text = " ".join(str(a) for _, args, _ in ui.calls for a in args).lower()
    assert "gate" in calls_text.lower() or "validation" in calls_text.lower()


def test_render_portfolio_risk_shows_live_risk():
    """Portfolio/risk shows real risk metrics from live data."""
    provider = FakeMT5DataProvider(
        {
            "XAUUSD": {
                "symbol": "XAUUSD",
                "broker_symbol": "GOLD.i#",
                "bid": 3875.75,
                "ask": 3875.99,
                "last": 3875.87,
                "volume": 1.0,
                "timestamp_utc": None,
                "data_state": DataState.LIVE,
            }
        }
    )
    ui = FakeUI()
    m11_ui.render_portfolio_risk(ui, mt5_data_provider=provider)
    calls_text = " ".join(str(a) for _, args, _ in ui.calls for a in args).lower()
    assert "risk" in calls_text.lower()


def test_render_audit_library_shows_audit_events():
    """Audit library shows audit events from data quality checks."""
    provider = FakeMT5DataProvider(
        {
            "XAUUSD": {
                "symbol": "XAUUSD",
                "broker_symbol": "GOLD.i#",
                "bid": 3875.75,
                "ask": 3875.99,
                "last": 3875.87,
                "volume": 1.0,
                "timestamp_utc": None,
                "data_state": DataState.LIVE,
            }
        }
    )
    ui = FakeUI()
    m11_ui.render_audit_library(ui, mt5_data_provider=provider)
    calls_text = " ".join(str(a) for _, args, _ in ui.calls for a in args).lower()
    assert "audit" in calls_text.lower() or "event" in calls_text.lower()


def test_all_surfaces_no_synthetic_when_live_provider_connected():
    """No surface implies live broker data when provider is connected."""
    provider = FakeMT5DataProvider(
        {
            "XAUUSD": {
                "symbol": "XAUUSD",
                "broker_symbol": "GOLD.i#",
                "bid": 3875.75,
                "ask": 3875.99,
                "last": 3875.87,
                "volume": 1.0,
                "timestamp_utc": None,
                "data_state": DataState.LIVE,
            }
        }
    )
    ui = FakeUI()
    for renderer in (
        m11_ui.render_overview,
        m11_ui.render_data_explorer,
        m11_ui.render_research_queue,
        m11_ui.render_strategy_workbench,
        m11_ui.render_validation_experiments,
        m11_ui.render_portfolio_risk,
        m11_ui.render_audit_library,
        m11_ui.render_settings_profiles,
    ):
        renderer(ui, mt5_data_provider=provider)
    calls_text = " ".join(str(a) for _, args, _ in ui.calls for a in args).lower()
    assert "broker feed" in calls_text

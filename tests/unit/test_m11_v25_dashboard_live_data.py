"""RED tests for V2.5 — Connect dashboard to live MT5 data.

Covers:
- Data explorer endpoint returns live OHLCV bars from MT5 (not synthetic fixtures)
- Health endpoint reports MT5 connectivity status (not NOT_PROBED)
- UI surfaces show broker_feed source label (not synthetic_fixture)
- All data labeled broker_feed — never synthetic/fixture
- No live order controls in any surface

No live trading authorized. Read-only market data only.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from superbot.m11.api import DataSource, create_app
from superbot.m11.auth import Role, SessionStore


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
        from decimal import Decimal

        from superbot.contracts.ohlcv import OHLCVBar, QualityStatus, Timeframe

        # Use M5-aligned timestamp (5-minute boundary from epoch)
        epoch = datetime(1970, 1, 1, tzinfo=UTC)
        bar_open = epoch.replace(hour=0, minute=0, second=0, microsecond=0)
        bar_open = bar_open.replace(minute=bar_open.minute // 5 * 5)

        return [
            OHLCVBar(
                schema_version="1.0",
                instrument_id=symbol,
                provider_id="xm-mt5",
                provider_symbol="GOLD.i#",
                mapping_version="1.0",
                timeframe=Timeframe.M5,
                bar_open_utc=bar_open,
                open=Decimal("3875.75"),
                high=Decimal("3875.99"),
                low=Decimal("3875.50"),
                close=Decimal("3875.90"),
                volume=Decimal("1.0"),
                volume_kind=None,
                bar_close_utc=None,
                source_timestamp="2026-01-15T10:00:00+00:00",
                source_timezone="UTC",
                source_revision=None,
                quality_status=QualityStatus.VALID,
                available_at_utc=bar_open,
                source_record_ref="mt5:GOLD.i#:1793533130",
            )
        ]

    def get_symbol_spec(self, symbol):
        return None


# --- RED tests ---


def test_data_explorer_returns_live_broker_data():
    """GET /data/explorer/{symbol}/{timeframe} returns live broker data,
    not synthetic fixtures."""
    provider = FakeMT5DataProvider()
    store = SessionStore()
    app = create_app(session_store=store, dashboard_service=None)
    app.state.mt5_provider = provider

    _, token = store.create_session(Role.OWNER)

    client = TestClient(app)
    response = client.get(
        "/data/explorer/XAUUSD/M5",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["source"] == DataSource.BROKER_FEED
    assert data["label"] == "broker feed — read-only, not live orders"
    assert data["live"] is True


def test_health_reports_mt5_connectivity():
    """GET /health reports MT5 connectivity status (not NOT_PROBED)."""
    provider = FakeMT5DataProvider()
    store = SessionStore()
    app = create_app(session_store=store, dashboard_service=None)
    app.state.mt5_provider = provider

    client = TestClient(app)
    _, token = store.create_session(Role.OWNER)

    response = client.get(
        "/health",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    # MT5 component should show connectivity status, not NOT_PROBED
    mt5_comp = data["components"]["mt5_readonly"]
    assert mt5_comp["status"] != "not_probed"


def test_ui_shows_broker_feed_label():
    """UI render functions use broker_feed source label, not synthetic_fixture."""
    from superbot.m11.ui import source_label

    assert source_label("broker_feed") == "broker feed — read-only, not live orders"
    assert source_label("synthetic_fixture") == "synthetic fixture — not live broker data"
    assert source_label("broker_feed") != source_label("synthetic_fixture")


def test_no_live_order_controls_in_ui():
    """No live order controls appear in any UI surface."""
    # These render functions should not reference live order placement
    import inspect

    from superbot.m11.ui import (
        render_data_explorer,
        render_overview,
        render_portfolio_risk,
    )

    for renderer in [render_overview, render_data_explorer, render_portfolio_risk]:
        source = inspect.getsource(renderer)
        assert "order_send" not in source
        assert "place_order" not in source
        assert "submit_order" not in source
        assert "live_order" not in source.lower()


def test_data_explorer_quality_state_from_provider():
    """Data explorer reflects quality state from MT5 provider (VALID/STALE/UNAVAILABLE)."""
    provider = FakeMT5DataProvider()
    store = SessionStore()
    app = create_app(session_store=store, dashboard_service=None)
    app.state.mt5_provider = provider

    client = TestClient(app)
    _, token = store.create_session(Role.OWNER)

    response = client.get(
        "/data/explorer/XAUUSD/M5",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["data_quality"]["stale_feed"] is False
    assert data["data_quality"]["source_disagreement"] is False
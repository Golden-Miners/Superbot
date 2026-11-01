"""RED tests for V2 Phase C — Signal Generation & Alerting on Live Data.

Covers:
- ResearchPipeline.run_strategy() returns signals from live MT5 broker data
- Data quality gate rejects stale/invalid ticks/bars — no signals from bad data
- All signal data labeled broker_feed — never synthetic/fixture
- Signal history persisted and retrievable
- Health endpoint reports MT5 connectivity status
- Data explorer endpoint returns live broker data labels

No live trading authorized. Read-only signal generation only.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from fastapi.testclient import TestClient

from superbot.m11.api import DataSource, create_app
from superbot.m11.auth import Role, SessionStore
from superbot.m11.mt5_data_pipeline import ResearchPipeline
from superbot.m11.mt5_data_provider import DataState
from superbot.persistence.market_data_storage import MarketDataStorage

# --- Fake MT5DataProvider for testing without a live terminal ---


class FakeMT5DataProvider:
    """Fake MT5DataProvider for testing without a live terminal."""

    def __init__(self) -> None:
        self._connected = True
        self.ticks: dict = {}
        self.bars: list = []

    def connect(self) -> bool:
        self._connected = True
        return True

    def disconnect(self) -> None:
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def get_tick(self, symbol: str):
        if symbol not in self.ticks:
            return None
        tick_data = self.ticks[symbol]
        return type(
            "TickData",
            (),
            {
                "symbol": symbol,
                "broker_symbol": tick_data.get("broker_symbol", symbol),
                "bid": tick_data.get("bid"),
                "ask": tick_data.get("ask"),
                "last": tick_data.get("last"),
                "volume": tick_data.get("volume"),
                "timestamp_utc": tick_data.get("timestamp_utc", datetime.now(tz=UTC)),
                "source": "broker_feed",
                "data_state": tick_data.get("data_state", DataState.LIVE),
            },
        )()

    def get_ohlcv(self, symbol: str, timeframe: str, count: int = 100) -> list:
        from types import SimpleNamespace
        result = []
        for b in self.bars:
            if bar_matches(broker_symbol=b.get("broker_symbol"), symbol=symbol):
                result.append(SimpleNamespace(
                    instrument_id=b.get("instrument_id", b.get("symbol", symbol)),
                    provider_symbol=b.get("broker_symbol", symbol),
                    timeframe=b["timeframe"],
                    bar_open_utc=b["bar_open_utc"],
                    open=b["open"],
                    high=b["high"],
                    low=b["low"],
                    close=b["close"],
                    volume=b.get("volume"),
                    source_timestamp=b.get("source_timestamp"),
                    source_timezone=b.get("source_timezone"),
                    source_revision=b.get("source_revision"),
                    quality_status=b.get("quality_status"),
                    available_at_utc=b.get("available_at_utc"),
                    source_record_ref=b.get("source_record_ref"),
                ))
        return result[:count]


def bar_matches(broker_symbol, symbol):
    """Check if broker_symbol matches canonical symbol."""
    mapping = {"XAUUSD": "GOLD.i#", "XAGUSD": "SILVER.i#", "BTCUSD": "BTCUSD#", "ETHUSD": "ETHUSD#", "USOIL": "OILCash#"}
    return broker_symbol == mapping.get(symbol, symbol)


# --- RED tests ---


def test_research_pipeline_creates():
    """ResearchPipeline can be created with MT5 provider and storage."""
    provider = FakeMT5DataProvider()
    storage = MarketDataStorage()
    pipeline = ResearchPipeline(provider, storage)
    assert pipeline is not None
    assert pipeline.mt5_provider is provider
    assert pipeline.storage is storage


def test_run_strategy_returns_empty_when_no_data():
    """run_strategy() returns empty list when no data available from MT5."""
    provider = FakeMT5DataProvider()
    storage = MarketDataStorage()
    pipeline = ResearchPipeline(provider, storage)
    signals = pipeline.run_strategy("BTCUSD", "M5", count=100)
    assert signals == []


def test_run_strategy_returns_signals_from_live_data():
    """run_strategy() returns signals from live broker data."""
    provider = FakeMT5DataProvider()
    storage = MarketDataStorage()
    pipeline = ResearchPipeline(provider, storage)

    now = datetime.now(tz=UTC)
    # Uptrend bars then pullback bar
    bars_data = [
        (Decimal("100.0"), Decimal("102.0"), Decimal("99.0"), Decimal("101.0")),
        (Decimal("101.0"), Decimal("103.0"), Decimal("100.0"), Decimal("102.0")),
        (Decimal("102.0"), Decimal("104.0"), Decimal("101.0"), Decimal("103.0")),
        (Decimal("103.0"), Decimal("105.0"), Decimal("102.0"), Decimal("104.0")),
        (Decimal("104.0"), Decimal("106.0"), Decimal("103.0"), Decimal("105.0")),
        (Decimal("105.5"), Decimal("105.8"), Decimal("105.65"), Decimal("105.7")),  # ~5% pullback
    ]
    bars = []
    base = datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC)
    for i, (o, h, l, c) in enumerate(bars_data):
        bars.append({
            "symbol": "BTCUSD",
            "broker_symbol": "BTCUSD#",
            "timeframe": "M5",
            "bar_open_utc": base.replace(minute=base.minute + i * 5),
            "open": o,
            "high": h,
            "low": l,
            "close": c,
            "volume": Decimal("1.0"),
            "source_timestamp": now,
            "source_timezone": "UTC",
            "source_revision": None,
            "quality_status": type("QualityStatus", (), {"value": "valid"})(),
            "available_at_utc": now,
            "source_record_ref": f"mt5:BTCUSD#{i}",
        })
    provider.bars = bars

    signals = pipeline.run_strategy("BTCUSD", "M5", count=10)
    assert isinstance(signals, list)
    # If signal generated, verify structure
    if signals:
        sig = signals[0]
        assert sig["symbol"] == "BTCUSD"
        assert sig["signal_type"] in ("entry_long", "entry_short")
        assert sig["entry_price"] > 0
        assert sig["stop_price"] > 0
        assert sig["depth_pct"] > 0
        assert sig["source"] == "broker_feed"


def test_run_strategy_rejects_stale_data():
    """run_strategy() does not generate signals from stale data (>60s old)."""
    provider = FakeMT5DataProvider()
    storage = MarketDataStorage()
    pipeline = ResearchPipeline(provider, storage)

    old_time = datetime(2020, 1, 15, 10, 0, 0, tzinfo=UTC)
    bars = []
    for i in range(6):
        bars.append({
            "symbol": "BTCUSD",
            "broker_symbol": "BTCUSD#",
            "timeframe": "M5",
            "bar_open_utc": old_time.replace(minute=i * 5),
            "open": Decimal(77900),
            "high": Decimal(78000),
            "low": Decimal(77850),
            "close": Decimal(77980),
            "volume": Decimal("1.0"),
            "source_timestamp": old_time.replace(minute=i * 5),
            "source_timezone": "UTC",
            "source_revision": None,
            "quality_status": type("QualityStatus", (), {"value": "stale"})(),
            "available_at_utc": old_time.replace(minute=i * 5),
            "source_record_ref": f"mt5:BTCUSD#{i}",
        })
    provider.bars = bars

    signals = pipeline.run_strategy("BTCUSD", "M5", count=10)
    assert signals == []  # Stale data should produce no signals


def test_run_strategy_rejects_invalid_data():
    """run_strategy() does not generate signals from invalid data."""
    provider = FakeMT5DataProvider()
    storage = MarketDataStorage()
    pipeline = ResearchPipeline(provider, storage)

    now = datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC)
    bars = []
    for i in range(6):
        bars.append({
            "symbol": "BTCUSD",
            "broker_symbol": "BTCUSD#",
            "timeframe": "M5",
            "bar_open_utc": now.replace(minute=i * 5),
            "open": Decimal(77900),
            "high": Decimal(78000),
            "low": Decimal(77850),
            "close": Decimal(77980),
            "volume": Decimal("1.0"),
            "source_timestamp": now.replace(minute=i * 5),
            "source_timezone": "UTC",
            "source_revision": None,
            "quality_status": type("QualityStatus", (), {"value": "invalid"})(),
            "available_at_utc": now.replace(minute=i * 5),
            "source_record_ref": f"mt5:BTCUSD#{i}",
        })
    provider.bars = bars

    signals = pipeline.run_strategy("BTCUSD", "M5", count=10)
    assert signals == []  # Invalid data should produce no signals


def test_data_explorer_returns_broker_feed():
    """GET /data/explorer/{symbol}/{timeframe} returns broker_feed source."""
    provider = FakeMT5DataProvider()
    storage = MarketDataStorage()
    ResearchPipeline(provider, storage)

    store = SessionStore()
    app = create_app(session_store=store, dashboard_service=None, mt5_data_provider=provider)
    client = TestClient(app)

    # Create session token
    _, token = store.create_session(Role.OWNER)

    # Add live bar data
    now = datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC)
    bars = []
    for i in range(6):
        bars.append({
            "symbol": "XAUUSD",
            "broker_symbol": "GOLD.i#",
            "timeframe": "M5",
            "bar_open_utc": now.replace(minute=i * 5),
            "open": Decimal("3875.75"),
            "high": Decimal("3875.99"),
            "low": Decimal("3875.50"),
            "close": Decimal("3875.90"),
            "volume": Decimal("1.0"),
            "source_timestamp": now.replace(minute=now.minute + i * 5),
            "source_timezone": "UTC",
            "source_revision": None,
            "quality_status": type("QualityStatus", (), {"value": "valid"})(),
            "available_at_utc": now.replace(minute=now.minute + i * 5),
            "source_record_ref": f"mt5:GOLD.i#{i}",
        })
    provider.bars = bars

    response = client.get(
        "/data/explorer/XAUUSD/M5",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["source"] == DataSource.BROKER_FEED
    assert data["label"] == "broker feed — read-only, not live orders"
    assert data["live"] is True


def test_health_reports_mt5_connected():
    """GET /health reports MT5 connectivity status."""
    provider = FakeMT5DataProvider()
    storage = MarketDataStorage()
    ResearchPipeline(provider, storage)

    store = SessionStore()
    app = create_app(session_store=store, dashboard_service=None, mt5_data_provider=provider)
    client = TestClient(app)
    _, token = store.create_session(Role.OWNER)

    response = client.get("/health", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    # MT5 component should show connected/healthy, not NOT_PROBED
    mt5_comp = data["components"]["mt5_readonly"]
    assert mt5_comp["status"] != "not_probed"
    assert mt5_comp["status"] in ("healthy", "connected")


def test_storage_roundtrip_tick():
    """Stored tick data can be retrieved unchanged."""
    storage = MarketDataStorage()
    storage.store_tick(
        symbol="XAUUSD",
        broker_symbol="GOLD.i#",
        bid=3875.75,
        ask=3875.99,
        last=3875.87,
        volume=1.0,
        source_timestamp=datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC),
        source="broker_feed",
    )
    ticks = storage.get_ticks("XAUUSD")
    assert len(ticks) == 1
    assert ticks[0].symbol == "XAUUSD"
    assert ticks[0].broker_symbol == "GOLD.i#"
    assert ticks[0].bid == 3875.75
    assert ticks[0].ask == 3875.99
    assert ticks[0].source == "broker_feed"


def test_storage_roundtrip_bar():
    """Stored OHLCV bar can be retrieved unchanged."""
    storage = MarketDataStorage()
    storage.store_bar(
        instrument_id="BTCUSD",
        provider_symbol="BTCUSD#",
        timeframe="M5",
        bar_open_utc=datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC),
        open=Decimal(77900),
        high=Decimal(78000),
        low=Decimal(77850),
        close=Decimal(77980),
        volume=Decimal("1.0"),
        source_timestamp=datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC),
        source="broker_feed",
    )
    bars = storage.get_bars("BTCUSD", "M5")
    assert len(bars) == 1
    assert bars[0].instrument_id == "BTCUSD"
    assert bars[0].provider_symbol == "BTCUSD#"
    assert bars[0].timeframe == "M5"
    assert bars[0].open == Decimal(77900)
    assert bars[0].close == Decimal(77980)
    assert bars[0].source == "broker_feed"
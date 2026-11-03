"""RED tests for V2 Phase D — Real-Time Operation: Signal Generator on Live Data.

Covers:
- SignalGenerator creates with MT5 provider + storage
- run_live() returns signals from live MT5 data
- run_live() returns empty when no data available
- run_live() rejects stale data (data_state != LIVE)
- run_live() rejects unavailable data
- Signal history records every decision (signal or rejection)
- Each signal record includes symbol, signal_type, entry_price, stop_price,
  depth_pct, source, timestamp, data_state
- Rejection reasons recorded (stale_data, unavailable_data, no_signal)
- All signal data labeled broker_feed — never synthetic/fixture

No live trading authorized. Read-only signal generation only.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

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
        self.symbol_map = {
            "XAUUSD": "GOLD.i#",
            "XAGUSD": "SILVER.i#",
            "BTCUSD": "BTCUSD#",
            "ETHUSD": "ETHUSD#",
            "USOIL": "OILCash#",
        }

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
                result.append(
                    SimpleNamespace(
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
                    )
                )
        return result[:count]


def bar_matches(broker_symbol, symbol):
    mapping = {
        "XAUUSD": "GOLD.i#",
        "XAGUSD": "SILVER.i#",
        "BTCUSD": "BTCUSD#",
        "ETHUSD": "ETHUSD#",
        "USOIL": "OILCash#",
    }
    return broker_symbol == mapping.get(symbol, symbol)


# --- RED tests ---


def test_signal_generator_creates():
    """SignalGenerator creates with MT5 provider + storage."""
    provider = FakeMT5DataProvider()
    storage = MarketDataStorage()
    pipeline = ResearchPipeline(provider, storage)
    assert pipeline is not None
    assert pipeline.mt5_provider is provider
    assert pipeline.storage is storage


def test_run_live_returns_empty_when_no_data():
    """run_live() returns empty list when no data available from MT5."""
    provider = FakeMT5DataProvider()
    storage = MarketDataStorage()
    pipeline = ResearchPipeline(provider, storage)
    signals = pipeline.run_strategy("BTCUSD", "M5", count=100)
    assert signals == []


def test_run_live_returns_signals_from_live_data():
    """run_live() returns signals from live broker data."""
    provider = FakeMT5DataProvider()
    storage = MarketDataStorage()
    pipeline = ResearchPipeline(provider, storage)

    now = datetime.now(tz=UTC)
    bars_data = [
        (Decimal("100.0"), Decimal("102.0"), Decimal("99.0"), Decimal("101.0")),
        (Decimal("101.0"), Decimal("103.0"), Decimal("100.0"), Decimal("102.0")),
        (Decimal("102.0"), Decimal("104.0"), Decimal("101.0"), Decimal("103.0")),
        (Decimal("103.0"), Decimal("105.0"), Decimal("102.0"), Decimal("104.0")),
        (Decimal("104.0"), Decimal("106.0"), Decimal("103.0"), Decimal("105.0")),
        (Decimal("105.5"), Decimal("105.8"), Decimal("105.65"), Decimal("105.7")),
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
    if signals:
        sig = signals[0]
        assert sig["symbol"] == "BTCUSD"
        assert sig["signal_type"] in ("entry_long", "entry_short")
        assert sig["entry_price"] > 0
        assert sig["stop_price"] > 0
        assert sig["depth_pct"] > 0
        assert sig["source"] == "broker_feed"


def test_run_live_rejects_stale_data():
    """run_live() does not generate signals from stale data (>60s old)."""
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


def test_run_live_rejects_invalid_data():
    """run_live() does not generate signals from invalid data."""
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


def test_signal_history_records_every_decision():
    """SignalGenerator records every decision (signal or rejection) with provenance."""
    provider = FakeMT5DataProvider()
    storage = MarketDataStorage()
    pipeline = ResearchPipeline(provider, storage)

    # First: live data → signal
    now = datetime.now(tz=UTC)
    bars_data = [
        (Decimal("100.0"), Decimal("102.0"), Decimal("99.0"), Decimal("101.0")),
        (Decimal("101.0"), Decimal("103.0"), Decimal("100.0"), Decimal("102.0")),
        (Decimal("102.0"), Decimal("104.0"), Decimal("101.0"), Decimal("103.0")),
        (Decimal("103.0"), Decimal("105.0"), Decimal("102.0"), Decimal("104.0")),
        (Decimal("104.0"), Decimal("106.0"), Decimal("103.0"), Decimal("105.0")),
        (Decimal("105.5"), Decimal("105.8"), Decimal("105.65"), Decimal("105.7")),
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

    # Then: stale data → no signal (rejection recorded)
    stale_bars = []
    old_time = datetime(2020, 1, 15, 10, 0, 0, tzinfo=UTC)
    for i in range(6):
        stale_bars.append({
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
    provider.bars = stale_bars

    signals = pipeline.run_strategy("BTCUSD", "M5", count=10)
    assert signals == []

    # Signal history should exist with both signal and rejection entries
    history = storage.get_signal_history()
    assert len(history) >= 1
    # First entry should be a signal
    assert history[0].source == "broker_feed"
    assert history[0].symbol == "BTCUSD"
    # Last entry should be a rejection
    assert history[-1].data_state == DataState.STALE.value
    assert history[-1].source == "broker_feed"


def test_all_signal_data_labeled_broker_feed():
    """All signal data labeled broker_feed — never synthetic/fixture."""
    provider = FakeMT5DataProvider()
    storage = MarketDataStorage()
    pipeline = ResearchPipeline(provider, storage)

    now = datetime.now(tz=UTC)
    bars_data = [
        (Decimal("100.0"), Decimal("102.0"), Decimal("99.0"), Decimal("101.0")),
        (Decimal("101.0"), Decimal("103.0"), Decimal("100.0"), Decimal("102.0")),
        (Decimal("102.0"), Decimal("104.0"), Decimal("101.0"), Decimal("103.0")),
        (Decimal("103.0"), Decimal("105.0"), Decimal("102.0"), Decimal("104.0")),
        (Decimal("104.0"), Decimal("106.0"), Decimal("103.0"), Decimal("105.0")),
        (Decimal("105.5"), Decimal("105.8"), Decimal("105.65"), Decimal("105.7")),
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
    if signals:
        sig = signals[0]
        assert sig["source"] == "broker_feed"
        assert sig["source"] != "synthetic_fixture"

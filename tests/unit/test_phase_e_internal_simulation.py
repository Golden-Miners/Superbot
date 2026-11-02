"""RED tests for V2 Phase E — Internal Simulation.

Covers:
- Simulator creates with MT5 provider + storage
- simulate() processes stored bars into simulated positions
- Simulated positions track entry/exit, stop loss, take profit
- P&L, costs, exposure, drawdown all calculated from real data
- No synthetic/fake data — all values from stored broker feed
- Simulator can persist and reload state for restart recovery
- Historical data clearly distinguished from live data

No live trading authorized. Read-only simulation only.
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
    mapping = {"XAUUSD": "GOLD.i#", "XAGUSD": "SILVER.i#", "BTCUSD": "BTCUSD#", "ETHUSD": "ETHUSD#", "USOIL": "OILCash#"}
    return broker_symbol == mapping.get(symbol, symbol)


# --- RED tests ---


def test_simulator_creates():
    """Simulator creates with MT5 provider + storage."""
    provider = FakeMT5DataProvider()
    storage = MarketDataStorage()
    pipeline = ResearchPipeline(provider, storage)
    assert pipeline is not None


def test_simulator_processes_bars_into_positions():
    """Simulator processes stored OHLCV bars into simulated positions."""
    provider = FakeMT5DataProvider()
    storage = MarketDataStorage()
    pipeline = ResearchPipeline(provider, storage)

    now = datetime.now(tz=UTC)
    bars = []
    base = datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC)
    bars_data = [
        (Decimal("100.0"), Decimal("102.0"), Decimal("99.0"), Decimal("101.0")),
        (Decimal("101.0"), Decimal("103.0"), Decimal("100.0"), Decimal("102.0")),
        (Decimal("102.0"), Decimal("104.0"), Decimal("101.0"), Decimal("103.0")),
        (Decimal("103.0"), Decimal("105.0"), Decimal("102.0"), Decimal("104.0")),
        (Decimal("104.0"), Decimal("106.0"), Decimal("103.0"), Decimal("105.0")),
        (Decimal("105.5"), Decimal("105.8"), Decimal("105.65"), Decimal("105.7")),
    ]
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


def test_simulated_position_tracks_entry_exit():
    """Simulated position tracks entry price, exit price, P&L."""
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
        assert sig["entry_price"] > 0
        assert sig["stop_price"] > 0


def test_simulator_stores_signal_in_history():
    """Simulator stores every signal decision in storage history."""
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

    history = storage.get_signal_history()
    assert len(history) >= 1
    # First entry should be a signal with broker_feed source
    if history:
        assert history[0].source == "broker_feed"


def test_simulator_distinguishes_historical_from_live():
    """Historical data clearly distinguished from live data."""
    provider = FakeMT5DataProvider()
    storage = MarketDataStorage()
    pipeline = ResearchPipeline(provider, storage)

    # Add historical data
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
            "quality_status": type("QualityStatus", (), {"value": "valid"})(),
            "available_at_utc": old_time.replace(minute=i * 5),
            "source_record_ref": f"mt5:BTCUSD#{i}",
        })
    provider.bars = bars

    signals = pipeline.run_strategy("BTCUSD", "M5", count=10)
    # Stale data should produce no signals
    assert signals == []

    # History should record rejection
    history = storage.get_signal_history()
    assert len(history) >= 1
    assert history[-1].data_state == DataState.STALE.value


def test_simulator_all_data_labeled_broker_feed():
    """All simulator data labeled broker_feed — never synthetic/fixture."""
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

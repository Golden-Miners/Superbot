"""RED tests for V2.4 — Storage and Replay of live market data.

Covers:
- Market data storage with source/acquisition timestamps
- Distinguishing historical broker data from currently live data
- Persisting real acquired market data locally
- Replaying stored data for research/backtesting
- Storage of tick data and OHLCV bars from MT5 feed
- Retrieval by symbol/timeframe/date range

No live trading authorized. Read-only storage only.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from superbot.persistence.market_data_storage import (
    DataFreshness,
    MarketDataStorage,
)

# --- Test data ---

FIXED_TIMESTAMP = datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC)


class FakeMT5Data:
    """Fake MT5 data provider for testing storage without live terminal."""

    def __init__(self):
        self.ticks = {}
        self.bars = {}

    def add_tick(self, symbol, broker_symbol, bid, ask, last, volume, time_utc):
        self.ticks[time_utc] = {
            "symbol": symbol,
            "broker_symbol": broker_symbol,
            "bid": bid,
            "ask": ask,
            "last": last,
            "volume": volume,
            "time": time_utc.timestamp(),
        }

    def add_bar(self, symbol, broker_symbol, timeframe, open_, high, low, close,
                volume, time_utc):
        self.bars[time_utc] = {
            "instrument_id": symbol,
            "provider_symbol": broker_symbol,
            "timeframe": timeframe,
            "bar_open_utc": time_utc,
            "open": Decimal(str(open_)),
            "high": Decimal(str(high)),
            "low": Decimal(str(low)),
            "close": Decimal(str(close)),
            "volume": Decimal(str(volume)),
            "time": time_utc.timestamp(),
        }


# --- RED tests ---


def test_storage_creates_with_empty_store():
    """MarketDataStorage can be created with an empty store."""
    storage = MarketDataStorage()
    assert storage is not None


def test_store_tick_data():
    """Tick data can be stored with source timestamp and acquisition timestamp."""
    storage = MarketDataStorage()
    storage.store_tick(
        symbol="XAUUSD",
        broker_symbol="GOLD.i#",
        bid=3875.75,
        ask=3875.99,
        last=3875.87,
        volume=1.0,
        source_timestamp=FIXED_TIMESTAMP,
        source="broker_feed",
    )
    ticks = storage.get_ticks("XAUUSD")
    assert len(ticks) == 1
    tick = ticks[0]
    assert tick.symbol == "XAUUSD"
    assert tick.broker_symbol == "GOLD.i#"
    assert tick.bid == 3875.75
    assert tick.ask == 3875.99
    assert tick.source_timestamp == FIXED_TIMESTAMP
    assert tick.source == "broker_feed"
    assert tick.acquisition_timestamp is not None
    assert tick.acquisition_timestamp >= FIXED_TIMESTAMP


def test_store_ohlcv_bar():
    """OHLCV bar can be stored with source timestamp and acquisition timestamp."""
    storage = MarketDataStorage()
    storage.store_bar(
        instrument_id="BTCUSD",
        provider_symbol="BTCUSD#",
        timeframe="M5",
        bar_open_utc=FIXED_TIMESTAMP,
        open=Decimal("77803.35"),
        high=Decimal("77818.35"),
        low=Decimal("77800.00"),
        close=Decimal("77810.00"),
        volume=Decimal("0.5"),
        source_timestamp=FIXED_TIMESTAMP,
        source="broker_feed",
    )
    bars = storage.get_bars("BTCUSD", "M5")
    assert len(bars) == 1
    bar = bars[0]
    assert bar.instrument_id == "BTCUSD"
    assert bar.provider_symbol == "BTCUSD#"
    assert bar.timeframe == "M5"
    assert bar.open == Decimal("77803.35")
    assert bar.source_timestamp == FIXED_TIMESTAMP
    assert bar.source == "broker_feed"
    assert bar.acquisition_timestamp is not None


def test_store_marks_data_as_historical_not_live():
    """Stored data is marked as historical, not live — never confused with live feed."""
    storage = MarketDataStorage()
    storage.store_tick(
        symbol="XAUUSD",
        broker_symbol="GOLD.i#",
        bid=3875.75,
        ask=3875.99,
        last=3875.87,
        volume=1.0,
        source_timestamp=FIXED_TIMESTAMP,
        source="broker_feed",
    )
    ticks = storage.get_ticks("XAUUSD")
    assert len(ticks) == 1
    assert ticks[0].data_freshness == DataFreshness.HISTORICAL
    assert ticks[0].data_freshness != DataFreshness.LIVE


def test_retrieve_ticks_by_symbol_and_range():
    """Ticks can be retrieved by symbol and time range."""
    storage = MarketDataStorage()
    t1 = FIXED_TIMESTAMP
    t2 = FIXED_TIMESTAMP + timedelta(minutes=1)
    t3 = FIXED_TIMESTAMP + timedelta(hours=1)
    storage.store_tick("XAUUSD", "GOLD.i#", 3875.75, 3875.99, 3875.87, 1.0, t1, "broker_feed")
    storage.store_tick("XAUUSD", "GOLD.i#", 3876.00, 3876.10, 3876.05, 2.0, t2, "broker_feed")
    storage.store_tick("BTCUSD", "BTCUSD#", 77803.35, 77818.35, 77810.0, 0.5, t3, "broker_feed")
    # Range covering t1 and t2 only
    ticks = storage.get_ticks("XAUUSD", start=t1, end=t2 + timedelta(seconds=30))
    assert len(ticks) == 2
    assert all(tick.symbol == "XAUUSD" for tick in ticks)


def test_retrieve_bars_by_symbol_timeframe_and_range():
    """Bars can be retrieved by symbol, timeframe, and time range."""
    storage = MarketDataStorage()
    t1 = FIXED_TIMESTAMP
    t2 = FIXED_TIMESTAMP + timedelta(minutes=5)
    storage.store_bar("XAUUSD", "GOLD.i#", "M5", t1,
                      Decimal("3875.75"), Decimal("3875.99"), Decimal("3875.50"),
                      Decimal("3875.90"), Decimal("1.0"), t1, "broker_feed")
    storage.store_bar("XAUUSD", "GOLD.i#", "M5", t2,
                      Decimal("3875.90"), Decimal("3876.00"), Decimal("3875.80"),
                      Decimal("3875.95"), Decimal("1.2"), t2, "broker_feed")
    storage.store_bar("XAUUSD", "GOLD.i#", "M15", t1,
                      Decimal("3875.75"), Decimal("3875.99"), Decimal("3875.50"),
                      Decimal("3875.90"), Decimal("1.0"), t1, "broker_feed")
    # Retrieve M5 bars only, within range
    bars = storage.get_bars("XAUUSD", "M5", start=t1, end=t2)
    assert len(bars) == 2
    assert all(bar.timeframe == "M5" for bar in bars)


def test_replay_stored_data_returns_identical_values():
    """Replayed stored data returns identical values — no fabrication."""
    storage = MarketDataStorage()
    storage.store_tick("XAUUSD", "GOLD.i#", 3875.75, 3875.99, 3875.87, 1.0,
                       FIXED_TIMESTAMP, "broker_feed")
    storage.store_bar("XAUUSD", "GOLD.i#", "M5", FIXED_TIMESTAMP,
                      Decimal("3875.75"), Decimal("3875.99"), Decimal("3875.50"),
                      Decimal("3875.90"), Decimal("1.0"), FIXED_TIMESTAMP, "broker_feed")
    ticks = storage.get_ticks("XAUUSD")
    bars = storage.get_bars("XAUUSD", "M5")
    assert len(ticks) == 1
    assert ticks[0].bid == 3875.75
    assert ticks[0].ask == 3875.99
    assert len(bars) == 1
    assert bars[0].open == Decimal("3875.75")
    assert bars[0].high == Decimal("3875.99")
    assert bars[0].low == Decimal("3875.50")
    assert bars[0].close == Decimal("3875.90")


def test_storage_preserves_source_label():
    """Every stored value carries source label — never implied live broker data."""
    storage = MarketDataStorage()
    storage.store_tick("XAUUSD", "GOLD.i#", 3875.75, 3875.99, 3875.87, 1.0,
                       FIXED_TIMESTAMP, "broker_feed")
    ticks = storage.get_ticks("XAUUSD")
    assert ticks[0].source == "broker_feed"
    assert ticks[0].source != "synthetic_fixture"
    assert ticks[0].source != "live_orders"


def test_get_ticks_empty_for_unknown_symbol():
    """get_ticks returns empty list for symbol with no stored data."""
    storage = MarketDataStorage()
    ticks = storage.get_ticks("UNKNOWN")
    assert ticks == []


def test_get_bars_empty_for_unknown_symbol_timeframe():
    """get_bars returns empty list for unknown symbol/timeframe."""
    storage = MarketDataStorage()
    bars = storage.get_bars("UNKNOWN", "M5")
    assert bars == []


def test_storage_acquisition_timestamp_set_automatically():
    """Acquisition timestamp is set automatically when data is stored."""
    storage = MarketDataStorage()
    before = datetime.now(tz=UTC)
    storage.store_tick("XAUUSD", "GOLD.i#", 3875.75, 3875.99, 3875.87, 1.0,
                       FIXED_TIMESTAMP, "broker_feed")
    after = datetime.now(tz=UTC)
    ticks = storage.get_ticks("XAUUSD")
    assert ticks[0].acquisition_timestamp is not None
    assert before <= ticks[0].acquisition_timestamp <= after


def test_storage_persists_ticks_across_restart(tmp_path):
    """Stored ticks survive a storage restart — read from same file."""
    storage_path = tmp_path / "test_storage.json"
    storage1 = MarketDataStorage(storage_path=storage_path)
    storage1.store_tick("XAUUSD", "GOLD.i#", 3875.75, 3875.99, 3875.87, 1.0,
                        FIXED_TIMESTAMP, "broker_feed")
    storage1.store_tick("BTCUSD", "BTCUSD#", 77803.35, 77818.35, 77810.0, 0.5,
                        FIXED_TIMESTAMP, "broker_feed")

    storage2 = MarketDataStorage(storage_path=storage_path)
    ticks = storage2.get_ticks("XAUUSD")
    assert len(ticks) == 1
    assert ticks[0].symbol == "XAUUSD"
    assert ticks[0].bid == 3875.75
    assert ticks[0].ask == 3875.99

    btcs = storage2.get_ticks("BTCUSD")
    assert len(btcs) == 1
    assert btcs[0].symbol == "BTCUSD"
    assert btcs[0].bid == 77803.35


def test_storage_persists_bars_across_restart(tmp_path):
    """Stored bars survive a storage restart — read from same file."""
    storage_path = tmp_path / "test_storage_bars.json"
    storage1 = MarketDataStorage(storage_path=storage_path)
    storage1.store_bar("XAUUSD", "GOLD.i#", "M5", FIXED_TIMESTAMP,
                       Decimal("3875.75"), Decimal("3875.99"), Decimal("3875.50"),
                       Decimal("3875.90"), Decimal("1.0"), FIXED_TIMESTAMP, "broker_feed")
    storage1.store_bar("ETHUSD", "ETHUSD#", "H1", FIXED_TIMESTAMP,
                       Decimal("2270.11"), Decimal("2272.01"), Decimal("2269.00"),
                       Decimal("2271.00"), Decimal("2.5"), FIXED_TIMESTAMP, "broker_feed")

    storage2 = MarketDataStorage(storage_path=storage_path)
    bars = storage2.get_bars("XAUUSD", "M5")
    assert len(bars) == 1
    assert bars[0].instrument_id == "XAUUSD"
    assert bars[0].open == Decimal("3875.75")

    eth_bars = storage2.get_bars("ETHUSD", "H1")
    assert len(eth_bars) == 1
    assert eth_bars[0].instrument_id == "ETHUSD"


def test_storage_persists_signals_across_restart(tmp_path):
    """Stored signals survive a storage restart — read from same file."""
    storage_path = tmp_path / "test_storage_signals.json"
    storage1 = MarketDataStorage(storage_path=storage_path)
    storage1.store_signal(
        symbol="XAUUSD", broker_symbol="GOLD.i#",
        signal_type="entry_long", entry_price=Decimal("3875.75"),
        stop_price=Decimal("3870.00"), depth_pct=Decimal("2.0"),
        data_state="live", source="broker_feed",
        timestamp_utc=FIXED_TIMESTAMP, rejection_reason=None,
    )
    storage1.store_signal(
        symbol="BTCUSD", broker_symbol="BTCUSD#",
        signal_type=None, entry_price=None, stop_price=None,
        depth_pct=None,
        data_state="stale", source="broker_feed",
        timestamp_utc=FIXED_TIMESTAMP, rejection_reason="data_quality_rejected",
    )

    storage2 = MarketDataStorage(storage_path=storage_path)
    signals = storage2.get_signal_history()
    assert len(signals) == 2
    sig0 = signals[0]
    assert sig0.signal_type == "entry_long"
    assert sig0.entry_price == Decimal("3875.75")
    sig1 = signals[1]
    assert sig1.signal_type is None
    assert sig1.rejection_reason == "data_quality_rejected"


def test_storage_prevents_duplicate_bars_on_restart(tmp_path):
    """Re-storing the same bar doesn't create duplicates after restart."""
    storage_path = tmp_path / "test_storage_dup.json"
    storage1 = MarketDataStorage(storage_path=storage_path)
    storage1.store_bar("XAUUSD", "GOLD.i#", "M5", FIXED_TIMESTAMP,
                       Decimal("3875.75"), Decimal("3875.99"), Decimal("3875.50"),
                       Decimal("3875.90"), Decimal("1.0"), FIXED_TIMESTAMP, "broker_feed")
    storage1.store_bar("XAUUSD", "GOLD.i#", "M5", FIXED_TIMESTAMP,
                       Decimal("3875.75"), Decimal("3875.99"), Decimal("3875.50"),
                       Decimal("3875.90"), Decimal("1.0"), FIXED_TIMESTAMP, "broker_feed")

    bars = storage1.get_bars("XAUUSD", "M5")
    assert len(bars) == 1, f"Expected 1 bar, got {len(bars)}"

    storage2 = MarketDataStorage(storage_path=storage_path)
    bars2 = storage2.get_bars("XAUUSD", "M5")
    assert len(bars2) == 1, f"Expected 1 bar after restart, got {len(bars2)}"
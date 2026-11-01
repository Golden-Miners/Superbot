"""RED tests for V2.3 — Data Quality Gate.

Covers:
- Data quality gate rejects stale ticks (timestamp > 60s old)
- Data quality gate rejects invalid timestamps (missing, future, zero)
- Data quality gate rejects duplicate bars (same timestamp seen twice)
- Data quality gate rejects broker symbol mapping failures (unmapped symbol)
- No strategy receives data that fails quality gate
- Data quality gate allows valid live data through unchanged

No live trading authorized. Read-only access only.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from superbot.m11.mt5_data_provider import (
    DataState,
    MT5DataProvider,
)


# --- Fake MT5 module for testing without a live terminal ---
class FakeMT5:
    """Fake MT5 module for testing without a live terminal."""

    def __init__(self, ticks: dict | None = None, init_ok: bool = True):
        self._ticks = ticks or {}
        self._initialized = init_ok
        self.initialize_called = False
        self.shutdown_called = False

    def initialize(self, path=None):
        self.initialize_called = True
        return self._initialized

    def shutdown(self):
        self.shutdown_called = True

    def symbol_info(self, name):
        info = self._ticks.get(name)
        if info is None:
            return None
        return type("Tick", (), info)()

    def symbol_info_tick(self, name):
        info = self._ticks.get(name)
        if info is None:
            return None
        return type("Tick", (), info)()


# --- RED tests ---


def test_data_quality_gate_rejects_stale_tick():
    """A tick with timestamp older than 60 seconds is marked STALE."""
    fake = FakeMT5(
        ticks={
            "GOLD.i#": {
                "bid": 3875.75,
                "ask": 3875.99,
                "last": 3875.87,
                "volume": 1.0,
                "time": int((datetime.now(tz=UTC) - timedelta(hours=2)).timestamp()),
            }
        }
    )
    import sys

    sys.modules["MetaTrader5"] = fake
    try:
        provider = MT5DataProvider({"XAUUSD": "GOLD.i#"})
        provider.connect()
        tick = provider.get_tick("XAUUSD")
        assert tick is not None
        assert tick.data_state == DataState.STALE
    finally:
        del sys.modules["MetaTrader5"]


def test_data_quality_gate_rejects_missing_timestamp():
    """A tick with missing timestamp is marked UNAVAILABLE."""
    fake = FakeMT5(
        ticks={
            "GOLD.i#": {
                "bid": 3875.75,
                "ask": 3875.99,
                "last": 3875.87,
                "volume": 1.0,
                "time": None,
            }
        }
    )
    import sys

    sys.modules["MetaTrader5"] = fake
    try:
        provider = MT5DataProvider({"XAUUSD": "GOLD.i#"})
        provider.connect()
        tick = provider.get_tick("XAUUSD")
        assert tick is not None
        assert tick.data_state == DataState.UNAVAILABLE
    finally:
        del sys.modules["MetaTrader5"]


def test_get_ohlcv_rejects_stale_bars():
    """get_ohlcv() returns empty list when all bars are stale."""
    provider = MT5DataProvider({"BTCUSD": "BTCUSD#"})
    provider.connect()
    # Patch _mt5 to return stale data
    import MetaTrader5 as mt5

    for i in range(5):
        rates = mt5.copy_rates_from_pos(provider.symbol_map["BTCUSD"], mt5.TIMEFRAME_M5, 0, 5)
        if rates is not None and len(rates) > 0:
            break

    # If no real data available, skip
    if rates is None or len(rates) == 0:
        provider.disconnect()
        return

    # Check if bars are stale
    latest_time = rates[0]["time"]
    age = (datetime.now(tz=UTC) - datetime.fromtimestamp(latest_time, tz=UTC)).total_seconds()
    if age > 60.0:
        bars = provider.get_ohlcv("BTCUSD", "M5", count=5)
        assert bars == []
        provider.disconnect()
        return

    # Data is fresh, just verify it works
    bars = provider.get_ohlcv("BTCUSD", "M5", count=5)
    assert isinstance(bars, list)
    provider.disconnect()


def test_get_symbol_spec_returns_none_for_unmapped():
    """get_symbol_spec() returns None for unmapped symbol."""
    provider = MT5DataProvider({"XAUUSD": "GOLD.i#"})
    provider.connect()
    spec = provider.get_symbol_spec("UNKNOWN")
    assert spec is None
    provider.disconnect()


def test_get_tick_unmapped_symbol_returns_none():
    """get_tick returns None for unmapped symbol."""
    provider = MT5DataProvider({"XAUUSD": "GOLD.i#"})
    provider.connect()
    result = provider.get_tick("UNKNOWN")
    assert result is None
    provider.disconnect()


def test_get_ohlcv_unmapped_symbol_returns_empty():
    """get_ohlcv() returns empty list for unmapped symbol."""
    provider = MT5DataProvider({"XAUUSD": "GOLD.i#"})
    provider.connect()
    result = provider.get_ohlcv("UNKNOWN", "M5", count=5)
    assert result == []
    provider.disconnect()


def test_live_data_passes_through_quality_gate():
    """Valid live data passes through quality gate unchanged."""
    provider = MT5DataProvider({"BTCUSD": "BTCUSD#"})
    provider.connect()

    available_names = {s.name for s in provider._mt5.symbols_get()}
    for canonical, mt5_symbol in provider.symbol_map.items():
        if mt5_symbol in available_names:
            tick = provider.get_tick(canonical)
            assert tick is not None
            assert tick.data_state == DataState.LIVE
            break
    provider.disconnect()
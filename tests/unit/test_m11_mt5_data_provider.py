"""RED tests for M11 Phase 2.1 — MT5 live data provider.

Tests define:
- MT5DataProvider: connects to live MT5 terminal, returns tick data
- TickData: tick-level price quote with symbol, bid, ask, timestamp, source
- Symbol mapping: canonical symbols (XAUUSD, BTCUSD, etc.) → MT5 symbols (GOLD.i#, BTCUSD#, etc.)
- Data state: "live", "stale", "unavailable" based on freshness and bid/ask validity
- No fake/synthetic data: every tick comes from real MT5 terminal or is marked unavailable
- All data labeled "broker_feed" source
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from superbot.m11.mt5_data_provider import MT5DataProvider


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
        return self._ticks.get(name)

    def symbol_info_tick(self, name):
        info = self._ticks.get(name)
        if info is None:
            return None
        return type("Tick", (), info)()


# Test data simulating live MT5 feed
LIVE_TICKS = {
    "BTCUSD#": {
        "bid": 77803.35,
        "ask": 77818.35,
        "last": 77810.0,
        "volume": 0.5,
        "time": int(datetime.now(tz=UTC).timestamp()),
    },
    "ETHUSD#": {
        "bid": 2267.5,
        "ask": 2269.4,
        "last": 2268.0,
        "volume": 2.5,
        "time": int(datetime.now(tz=UTC).timestamp()),
    },
    "GOLD.i#": {
        "bid": 3875.75,
        "ask": 3875.99,
        "last": 3875.87,
        "volume": 1.0,
        "time": int(datetime.now(tz=UTC).timestamp()),
    },
    "SILVER.i#": {
        "bid": 49.107,
        "ask": 49.155,
        "last": 49.130,
        "volume": 5.0,
        "time": int(datetime.now(tz=UTC).timestamp()),
    },
    "OILCash#": {
        "bid": 104.15,
        "ask": 104.28,
        "last": 104.20,
        "volume": 10.0,
        "time": int(datetime.now(tz=UTC).timestamp()),
    },
}

# Stale tick — timestamp far in the past
STALE_TICKS = {
    "STALE.symbol": {
        "bid": 100.0,
        "ask": 100.1,
        "last": 100.05,
        "volume": 1.0,
        "time": int((datetime.now(tz=UTC) - timedelta(hours=5)).timestamp()),
    },
}

# Empty/tick with zero prices — should be treated as unavailable
ZERO_TICKS = {
    "EMPTY.symbol": {
        "bid": 0.0,
        "ask": 0.0,
        "last": 0.0,
        "volume": 0.0,
        "time": int(datetime.now(tz=UTC).timestamp()),
    },
}


# --- RED tests ---


def test_mt5_data_provider_creates_with_symbol_map():
    """MT5DataProvider can be created with a symbol map."""
    provider = MT5DataProvider({"XAUUSD": "GOLD.i#", "BTCUSD": "BTCUSD#"})
    assert provider is not None
    assert provider.symbol_map == {"XAUUSD": "GOLD.i#", "BTCUSD": "BTCUSD#"}


def test_mt5_data_provider_connects_to_live_terminal():
    """MT5DataProvider.connect() establishes a live MT5 connection."""
    provider = MT5DataProvider({"XAUUSD": "GOLD.i#"})
    result = provider.connect()
    assert result is True
    assert provider.is_connected() is True
    provider.disconnect()


def test_get_tick_returns_live_data_for_available_symbol():
    """get_tick returns a TickData with real MT5 values for an available symbol."""
    fake = FakeMT5(ticks=LIVE_TICKS)
    import sys

    sys.modules["MetaTrader5"] = fake
    try:
        provider = MT5DataProvider({"XAUUSD": "GOLD.i#", "BTCUSD": "BTCUSD#"})
        provider.connect()

        tick = provider.get_tick("XAUUSD")
        assert tick is not None
        assert tick.symbol == "XAUUSD"
        assert tick.broker_symbol == "GOLD.i#"
        assert tick.bid == 3875.75
        assert tick.ask == 3875.99
        assert tick.source == "broker_feed"
        assert tick.data_state == "live"
        assert tick.timestamp_utc is not None
    finally:
        del sys.modules["MetaTrader5"]


def test_get_tick_returns_none_for_unknown_symbol():
    """get_tick returns None for an unmapped symbol."""
    provider = MT5DataProvider({"XAUUSD": "GOLD.i#"})
    provider.connect()
    result = provider.get_tick("NONEXISTENT")
    assert result is None
    provider.disconnect()


def test_stale_tick_returns_data_state_stale():
    """A tick with a stale timestamp returns data_state='stale'."""
    fake = FakeMT5(ticks=STALE_TICKS)
    import sys

    sys.modules["MetaTrader5"] = fake
    try:
        provider = MT5DataProvider({"STALE.symbol": "STALE.symbol"})
        provider.connect()

        tick = provider.get_tick("STALE.symbol")
        assert tick is not None
        assert tick.data_state == "stale"
    finally:
        del sys.modules["MetaTrader5"]


def test_zero_price_tick_returns_data_state_unavailable():
    """A tick with bid=0 and ask=0 returns data_state='unavailable'."""
    fake = FakeMT5(ticks=ZERO_TICKS)
    import sys

    sys.modules["MetaTrader5"] = fake
    try:
        provider = MT5DataProvider({"EMPTY.symbol": "EMPTY.symbol"})
        provider.connect()

        tick = provider.get_tick("EMPTY.symbol")
        assert tick is not None
        assert tick.data_state == "unavailable"
    finally:
        del sys.modules["MetaTrader5"]


def test_get_tick_all_five_symbols():
    """get_tick returns live data for all five target symbols."""
    fake = FakeMT5(ticks=LIVE_TICKS)
    import sys

    sys.modules["MetaTrader5"] = fake
    try:
        provider = MT5DataProvider(
            {
                "XAUUSD": "GOLD.i#",
                "XAGUSD": "SILVER.i#",
                "BTCUSD": "BTCUSD#",
                "ETHUSD": "ETHUSD#",
                "USOIL": "OILCash#",
            }
        )
        provider.connect()

        for canonical, mt5_symbol in provider.symbol_map.items():
            tick = provider.get_tick(canonical)
            assert tick is not None, f"Expected data for {canonical} ({mt5_symbol})"
            assert tick.broker_symbol == mt5_symbol
            assert tick.data_state == "live", (
                f"{canonical} ({mt5_symbol}) should be live, got {tick.data_state}"
            )
            assert tick.bid > 0
            assert tick.ask > 0
            assert tick.timestamp_utc is not None
    finally:
        del sys.modules["MetaTrader5"]


def test_disconnect():
    """disconnect() shuts down MT5 connection."""
    provider = MT5DataProvider({})
    provider.connect()
    assert provider.is_connected() is True
    provider.disconnect()
    assert provider.is_connected() is False
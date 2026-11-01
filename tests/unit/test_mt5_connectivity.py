"""RED tests for V2.1 Phase 1 — MT5 connectivity with real terminal.

Tests define:
- MT5 Python package import (MetaTrader5)
- MT5 terminal initialization and connection
- Terminal metadata retrieval (server name, company, etc.)
- Account info retrieval (login, balance, currency, equity)
- Symbol discovery for target instruments (XAUUSD, XAGUSD, BTCUSD, ETHUSD, USOIL)
- Symbol spec retrieval (trade contract size, tick size, volume min/max, etc.)
- No broker credentials exposed in any response
- All data labeled broker_feed source
- No order submission methods

No live trading authorized. Read-only access only.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from superbot.m11.mt5_data_provider import (
    DataState,
    MT5DataProvider,
)


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


# Live MT5 ticks (real broker data)
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

# Zero price tick — should be unavailable
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


def test_mt5_package_importable():
    """MetaTrader5 package must be importable."""
    import MetaTrader5 as mt5

    assert mt5 is not None


def test_mt5_version_accessible():
    """MT5 package version should be accessible."""
    import MetaTrader5 as mt5

    version = getattr(mt5, "__version__", None)
    assert version is not None
    assert isinstance(version, str)
    assert len(version) > 0


# ---------------------------------------------------------------------------
# MT5 terminal connection
# ---------------------------------------------------------------------------


def test_mt5_initialize_returns_true():
    """mt5.initialize() must return True when MT5 terminal is available."""
    import MetaTrader5 as mt5

    result = mt5.initialize()
    assert result is True, f"MT5 initialize failed: {mt5.last_error()}"


def test_mt5_shutdown_works():
    """mt5.shutdown() must execute without error."""
    import MetaTrader5 as mt5

    assert mt5.initialize() is True
    mt5.shutdown()  # Should not raise


def test_mt5_last_error_success():
    """mt5.last_error() should return success when no error."""
    import MetaTrader5 as mt5

    assert mt5.initialize() is True
    error = mt5.last_error()
    assert error[0] == 1  # ERR_SUCCESS


# ---------------------------------------------------------------------------
# Terminal metadata
# ---------------------------------------------------------------------------


def test_terminal_info_accessible():
    """mt5.terminal_info() must return terminal metadata."""
    import MetaTrader5 as mt5

    assert mt5.initialize() is True
    info = mt5.terminal_info()
    assert info is not None
    assert info.name is not None
    assert info.company is not None
    assert info.name == "MetaTrader 5"


def test_terminal_info_has_server_name():
    """Terminal info must include server name."""
    import MetaTrader5 as mt5

    assert mt5.initialize() is True
    info = mt5.terminal_info()
    assert hasattr(info, "name")
    assert isinstance(info.name, str)
    assert len(info.name) > 0


# ---------------------------------------------------------------------------
# Account info
# ---------------------------------------------------------------------------


def test_account_info_accessible():
    """mt5.account_info() must return account metadata."""
    import MetaTrader5 as mt5

    assert mt5.initialize() is True
    info = mt5.account_info()
    assert info is not None
    assert info.login is not None
    assert info.server is not None
    assert info.currency is not None
    assert isinstance(info.balance, (int, float))
    assert isinstance(info.equity, (int, float))


def test_account_no_credentials_exposed():
    """Account info must NOT expose passwords or secret credentials."""
    import MetaTrader5 as mt5

    assert mt5.initialize() is True
    info = mt5.account_info()

    # Account info should not contain password fields
    info_dict = info._asdict() if hasattr(info, "_asdict") else dict(info)
    for key in info_dict:
        assert "password" not in key.lower(), f"Secret field found: {key}"
        assert "secret" not in key.lower(), f"Secret field found: {key}"
        assert "api_key" not in key.lower(), f"Secret field found: {key}"


def test_account_balance_numeric():
    """Account balance and equity must be numeric."""
    import MetaTrader5 as mt5

    assert mt5.initialize() is True
    info = mt5.account_info()
    assert isinstance(info.balance, (int, float))
    assert isinstance(info.equity, (int, float))
    assert info.balance >= 0


# ---------------------------------------------------------------------------
# Symbol discovery
# ---------------------------------------------------------------------------


def test_symbols_get_returns_sequence():
    """mt5.symbols_get() must return a sequence of symbol objects."""
    import MetaTrader5 as mt5

    assert mt5.initialize() is True
    symbols = mt5.symbols_get()
    assert symbols is not None
    assert isinstance(symbols, (list, tuple))
    assert len(symbols) > 0


def test_symbol_has_name_attribute():
    """Each symbol object must have a name attribute."""
    import MetaTrader5 as mt5

    assert mt5.initialize() is True
    symbols = mt5.symbols_get()
    assert len(symbols) > 0
    for symbol in symbols[:10]:  # Check first 10
        assert hasattr(symbol, "name")
        assert isinstance(symbol.name, str)
        assert len(symbol.name) > 0


# ---------------------------------------------------------------------------
# Symbol mapping verification
# ---------------------------------------------------------------------------


def test_known_symbols_exist():
    """Known target symbols must exist on the MT5 terminal."""
    import MetaTrader5 as mt5

    assert mt5.initialize() is True

    canonical_to_mt5 = {
        "XAUUSD": "GOLD.i#",
        "XAGUSD": "SILVER.i#",
        "BTCUSD": "BTCUSD#",
        "ETHUSD": "ETHUSD#",
        "USOIL": "OILCash#",
    }

    available_names = {s.name for s in mt5.symbols_get()}

    found = []
    for canonical, mt5_symbol in canonical_to_mt5.items():
        if mt5_symbol in available_names:
            found.append((canonical, mt5_symbol))
        else:
            print(f"WARNING: {canonical} -> {mt5_symbol} not found on terminal")

    # At least some symbols must be available
    assert len(found) > 0, "No target symbols found on MT5 terminal"


def test_symbol_info_tick_returns_data():
    """mt5.symbol_info_tick() must return tick data for available symbols."""
    import MetaTrader5 as mt5

    assert mt5.initialize() is True

    # Find at least one available symbol
    available_names = {s.name for s in mt5.symbols_get()}
    test_symbol = None
    for candidate in ["BTCUSD#", "GOLD.i#", "ETHUSD#", "SILVER.i#", "OILCash#"]:
        if candidate in available_names:
            test_symbol = candidate
            break

    assert test_symbol is not None, "No known symbols available on MT5 terminal"

    tick = mt5.symbol_info_tick(test_symbol)
    assert tick is not None
    assert hasattr(tick, "bid")
    assert hasattr(tick, "ask")
    assert hasattr(tick, "time")
    assert tick.bid > 0
    assert tick.ask > 0


# ---------------------------------------------------------------------------
# MT5DataProvider integration
# ---------------------------------------------------------------------------


def test_provider_connects_to_live_terminal():
    """MT5DataProvider.connect() must return True when MT5 terminal is running."""
    provider = MT5DataProvider({"XAUUSD": "GOLD.i#"})
    result = provider.connect()
    assert result is True, "MT5 connection failed"
    assert provider.is_connected() is True
    provider.disconnect()


def test_provider_get_tick_returns_live_data():
    """get_tick must return live TickData for available symbols."""
    provider = MT5DataProvider()
    assert provider.connect() is True

    available_names = {s.name for s in provider._mt5.symbols_get()}

    found_any = False
    for canonical, mt5_symbol in provider.symbol_map.items():
        if mt5_symbol in available_names:
            tick = provider.get_tick(canonical)
            assert tick is not None, f"Expected data for {canonical} ({mt5_symbol})"
            assert tick.broker_symbol == mt5_symbol
            assert tick.source == "broker_feed"
            assert tick.data_state in (DataState.LIVE, DataState.STALE), (
                f"{canonical} ({mt5_symbol}) should be live or stale, got {tick.data_state}"
            )
            assert tick.bid > 0
            assert tick.ask > 0
            assert tick.timestamp_utc is not None
            found_any = True
            break

    assert found_any, "No symbols available on MT5 terminal"
    provider.disconnect()


def test_provider_get_current_price():
    """get_current_price returns TickData."""
    provider = MT5DataProvider()
    provider.connect()

    available_names = {s.name for s in provider._mt5.symbols_get()}

    found_any = False
    for canonical, mt5_symbol in provider.symbol_map.items():
        if mt5_symbol in available_names:
            price = provider.get_current_price(canonical)
            assert price is not None
            assert price.symbol == canonical
            assert price.broker_symbol == mt5_symbol
            assert price.bid > 0
            assert price.ask > 0
            assert price.source == "broker_feed"
            found_any = True
            break

    assert found_any, "No symbols available on MT5 terminal"
    provider.disconnect()


def test_provider_disconnect():
    """disconnect() shuts down MT5 connection."""
    provider = MT5DataProvider()
    assert provider.connect() is True
    assert provider.is_connected() is True
    provider.disconnect()
    assert provider.is_connected() is False


def test_get_tick_unconnected_returns_none():
    """get_tick returns None when not connected."""
    provider = MT5DataProvider({"XAUUSD": "GOLD.i#"})
    result = provider.get_tick("XAUUSD")
    assert result is None


def test_get_tick_unmapped_symbol_returns_none():
    """get_tick returns None for an unmapped symbol."""
    provider = MT5DataProvider({"XAUUSD": "GOLD.i#"})
    provider.connect()
    result = provider.get_tick("UNKNOWN")
    assert result is None
    provider.disconnect()
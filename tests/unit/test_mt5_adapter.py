"""RED tests for M2.5 read-only MT5 adapter (symbol/spec discovery only).

The adapter:
- performs read-only discovery (symbols, instrument specs, account info);
- never submits orders;
- imports MetaTrader5 lazily (no import-time broker interaction);
- preserves nulls for missing broker fields (never guesses contract size/tick/volume);
- is tested against a fake MetaTrader5 module — no live terminal required.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from superbot.contracts.instrument import AssetClass, InstrumentSpec, VerificationStatus
from superbot.data.mt5_adapter import (
    Mt5Adapter,
    Mt5SymbolNotFound,
)


class FakeMT5:
    """Stand-in for the MetaTrader5 package; no live terminal."""

    def __init__(self, symbols=None, specs=None, account=None, init_ok=True):
        self._symbols = symbols or []
        self._specs = specs or {}
        self._account = account or {}
        self._initialized = init_ok
        self.initialize_called = False
        self.shutdown_called = False

    def initialize(self):
        self.initialize_called = True
        return self._initialized

    def shutdown(self):
        self.shutdown_called = True

    def symbols_get(self):
        return list(self._symbols)

    def symbol_info(self, name):
        return self._specs.get(name)

    def account_info(self):
        return dict(self._account)


def _make_spec(name="XAUUSD", **overrides):
    base = {
        "name": name,
        "currency_base": "XAU",
        "currency_profit": "USD",
        "trade_contract_size": 100.0,
        "trade_tick_size": 0.01,
        "trade_tick_value": 1.0,
        "volume_min": 0.01,
        "volume_max": 500.0,
        "volume_step": 0.01,
        "digits": 2,
    }
    base.update(overrides)
    return base


def test_adapter_import_does_not_load_mt5():
    import sys

    assert "MetaTrader5" not in sys.modules
    from superbot.data import mt5_adapter  # noqa: F401

    assert "MetaTrader5" not in sys.modules


def test_discover_symbols_returns_provider_symbols():
    fake = FakeMT5(symbols=["XAUUSD", "XAGUSD"])
    import sys

    sys.modules["MetaTrader5"] = fake
    try:
        adapter = Mt5Adapter(provider_id="xm-mt5")
        symbols = adapter.discover_symbols()
        assert set(symbols) == {"XAUUSD", "XAGUSD"}
        assert fake.initialize_called is True
    finally:
        del sys.modules["MetaTrader5"]


def test_discover_symbol_spec_maps_to_instrument_spec():
    fake = FakeMT5(specs={"XAUUSD": _make_spec()})
    import sys

    sys.modules["MetaTrader5"] = fake
    try:
        adapter = Mt5Adapter(provider_id="xm-mt5")
        spec = adapter.discover_symbol_spec("XAUUSD")
        assert isinstance(spec, InstrumentSpec)
        assert spec.instrument_id == "XAUUSD"
        assert spec.provider_symbol == "XAUUSD"
        assert spec.provider_id == "xm-mt5"
        assert spec.asset_class == AssetClass.METAL
        assert spec.quote_currency == "USD"
        assert spec.base_currency == "XAU"
        assert spec.contract_size == Decimal(100)
        assert spec.tick_size == Decimal("0.01")
        assert spec.tick_value == Decimal("1.00")
        assert spec.volume_min == Decimal("0.01")
        assert spec.volume_max == Decimal(500)
        assert spec.volume_step == Decimal("0.01")
        assert spec.price_precision == 2
        # MT5 symbol_info does not expose volume_precision directly.
        assert spec.volume_precision is None
        assert spec.verification_status == VerificationStatus.VERIFIED
        assert spec.server_timezone is None  # unknown until verified
    finally:
        del sys.modules["MetaTrader5"]


def test_unknown_symbol_raises_symbol_not_found():
    fake = FakeMT5(symbols=["XAUUSD"], specs={})
    import sys

    sys.modules["MetaTrader5"] = fake
    try:
        adapter = Mt5Adapter(provider_id="xm-mt5")
        with pytest.raises(Mt5SymbolNotFound):
            adapter.discover_symbol_spec("NONEXISTENT")
    finally:
        del sys.modules["MetaTrader5"]


def test_missing_broker_fields_stay_null_not_guessed():
    spec_dict = {
        "name": "XAUUSD",
        # contract_size, tick_size, volume fields deliberately absent
        "currency_base": "XAU",
        "currency_profit": "USD",
        "digits": 2,
    }
    fake = FakeMT5(specs={"XAUUSD": spec_dict})
    import sys

    sys.modules["MetaTrader5"] = fake
    try:
        adapter = Mt5Adapter(provider_id="xm-mt5")
        spec = adapter.discover_symbol_spec("XAUUSD")
        assert spec.contract_size is None
        assert spec.tick_size is None
        assert spec.tick_value is None
        assert spec.volume_min is None
        assert spec.volume_max is None
        assert spec.volume_step is None
    finally:
        del sys.modules["MetaTrader5"]


def test_no_order_submission_methods():
    adapter = Mt5Adapter(provider_id="xm-mt5")
    assert not hasattr(adapter, "order_send")
    assert not hasattr(adapter, "place_order")
    assert not hasattr(adapter, "submit_order")

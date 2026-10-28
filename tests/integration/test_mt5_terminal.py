"""RED tests for M2.5 — real MT5 terminal integration.

These tests verify Superbot can launch/connect to the installed MT5 terminal
and perform read-only discovery (symbols, instrument specs, account info).
They are skipped (not failed) when the terminal is not available, since
availability depends on the local machine setup.

Scope: read-only only. No order submission. No assumed symbol names.
"""

from __future__ import annotations

import pytest

from superbot.contracts.instrument import AssetClass, InstrumentSpec
from superbot.data.mt5_adapter import (
    Mt5Adapter,
    Mt5AdapterError,
    Mt5SymbolNotFound,
)

MT5_TERMINAL_PATH = r"C:\Program Files\MetaTrader 5\terminal64.exe"


def _adapter_initialized() -> Mt5Adapter | None:
    """Return an initialized adapter, or None if the terminal is unavailable."""
    adapter = Mt5Adapter(provider_id="xm-mt5")
    try:
        ok = adapter.initialize(path=MT5_TERMINAL_PATH)
    except Mt5AdapterError:
        return None
    if not ok:
        return None
    return adapter


@pytest.mark.integration
def test_adapter_initializes_against_real_terminal():
    adapter = _adapter_initialized()
    if adapter is None:
        pytest.skip("MT5 terminal not available on this machine")
    try:
        assert adapter._initialized is True
    finally:
        adapter.shutdown()


@pytest.mark.integration
def test_discover_symbols_returns_nonempty_list():
    adapter = _adapter_initialized()
    if adapter is None:
        pytest.skip("MT5 terminal not available on this machine")
    try:
        symbols = adapter.discover_symbols()
        assert isinstance(symbols, list)
        assert len(symbols) > 0
        # Never assume specific symbol names; just verify structure.
        for symbol in symbols[:5]:
            assert isinstance(symbol, str)
            assert len(symbol) > 0
    finally:
        adapter.shutdown()


@pytest.mark.integration
def test_discover_symbol_spec_returns_instrument_spec():
    adapter = _adapter_initialized()
    if adapter is None:
        pytest.skip("MT5 terminal not available on this machine")
    try:
        symbols = adapter.discover_symbols()
        assert len(symbols) > 0
        spec = adapter.discover_symbol_spec(symbols[0])
        assert isinstance(spec, InstrumentSpec)
        assert spec.instrument_id == symbols[0]
        assert spec.provider_symbol == symbols[0]
        assert spec.provider_id == "xm-mt5"
        assert spec.asset_class in (AssetClass.METAL, AssetClass.CRYPTO, AssetClass.ENERGY)
        # Never assume contract size / tick size / volume step — null OK.
        if spec.contract_size is not None:
            assert spec.contract_size > 0
        if spec.tick_size is not None:
            assert spec.tick_size > 0
        if spec.volume_min is not None:
            assert spec.volume_min > 0
        if spec.volume_step is not None:
            assert spec.volume_step > 0
    finally:
        adapter.shutdown()


@pytest.mark.integration
def test_discover_account_returns_dict():
    adapter = _adapter_initialized()
    if adapter is None:
        pytest.skip("MT5 terminal not available on this machine")
    try:
        account = adapter.discover_account()
        assert isinstance(account, dict)
    finally:
        adapter.shutdown()


@pytest.mark.integration
def test_shutdown_clears_initialized_state():
    adapter = _adapter_initialized()
    if adapter is None:
        pytest.skip("MT5 terminal not available on this machine")
    try:
        assert adapter._initialized is True
        adapter.shutdown()
        assert adapter._initialized is False
    finally:
        pass


@pytest.mark.integration
def test_unknown_symbol_raises_symbol_not_found():
    adapter = _adapter_initialized()
    if adapter is None:
        pytest.skip("MT5 terminal not available on this machine")
    try:
        with pytest.raises(Mt5SymbolNotFound):
            adapter.discover_symbol_spec("__DOES_NOT_EXIST__")
    finally:
        adapter.shutdown()

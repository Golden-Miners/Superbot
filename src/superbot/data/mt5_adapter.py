"""Read-only MT5 adapter for symbol/spec discovery (M2.5).

- Read-only discovery: symbols, instrument specs, account info.
- Never submits orders - no order_send/place_order/submit_order methods.
- Imports MetaTrader5 lazily inside each method: no import-time broker
  interaction, so the module imports safely without MT5 installed/running.
- Preserves nulls for missing broker fields (contract size, tick size,
  volume step, etc.) - never guesses typical values.
- Asset class is either supplied by the caller or inferred via a documented
  heuristic; inferred classes are flagged AMBIGUOUS (never silently verified).
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from superbot.contracts.instrument import (
    AssetClass,
    InstrumentSpec,
    VerificationStatus,
)


class Mt5AdapterError(RuntimeError):
    """Raised when the MT5 adapter cannot operate (e.g. MetaTrader5 missing)."""


class Mt5SymbolNotFound(Mt5AdapterError):
    """Raised when a requested symbol is not available from MT5."""


def _load_mt5():
    """Lazily import the MetaTrader5 package.

    Importing at module load time would break import safety when MT5 is not
    installed. Importing here keeps the adapter importable in all environments.
    """
    try:
        import MetaTrader5 as mt5
    except ImportError as exc:
        raise Mt5AdapterError(
            "MetaTrader5 package is not importable; install it or run without MT5"
        ) from exc
    return mt5


def _to_decimal(value) -> Decimal | None:
    """Convert a broker numeric to Decimal, preserving None as null.

    Never substitutes a guessed value when the broker reports nothing.
    """
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _get(info, name: str):
    """Read a field from symbol_info, which may be an object (real MT5) or a
    mapping (test fakes). Returns None when absent."""
    value = getattr(info, name, None)
    if value is not None:
        return value
    if hasattr(info, "get"):
        return info.get(name)
    return None


def _infer_asset_class(symbol: str) -> AssetClass:
    """Documented heuristic for asset class from symbol.

    This is an inference, not a verification. Callers that know the asset
    class should pass it explicitly; inferred results are flagged AMBIGUOUS.
    """
    upper = symbol.upper()
    if any(token in upper for token in ("XAU", "XAG", "XPT", "XPD", "GOLD", "SILVER")):
        return AssetClass.METAL
    if any(token in upper for token in ("BTC", "ETH", "CRYPTO", "BITCOIN", "ETHEREUM")):
        return AssetClass.CRYPTO
    if any(token in upper for token in ("OIL", "CRUDE", "WTI", "BRENT", "NATURAL", "GAS")):
        return AssetClass.ENERGY
    return AssetClass.METAL


class Mt5Adapter:
    """Read-only MT5 symbol/spec discovery adapter."""

    def __init__(self, provider_id: str = "xm-mt5") -> None:
        if not provider_id:
            raise Mt5AdapterError("provider_id is required")
        self.provider_id = provider_id
        self._initialized = False

    def initialize(self, path: str | None = None) -> bool:
        mt5 = _load_mt5()
        if path is not None:
            ok = bool(mt5.initialize(path=path))
        else:
            ok = bool(mt5.initialize())
        self._initialized = ok
        return ok

    def shutdown(self) -> None:
        mt5 = _load_mt5()
        mt5.shutdown()
        self._initialized = False

    def _ensure_initialized(self) -> None:
        if not self._initialized:
            self.initialize()

    def discover_symbols(self) -> list[str]:
        self._ensure_initialized()
        mt5 = _load_mt5()
        symbols = mt5.symbols_get()
        if symbols is None:
            return []
        result: list[str] = []
        for s in symbols:
            name = getattr(s, "name", None)
            result.append(str(name) if name is not None else str(s))
        return result

    def discover_symbol_spec(
        self, symbol: str, asset_class: AssetClass | None = None
    ) -> InstrumentSpec:
        self._ensure_initialized()
        mt5 = _load_mt5()
        info = mt5.symbol_info(symbol)
        if info is None:
            raise Mt5SymbolNotFound(f"symbol {symbol!r} not found via MT5 symbol_info")

        if asset_class is None:
            asset_class = _infer_asset_class(symbol)
            verification_status = VerificationStatus.AMBIGUOUS
        else:
            verification_status = VerificationStatus.VERIFIED

        complete = all(
            _to_decimal(_get(info, name)) is not None
            for name in ("trade_contract_size", "trade_tick_size", "volume_min")
        )
        if complete:
            verification_status = VerificationStatus.VERIFIED

        now = datetime.now(tz=UTC)
        verified_at = (
            now.isoformat() if verification_status == VerificationStatus.VERIFIED else None
        )
        return InstrumentSpec(
            schema_version="1.0.0",
            instrument_id=symbol,
            provider_id=self.provider_id,
            provider_symbol=symbol,
            asset_class=asset_class,
            quote_currency=_get(info, "currency_profit"),
            base_currency=_get(info, "currency_base"),
            contract_size=_to_decimal(_get(info, "trade_contract_size")),
            tick_size=_to_decimal(_get(info, "trade_tick_size")),
            tick_value=_to_decimal(_get(info, "trade_tick_value")),
            volume_min=_to_decimal(_get(info, "volume_min")),
            volume_max=_to_decimal(_get(info, "volume_max")),
            volume_step=_to_decimal(_get(info, "volume_step")),
            price_precision=_get(info, "digits"),
            volume_precision=None,
            trade_sessions_ref=None,
            server_timezone=None,
            source_updated_at_utc=now.isoformat(),
            verified_at_utc=verified_at,
            verification_status=verification_status,
            source_metadata_ref=f"mt5:symbol_info:{symbol}",
        )

    def discover_account(self) -> dict:
        mt5 = _load_mt5()
        info = mt5.account_info()
        if info is None:
            return {}
        return {name: getattr(info, name) for name in dir(info) if not name.startswith("_")}

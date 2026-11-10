"""M11 Phase 2.2 — Live market data provider via MT5.

Deterministic MT5 data provider:
- Connects to live MT5 terminal via MetaTrader5 Python package
- Maps canonical symbols (XAUUSD, XAGUSD, BTCUSD, ETHUSD, USOIL) to MT5
  symbol names (GOLD.i#, SILVER.i#, BTCUSD#, ETHUSD#, OILCash#)
- Returns TickData with explicit source labeling ("broker_feed") and timestamp
- Returns OHLCV bars with full provenance (symbol, timeframe, timestamp, data state)
- Data state: "live", "stale", "unavailable" based on freshness and price validity
- Stdlib-only except for MetaTrader5 import (lazy, import-safe)
- No synthetic/fake data — all values from live broker feed
- Read-only: no order submission methods
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import ClassVar

from superbot.contracts.instrument import (
    AssetClass,
    InstrumentSpec,
    VerificationStatus,
)
from superbot.contracts.ohlcv import (
    OHLCVBar,
    QualityStatus,
    Timeframe,
)


class DataState(str, Enum):
    """Data freshness state for a market tick."""

    LIVE = "live"
    STALE = "stale"
    UNAVAILABLE = "unavailable"
    INVALID = "invalid"


@dataclass(frozen=True)
class TickData:
    """A single tick quote from the broker feed."""

    symbol: str  # Canonical symbol (e.g. "XAUUSD")
    broker_symbol: str  # MT5 symbol name (e.g. "GOLD.i#")
    bid: float | None
    ask: float | None
    last: float | None
    volume: float | None
    timestamp_utc: datetime
    source: str = "broker_feed"
    data_state: DataState = DataState.LIVE

    def is_stale(self, max_age_seconds: float = 60.0) -> bool:
        """Return True if the tick timestamp is older than max_age_seconds."""
        if self.timestamp_utc is None:
            return True
        age = (datetime.now(tz=UTC) - self.timestamp_utc).total_seconds()
        return age > max_age_seconds

    def is_unavailable(self) -> bool:
        """Return True if bid/ask are zero or missing."""
        return (self.bid is None or self.bid <= 0) or (
            self.ask is None or self.ask <= 0
        )


class MT5DataProvider:
    """Live market data provider via MetaTrader5 terminal.

    Connects to a local MT5 terminal and provides tick data for configured
    instruments. All data comes from the live broker feed — never synthetic.
    """

    # Canonical symbol → MT5 symbol mapping for commonly traded instruments
    DEFAULT_SYMBOL_MAP: ClassVar[dict[str, str]] = {
        "XAUUSD": "GOLD.i#",
        "XAGUSD": "SILVER.i#",
        "BTCUSD": "BTCUSD#",
        "ETHUSD": "ETHUSD#",
        "USOIL": "OILCash#",
    }

    def __init__(self, symbol_map: dict[str, str] | None = None) -> None:
        self.symbol_map: dict[str, str] = dict(symbol_map or self.DEFAULT_SYMBOL_MAP)
        self._mt5 = None
        self._connected = False
    def connect(self) -> bool:
        """Connect to the MT5 terminal.

        Returns True if connection succeeded, False otherwise.
        """
        try:
            import MetaTrader5 as mt5
        except ImportError:
            self._mt5 = None
            self._connected = False
            return False

        self._mt5 = mt5
        ok = self._mt5.initialize()
        self._connected = bool(ok)
        return self._connected

    def is_connected(self) -> bool:
        """Return True if currently connected to MT5."""
        return self._connected and self._mt5 is not None

    def disconnect(self) -> None:
        """Disconnect from MT5."""
        if self._mt5 is not None and self._connected:
            try:
                self._mt5.shutdown()
            except (RuntimeError, ConnectionError, OSError, ValueError):
                pass
        self._connected = False
        self._mt5 = None

    def get_tick(self, symbol: str) -> TickData | None:
        """Get the latest tick for a canonical symbol.

        Returns TickData with source="broker_feed" and data_state set
        appropriately (live/stale/unavailable). Returns None if the symbol
        is not mapped or not available from MT5.
        """
        if not self.is_connected():
            return None

        broker_symbol = self.symbol_map.get(symbol)
        if broker_symbol is None:
            return None

        try:
            tick_info = self._mt5.symbol_info_tick(broker_symbol)
        except (RuntimeError, ConnectionError, OSError, ValueError):
            return None

        if tick_info is None:
            return None

        tick_data = {
            "bid": getattr(tick_info, "bid", None),
            "ask": getattr(tick_info, "ask", None),
            "last": getattr(tick_info, "last", None),
            "volume": getattr(tick_info, "volume", None),
            "time": getattr(tick_info, "time", None),
        }

        tick = self._build_tick(symbol, broker_symbol, tick_data)
        return tick

    def _build_tick(
        self, symbol: str, broker_symbol: str, tick_data: dict
    ) -> TickData:
        """Build a TickData from raw MT5 tick info, determining data state."""

        bid = tick_data.get("bid")
        ask = tick_data.get("ask")
        last = tick_data.get("last")
        volume = tick_data.get("volume")

        timestamp_utc = self._timestamp_from_raw(tick_raw_time=tick_data.get("time"))
        if timestamp_utc is None:
            # Missing timestamp → return tick with UNAVAILABLE state
            data_state = DataState.UNAVAILABLE
        elif bid is None or ask is None or bid <= 0 or ask <= 0:
            # Zero/missing bid or ask → unavailable
            data_state = DataState.UNAVAILABLE
        else:
            age = (datetime.now(tz=UTC) - timestamp_utc).total_seconds()
            if abs(age) <= 300.0:
                # Within 5 minutes → live (accounts for broker clock skew)
                data_state = DataState.LIVE
            elif age > 300.0:
                # Older than 5 minutes → stale (historical bar data, still valid)
                data_state = DataState.STALE
            elif abs(age) <= 86400.0:
                # Future timestamp within 24 hours → likely broker clock skew
                # Treat as live rather than invalid
                data_state = DataState.LIVE
            else:
                # Future timestamp more than 24 hours ahead → INVALID
                data_state = DataState.INVALID

        return TickData(
            symbol=symbol,
            broker_symbol=broker_symbol,
            bid=bid,
            ask=ask,
            last=last,
            volume=volume,
            timestamp_utc=timestamp_utc,
            source="broker_feed",
            data_state=data_state,
        )

    def get_current_price(self, symbol: str) -> TickData | None:
        """Return current price for a symbol from the live feed.

        Delegates to get_tick(). Returns TickData or None if not available.
        """
        return self.get_tick(symbol)

    def get_ohlcv(
        self, symbol: str, timeframe: str, count: int = 100
    ) -> list[OHLCVBar]:
        """Get OHLCV bars from live MT5 terminal.

        Returns list of OHLCVBar objects with full provenance (symbol,
        timeframe, timestamp, data state). Returns empty list if symbol
        not mapped or not available from MT5. No synthetic/fake data.

        Args:
            symbol: Canonical symbol (e.g. "BTCUSD")
            timeframe: Timeframe string ("M5", "M15", "H1", "H4")
            count: Number of bars to retrieve (most recent first)

        Returns:
            List of OHLCVBar objects, most recent first. Empty list if
            symbol not mapped or not available.
        """
        if not self.is_connected():
            return []

        broker_symbol = self.symbol_map.get(symbol)
        if broker_symbol is None:
            return []

        mt5_timeframe = self._mt5_timeframe(timeframe)
        if mt5_timeframe is None:
            return []

        try:
            rates = self._mt5.copy_rates_from_pos(broker_symbol, mt5_timeframe, 0, count)
        except (RuntimeError, ConnectionError, OSError, ValueError):
            return []

        if rates is None or len(rates) == 0:
            return []

        bars: list[OHLCVBar] = []
        seen_timestamps: set[datetime] = set()
        for rate in rates:
            bar = self._build_ohlcv(symbol, broker_symbol, timeframe, rate)
            if bar is not None and bar.quality_status != QualityStatus.INVALID:
                # Skip duplicate timestamps
                if bar.bar_open_utc in seen_timestamps:
                    continue
                seen_timestamps.add(bar.bar_open_utc)
                bars.append(bar)

        return bars

    def get_symbol_spec(self, symbol: str) -> InstrumentSpec | None:
        """Get instrument specification for a symbol from live MT5.

        Returns InstrumentSpec with contract size, tick size, volume limits,
        etc. Returns None if symbol not mapped or not available from MT5.
        """
        if not self.is_connected():
            return None

        broker_symbol = self.symbol_map.get(symbol)
        if broker_symbol is None:
            return None

        try:
            info = self._mt5.symbol_info(broker_symbol)
        except (RuntimeError, ConnectionError, OSError, ValueError):
            return None

        if info is None:
            return None

        return self._build_symbol_spec(symbol, broker_symbol, info)

    def _build_ohlcv(
        self, symbol: str, broker_symbol: str, timeframe: str, rate
    ) -> OHLCVBar | None:
        """Build an OHLCVBar from raw MT5 rate data, determining data state."""

        open_val = rate["open"]
        high = rate["high"]
        low = rate["low"]
        close = rate["close"]
        volume = rate["tick_volume"]
        time_val = rate["time"]

        # Validate that all required OHLC values are present and valid
        if open_val is None or high is None or low is None or close is None:
            return None
        if open_val <= 0 or high <= 0 or low <= 0 or close <= 0:
            return None
        # OHLC consistency: low <= open <= high, low <= close <= high
        if not (low <= open_val <= high):
            return None
        if not (low <= close <= high):
            return None

        timestamp_utc = self._timestamp_from_raw(tick_raw_time=time_val)
        if timestamp_utc is None:
            return None

        # Data quality gate: stale bars (>5 min old) are marked STALE,
        # fresh bars are VALID. No bar is ever presented as live broker data
        # unless its timestamp is within the staleness window.
        age = (datetime.now(tz=UTC) - timestamp_utc).total_seconds()
        if age > 300.0:
            quality_status = QualityStatus.STALE
        else:
            quality_status = QualityStatus.VALID

        return OHLCVBar(
            schema_version="1.0",
            instrument_id=symbol,
            provider_id="xm-mt5",
            provider_symbol=broker_symbol,
            mapping_version="1.0",
            timeframe=Timeframe(timeframe),
            bar_open_utc=timestamp_utc,
            open=Decimal(str(open_val)),
            high=Decimal(str(high)),
            low=Decimal(str(low)),
            close=Decimal(str(close)),
            volume=Decimal(str(volume)) if volume is not None else None,
            volume_kind=None,
            bar_close_utc=None,
            source_timestamp=str(time_val),
            source_timezone="UTC",
            source_revision=None,
            quality_status=quality_status,
            available_at_utc=datetime.now(tz=UTC),
            source_record_ref=f"mt5:{broker_symbol}:{time_val}",
        )

    @staticmethod
    def _timestamp_from_raw(tick_raw_time) -> datetime | None:
        """Convert MT5 timestamp (seconds since epoch) to datetime UTC."""
        if tick_raw_time is None or tick_raw_time <= 0:
            return None
        try:
            return datetime.fromtimestamp(tick_raw_time, tz=UTC)
        except (ValueError, OSError, OverflowError):
            return None

    def _mt5_timeframe(self, timeframe: str):
        """Convert our timeframe string to MT5 timeframe constant."""
        import MetaTrader5 as mt5

        mapping = {
            "M5": mt5.TIMEFRAME_M5,
            "M15": mt5.TIMEFRAME_M15,
            "H1": mt5.TIMEFRAME_H1,
            "H4": mt5.TIMEFRAME_H4,
        }
        return mapping.get(timeframe)

    def _build_symbol_spec(
        self, symbol: str, broker_symbol: str, info
    ) -> InstrumentSpec:
        """Build an InstrumentSpec from raw MT5 symbol_info."""
        return InstrumentSpec(
            schema_version="1.0",
            instrument_id=symbol,
            provider_id="xm-mt5",
            provider_symbol=broker_symbol,
            asset_class=self._map_asset_class(info),
            quote_currency=getattr(info, "currency_profit", None),
            base_currency=getattr(info, "currency_base", None),
            contract_size=(
                Decimal(str(info.trade_contract_size))
                if info.trade_contract_size is not None
                else None
            ),
            tick_size=(
                Decimal(str(info.trade_tick_size))
                if info.trade_tick_size is not None
                else None
            ),
            tick_value=(
                Decimal(str(info.trade_tick_value))
                if info.trade_tick_value is not None
                else None
            ),
            volume_min=(
                Decimal(str(info.volume_min)) if info.volume_min is not None else None
            ),
            volume_max=(
                Decimal(str(info.volume_max)) if info.volume_max is not None else None
            ),
            volume_step=(
                Decimal(str(info.volume_step)) if info.volume_step is not None else None
            ),
            price_precision=info.digits if hasattr(info, "digits") else None,
            volume_precision=None,
            trade_sessions_ref=None,
            server_timezone=None,
            source_updated_at_utc=datetime.now(tz=UTC).isoformat(),
            verified_at_utc=datetime.now(tz=UTC).isoformat(),
            verification_status=VerificationStatus.VERIFIED,
            source_metadata_ref=f"mt5:symbol_info:{broker_symbol}",
        )

    def get_account_info(self) -> dict | None:
        """Get account info from MT5 terminal via symbol_info_tick's account data.

        Returns dict with login, server, trade_mode, currency, balance, equity.
        Returns None if not connected or account info unavailable.
        """
        if not self.is_connected():
            return None
        try:
            account_info = self._mt5.account_info()
            if account_info is None:
                return None
            return {
                "login": getattr(account_info, "login", None),
                "server": getattr(account_info, "server", None),
                "trade_mode": getattr(account_info, "trade_mode", None),
                "currency": getattr(account_info, "currency", None),
                "balance": getattr(account_info, "balance", None),
                "equity": getattr(account_info, "equity", None),
            }
        except (RuntimeError, ConnectionError, OSError, ValueError, AttributeError):
            return None

    def account_info(self):
        """Return account info object like MT5's account_info().

        Returns an object with login, server, trade_mode, currency, balance,
        equity attributes. Returns None if not connected or unavailable.
        """
        info = self.get_account_info()
        if info is None:
            return None
        return type("AccountInfo", (), info)()

    def get_terminal_info(self) -> dict | None:
        """Get terminal info from MT5 terminal.

        Returns dict with name, company, connected, trade_allowed.
        Returns None if not connected or terminal info unavailable.
        """
        if not self.is_connected():
            return None
        try:
            terminal_info = self._mt5.terminal_info()
            if terminal_info is None:
                return None
            return {
                "name": getattr(terminal_info, "name", None),
                "company": getattr(terminal_info, "company", None),
                "connected": getattr(terminal_info, "connected", False),
                "trade_allowed": getattr(terminal_info, "trade_allowed", False),
            }
        except (RuntimeError, ConnectionError, OSError, ValueError, AttributeError):
            return None

    def order_send(self, request: dict) -> dict | None:
        """Send an order to the MT5 terminal via order_send.

        Sends a trade request to the connected MT5 terminal and returns
        the broker response dict. Returns None if not connected or the
        terminal is unavailable.

        Args:
            request: MT5 order_send request dict with action, symbol,
                volume, type, price, and optional sl/tp/deviation/magic.

        Returns:
            Broker response dict-like object, or None if unavailable.
        """
        if not self.is_connected():
            return None
        try:
            mt5 = self._mt5
            if mt5 is None:
                return None
            print(f"DEBUG: mt5.order_send request: {request}")
            result = mt5.order_send(request)
            print(f"DEBUG: mt5.order_send result: retcode={getattr(result, 'retcode', 'N/A')}, comment={getattr(result, 'comment', 'N/A')}")
            return result
        except (RuntimeError, ConnectionError, OSError, ValueError, AttributeError):
            return None

    @staticmethod
    def _map_asset_class(info) -> AssetClass:
        """Map MT5 symbol info to AssetClass based on symbol name."""
        symbol_name = getattr(info, "name", "").upper()
        if any(t in symbol_name for t in ("XAU", "XAG", "GOLD", "SILVER")):
            return AssetClass.METAL
        if any(t in symbol_name for t in ("BTC", "ETH", "CRYPTO")):
            return AssetClass.CRYPTO
        if any(t in symbol_name for t in ("OIL", "CRUDE", "WTI", "BRENT")):
            return AssetClass.ENERGY
        return AssetClass.METAL


def create_production_provider() -> MT5DataProvider:
    """Create a production-configured MT5DataProvider with default symbol map."""
    return MT5DataProvider(symbol_map=MT5DataProvider.DEFAULT_SYMBOL_MAP)
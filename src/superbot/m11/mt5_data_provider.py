"""M11 Phase 2.1 — MT5 live data provider.

Deterministic MT5 data provider:
- Connects to live MT5 terminal via MetaTrader5 Python package
- Maps canonical symbols (XAUUSD, XAGUSD, BTCUSD, ETHUSD, USOIL) to MT5
  symbol names (GOLD.i#, SILVER.i#, BTCUSD#, ETHUSD#, OILCash#)
- Returns TickData with explicit source labeling ("broker_feed") and timestamp
- Data state: "live", "stale", "unavailable" based on freshness and price validity
- Stdlib-only except for MetaTrader5 import (lazy, import-safe)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import ClassVar


class DataState(str, Enum):
    """Data freshness state for a market tick."""

    LIVE = "live"
    STALE = "stale"
    UNAVAILABLE = "unavailable"


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

        return self._build_tick(symbol, broker_symbol, tick_data)

    def _build_tick(
        self, symbol: str, broker_symbol: str, tick_data: dict
    ) -> TickData:
        """Build a TickData from raw MT5 tick info, determining data state."""

        bid = tick_data.get("bid")
        ask = tick_data.get("ask")
        last = tick_data.get("last")
        volume = tick_data.get("volume")

        # Determine data state
        data_state = DataState.LIVE

        if bid is None or ask is None or bid <= 0 or ask <= 0:
            data_state = DataState.UNAVAILABLE
            timestamp_utc = None
        else:
            timestamp_utc = self._timestamp_from_raw(tick_raw_time=tick_data.get("time"))
            if timestamp_utc is None:
                data_state = DataState.UNAVAILABLE
            else:
                age = (datetime.now(tz=UTC) - timestamp_utc).total_seconds()
                if age > 60.0:
                    data_state = DataState.STALE

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

    @staticmethod
    def _timestamp_from_raw(tick_raw_time) -> datetime | None:
        """Convert MT5 timestamp (seconds since epoch) to datetime UTC."""
        if tick_raw_time is None or tick_raw_time <= 0:
            return None
        try:
            return datetime.fromtimestamp(tick_raw_time, tz=UTC)
        except (ValueError, OSError, OverflowError):
            return None


def create_production_provider() -> MT5DataProvider:
    """Create a production-configured MT5DataProvider with default symbol map."""
    return MT5DataProvider(symbol_map=MT5DataProvider.DEFAULT_SYMBOL_MAP)
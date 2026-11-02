"""V2.4 — Storage and Replay of live market data.

Deterministic market data storage service:
- Stores tick data and OHLCV bars with source/acquisition timestamps
- Distinguishes historical broker data from currently live data
- All stored data labeled with source ("broker_feed") — never synthetic
- Stdlib-only; no import-time network/database activity
- Read-only: no order submission or data fabrication
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum


class DataFreshness(str, Enum):
    """Freshness state for stored market data."""
    LIVE = "live"          # Currently streaming from broker feed
    HISTORICAL = "historical"  # Stored historical data, not current feed


@dataclass(frozen=True)
class StoredMarketData:
    """A single stored market data record."""
    symbol: str
    broker_symbol: str
    bid: float | None
    ask: float | None
    last: float | None
    volume: float | None
    source_timestamp: datetime
    source: str
    acquisition_timestamp: datetime
    data_freshness: DataFreshness = DataFreshness.HISTORICAL


@dataclass(frozen=True)
class StoredOHLCVBar:
    """A single stored OHLCV bar."""
    instrument_id: str
    provider_symbol: str
    timeframe: str
    bar_open_utc: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal | None
    source_timestamp: datetime
    source: str
    acquisition_timestamp: datetime
    data_freshness: DataFreshness = DataFreshness.HISTORICAL


@dataclass(frozen=True)
class StoredSignal:
    """A single stored signal decision (signal or rejection)."""
    symbol: str
    broker_symbol: str
    signal_type: str | None          # "entry_long" | "entry_short" | None (rejection)
    entry_price: Decimal | None
    stop_price: Decimal | None
    depth_pct: Decimal | None
    data_state: str                  # "live" | "stale" | "unavailable" | "invalid"
    source: str                      # "broker_feed"
    timestamp_utc: datetime
    rejection_reason: str | None     # "stale_data" | "unavailable_data" | "no_signal" | None


class MarketDataStorage:
    """Storage and replay service for live market data.

    Persists real acquired market data locally with source and acquisition
    timestamps. All stored data is labeled HISTORICAL — never presented
    as live broker data. Read-only: no order submission or data fabrication.
    """

    def __init__(self) -> None:
        self._ticks: list[StoredMarketData] = []
        self._bars: list[StoredOHLCVBar] = []
        self._signals: list[StoredSignal] = []

    def store_tick(
        self,
        symbol: str,
        broker_symbol: str,
        bid: float | None,
        ask: float | None,
        last: float | None,
        volume: float | None,
        source_timestamp: datetime,
        source: str = "broker_feed",
    ) -> None:
        """Store a tick quote with acquisition timestamp."""
        acquisition_time = datetime.now(tz=UTC)
        self._ticks.append(
            StoredMarketData(
                symbol=symbol,
                broker_symbol=broker_symbol,
                bid=bid,
                ask=ask,
                last=last,
                volume=volume,
                source_timestamp=source_timestamp,
                source=source,
                acquisition_timestamp=acquisition_time,
                data_freshness=DataFreshness.HISTORICAL,
            )
        )

    def store_bar(
        self,
        instrument_id: str,
        provider_symbol: str,
        timeframe: str,
        bar_open_utc: datetime,
        open: Decimal,
        high: Decimal,
        low: Decimal,
        close: Decimal,
        volume: Decimal | None,
        source_timestamp: datetime,
        source: str = "broker_feed",
    ) -> None:
        """Store an OHLCV bar with acquisition timestamp."""
        acquisition_time = datetime.now(tz=UTC)
        self._bars.append(
            StoredOHLCVBar(
                instrument_id=instrument_id,
                provider_symbol=provider_symbol,
                timeframe=timeframe,
                bar_open_utc=bar_open_utc,
                open=open,
                high=high,
                low=low,
                close=close,
                volume=volume,
                source_timestamp=source_timestamp,
                source=source,
                acquisition_timestamp=acquisition_time,
                data_freshness=DataFreshness.HISTORICAL,
            )
        )

    def get_ticks(
        self,
        symbol: str,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[StoredMarketData]:
        """Retrieve stored ticks for a symbol, optionally filtered by time range."""
        ticks = [t for t in self._ticks if t.symbol == symbol]
        if start is not None:
            ticks = [t for t in ticks if t.source_timestamp >= start]
        if end is not None:
            ticks = [t for t in ticks if t.source_timestamp <= end]
        return ticks

    def get_bars(
        self,
        instrument_id: str,
        timeframe: str,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[StoredOHLCVBar]:
        """Retrieve stored OHLCV bars for a symbol/timeframe, optionally filtered by time range."""
        bars = [
            b for b in self._bars
            if b.instrument_id == instrument_id and b.timeframe == timeframe
        ]
        if start is not None:
            bars = [b for b in bars if b.bar_open_utc >= start]
        if end is not None:
            bars = [b for b in bars if b.bar_open_utc <= end]
        return bars


    def store_signal(
        self,
        symbol: str,
        broker_symbol: str,
        signal_type: str | None,
        entry_price: Decimal | None,
        stop_price: Decimal | None,
        depth_pct: Decimal | None,
        data_state: str,
        source: str,
        timestamp_utc: datetime,
        rejection_reason: str | None,
    ) -> None:
        """Store a signal decision (signal or rejection) with provenance."""
        self._signals.append(
            StoredSignal(
                symbol=symbol,
                broker_symbol=broker_symbol,
                signal_type=signal_type,
                entry_price=entry_price,
                stop_price=stop_price,
                depth_pct=depth_pct,
                data_state=data_state,
                source=source,
                timestamp_utc=timestamp_utc,
                rejection_reason=rejection_reason,
            )
        )

    def get_signal_history(self) -> list[StoredSignal]:
        """Retrieve all stored signal decisions (signals and rejections)."""
        return list(self._signals)


def create_production_storage() -> MarketDataStorage:
    """Create a production-configured MarketDataStorage instance."""
    return MarketDataStorage()
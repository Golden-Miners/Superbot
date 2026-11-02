"""V2.4 — Storage and Replay of live market data.

Deterministic market data storage service:
- Stores tick data and OHLCV bars with source/acquisition timestamps
- Distinguishes historical broker data from currently live data
- All stored data labeled with source ("broker_feed") — never synthetic
- Stdlib-only; no import-time network/database activity
- Read-only: no order submission or data fabrication
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path


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

    Data is persisted to a JSON file so it survives application restarts.
    """

    def __init__(self, storage_path: str | Path | None = None) -> None:
        self.storage_path = Path(storage_path) if storage_path else None
        self._ticks: list[StoredMarketData] = []
        self._bars: list[StoredOHLCVBar] = []
        self._signals: list[StoredSignal] = []
        if self.storage_path is not None and self.storage_path.exists():
            self._load()

    def _load(self) -> None:
        """Load stored data from JSON file if it exists."""
        if not self.storage_path or not self.storage_path.exists():
            return
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for t in data.get("ticks", []):
                self._ticks.append(
                    StoredMarketData(
                        symbol=t["symbol"],
                        broker_symbol=t["broker_symbol"],
                        bid=t["bid"],
                        ask=t["ask"],
                        last=t["last"],
                        volume=t["volume"],
                        source_timestamp=datetime.fromisoformat(t["source_timestamp"]),
                        source=t["source"],
                        acquisition_timestamp=datetime.fromisoformat(t["acquisition_timestamp"]),
                        data_freshness=DataFreshness(t["data_freshness"]),
                    )
                )
            for b in data.get("bars", []):
                self._bars.append(
                    StoredOHLCVBar(
                        instrument_id=b["instrument_id"],
                        provider_symbol=b["provider_symbol"],
                        timeframe=b["timeframe"],
                        bar_open_utc=datetime.fromisoformat(b["bar_open_utc"]),
                        open=Decimal(b["open"]),
                        high=Decimal(b["high"]),
                        low=Decimal(b["low"]),
                        close=Decimal(b["close"]),
                        volume=Decimal(b["volume"]) if b["volume"] is not None else None,
                        source_timestamp=datetime.fromisoformat(b["source_timestamp"]),
                        source=b["source"],
                        acquisition_timestamp=datetime.fromisoformat(b["acquisition_timestamp"]),
                        data_freshness=DataFreshness(b["data_freshness"]),
                    )
                )
            for s in data.get("signals", []):
                self._signals.append(
                    StoredSignal(
                        symbol=s["symbol"],
                        broker_symbol=s["broker_symbol"],
                        signal_type=s["signal_type"],
                        entry_price=Decimal(s["entry_price"]) if s["entry_price"] is not None else None,
                        stop_price=Decimal(s["stop_price"]) if s["stop_price"] is not None else None,
                        depth_pct=Decimal(s["depth_pct"]) if s["depth_pct"] is not None else None,
                        data_state=s["data_state"],
                        source=s["source"],
                        timestamp_utc=datetime.fromisoformat(s["timestamp_utc"]),
                        rejection_reason=s["rejection_reason"],
                    )
                )
            # Deduplicate bars by (instrument_id, timeframe, bar_open_utc) on load
            seen_bar_keys: set[tuple[str, str, datetime]] = set()
            deduped_bars: list[StoredOHLCVBar] = []
            for b in self._bars:
                key = (b.instrument_id, b.timeframe, b.bar_open_utc)
                if key not in seen_bar_keys:
                    seen_bar_keys.add(key)
                    deduped_bars.append(b)
            self._bars = deduped_bars
        except (json.JSONDecodeError, OSError, KeyError, ValueError):
            # Corrupt or unreadable file — start empty
            self._ticks = []
            self._bars = []
            self._signals = []

    def _save(self) -> None:
        """Persist all stored data to JSON file."""
        if self.storage_path is None:
            return
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "ticks": [
                {
                    "symbol": t.symbol,
                    "broker_symbol": t.broker_symbol,
                    "bid": t.bid,
                    "ask": t.ask,
                    "last": t.last,
                    "volume": t.volume,
                    "source_timestamp": t.source_timestamp.isoformat(),
                    "source": t.source,
                    "acquisition_timestamp": t.acquisition_timestamp.isoformat(),
                    "data_freshness": t.data_freshness.value,
                }
                for t in self._ticks
            ],
            "bars": [
                {
                    "instrument_id": b.instrument_id,
                    "provider_symbol": b.provider_symbol,
                    "timeframe": b.timeframe,
                    "bar_open_utc": b.bar_open_utc.isoformat(),
                    "open": str(b.open),
                    "high": str(b.high),
                    "low": str(b.low),
                    "close": str(b.close),
                    "volume": str(b.volume) if b.volume is not None else None,
                    "source_timestamp": b.source_timestamp.isoformat(),
                    "source": b.source,
                    "acquisition_timestamp": b.acquisition_timestamp.isoformat(),
                    "data_freshness": b.data_freshness.value,
                }
                for b in self._bars
            ],
            "signals": [
                {
                    "symbol": s.symbol,
                    "broker_symbol": s.broker_symbol,
                    "signal_type": s.signal_type,
                    "entry_price": str(s.entry_price) if s.entry_price is not None else None,
                    "stop_price": str(s.stop_price) if s.stop_price is not None else None,
                    "depth_pct": str(s.depth_pct) if s.depth_pct is not None else None,
                    "data_state": s.data_state,
                    "source": s.source,
                    "timestamp_utc": s.timestamp_utc.isoformat(),
                    "rejection_reason": s.rejection_reason,
                }
                for s in self._signals
            ],
        }
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

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
        self._save()

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
        # Deduplicate: don't store duplicate bars (same instrument, timeframe, timestamp)
        for existing in self._bars:
            if (existing.instrument_id == instrument_id
                    and existing.timeframe == timeframe
                    and existing.bar_open_utc == bar_open_utc):
                return
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
        self._save()

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
        self._save()

    def get_signal_history(self) -> list[StoredSignal]:
        """Retrieve all stored signal decisions (signals and rejections)."""
        return list(self._signals)


def create_production_storage() -> MarketDataStorage:
    """Create a production-configured MarketDataStorage instance."""
    return MarketDataStorage()
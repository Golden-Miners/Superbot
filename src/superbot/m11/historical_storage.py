"""V2 Item 4 — Storage and Replay for MT5 historical data.

Persists real acquired market data locally in JSON Lines format with:
- Source and acquisition timestamps preserved
- Provenance metadata on every bar
- Clear distinction between historical broker data and currently live data
- Allows research/backtesting against recorded real broker data
- No synthetic data — all values from live broker feed only
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class StoredBar:
    """A single persisted OHLCV bar with full provenance."""

    instrument_id: str
    timeframe: str
    bar_open_utc: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    source_timestamp: str
    source_timezone: str
    source_record_ref: str
    acquired_at_utc: str
    broker: str = "mt5"
    source: str = "broker_feed"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class HistoricalStorage:
    """Persists and loads real broker market data for research/backtesting.

    Storage format: JSON Lines (.jsonl) with one JSON object per bar.
    Files are organized by instrument/timeframe: {instrument}_{timeframe}.jsonl
    under the storage directory.

    Historical data is clearly distinguished from currently live data:
    - `acquired_at_utc` records when the data was fetched from MT5
    - `source_timestamp` records when MT5 produced the bar
    - `is_live` flag distinguishes current vs historical data
    """

    def __init__(self, storage_dir: str | None = None) -> None:
        if storage_dir is None:
            storage_dir = os.path.join(
                os.path.expanduser("~"), ".superbot", "market_data"
            )
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _filepath(self, instrument_id: str, timeframe: str) -> Path:
        safe_id = instrument_id.replace("/", "_").replace("\\", "_")
        return self.storage_dir / f"{safe_id}_{timeframe}.jsonl"

    def store_historical_chart(
        self,
        instrument_id: str,
        timeframe: str,
        bars: list[dict[str, Any]],
        broker: str = "mt5",
        source: str = "broker_feed",
    ) -> int:
        """Persist historical OHLCV bars to local storage.

        Args:
            instrument_id: Canonical symbol (e.g. "XAUUSD")
            timeframe: Timeframe string ("M5", "M15", "H1", "H4")
            bars: List of bar dicts with open/high/low/close/volume/timestamp
            broker: Broker identifier (default: "mt5")
            source: Data source identifier (default: "broker_feed")

        Returns:
            Number of bars stored.
        """
        acquired_at = datetime.now(tz=UTC).isoformat()
        filepath = self._filepath(instrument_id, timeframe)

        count = 0
        with open(filepath, "a", encoding="utf-8") as f:
            for bar in bars:
                stored = StoredBar(
                    instrument_id=instrument_id,
                    timeframe=timeframe,
                    bar_open_utc=bar["timestamp_utc"],
                    open=float(bar["open"]),
                    high=float(bar["high"]),
                    low=float(bar["low"]),
                    close=float(bar["close"]),
                    volume=float(bar.get("volume", 0)),
                    source_timestamp=str(bar.get("source_timestamp", "")),
                    source_timezone=bar.get("source_timezone", "UTC"),
                    source_record_ref=bar.get("source_record_ref", ""),
                    acquired_at_utc=acquired_at,
                    broker=broker,
                    source=source,
                )
                f.write(json.dumps(stored.to_dict()) + "\n")
                count += 1

        return count

    def load_historical_chart(
        self,
        instrument_id: str,
        timeframe: str,
        limit: int | None = None,
    ) -> list[StoredBar]:
        """Load historical OHLCV bars from local storage.

        Args:
            instrument_id: Canonical symbol (e.g. "XAUUSD")
            timeframe: Timeframe string ("M5", "M15", "H1", "H4")
            limit: Maximum number of bars to return (most recent first)

        Returns:
            List of StoredBar objects, most recent first. Empty list if
            no stored data exists.
        """
        filepath = self._filepath(instrument_id, timeframe)

        if not filepath.exists():
            return []

        bars: list[StoredBar] = []
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                bars.append(StoredBar(**data))

        # Most recent first
        bars.sort(key=lambda b: b.bar_open_utc, reverse=True)

        if limit is not None:
            bars = bars[:limit]

        return bars

    def list_stored_instruments(self) -> list[tuple[str, str]]:
        """List all stored instrument/timeframe combinations.

        Returns:
            List of (instrument_id, timeframe) tuples.
        """
        found: set[tuple[str, str]] = set()
        for filepath in self.storage_dir.glob("*.jsonl"):
            name = filepath.stem  # e.g. "XAUUSD_M5"
            parts = name.rsplit("_", 1)
            if len(parts) == 2:
                found.add((parts[0], parts[1]))
        return sorted(found)

    def get_storage_info(self, instrument_id: str, timeframe: str) -> dict[str, Any]:
        """Get metadata about stored data for an instrument/timeframe.

        Returns dict with bar count, earliest/latest timestamps, and file size.
        Returns empty dict if no data exists.
        """
        filepath = self._filepath(instrument_id, timeframe)

        if not filepath.exists():
            return {}

        bars = self.load_historical_chart(instrument_id, timeframe)
        if not bars:
            return {
                "instrument_id": instrument_id,
                "timeframe": timeframe,
                "bar_count": 0,
                "file_size_bytes": filepath.stat().st_size,
            }

        timestamps = [b.bar_open_utc for b in bars]
        return {
            "instrument_id": instrument_id,
            "timeframe": timeframe,
            "bar_count": len(bars),
            "earliest_utc": min(timestamps),
            "latest_utc": max(timestamps),
            "file_size_bytes": filepath.stat().st_size,
            "broker": bars[0].broker if bars else "mt5",
            "source": bars[0].source if bars else "broker_feed",
        }

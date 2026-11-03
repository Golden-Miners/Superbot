"""V2 Item 2 — MT5 Historical Chart Data Provider.

Wraps MT5DataProvider.get_ohlcv() to serve historical chart data with full
provenance metadata. Every bar carries broker/source, symbol, timestamp,
and data freshness information. No synthetic data — all values from live
MT5 terminal only.

Supports timeframes: M5, M15, H1, H4.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from superbot.m11.mt5_data_provider import MT5DataProvider


class DataFreshness(str, Enum):
    """Data freshness state for chart bars."""

    LIVE = "live"
    STALE = "stale"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class HistoricalChartBar:
    """A single OHLCV bar with provenance metadata."""

    symbol: str
    broker_symbol: str
    source: str
    timestamp_utc: str
    data_freshness: DataFreshness
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class HistoricalChartData:
    """Historical chart data with full provenance metadata."""

    instrument_id: str
    timeframe: str
    source: str
    broker: str
    timestamp_utc: str
    data_freshness: DataFreshness
    bars: list[HistoricalChartBar]

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for API responses."""
        return {
            "instrument_id": self.instrument_id,
            "timeframe": self.timeframe,
            "source": self.source,
            "broker": self.broker,
            "timestamp_utc": self.timestamp_utc,
            "data_freshness": self.data_freshness.value,
            "bars": [
                {
                    "symbol": bar.symbol,
                    "broker_symbol": bar.broker_symbol,
                    "source": bar.source,
                    "timestamp_utc": bar.timestamp_utc,
                    "data_freshness": bar.data_freshness.value,
                    "open": bar.open,
                    "high": bar.high,
                    "low": bar.low,
                    "close": bar.close,
                    "volume": bar.volume,
                }
                for bar in self.bars
            ],
        }


class HistoricalChartProvider:
    """Live market data provider for historical chart data via MT5.

    Wraps MT5DataProvider.get_ohlcv() and returns OHLCV bars with full
    provenance metadata. No synthetic data — all values from live broker
    feed only.
    """

    SUPPORTED_TIMEFRAMES: list[str] = ["M5", "M15", "H1", "H4"]

    def __init__(self, mt5_data_provider: MT5DataProvider | None = None) -> None:
        self.mt5_data_provider = mt5_data_provider
        self._connected = False

    def connect(self) -> bool:
        """Connect to the MT5 data provider.

        Returns True if connection succeeded.
        """
        if self.mt5_data_provider is not None:
            self._connected = self.mt5_data_provider.connect()
        else:
            self._connected = False
        return self._connected

    def disconnect(self) -> None:
        """Disconnect from MT5 data provider."""
        if self.mt5_data_provider is not None:
            self.mt5_data_provider.disconnect()
        self._connected = False

    def is_connected(self) -> bool:
        """Return True if connected to MT5 data provider."""
        return self._connected and self.mt5_data_provider is not None

    def get_historical_chart(
        self,
        instrument_id: str,
        timeframe: str,
        count: int = 100,
    ) -> HistoricalChartData:
        """Get historical chart data for an instrument and timeframe.

        Returns HistoricalChartData with full provenance metadata.
        Returns empty result (unavailable) when not connected or no data.

        Args:
            instrument_id: Canonical symbol (e.g. "XAUUSD")
            timeframe: Timeframe string ("M5", "M15", "H1", "H4")
            count: Number of bars to retrieve (most recent first)

        Returns:
            HistoricalChartData with provenance metadata. Empty bars list
            if not connected or no data available.
        """
        if timeframe not in self.SUPPORTED_TIMEFRAMES:
            raise ValueError(
                f"Unsupported timeframe: {timeframe}. "
                f"Supported: {', '.join(self.SUPPORTED_TIMEFRAMES)}"
            )

        if not self.is_connected():
            return HistoricalChartData(
                instrument_id=instrument_id,
                timeframe=timeframe,
                source="broker_feed",
                broker="mt5",
                timestamp_utc=datetime.now(tz=UTC).isoformat(),
                data_freshness=DataFreshness.UNAVAILABLE,
                bars=[],
            )

        mt5_bars = self.mt5_data_provider.get_ohlcv(
            instrument_id, timeframe, count=count
        )

        bars: list[HistoricalChartBar] = []
        for bar in mt5_bars:
            freshness = self._determine_freshness(bar.bar_open_utc)
            bars.append(
                HistoricalChartBar(
                    symbol=bar.instrument_id,
                    broker_symbol=bar.provider_symbol,
                    source=bar.source,
                    timestamp_utc=bar.bar_open_utc.isoformat(),
                    data_freshness=freshness,
                    open=float(bar.open),
                    high=float(bar.high),
                    low=float(bar.low),
                    close=float(bar.close),
                    volume=float(bar.volume) if bar.volume else 0.0,
                )
            )

        # Determine overall freshness from the most recent bar
        if bars:
            overall_freshness = bars[0].data_freshness
            latest_timestamp = bars[0].timestamp_utc
        else:
            overall_freshness = DataFreshness.UNAVAILABLE
            latest_timestamp = datetime.now(tz=UTC).isoformat()

        return HistoricalChartData(
            instrument_id=instrument_id,
            timeframe=timeframe,
            source="broker_feed",
            broker="mt5",
            timestamp_utc=latest_timestamp,
            data_freshness=overall_freshness,
            bars=bars,
        )

    @staticmethod
    def _determine_freshness(bar_timestamp: datetime) -> DataFreshness:
        """Determine data freshness from bar timestamp."""
        if bar_timestamp.tzinfo is None:
            return DataFreshness.UNAVAILABLE

        now = datetime.now(tz=UTC)
        age_seconds = (now - bar_timestamp).total_seconds()

        if age_seconds < -60.0:
            return DataFreshness.UNAVAILABLE
        if age_seconds > 60.0:
            return DataFreshness.STALE
        return DataFreshness.LIVE

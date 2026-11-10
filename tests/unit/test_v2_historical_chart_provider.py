"""RED tests for V2 Item 2 — MT5 Historical Chart Data Provider.

Covers:
- HistoricalChartProvider wraps MT5DataProvider.get_ohlcv()
- Every OHLCV bar carries provenance: broker/source, symbol, timestamp, freshness
- Supports timeframes: M5, M15, H1, H4
- Returns OHLCV bars from live MT5 terminal (no synthetic data)
- Rejects unknown timeframes
- Returns empty list when not connected or no data available

No live trading authorized. Read-only market data only.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from superbot.m11.charts import ohlcv_chart
from superbot.m11.historical_chart_provider import (
    HistoricalChartProvider,
    HistoricalChartData,
    DataFreshness,
)
from superbot.m11.mt5_data_provider import DataState, MT5DataProvider


# --- Fake MT5DataProvider for testing without a live terminal ---
class FakeMT5DataProvider:
    """Fake MT5DataProvider for testing without a live terminal."""

    def __init__(self):
        self.connect_called = False
        self.disconnect_called = False

    def connect(self):
        self.connect_called = True
        return True

    def disconnect(self):
        self.disconnect_called = True

    def is_connected(self):
        return True

    def get_tick(self, symbol):
        from superbot.m11.mt5_data_provider import DataState, TickData

        return TickData(
            symbol=symbol,
            broker_symbol="GOLD.i#",
            bid=3875.75,
            ask=3875.99,
            last=3875.87,
            volume=1.0,
            timestamp_utc=datetime.now(tz=UTC),
            source="broker_feed",
            data_state=DataState.LIVE,
        )

    def get_ohlcv(self, symbol, timeframe, count=100):
        from superbot.contracts.ohlcv import OHLCVBar, QualityStatus, Timeframe

        now = datetime.now(tz=UTC)
        # Align to 5-minute boundary
        aligned = now.replace(minute=(now.minute // 5) * 5, second=0, microsecond=0)

        bars = []
        for i in range(count):
            bar_time = aligned - timedelta(minutes=i * 5)
            bars.append(
                OHLCVBar(
                    schema_version="1.0",
                    instrument_id=symbol,
                    provider_id="xm-mt5",
                    provider_symbol="GOLD.i#",
                    mapping_version="1.0",
                    timeframe=Timeframe(timeframe),
                    bar_open_utc=bar_time,
                    open=Decimal("3875.75"),
                    high=Decimal("3875.99"),
                    low=Decimal("3875.50"),
                    close=Decimal("3875.90"),
                    volume=Decimal("1.0"),
                    volume_kind=None,
                    bar_close_utc=None,
                    source_timestamp=str(bar_time.timestamp()),
                    source_timezone="UTC",
                    source_revision=None,
                    quality_status=QualityStatus.VALID,
                    available_at_utc=bar_time,
                    source_record_ref=f"mt5:GOLD.i#{bar_time.timestamp()}",
                )
            )
        return bars

    def get_symbol_spec(self, symbol):
        return None


# --- RED tests ---


def test_historical_chart_provider_creates():
    """HistoricalChartProvider can be instantiated with default timeframes."""
    provider = HistoricalChartProvider()
    assert provider is not None
    assert provider.supported_timeframes == ["M5", "M15", "H1", "H4"]


def test_get_historical_chart_returns_bars():
    """get_historical_chart returns OHLCV bars with provenance metadata."""
    mt5_provider = FakeMT5DataProvider()
    provider = HistoricalChartProvider(mt5_data_provider=mt5_provider)
    assert provider.connect() is True

    chart_data = provider.get_historical_chart("XAUUSD", "M5", count=10)

    assert chart_data is not None
    assert chart_data.instrument_id == "XAUUSD"
    assert chart_data.source == "broker_feed"
    assert chart_data.timeframe == "M5"
    assert len(chart_data.bars) > 0

    for bar in chart_data.bars:
        assert bar.symbol == "XAUUSD"
        assert bar.broker_symbol == "GOLD.i#"
        assert bar.source == "broker_feed"
        assert bar.timestamp_utc is not None
        assert bar.data_freshness.value in ("live", "stale", "unavailable")
        assert bar.open > 0
        assert bar.high > 0
        assert bar.low > 0
        assert bar.close > 0


def test_get_historical_chart_rejects_unknown_timeframe():
    """get_historical_chart raises ValueError for unsupported timeframe."""
    mt5_provider = FakeMT5DataProvider()
    provider = HistoricalChartProvider(mt5_data_provider=mt5_provider)
    provider.connect()

    with pytest.raises(ValueError, match="unsupported timeframe"):
        provider.get_historical_chart("XAUUSD", "M30", count=10)


def test_get_historical_chart_not_connected_returns_empty():
    """get_historical_chart returns empty result when not connected."""
    mt5_provider = FakeMT5DataProvider()
    provider = HistoricalChartProvider(mt5_data_provider=mt5_provider)
    # Don't call connect()

    chart_data = provider.get_historical_chart("XAUUSD", "M5", count=10)

    assert chart_data is not None
    assert len(chart_data.bars) == 0
    assert chart_data.data_freshness == DataFreshness.UNAVAILABLE


def test_get_historical_chart_provenance_metadata():
    """Every bar carries broker/source, symbol, timestamp, freshness metadata."""
    mt5_provider = FakeMT5DataProvider()
    provider = HistoricalChartProvider(mt5_data_provider=mt5_provider)
    provider.connect()

    chart_data = provider.get_historical_chart("XAUUSD", "M5", count=5)

    assert chart_data.broker == "mt5"
    assert chart_data.source == "broker_feed"
    assert chart_data.instrument_id == "XAUUSD"
    assert chart_data.timestamp_utc is not None
    assert chart_data.data_freshness in ("live", "stale", "unavailable")
    assert chart_data.data_freshness != "live" or chart_data.timestamp_utc is not None


def test_historical_chart_data_to_dict():
    """HistoricalChartData can be serialized to dict for API responses."""
    mt5_provider = FakeMT5DataProvider()
    provider = HistoricalChartProvider(mt5_data_provider=mt5_provider)
    provider.connect()

    chart_data = provider.get_historical_chart("XAUUSD", "M5", count=3)
    data_dict = chart_data.to_dict()

    assert "instrument_id" in data_dict
    assert "timeframe" in data_dict
    assert "source" in data_dict
    assert "broker" in data_dict
    assert "data_freshness" in data_dict
    assert "bars" in data_dict
    assert len(data_dict["bars"]) == 3


def test_chart_generation_with_historical_data():
    """ohlcv_chart can generate a chart from HistoricalChartData."""
    mt5_provider = FakeMT5DataProvider()
    provider = HistoricalChartProvider(mt5_data_provider=mt5_provider)
    provider.connect()

    chart_data = provider.get_historical_chart("XAUUSD", "M5", count=5)

    fig = ohlcv_chart(
        symbol=chart_data.instrument_id,
        timeframe=chart_data.timeframe,
        ohlcv=[
            {
                "t": bar.timestamp_utc,
                "o": bar.open,
                "h": bar.high,
                "l": bar.low,
                "c": bar.close,
                "v": bar.volume,
            }
            for bar in chart_data.bars
        ],
        source=chart_data.source,
    )

    assert fig is not None

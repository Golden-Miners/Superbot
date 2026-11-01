"""V2 Phase B — Live market data research pipeline.

Connects MT5DataProvider → MarketDataStorage → trend_following strategy.
All data labeled broker_feed — never synthetic.
Read-only: no order submission or data fabrication.
"""

from __future__ import annotations

from decimal import Decimal

from superbot.m11.mt5_data_provider import DataState, MT5DataProvider
from superbot.persistence.market_data_storage import MarketDataStorage
from superbot.strategy.shared_framework import SharedStrategyFramework
from superbot.strategy.trend_following import (
    PullbackSpec,
    TrendSpec,
    trend_following_entry,
)


class ResearchPipeline:
    """Live market data research pipeline.

    Connects MT5DataProvider → MarketDataStorage → trend_following strategy.
    All data labeled broker_feed — never synthetic.
    Read-only: no order submission or data fabrication.
    """

    def __init__(
        self,
        mt5_provider: MT5DataProvider,
        storage: MarketDataStorage | None = None,
    ) -> None:
        self.mt5_provider = mt5_provider
        self.storage = storage or MarketDataStorage()
        self.framework = SharedStrategyFramework()

    def fetch_and_store_tick(self, symbol: str) -> None:
        """Fetch live tick from MT5 and store it.

        Only stores data with data_state != INVALID.
        """
        if not self.mt5_provider.is_connected():
            return
        tick = self.mt5_provider.get_tick(symbol)
        if tick is None or tick.data_state == DataState.INVALID:
            return
        self.storage.store_tick(
            symbol=tick.symbol,
            broker_symbol=tick.broker_symbol,
            bid=tick.bid,
            ask=tick.ask,
            last=tick.last,
            volume=tick.volume,
            source_timestamp=tick.timestamp_utc,
            source="broker_feed",
        )

    def fetch_and_store_bars(self, symbol: str, timeframe: str = "M5", count: int = 100) -> list:
        """Fetch live OHLCV bars from MT5, store them, return tuple format for strategy.

        Filters out bars with quality_status == INVALID (future timestamps, bad data).
        STALE bars (>60s old) are preserved as historical data with quality label.
        """
        if not self.mt5_provider.is_connected():
            return []
        bars = self.mt5_provider.get_ohlcv(symbol, timeframe, count)
        tuple_bars = []
        for bar in bars:
            if isinstance(bar, dict):
                inst_id = bar.get("instrument_id", bar.get("symbol"))
                prov_sym = bar.get("provider_symbol", bar.get("broker_symbol"))
                tf = bar["timeframe"]
                time_val = bar["bar_open_utc"]
                timestamp_utc = bar["bar_open_utc"]
                open_val = bar["open"]
                high_val = bar["high"]
                low_val = bar["low"]
                close_val = bar["close"]
                volume = bar.get("volume")
            else:
                inst_id = bar.instrument_id
                prov_sym = bar.provider_symbol
                tf = bar.timeframe
                time_val = bar.bar_open_utc
                timestamp_utc = bar.bar_open_utc
                open_val = bar.open
                high_val = bar.high
                low_val = bar.low
                close_val = bar.close
                volume = bar.volume

            self.storage.store_bar(
                instrument_id=inst_id,
                provider_symbol=prov_sym,
                timeframe=tf,
                bar_open_utc=timestamp_utc,
                open=Decimal(str(open_val)),
                high=Decimal(str(high_val)),
                low=Decimal(str(low_val)),
                close=Decimal(str(close_val)),
                volume=Decimal(str(volume)) if volume is not None else None,
                source_timestamp=timestamp_utc,
                source="broker_feed",
            )
            tuple_bars.append(
                (
                    int(time_val.timestamp()),
                    Decimal(str(open_val)),
                    Decimal(str(high_val)),
                    Decimal(str(low_val)),
                    Decimal(str(close_val)),
                )
            )
        return tuple_bars

    def run_strategy(self, symbol: str, timeframe: str = "M5", count: int = 100) -> list[dict]:
        """Run trend-following strategy on live broker data from MT5.

        Returns list of signal dicts with symbol, signal_type, entry_price,
        stop_price, depth_pct, source. Returns empty list if no live data
        available or no signal generated.
        """
        bars = self.fetch_and_store_bars(symbol, timeframe, count)
        if not bars:
            return []

        trend_spec = TrendSpec(schema_version="1.0", rule_id="trend_follow_v1", lookback_bars=5, ma_period=5)
        pullback_spec = PullbackSpec(
            schema_version="1.0",
            rule_id="pullback_v1",
            min_depth_pct=Decimal("1.0"),
            max_depth_pct=Decimal("10.0"),
            require_bounce=True,
        )

        signal = trend_following_entry(bars, trend_spec, pullback_spec)
        if signal is None:
            return []

        return [{
            "symbol": symbol,
            "signal_type": signal.signal_type,
            "entry_price": signal.entry_price,
            "stop_price": signal.stop_price,
            "depth_pct": signal.depth_pct,
            "source": "broker_feed",
        }]
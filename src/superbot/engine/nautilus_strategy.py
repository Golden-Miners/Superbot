"""NautilusTrader strategy for M3.3 equivalence testing."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from nautilus_trader.config import StrategyConfig
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.trading.strategy import Strategy


class RefStrategyConfig(StrategyConfig, frozen=True):
    instrument_id: InstrumentId
    bar_type: Any  # BarType
    trade_size: Decimal
    stop: Decimal
    target: Decimal
    entry_index: int


class RefStrategy(Strategy):
    def __init__(self, config: RefStrategyConfig) -> None:
        super().__init__(config)
        self._bar_type = config.bar_type
        self._bar_index = -1
        self._entered = False
        self._exited = False
        self.events: list = []

    def on_start(self) -> None:
        self.subscribe_bars(bar_type=self._bar_type)

    def on_bar(self, bar) -> None:
        self._bar_index += 1

        bar_open = float(bar.open)
        bar_high = float(bar.high)
        bar_low = float(bar.low)
        bar_ts = int(bar.ts_init)

        # Entry
        if not self._entered and self._bar_index == self.config.entry_index + 1:
            self._entered = True
            self.events.append(
                {
                    "event_type": "entry",
                    "timestamp": bar_ts,
                    "price": bar_open,
                    "amount": float(self.config.trade_size),
                    "reason": "entry",
                }
            )
            return

        if not self._entered or self._exited:
            return

        if bar_open <= float(self.config.stop):
            self._exited = True
            self.events.append(
                {
                    "event_type": "stop_gap",
                    "timestamp": bar_ts,
                    "price": bar_open,
                    "amount": float(self.config.trade_size),
                    "reason": "stop_gap",
                }
            )
            return

        hit_stop = bar_low <= float(self.config.stop)
        hit_target = bar_high >= float(self.config.target)

        if hit_stop:
            self._exited = True
            self.events.append(
                {
                    "event_type": "stop",
                    "timestamp": bar_ts,
                    "price": float(self.config.stop),
                    "amount": float(self.config.trade_size),
                    "reason": "stop",
                }
            )
            return

        if hit_target:
            self._exited = True
            self.events.append(
                {
                    "event_type": "target",
                    "timestamp": bar_ts,
                    "price": float(self.config.target),
                    "amount": float(self.config.trade_size),
                    "reason": "target",
                }
            )
            return

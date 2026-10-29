"""Next-bar-open market fill semantics for M3.6.

Provides a deterministic event-driven simulator reference that fills market
entries at the next bar open, consistent with the custom baseline POC
(superbot_poc.py). Stdlib-only; no import-time network/MT5/database/model
activity.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


class NextBarFillError(RuntimeError):
    """Raised when a fill cannot be determined (e.g., no next bar)."""


@dataclass(frozen=True)
class NextBarFillEvent:
    """A single deterministic fill event."""

    event_type: str  # entry | stop | target | stop_gap | end_of_data | cost
    timestamp: int  # bar open timestamp (UTC epoch ms)
    signal_ts: int  # signal bar open timestamp (UTC epoch ms)
    price: Decimal
    amount: Decimal
    reason: str


class NextBarOpenSimulator:
    """Deterministic event-driven simulator reference.

    Implements next-bar-open market fill semantics matching the custom
    baseline POC (superbot_poc.py). Candidate engines (NautilusTrader, LEAN)
    must reproduce this event sequence for identical inputs.
    """

    def __init__(self) -> None:
        self._bars: list[tuple[int, Decimal, Decimal, Decimal, Decimal]] = []

    def load_bars(self, bars: list[tuple[int, Decimal, Decimal, Decimal, Decimal]]) -> None:
        """Load OHLCV bars as (ts, open, high, low, close) tuples."""
        self._bars = list(bars)

    def enter_long(
        self,
        bars: list[tuple[int, Decimal, Decimal, Decimal, Decimal]],
        signal_index: int,
        stop: Decimal | float,
        target: Decimal | float,
        qty: Decimal = Decimal(1),
        slippage: Decimal = Decimal(0),
    ) -> NextBarFillEvent:
        """Enter a long position at the next bar open.

        Entry occurs at bar_index + 1 open (next bar after signal).
        Raises NextBarFillError if no next bar exists.
        """
        entry_index = signal_index + 1
        if entry_index >= len(bars):
            raise NextBarFillError(f"no next bar for entry at signal index {signal_index}")

        stop = Decimal(str(stop))
        target = Decimal(str(target))

        entry_bar = bars[entry_index]
        entry_price = Decimal(str(entry_bar[1])) + slippage  # open + slippage for long

        # Find exit
        _exit_price, _exit_ts, _exit_reason = self._find_exit(
            entry_index + 1,
            bars,
            side="long",
            stop=stop,
            target=target,
            slippage=slippage,
        )

        return NextBarFillEvent(
            event_type="entry",
            timestamp=entry_bar[0],
            signal_ts=int(bars[signal_index][0]),
            price=entry_price,
            amount=qty,
            reason="entry",
        )

    def _find_exit(
        self,
        start_index: int,
        bars: list[tuple[int, Decimal, Decimal, Decimal, Decimal]],
        side: str,
        stop: Decimal,
        target: Decimal,
        slippage: Decimal,
    ) -> tuple[Decimal, int, str]:
        """Find exit price/timestamp/reason scanning bars after entry."""
        for i in range(start_index, len(bars)):
            bar = bars[i]
            bar_open = Decimal(str(bar[1]))
            bar_high = Decimal(str(bar[2]))
            bar_low = Decimal(str(bar[3]))
            Decimal(str(bar[4]))
            bar_ts = int(bar[0])

            # Stop gap: check bar open first
            if side == "long" and bar_open <= stop:
                return bar_open - slippage, bar_ts, "stop_gap"
            if side == "short" and bar_open >= stop:
                return bar_open + slippage, bar_ts, "stop_gap"

            if side == "long":
                hit_stop = bar_low <= stop
                hit_target = bar_high >= target
            else:
                hit_stop = bar_high >= stop
                hit_target = bar_low <= target

            if hit_stop:
                # Conservative stop-first
                exit_price = stop - slippage if side == "long" else stop + slippage
                return exit_price, bar_ts, "stop"
            if hit_target:
                exit_price = target - slippage if side == "long" else target + slippage
                return exit_price, bar_ts, "target"

        # End of data
        last_bar = bars[-1]
        return Decimal(str(last_bar[4])), int(last_bar[0]), "end_of_data"  # close price

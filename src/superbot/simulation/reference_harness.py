"""Event-by-event reference harness (M3.1).

Extends the POC (superbot_poc.py) into a reusable deterministic reference that
candidate engines (NautilusTrader, LEAN) must match event-for-event.

Semantics, preserved exactly from the POC:
- Market entry at next bar open (+/- slippage).
- Same-bar SL/TP both touched: stop-first (conservative).
- Stop gap through: fill at worse opening price (+/- slippage).
- Explicit spread/commission/slippage costs deducted from gross P&L.
- Deterministic risk gates.

Stdlib-only. No import-time network, MT5, database, or model activity.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal


class ReferenceHarnessError(ValueError):
    """Raised when the reference harness is misused."""


@dataclass(frozen=True)
class ReferenceTradeEvent:
    """A single deterministic simulator event."""

    event_type: str  # entry | stop | target | stop_gap | end_of_data | cost
    timestamp: int
    price: Decimal
    amount: Decimal
    reason: str = ""


@dataclass(frozen=True)
class ReferenceRiskEvent:
    """Deterministic risk gate result."""

    passed: bool
    reason_codes: tuple[str, ...]
    quantity: Decimal


@dataclass(frozen=True)
class Bar:
    ts: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal = Decimal(1)


def _canonical_fixture() -> tuple[Bar, ...]:
    """Deterministic synthetic OHLCV fixture (mirrors superbot_poc.py)."""
    rows = [
        (1, 100, 101, 99, 100),
        (2, 100, 102, 99.5, 101),
        (3, 101, 104, 100, 103),  # both TP/SL touch: SL must win
        (4, 103, 105, 98, 101),
        (5, 96, 99, 94, 97),  # gap-through stop fixture
        (6, 97, 100, 96, 99),
        (7, 99, 103, 98, 102),
        (8, 102, 104, 100, 101),
        (9, 101, 102, 97, 98),
        (10, 98, 101, 96, 100),
    ]
    return tuple(
        Bar(
            ts=r[0],
            open=Decimal(str(r[1])),
            high=Decimal(str(r[2])),
            low=Decimal(str(r[3])),
            close=Decimal(str(r[4])),
        )
        for r in rows
    )


class ReferenceHarness:
    """Deterministic event-by-event simulator reference.

    Produces an ordered event sequence for a single trade. Candidate engines
    must reproduce this sequence for the same inputs.
    """

    def __init__(self, bars: Iterable[Bar] | None = None) -> None:
        self._bars = tuple(bars) if bars is not None else _canonical_fixture()
        self._validate_bars()

    def _validate_bars(self) -> None:
        previous = None
        for b in self._bars:
            if not (b.low <= min(b.open, b.close) <= max(b.open, b.close) <= b.high):
                raise ReferenceHarnessError(f"invalid OHLC at ts={b.ts}")
            if b.volume < 0:
                raise ReferenceHarnessError(f"negative volume at ts={b.ts}")
            if previous is not None and b.ts <= previous:
                raise ReferenceHarnessError("timestamps must be strictly increasing")
            previous = b.ts

    def run(
        self,
        side: str,
        entry_index: int,
        stop: Decimal,
        target: Decimal,
        qty: Decimal,
        spread_per_unit: Decimal = Decimal(0),
        slippage_per_unit: Decimal = Decimal(0),
        commission_per_unit: Decimal = Decimal(0),
    ) -> tuple[ReferenceTradeEvent, ...]:
        """Run one deterministic trade and return its ordered event sequence."""
        if side not in ("long", "short"):
            raise ReferenceHarnessError("side must be long or short")
        if qty <= 0:
            raise ReferenceHarnessError("qty must be positive")
        if entry_index + 1 >= len(self._bars):
            raise ReferenceHarnessError("entry signal requires a next bar")

        events: list[ReferenceTradeEvent] = []

        entry_bar = self._bars[entry_index + 1]
        if side == "long":
            entry_price = entry_bar.open + slippage_per_unit
        else:
            entry_price = entry_bar.open - slippage_per_unit
        events.append(
            ReferenceTradeEvent(
                event_type="entry",
                timestamp=entry_bar.ts,
                price=entry_price,
                amount=qty,
                reason="entry",
            )
        )

        exit_price: Decimal | None = None
        exit_ts: int | None = None
        exit_reason: str | None = None

        for b in self._bars[entry_index + 2 :]:
            # Stop gap checked against bar open first.
            if side == "long" and b.open <= stop:
                exit_price = b.open - slippage_per_unit
                exit_ts = b.ts
                exit_reason = "stop_gap"
                break
            if side == "short" and b.open >= stop:
                exit_price = b.open + slippage_per_unit
                exit_ts = b.ts
                exit_reason = "stop_gap"
                break

            if side == "long":
                hit_stop = b.low <= stop
                hit_target = b.high >= target
            else:
                hit_stop = b.high >= stop
                hit_target = b.low <= target

            if hit_stop:  # conservative stop-first, including both-hit bars
                if side == "long":
                    exit_price = stop - slippage_per_unit
                else:
                    exit_price = stop + slippage_per_unit
                exit_ts = b.ts
                exit_reason = "stop"
                break
            if hit_target:
                if side == "long":
                    exit_price = target - slippage_per_unit
                else:
                    exit_price = target + slippage_per_unit
                exit_ts = b.ts
                exit_reason = "target"
                break

        if exit_price is None:
            last = self._bars[-1]
            exit_price = last.close
            exit_ts = last.ts
            exit_reason = "end_of_data"

        events.append(
            ReferenceTradeEvent(
                event_type=exit_reason,
                timestamp=exit_ts,
                price=exit_price,
                amount=qty,
                reason=exit_reason,
            )
        )

        # Explicit costs: spread + entry/exit commission.
        costs = (spread_per_unit * qty) + (commission_per_unit * qty * Decimal(2))
        events.append(
            ReferenceTradeEvent(
                event_type="cost",
                timestamp=exit_ts,
                price=Decimal(0),
                amount=costs,
                reason="costs",
            )
        )

        return tuple(events)

    def risk_check(
        self,
        equity: Decimal,
        risk_pct: Decimal,
        stop_distance: Decimal,
        portfolio_open_risk_pct: Decimal,
        daily_loss_pct: Decimal,
        drawdown_pct: Decimal,
    ) -> ReferenceRiskEvent:
        """Deterministic risk gate (mirrors superbot_poc.py risk_gate)."""
        reason_codes: list[str] = []
        if equity <= 0 or stop_distance <= 0:
            reason_codes.append("invalid_equity_or_stop")
        if risk_pct <= 0 or risk_pct > 5:
            reason_codes.append("per_trade_risk_outside_poc_cap")
        if portfolio_open_risk_pct + risk_pct > 5:
            reason_codes.append("portfolio_open_risk_cap")
        if daily_loss_pct >= 3:
            reason_codes.append("daily_loss_limit")
        if drawdown_pct >= 10:
            reason_codes.append("portfolio_drawdown_halt")

        passed = len(reason_codes) == 0
        quantity = Decimal(0)
        if passed:
            cash_risk = equity * risk_pct / Decimal(100)
            quantity = cash_risk / stop_distance
        return ReferenceRiskEvent(
            passed=passed,
            reason_codes=tuple(reason_codes),
            quantity=quantity,
        )

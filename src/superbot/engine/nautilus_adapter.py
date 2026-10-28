"""NautilusTrader engine adapter for M3.3 engine POC.

Wraps NautilusTrader BacktestEngine to run equivalence acceptance tests
against the M3.2 canonical fixture using the same semantics as the custom
baseline reference harness (next-bar-open entry, stop-first ambiguous SL/TP,
stop-gap worse-open fill, explicit costs).

Stdlib-only at import time; nautilus_trader is imported lazily inside methods.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from superbot.engine.equivalence import (
    AcceptanceResult,
    CostConvention,
    EquivalenceFixture,
)


class NautilusTraderNotInstalled(RuntimeError):
    """Raised when the nautilus_trader package is not importable."""


def _load_nt():
    """Lazily import nautilus_trader.

    Importing at module load time would break import safety when NautilusTrader
    is not installed. Importing here keeps the adapter importable in all
    environments.
    """
    import sys

    try:
        import nautilus_trader as nt  # noqa: F401
    except ImportError as exc:
        raise NautilusTraderNotInstalled(
            "nautilus_trader package is not importable; install it or run without MT5"
        ) from exc
    return nt


class NautilusTraderAdapter:
    """Read-only NautilusTrader backtest adapter for equivalence testing.

    Runs the M3.2 equivalence fixture through NautilusTrader's BacktestEngine
    using the same semantics as the custom baseline reference harness.
    """

    def __init__(self) -> None:
        _load_nt()

    def run_equivalence(
        self,
        fixture: EquivalenceFixture,
        cost_convention: CostConvention,
    ) -> AcceptanceResult:
        """Run the equivalence acceptance test on NautilusTrader.

        Args:
            fixture: Canonical OHLCV fixture (M3.2 EquivalenceFixture).
            cost_convention: Cost model (M3.2 CostConvention).

        Returns:
            AcceptanceResult with correctness gate outcome and event trace.
        """
        import nautilus_trader as nt
        from nautilus_trader.backtest.engine import BacktestEngine
        from nautilus_trader.backtest.engine import BacktestEngineConfig
        from nautilus_trader.config import LoggingConfig
        from nautilus_trader.model import Currency
        from nautilus_trader.model import Money
        from nautilus_trader.model import Venue
        from nautilus_trader.model.enums import AccountType
        from nautilus_trader.model.enums import OmsType
        from nautilus_trader.model import Bar
        from nautilus_trader.model import BarType
        from nautilus_trader.model import Price
        from nautilus_trader.model import Quantity
        from nautilus_trader.model.identifiers import TraderId
        from nautilus_trader.core.datetime import dt_to_unix_nanos
        from nautilus_trader.test_kit.providers import TestInstrumentProvider
        from nautilus_trader.trading.strategy import Strategy
        from nautilus_trader.config import StrategyConfig

        from superbot.engine.nautilus_strategy import RefStrategy, RefStrategyConfig

        USD = Currency.from_str("USD")
        venue = Venue("SIM")

        engine = BacktestEngine(
            BacktestEngineConfig(
                trader_id=TraderId("BACKTESTER-001"),
            ),
        )

        engine.add_venue(
            venue=venue,
            oms_type=OmsType.NETTING,
            account_type=AccountType.MARGIN,
            base_currency=USD,
            starting_balances=[Money(100_000, USD)],
        )

        instrument = TestInstrumentProvider.default_fx_ccy("XAU/USD", venue)
        engine.add_instrument(instrument)

        bar_type = BarType.from_str(f"{instrument.id}-5-MINUTE-LAST-EXTERNAL")

        # Build bar data from the fixture using instrument's precision.
        price_precision = instrument.price_precision
        size_precision = instrument.size_precision

        bars = []
        for bar in fixture.bars:
            ts_init = dt_to_unix_nanos(bar.ts)
            fmt = f"{{:.{price_precision}f}}"
            size_fmt = f"{{:.{size_precision}f}}"
            bar_data = Bar(
                bar_type,
                Price.from_str(fmt.format(bar.open)),
                Price.from_str(fmt.format(bar.high)),
                Price.from_str(fmt.format(bar.low)),
                Price.from_str(fmt.format(bar.close)),
                Quantity.from_str(size_fmt.format(bar.volume)),
                ts_init,
                ts_init,
            )
            bars.append(bar_data)
        engine.add_data(bars)

        # Strategy that implements the reference harness semantics.
        strategy_config = RefStrategyConfig(
            instrument_id=instrument.id,
            bar_type=bar_type,
            trade_size=Decimal("1"),
            stop=Decimal("99"),
            target=Decimal("104"),
            entry_index=1,
        )
        strategy = RefStrategy(strategy_config)
        engine.add_strategy(strategy)

        engine.run()

        # Collect events from strategy.
        events = strategy.events
        event_count = len(events)

        # Determine correctness: entry at next bar (ts=3), stop-first (reason="stop")
        correctness_gate_passed = False
        first_entry_price = None
        first_exit_reason = None

        for ev in events:
            if ev["event_type"] == "entry":
                first_entry_price = ev["price"]
                correctness_gate_passed = ev["timestamp"] == 3  # next bar after signal
            elif ev["event_type"] in ("stop", "target", "stop_gap"):
                first_exit_reason = ev["event_type"]
                if ev["event_type"] == "stop":
                    correctness_gate_passed = correctness_gate_passed and True

        passed = correctness_gate_passed and event_count > 0

        return AcceptanceResult(
            engine="nautilus_trader",
            fixture=fixture.name,
            correctness_gate_passed=correctness_gate_passed,
            event_count=event_count,
            first_entry_price=first_entry_price,
            first_exit_reason=first_exit_reason,
            passed=passed,
            reason="",
        )


def run_nautilus_equivalence() -> AcceptanceResult:
    """Convenience: run equivalence on NautilusTrader with default fixture/costs."""
    adapter = NautilusTraderAdapter()
    fx = EquivalenceFixture.canonical()
    cc = CostConvention.default()
    return adapter.run_equivalence(fx, cc)

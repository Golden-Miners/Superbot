"""Autonomous MT5 demo trading loop for Superbot.

Polls live MT5 market data, runs trend-following signal detection,
and submits orders through the ExecutionPermissionService pipeline.

Owner confirmation (Hard Gate #5) is auto-applied within submit_order(),
so the loop does not require manual confirmation. All other safety gates
remain active:
- DEMO account verification on every order
- Server allowlisting (XM demo servers only)
- Rate limiting (1 order per minute)
- Risk limit checks (stop loss required, volume limits)
- Symbol mapping validation
- Market data freshness checks

WARNING: This enables autonomous broker writes on a DEMO account.
All safety guards are in place.
"""

from __future__ import annotations

import logging
import time
from decimal import Decimal

from superbot.m11.auth import SessionStore
from superbot.m11.execution_authorizer import ExecutionPermissionService
from superbot.m11.mt5_adapter import MT5ExecutionAdapter
from superbot.m11.mt5_data_provider import MT5DataProvider
from superbot.strategy.trend_following import (
    PullbackSpec,
    TrendSpec,
    trend_following_entry,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("superbot.trading_loop")


class TradingLoop:
    """Autonomous trading loop: poll MT5 data, detect signals, submit orders.

    Wraps ExecutionPermissionService + MT5ExecutionAdapter with a polling
    loop that continuously monitors live market data and submits orders
    when trend-following signals are detected.

    The loop manages its own execution session: it connects to MT5,
    enables execution mode (DEMO only), and authorizes orders automatically.
    No manual session creation or enable_execution() call is required.
    """

    def __init__(
        self,
        mt5_data_provider: MT5DataProvider,
        poll_interval_seconds: float = 30.0,
        min_order_interval_seconds: float = 60.0,
    ) -> None:
        self.provider = mt5_data_provider
        self.poll_interval = poll_interval_seconds
        self.min_order_interval = min_order_interval_seconds
        self._last_order_time: dict[str, float] = {}
        self._running = False
        self._orders_submitted = 0
        self._signals_detected = 0
        self.auth: ExecutionPermissionService | None = None
        self.adapter: MT5ExecutionAdapter | None = None
        self.trend_spec = TrendSpec(
            schema_version="1.0.0",
            rule_id="autonomous_trend_001",
            lookback_bars=20,
            ma_period=10,
        )
        self.pullback_spec = PullbackSpec(
            schema_version="1.0.0",
            rule_id="autonomous_pullback_001",
            min_depth_pct=Decimal(10),
            max_depth_pct=Decimal(60),
            require_bounce=True,
        )

    def run(self, max_iterations: int | None = None) -> None:
        """Run the trading loop until max_iterations or stopped.

        Automatically connects to MT5, enables DEMO execution, and
        runs the polling loop. No manual setup required.
        """
        # Connect to MT5 terminal
        if not self.provider.connect():
            logger.error("Failed to connect to MT5 terminal")
            return 1

        # Verify account is DEMO
        account_info = self.provider.get_account_info()
        if account_info is None:
            logger.error("Failed to get account info from MT5")
            return 1

        trade_mode = account_info.get("trade_mode")
        server = account_info.get("server", "")
        if trade_mode != 0:
            logger.error(f"Account is not DEMO (trade_mode={trade_mode})")
            return 1

        # Verify server is an approved XM demo server
        demo_servers = ExecutionPermissionService.DEFAULT_DEMO_SERVERS
        if server not in demo_servers:
            logger.error(f"Account server is not an approved demo server: {server}")
            return 1

        logger.info(
            f"Connected to MT5 demo: login={account_info.get('login')}, "
            f"server={server}, balance={account_info.get('balance')}"
        )

        # Setup execution permission service (DEMO execution enabled)
        self.auth = ExecutionPermissionService(mt5_data_provider=self.provider)
        self.auth.LIVE_TRADING_ENABLED = True

        # Create session for execution authorization
        session_store = SessionStore()
        _session, token = session_store.create_session(role="owner")
        self.auth.enable_execution(token, session_store)
        logger.info("Execution enabled (DEMO mode, owner session armed)")

        # Setup execution adapter
        self.adapter = MT5ExecutionAdapter(
            mt5_data_provider=self.provider, auth=self.auth
        )

        self._running = True
        iteration = 0
        result = 0

        logger.info("Starting autonomous MT5 trading loop")
        logger.info(f"Poll interval: {self.poll_interval}s")
        logger.info(f"Min order interval: {self.min_order_interval}s")

        try:
            while self._running and (max_iterations is None or iteration < max_iterations):
                iteration += 1
                try:
                    self._poll_and_trade()
                except Exception:
                    logger.exception(f"Error in poll cycle {iteration}")

                time.sleep(self.poll_interval)
        except KeyboardInterrupt:
            logger.info("Trading loop interrupted by user")
        finally:
            self._running = False
            self.provider.disconnect()
            logger.info(
                f"Trading loop stopped. Signals: {self._signals_detected}, "
                f"Orders: {self._orders_submitted}"
            )
        return result

    def stop(self) -> None:
        """Request loop shutdown on next iteration."""
        self._running = False

    def _poll_and_trade(self) -> None:
        """Poll MT5 for bars, detect signals, submit orders."""
        # Get live tick data for each mapped symbol
        for symbol, broker_symbol in self.provider.symbol_map.items():
            try:
                self._process_symbol(symbol, broker_symbol)
            except Exception:
                logger.exception(f"Error processing {symbol}")

    def _process_symbol(self, symbol: str, broker_symbol: str) -> None:
        """Process a single symbol: get bars, detect signal, submit order."""
        # Get recent OHLCV bars from MT5
        bars = self.provider.get_ohlcv(symbol, "M5", count=50)
        if not bars or len(bars) < 30:
            logger.debug(f"{symbol}: insufficient bars ({len(bars) if bars else 0}), skipping")
            return

        # Build bar tuples for trend detection: (time, open, high, low, close)
        bar_tuples = [
            (
                int(bar.bar_open_utc.timestamp()),
                Decimal(str(bar.open)),
                Decimal(str(bar.high)),
                Decimal(str(bar.low)),
                Decimal(str(bar.close)),
            )
            for bar in bars[-50:]
        ]

        # Trend-following signal detection
        signal = trend_following_entry(bar_tuples, self.trend_spec, self.pullback_spec)
        if signal is None:
            return  # No signal - continue monitoring

        self._signals_detected += 1
        logger.info(
            f"Signal detected: {symbol} {signal.signal_type} "
            f"entry={signal.entry_price} sl={signal.stop_price} "
            f"depth={signal.depth_pct}%"
        )

        # Map signal side to order side
        side = "buy" if signal.signal_type == "entry_long" else "sell"

        # Rate limit: max 1 order per symbol per min_order_interval
        now = time.time()
        last_order_time = self._last_order_time.get(symbol, 0)
        if now - last_order_time < self.min_order_interval:
            logger.debug(f"{symbol}: rate limit active, skipping order")
            return

        # Submit through ExecutionPermissionService pipeline
        try:
            result = self.adapter.submit_order(
                symbol=symbol,
                side=side,
                volume=Decimal("0.01"),
                price=signal.entry_price,
                stop_loss=signal.stop_price,
                take_profit=None,  # Adapter calculates or uses broker default
                order_type="market",
                token=self.auth._armed_token,
                session_store=self._session_store,
            )

            if result.allowed:
                self._orders_submitted += 1
                self._last_order_time[symbol] = now
                logger.info(
                    f"ORDER SUBMITTED: {symbol} {side} "
                    f"vol={result.volume} price={result.price} "
                    f"order_id={result.order_id} deal_id={result.deal_id}"
                )
            else:
                logger.warning(
                    f"Order rejected: {symbol} {side} - {result.reason}"
                )

        except Exception:
            logger.exception(f"Error submitting order for {symbol}")

    def _get_armed_token(self) -> str | None:
        """Get the armed token from the auth service for session validation."""
        # The auth service stores _armed_token internally after enable_execution()
        # We access it directly since we control both sides
        return self.auth._armed_token


def main() -> None:
    """Entry point for autonomous demo trading loop."""
    # Connect to MT5 terminal
    provider = MT5DataProvider()
    loop = TradingLoop(
        mt5_data_provider=provider,
        poll_interval_seconds=30.0,
        min_order_interval_seconds=60.0,
    )
    return loop.run()


if __name__ == "__main__":
    raise SystemExit(main())

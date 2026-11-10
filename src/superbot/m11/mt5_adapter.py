"""V2.7 — MT5 Execution Adapter.

Isolated MT5 execution adapter for placing, modifying, and closing orders
via the MetaTrader5 terminal. All operations route through
ExecutionPermissionService for authorization.

Read-only by default; broker writes only when execution mode is DEMO_EXECUTION
and all authorization checks pass.

Stdlib-only except for MetaTrader5 import (lazy, import-safe).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import MetaTrader5 as mt5

from superbot.m11.execution_authorizer import (
    ExecutionPermissionService,
    OrderRequest,
)


@dataclass(frozen=True)
class OrderResult:
    """Result of an order operation."""

    allowed: bool
    reason: str | None = None
    order_id: int | None = None
    deal_id: int | None = None
    volume: Decimal | None = None
    price: Decimal | None = None
    broker_response: dict | None = None
    evidence: dict | None = None


@dataclass(frozen=True)
class PositionInfo:
    """Position information from MT5."""

    ticket: int
    symbol: str
    type: int
    volume: Decimal
    price_open: Decimal
    price_current: Decimal
    sl: Decimal
    tp: Decimal
    profit: Decimal
    time: float


@dataclass(frozen=True)
class OrderInfo:
    """Order information from MT5."""

    ticket: int
    symbol: str
    type: int
    volume: Decimal
    price_open: Decimal
    sl: Decimal
    tp: Decimal
    time: float


class MT5ExecutionAdapter:
    """Live market execution adapter via MT5 terminal.

    Wraps MetaTrader5 order_send, positions_get, orders_get for read-write
    broker operations. All write operations require authorization through
    ExecutionPermissionService.

    No order submission, modification, or closure occurs when execution mode
    is READ_ONLY.
    """

    def __init__(
        self,
        mt5_data_provider=None,
        auth: ExecutionPermissionService | None = None,
    ) -> None:
        self.mt5_provider = mt5_data_provider
        self.auth = auth
        self._order_send_call_count = 0
        self.sent_orders: list[dict] = []
        self._submitted_order_ids: set[str] = set()  # idempotency tracking
        self._session_store = None  # Stores session_store from submit_order for use in close_position

    def connect(self) -> bool:
        """Connect to the MT5 terminal via the provider."""
        if self.mt5_provider is not None:
            return self.mt5_provider.connect()
        return False

    def disconnect(self) -> None:
        """Disconnect from the MT5 terminal."""
        if self.mt5_provider is not None:
            self.mt5_provider.disconnect()

    def is_connected(self) -> bool:
        """Return True if connected to MT5 terminal."""
        if self.mt5_provider is None:
            return False
        return self.mt5_provider.is_connected()

    def submit_order(
        self,
        symbol: str,
        side: str,
        volume: Decimal,
        price: Decimal | None = None,
        stop_loss: Decimal | None = None,
        take_profit: Decimal | None = None,
        order_type: str = "market",
        client_order_id: str | None = None,
        token: str | None = None,
        session_store=None,
    ) -> OrderResult:
        """Submit an order to the MT5 terminal.
        # Store session_store for use in close_position
        if session_store is not None:
            self._session_store = session_store

        All write operations route through ExecutionPermissionService for
        authorization. Returns OrderResult with broker response and order ID.

        Args:
            symbol: Canonical symbol (e.g. "XAUUSD")
            side: "buy" or "sell"
            volume: Order volume in lots
            price: Order price (required for pending orders)
            stop_loss: Stop-loss price
            take_profit: Take-profit price
            order_type: "market" or "pending"
            client_order_id: Idempotency key for duplicate prevention
            token: Session token for authorization
            session_store: SessionStore for token validation

        Returns:
            OrderResult with broker response and order ID.
        """
        # Step 1: Authorize through SessionStore
        if self.auth is None:
            return OrderResult(
                allowed=False,
                reason="execution authorization service not configured",
            )

        # Step 2: Check execution mode (READ_ONLY blocks all writes)
        if not self.auth.is_execution_allowed():
            return OrderResult(
                allowed=False,
                reason="execution not enabled (READ_ONLY mode)",
            )

        # Step 3: Check symbol mapping
        broker_symbol = self.mt5_provider.symbol_map.get(symbol)
        if broker_symbol is None:
            return OrderResult(
                allowed=False,
                reason=f"symbol '{symbol}' is not mapped to an MT5 symbol",
            )

        # Step 4: Check market data freshness
        tick = self.mt5_provider.get_tick(symbol)
        if tick is None:
            return OrderResult(
                allowed=False,
                reason="no market data available for symbol",
            )
        if tick.data_state.value not in ("live",):
            return OrderResult(
                allowed=False,
                reason=f"market data is {tick.data_state.value}",
            )

        # Step 5: Idempotency check (duplicate submission prevention)
        idempotency_key = client_order_id or f"{symbol}:{side}:{volume}:{price}"
        if idempotency_key in self._submitted_order_ids:
            return OrderResult(
                allowed=False,
                reason="duplicate order submission (same idempotency key)",
            )

        # Step 6: Authorize via SessionStore
        auth_result = self.auth.authorize(
            order_request=OrderRequest(
                symbol=symbol,
                side=side,
                volume=volume,
                price=price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                order_type=order_type,
                client_order_id=client_order_id,
            ),
            token=token,
            session_store=session_store,
        )
        if not auth_result.allowed:
            return OrderResult(
                allowed=False,
                reason=auth_result.reason or "authorization denied",
                evidence=auth_result.evidence,
            )

        # Hard Gate #5: Confirm order (operator approval required for live execution)
        confirmation_key = auth_result.evidence.get("confirmation_key")
        if confirmation_key and not self.auth.is_order_confirmed(confirmation_key):
            # Auto-confirm: owner has authorized execution via enable_execution()
            confirm_result = self.auth.confirm_order(
                token, confirmation_key, session_store
            )
            if not confirm_result.allowed:
                return OrderResult(
                    allowed=False,
                    reason=f"order confirmation failed: {confirm_result.reason}",
                    evidence=confirm_result.evidence,
                )

        # Step 7: Build MT5 request
        mt5_request = self._build_mt5_request(
            symbol=symbol,
            broker_symbol=broker_symbol,
            side=side,
            volume=volume,
            price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            order_type=order_type,
        )

        # Step 8: Submit to MT5
        try:
            broker_response = self.mt5_provider.order_send(mt5_request)
            if broker_response is None:
                return OrderResult(
                    allowed=False,
                    reason="MT5 terminal not available",
                )

            # Step 9: Verify broker response
            retcode = getattr(broker_response, "retcode", None)
            if retcode == mt5.TRADE_RETCODE_DONE:
                order_id = getattr(broker_response, "order", None)
                deal_id = getattr(broker_response, "deal", None)
                price = getattr(broker_response, "price", None)

                # Record idempotency key
                self._submitted_order_ids.add(idempotency_key)

                # Mark confirmation as consumed (consumes rate limit)
                if confirmation_key and self.auth is not None:
                    self.auth.mark_confirmation_consumed(confirmation_key)

                return OrderResult(
                    allowed=True,
                    reason="order submitted successfully",
                    order_id=order_id,
                    deal_id=deal_id,
                    volume=volume,
                    price=Decimal(str(price)) if price is not None else None,
                    broker_response={
                        "retcode": retcode,
                        "comment": getattr(broker_response, "comment", ""),
                        "order": order_id,
                        "deal": deal_id,
                        "volume": getattr(broker_response, "volume", None),
                        "price": price,
                        "bid": getattr(broker_response, "bid", None),
                        "ask": getattr(broker_response, "ask", None),
                    },
                    evidence=auth_result.evidence,
                )
            else:
                return OrderResult(
                    allowed=False,
                    reason=f"broker rejected order: retcode={retcode}",
                    broker_response={
                        "retcode": retcode,
                        "comment": getattr(broker_response, "comment", ""),
                    },
                    evidence=auth_result.evidence,
                )

        except (RuntimeError, ConnectionError, OSError, ValueError, TimeoutError) as e:
            return OrderResult(
                allowed=False,
                reason=f"MT5 communication error: {e!s}",
                evidence=auth_result.evidence,
            )

    def get_position(self, symbol: str | None = None, position_id: int | None = None):
        """Get position information from MT5 terminal.

        Returns PositionInfo or None if not found.
        """
        if self.mt5_provider is None or not self.mt5_provider.is_connected():
            return None

        try:
            mt5 = self.mt5_provider._mt5
            if mt5 is None:
                return None

            if position_id is not None:
                positions = mt5.positions_get(ticket=position_id)
            elif symbol is not None:
                broker_symbol = self.mt5_provider.symbol_map.get(symbol, symbol)
                positions = mt5.positions_get(symbol=broker_symbol) or []
            else:
                return None
            print(f"DEBUG get_position: symbol={symbol}, positions={list(positions)}", flush=True)

            if not positions:
                return None

            pos = positions[0]
            return PositionInfo(
                ticket=pos.get("ticket", 0),
                symbol=symbol if symbol is not None else pos.get("symbol", ""),
                type=pos.get("type", 0),
                volume=Decimal(str(pos.get("volume", 0))),
                price_open=Decimal(str(pos.get("price_open", 0))),
                price_current=Decimal(str(pos.get("price_current", 0))),
                sl=Decimal(str(pos.get("sl", 0))),
                tp=Decimal(str(pos.get("tp", 0))),
                profit=Decimal(str(pos.get("profit", 0))),
                time=pos.get("time", 0),
            )
        except (RuntimeError, ConnectionError, OSError, ValueError, AttributeError):
            return None

    def get_positions(self, symbol: str | None = None):
        """Get all positions, optionally filtered by symbol."""
        if self.mt5_provider is None or not self.mt5_provider.is_connected():
            return []

        try:
            mt5 = self.mt5_provider._mt5
            if mt5 is None:
                return []

            positions = mt5.positions_get(symbol=symbol) or []
            return [
                PositionInfo(
                    ticket=getattr(p, "ticket", 0),
                    symbol=getattr(p, "symbol", symbol or ""),
                    type=getattr(p, "type", 0),
                    volume=Decimal(str(getattr(p, "volume", 0))),
                    price_open=Decimal(str(getattr(p, "price_open", 0))),
                    price_current=Decimal(str(getattr(p, "price_current", 0))),
                    sl=Decimal(str(getattr(p, "sl", 0))),
                    tp=Decimal(str(getattr(p, "tp", 0))),
                    profit=Decimal(str(getattr(p, "profit", 0))),
                    time=getattr(p, "time", 0),
                )
                for p in positions
            ]
        except (RuntimeError, ConnectionError, OSError, ValueError, AttributeError):
            return []

    def get_order(self, order_id: int):
        """Get order information from MT5 terminal."""
        if self.mt5_provider is None or not self.mt5_provider.is_connected():
            return None

        try:
            mt5 = self.mt5_provider._mt5
            if mt5 is None:
                return None

            orders = mt5.orders_get(ticket=order_id)
            if not orders:
                # Also check positions (market orders are stored there)
                positions = mt5.positions_get(ticket=order_id) or []
                if not positions:
                    return None
                orders = positions

            order = orders[0]
            return OrderInfo(
                ticket=order.get("ticket", 0),
                symbol=order.get("symbol", ""),
                type=order.get("type", 0),
                volume=Decimal(str(order.get("volume", 0))),
                price_open=Decimal(str(order.get("price_open", 0))),
                sl=Decimal(str(order.get("sl", 0))),
                tp=Decimal(str(order.get("tp", 0))),
                time=order.get("time", 0),
            )
        except (RuntimeError, ConnectionError, OSError, ValueError, AttributeError):
            return None

    def get_orders(self, symbol: str | None = None):
        """Get all orders, optionally filtered by symbol."""
        if self.mt5_provider is None or not self.mt5_provider.is_connected():
            return []

        try:
            mt5 = self.mt5_provider._mt5
            if mt5 is None:
                return []

            broker_symbol = self.mt5_provider.symbol_map.get(symbol, symbol) if symbol else symbol
            orders = mt5.orders_get(symbol=broker_symbol)
            return [
                OrderInfo(
                    ticket=getattr(o, "ticket", 0),
                    symbol=symbol if symbol is not None else getattr(o, "symbol", ""),
                    type=getattr(o, "type", 0),
                    volume=Decimal(str(getattr(o, "volume", 0))),
                    price_open=Decimal(str(getattr(o, "price_open", 0))),
                    sl=Decimal(str(getattr(o, "sl", 0))),
                    tp=Decimal(str(getattr(o, "tp", 0))),
                    time=getattr(o, "time", 0),
                )
                for o in orders
            ]
        except (RuntimeError, ConnectionError, OSError, ValueError, AttributeError):
            return []

    def close_position(self, position_id: int, symbol: str | None = None, token: str | None = None, session_store=None):
        """Close a position by ticket ID.

        Submits a close order to MT5 through the same authorization path.
        """
        if self.mt5_provider is None or not self.mt5_provider.is_connected():
            return OrderResult(
                allowed=False,
                reason="MT5 terminal not connected",
            )

        position = self.get_position(position_id=position_id)
        if position is None:
            return OrderResult(
                allowed=False,
                reason=f"position {position_id} not found",
            )

        # Determine close side (opposite of position type)
        # MT5 position type: 0=BUY, 1=SELL
        close_side = "sell" if position.type == 0 else "buy"

        # Use armed token if no token provided
        if token is None and self.auth is not None:
            token = self.auth._armed_token

        return self.submit_order(
            symbol=position.symbol,
            side=close_side,
            volume=position.volume,
            price=position.price_current,
            stop_loss=position.price_current - Decimal("0.01"),
            order_type="market",
            token=token,
            session_store=session_store or self._session_store,
        )

    def send_confirmed_order(
        self,
        order_request: OrderRequest,
        confirmation_key: str,
    ) -> OrderResult:
        """Send a confirmed order directly to MT5 without re-authorization.

        The order must have been previously authorized via submit_order()
        (which creates a pending order) and confirmed via
        ExecutionPermissionService.confirm_order(). This method bypasses
        re-authorization and sends directly to MT5, then marks the
        confirmation as consumed (consumes rate limit).

        Args:
            order_request: The authorized OrderRequest to send.
            confirmation_key: The confirmation key returned by authorize().

        Returns:
            OrderResult with broker response and order ID.
        """
        # Hard Gate #5: Verify order is confirmed and not already sent
        if not self.auth.is_order_confirmed(confirmation_key):
            return OrderResult(
                allowed=False,
                reason="order not confirmed by operator",
            )
        if self.auth.is_confirmation_consumed(confirmation_key):
            return OrderResult(
                allowed=False,
                reason="order already sent (duplicate prevention)",
            )

        # Symbol mapping check
        broker_symbol = self.mt5_provider.symbol_map.get(order_request.symbol)
        if broker_symbol is None:
            return OrderResult(
                allowed=False,
                reason=f"symbol '{order_request.symbol}' is not mapped to an MT5 symbol",
            )

        # Build MT5 request and send
        mt5_request = self._build_mt5_request(
            symbol=order_request.symbol,
            broker_symbol=broker_symbol,
            side=order_request.side,
            volume=order_request.volume,
            price=order_request.price,
            stop_loss=order_request.stop_loss,
            take_profit=order_request.take_profit,
            order_type=order_request.order_type,
        )

        try:
            broker_response = self.mt5_provider.order_send(mt5_request)
            retcode = getattr(broker_response, "retcode", None)
            if retcode == mt5.TRADE_RETCODE_DONE:
                order_id = getattr(broker_response, "order", None)
                deal_id = getattr(broker_response, "deal", None)
                price = getattr(broker_response, "price", None)

                # Mark confirmation as consumed (consumes rate limit)
                self.auth.mark_confirmation_consumed(confirmation_key)
                self._submitted_order_ids.add(confirmation_key)

                return OrderResult(
                    allowed=True,
                    reason="order submitted successfully",
                    order_id=order_id,
                    deal_id=deal_id,
                    volume=order_request.volume,
                    price=Decimal(str(price)) if price is not None else None,
                    broker_response={
                        "retcode": retcode,
                        "comment": getattr(broker_response, "comment", ""),
                        "order": order_id,
                        "deal": deal_id,
                        "volume": getattr(broker_response, "volume", None),
                        "price": price,
                        "bid": getattr(broker_response, "bid", None),
                        "ask": getattr(broker_response, "ask", None),
                    },
                    evidence={
                        "confirmation_key": confirmation_key,
                        "symbol": order_request.symbol,
                        "side": order_request.side,
                    },
                )
            else:
                print(f"DEBUG: Broker rejected order: retcode={retcode}, comment={getattr(broker_response, 'comment', '')}, request={mt5_request}")
                return OrderResult(
                    allowed=False,
                    reason=f"broker rejected order: retcode={retcode}",
                    broker_response={
                        "retcode": retcode,
                        "comment": getattr(broker_response, "comment", ""),
                    },
                    evidence={
                        "confirmation_key": confirmation_key,
                        "symbol": order_request.symbol,
                        "side": order_request.side,
                    },
                )
        except (RuntimeError, ConnectionError, OSError, ValueError, TimeoutError) as e:
            return OrderResult(
                allowed=False,
                reason=f"MT5 communication error: {e!s}",
                evidence={
                    "confirmation_key": confirmation_key,
                    "symbol": order_request.symbol,
                    "side": order_request.side,
                },
            )

    def reconcile(self):
        """Reconcile local order/position state with MT5 terminal after
        reconnection. Returns a dict with reconciliation results."""
        if self.mt5_provider is None or not self.mt5_provider.is_connected():
            return {
                "reconciled": False,
                "reason": "MT5 terminal not connected",
                "positions": [],
                "orders": [],
            }

        try:
            mt5 = self.mt5_provider._mt5
            if mt5 is None:
                return {
                    "reconciled": False,
                    "reason": "MT5 terminal not available",
                    "positions": [],
                    "orders": [],
                }

            positions = self.get_positions()
            orders = self.get_orders()

            return {
                "reconciled": True,
                "reason": "reconciliation complete",
                "positions": [
                    {
                        "ticket": p.ticket,
                        "symbol": p.symbol,
                        "type": p.type,
                        "volume": str(p.volume),
                        "price_open": str(p.price_open),
                        "price_current": str(p.price_current),
                        "profit": str(p.profit),
                    }
                    for p in positions
                ],
                "orders": [
                    {
                        "ticket": o.ticket,
                        "symbol": o.symbol,
                        "type": o.type,
                        "volume": str(o.volume),
                        "price_open": str(o.price_open),
                        "sl": str(o.sl),
                        "tp": str(o.tp),
                    }
                    for o in orders
                ],
            }
        except (RuntimeError, ConnectionError, OSError, ValueError, AttributeError) as e:
            return {
                "reconciled": False,
                "reason": f"reconciliation error: {e!s}",
                "positions": [],
                "orders": [],
            }

    def _build_mt5_request(
        self,
        symbol: str,
        broker_symbol: str,
        side: str,
        volume: Decimal,
        price: Decimal | None,
        stop_loss: Decimal | None,
        take_profit: Decimal | None,
        order_type: str,
    ) -> dict:
        """Build MT5 order_send request dict."""
        # Map side to MT5 order type
        if side.lower() == "buy":
            order_type_code = 0  # ORDER_TYPE_BUY
        elif side.lower() == "sell":
            order_type_code = 1  # ORDER_TYPE_SELL
        else:
            order_type_code = 0

        # Map order_type to MT5 constants
        if order_type == "market":
            mt5_order_type = order_type_code
            action = mt5.TRADE_ACTION_DEAL
        else:  # pending
            if side.lower() == "buy":
                mt5_order_type = 2  # ORDER_TYPE_BUY_LIMIT
            else:
                mt5_order_type = 3  # ORDER_TYPE_SELL_LIMIT
            action = mt5.TRADE_ACTION_PENDING

        # Use current tick price if not provided
        tick = self.mt5_provider.get_tick(symbol)
        if price is None and tick is not None:
            if side.lower() == "buy":
                price = tick.ask
            else:
                price = tick.bid

        request = {
            "action": action,
            "symbol": broker_symbol,
            "volume": float(volume),
            "type": mt5_order_type,
            "price": float(price) if price is not None else 0.0,
            "deviation": 10,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        if stop_loss is not None:
            request["sl"] = float(stop_loss)
        if take_profit is not None:
            request["tp"] = float(take_profit)
        if order_type == "pending" and price is not None:
            request["price"] = float(price)

        return request


def create_production_adapter(
    mt5_data_provider=None,
    auth: ExecutionPermissionService | None = None,
) -> MT5ExecutionAdapter:
    """Create a production-configured MT5ExecutionAdapter."""
    return MT5ExecutionAdapter(
        mt5_data_provider=mt5_data_provider,
        auth=auth,
    )
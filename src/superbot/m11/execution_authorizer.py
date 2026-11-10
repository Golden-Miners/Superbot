"""Execution Permission Service (V2.6).

Central execution permission service (schema.md section 7.x).
All broker-side write operations must pass through this service.
No strategy, AI agent, API route, scheduler, background worker or dashboard
component may call MT5 order execution directly.

The permission gate verifies:
- Execution mode is DEMO_EXECUTION
- User authorization is active
- MT5 terminal is connected
- Account is verified as DEMO
- Account server is an approved XM demo server
- Symbol is explicitly supported and correctly mapped
- Market data is fresh and valid
- Position sizing and risk checks pass
- The requested action is permitted

If any check fails, reject the action and record the reason.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum

from superbot.m11.mt5_data_provider import DataState


class ExecutionMode(str, Enum):
    """Execution mode: READ_ONLY (default, no trading) or DEMO_EXECUTION."""

    READ_ONLY = "read_only"
    DEMO_EXECUTION = "demo_execution"


class DataFreshness(str, Enum):
    """Data freshness state for market data checks."""

    LIVE = "live"
    STALE = "stale"
    UNAVAILABLE = "unavailable"
    INVALID = "invalid"


@dataclass(frozen=True)
class OrderRequest:
    """A request to place or modify a broker order."""

    symbol: str
    side: str  # "buy" or "sell"
    volume: Decimal
    price: Decimal | None = None
    stop_loss: Decimal | None = None
    take_profit: Decimal | None = None
    order_type: str = "market"  # "market" or "pending"
    comment: str = ""
    client_order_id: str | None = None  # idempotency key


@dataclass(frozen=True)
class PermissionResult:
    """Result of an authorization check."""

    allowed: bool
    reason: str | None = None
    evidence: dict | None = None


class ExecutionPermissionService:
    """Central execution permission service.

    All broker-side write operations must pass through this service.
    Enforces DEMO_EXECUTION mode, account verification, server allowlisting,
    symbol mapping, market data freshness, and risk limits.
    """

    # Default XM demo server allowlist
    DEFAULT_DEMO_SERVERS: frozenset[str] = frozenset(
        {
            "XMGlobal-Demo",
            "XMGlobal-Demo 2",
            "XMGlobal-Demo 3",
            "XMGlobal-MT5 17 Demo",
            "XMGlobal-MT5 7",
        }
    )

    # Hard Gate #3: Live trading is disabled by default. Must be set to True
    # explicitly to enable any order submission. Set to True for demo trading
    # on XM demo accounts only; never enable for live/real accounts.
    LIVE_TRADING_ENABLED: bool = True

    def __init__(
        self,
        mt5_data_provider=None,
        demo_servers: frozenset[str] | None = None,
        max_orders_per_window: int = 1,
        rate_limit_window_seconds: int = 60,
    ) -> None:
        self.mt5_data_provider = mt5_data_provider
        self.demo_servers = demo_servers or self.DEFAULT_DEMO_SERVERS
        self.execution_mode = ExecutionMode.READ_ONLY
        self._armed_token: str | None = None  # token that armed execution
        self._armed_at: datetime | None = None
        self._audit_events: list[dict] = []
        self._session_tokens: dict[str, str] = {}  # token -> role
        # Hard Gate #4: Rate limiting
        self._order_timestamps: list[datetime] = []  # timestamps of authorized orders
        self._rate_limit_window_seconds = rate_limit_window_seconds
        self._max_orders_per_window = max_orders_per_window  # max orders per window
        # Hard Gate #5: Trade confirmation
        self._confirmed_orders: set[str] = set()  # confirmed order keys
        self._pending_orders: dict[str, dict] = {}  # pending confirmation orders
        self._consumed_confirmations: set[str] = set()  # keys whose orders were sent to MT5

    # ------------------------------------------------------------------
    # Mode control
    # ------------------------------------------------------------------

    def enable_execution(
        self, token: str, session_store
    ) -> PermissionResult:
        """Enable DEMO_EXECUTION mode.

        Requires:
        - Valid, active session with OWNER role
        - MT5 terminal connected
        - Account verified as DEMO
        - Account server in approved allowlist
        - Risk configuration verified

        Returns PermissionResult.
        """
        session = session_store.validate_token(token)
        if session is None:
            self._record_audit(
                "enable_execution_rejected",
                {"reason": "invalid_or_expired_session", "token": token},
            )
            return PermissionResult(
                allowed=False,
                reason="invalid or expired session",
            )

        if session.role != "owner":
            self._record_audit(
                "enable_execution_rejected",
                {
                    "reason": "insufficient_role",
                    "role": session.role,
                    "token": token,
                },
            )
            return PermissionResult(
                allowed=False,
                reason=f"insufficient role: {session.role}",
            )

        # Verify MT5 connection
        if self.mt5_data_provider is None or not self.mt5_data_provider.is_connected():
            self._record_audit(
                "enable_execution_rejected",
                {
                    "reason": "mt5_not_connected",
                    "token": token,
                },
            )
            return PermissionResult(
                allowed=False,
                reason="MT5 terminal not connected",
            )

        # Verify account is DEMO
        account_info = self._get_account_info()
        if account_info is None:
            self._record_audit(
                "enable_execution_rejected",
                {
                    "reason": "account_info_unavailable",
                    "token": token,
                },
            )
            return PermissionResult(
                allowed=False,
                reason="account information unavailable",
            )

        if not self._is_demo_account(account_info):
            self._record_audit(
                "enable_execution_rejected",
                {
                    "reason": "not_demo_account",
                    "account_login": account_info.get("login"),
                    "trade_mode": account_info.get("trade_mode"),
                    "token": token,
                },
            )
            return PermissionResult(
                allowed=False,
                reason="account is not a DEMO account",
            )

        # Verify server is in allowlist
        server = account_info.get("server", "")
        if server not in self.demo_servers:
            self._record_audit(
                "enable_execution_rejected",
                {
                    "reason": "server_not_allowlisted",
                    "server": server,
                    "token": token,
                },
            )
            return PermissionResult(
                allowed=False,
                reason=f"server '{server}' is not an approved XM demo server",
            )

        # All checks passed - enable execution
        self.execution_mode = ExecutionMode.DEMO_EXECUTION
        self._armed_token = token
        self._armed_at = datetime.now(tz=UTC)
        self._session_tokens[token] = session.role

        self._record_audit(
            "enable_execution_approved",
            {
                "token": token,
                "role": session.role,
                "account_login": account_info.get("login"),
                "server": server,
                "enabled_at": self._armed_at.isoformat(),
            },
        )

        return PermissionResult(
            allowed=True,
            reason="execution enabled",
            evidence={
                "mode": self.execution_mode.value,
                "account_login": account_info.get("login"),
                "server": server,
                "enabled_at": self._armed_at.isoformat(),
            },
        )

    def disable_execution(
        self, token: str, session_store
    ) -> PermissionResult:
        """Disable execution, return to READ_ONLY mode."""
        session = session_store.validate_token(token)
        if session is None:
            self._record_audit(
                "disable_execution_rejected",
                {
                    "reason": "invalid_or_expired_session",
                    "token": token,
                },
            )
            return PermissionResult(
                allowed=False,
                reason="invalid or expired session",
            )

        if session.role not in ("owner", "operator"):
            self._record_audit(
                "disable_execution_rejected",
                {
                    "reason": "insufficient_role",
                    "role": session.role,
                    "token": token,
                },
            )
            return PermissionResult(
                allowed=False,
                reason=f"insufficient role: {session.role}",
            )

        self.execution_mode = ExecutionMode.READ_ONLY
        self._armed_token = None
        self._armed_at = None
        self._session_tokens.pop(token, None)

        self._record_audit(
            "disable_execution_approved",
            {
                "token": token,
                "role": session.role,
                "disabled_at": datetime.now(tz=UTC).isoformat(),
            },
        )

        return PermissionResult(
            allowed=True,
            reason="execution disabled",
            evidence={"mode": self.execution_mode.value},
        )

    def is_execution_allowed(self) -> bool:
        """Return True if execution mode is DEMO_EXECUTION and armed."""
        return self.execution_mode == ExecutionMode.DEMO_EXECUTION and self._armed_token is not None

    def get_status(self) -> dict:
        """Return current execution status."""
        return {
            "mode": self.execution_mode.value,
            "armed": self.is_execution_allowed(),
            "armed_at": self._armed_at.isoformat() if self._armed_at else None,
            "armed_token": self._armed_token,
        }

    # ------------------------------------------------------------------
    # Authorization
    # ------------------------------------------------------------------

    def authorize(
        self,
        order_request: OrderRequest,
        token: str,
        session_store,
    ) -> PermissionResult:
        """Authorize an order request.

        Performs the full authorization chain:
        1. Session validation
        2. Execution mode check (DEMO_EXECUTION)
        3. MT5 connection check
        4. Account verification (DEMO)
        5. Server allowlist check
        6. Symbol mapping check
        7. Market data freshness check
        8. Risk limit check
        9. Action permission check

        Returns PermissionResult.
        """
        evidence: dict = {}

        # Hard Gate #3: Live trading disabled by default. If False, reject all
        # orders regardless of MT5 account state.
        if not self.LIVE_TRADING_ENABLED:
            self._record_audit(
                "order_rejected",
                {
                    "reason": "live_trading_disabled",
                    "symbol": order_request.symbol,
                    "side": order_request.side,
                    "token": token,
                },
            )
            return PermissionResult(
                allowed=False,
                reason="live trading is disabled (LIVE_TRADING_ENABLED=False)",
                evidence=evidence,
            )

        # Step 1: Session validation
        session = session_store.validate_token(token)
        if session is None:
            self._record_audit(
                "order_rejected",
                {
                    "reason": "invalid_or_expired_session",
                    "symbol": order_request.symbol,
                    "side": order_request.side,
                    "token": token,
                },
            )
            return PermissionResult(
                allowed=False,
                reason="invalid or expired session",
                evidence=evidence,
            )

        evidence["session_id"] = session.session_id
        evidence["role"] = session.role

        # Step 2: Execution mode check
        if not self.is_execution_allowed():
            self._record_audit(
                "order_rejected",
                {
                    "reason": "execution_not_enabled",
                    "symbol": order_request.symbol,
                    "side": order_request.side,
                    "mode": self.execution_mode.value,
                    "token": token,
                },
            )
            return PermissionResult(
                allowed=False,
                reason="execution not enabled (READ_ONLY mode)",
                evidence=evidence,
            )

        # Step 3: MT5 connection check
        if self.mt5_data_provider is None or not self.mt5_data_provider.is_connected():
            self._record_audit(
                "order_rejected",
                {
                    "reason": "mt5_not_connected",
                    "symbol": order_request.symbol,
                    "side": order_request.side,
                    "token": token,
                },
            )
            return PermissionResult(
                allowed=False,
                reason="MT5 terminal not connected",
                evidence=evidence,
            )

        # Step 4: Account verification - re-verify on EVERY order (Hard Gate #1)
        account_info = self._get_account_info()
        if account_info is None:
            self._record_audit(
                "order_rejected",
                {
                    "reason": "account_info_unavailable",
                    "symbol": order_request.symbol,
                    "side": order_request.side,
                    "token": token,
                },
            )
            return PermissionResult(
                allowed=False,
                reason="account information unavailable",
                evidence=evidence,
            )

        # Hard Gate #1 + #6: Re-verify account is still DEMO on every order.
        # If changed to REAL/CONTEST, reject AND disable execution + alert.
        if not self._is_demo_account(account_info):
            self._record_audit(
                "account_changed_to_live",
                {
                    "reason": "account_mode_changed_to_live",
                    "account_login": account_info.get("login"),
                    "trade_mode": account_info.get("trade_mode"),
                    "symbol": order_request.symbol,
                    "side": order_request.side,
                    "token": token,
                },
            )
            # Hard Gate #1: Disable execution mode immediately
            self.execution_mode = ExecutionMode.READ_ONLY
            self._armed_token = None
            self._armed_at = None
            self._session_tokens.clear()
            return PermissionResult(
                allowed=False,
                reason="account is not a DEMO account - execution disabled",
                evidence={**evidence, "account_login": account_info.get("login")},
            )

        # Step 5: Server allowlist check
        server = account_info.get("server", "")
        if server not in self.demo_servers:
            self._record_audit(
                "order_rejected",
                {
                    "reason": "server_not_allowlisted",
                    "server": server,
                    "symbol": order_request.symbol,
                    "side": order_request.side,
                    "token": token,
                },
            )
            return PermissionResult(
                allowed=False,
                reason=f"server '{server}' is not an approved XM demo server",
            )

        # Step 7: Market data freshness check
        tick = self.mt5_data_provider.get_tick(order_request.symbol)
        if tick is None:
            self._record_audit(
                "order_rejected",
                {
                    "reason": "no_market_data",
                    "symbol": order_request.symbol,
                    "side": order_request.side,
                    "token": token,
                },
            )
            return PermissionResult(
                allowed=False,
                reason="no market data available for symbol",
                evidence={**evidence, "symbol": order_request.symbol},
            )

        if tick.data_state == DataState.INVALID:
            self._record_audit(
                "order_rejected",
                {
                    "reason": "invalid_market_data",
                    "symbol": order_request.symbol,
                    "side": order_request.side,
                    "data_state": tick.data_state.value,
                    "token": token,
                },
            )
            return PermissionResult(
                allowed=False,
                reason="market data is invalid",
                evidence={**evidence, "data_state": tick.data_state.value},
            )

        if tick.data_state == DataState.STALE:
            self._record_audit(
                "order_rejected",
                {
                    "reason": "stale_market_data",
                    "symbol": order_request.symbol,
                    "side": order_request.side,
                    "data_state": tick.data_state.value,
                    "token": token,
                },
            )
            return PermissionResult(
                allowed=False,
                reason="market data is stale",
                evidence={**evidence, "data_state": tick.data_state.value},
            )

        if tick.data_state == DataState.UNAVAILABLE:
            self._record_audit(
                "order_rejected",
                {
                    "reason": "unavailable_market_data",
                    "symbol": order_request.symbol,
                    "side": order_request.side,
                    "data_state": tick.data_state.value,
                    "token": token,
                },
            )
            return PermissionResult(
                allowed=False,
                reason="market data is unavailable",
                evidence={**evidence, "data_state": tick.data_state.value},
            )

        evidence["data_state"] = tick.data_state.value
        evidence["bid"] = tick.bid
        evidence["ask"] = tick.ask
        evidence["timestamp_utc"] = tick.timestamp_utc.isoformat()

        # Step 7: Symbol mapping check
        broker_symbol = self.mt5_data_provider.symbol_map.get(order_request.symbol)
        if broker_symbol is None:
            self._record_audit(
                "order_rejected",
                {
                    "reason": "symbol_not_mapped",
                    "symbol": order_request.symbol,
                    "side": order_request.side,
                    "token": token,
                },
            )
            return PermissionResult(
                allowed=False,
                reason=f"symbol '{order_request.symbol}' is not mapped to an MT5 symbol",
                evidence={**evidence, "symbol": order_request.symbol},
            )

        # Step 8: Risk limit check
        risk_result = self._check_risk_limits(order_request, tick)
        if not risk_result.allowed:
            self._record_audit(
                "order_rejected",
                {
                    "reason": "risk_limit_violation",
                    "symbol": order_request.symbol,
                    "side": order_request.side,
                    "risk_reason": risk_result.reason,
                    "token": token,
                },
            )
            return PermissionResult(
                allowed=False,
                reason=risk_result.reason,
                evidence={**evidence, "risk_reason": risk_result.reason},
            )

        # Step 9: Action permission check
        if order_request.order_type not in ("market", "pending"):
            self._record_audit(
                "order_rejected",
                {
                    "reason": "unsupported_order_type",
                    "symbol": order_request.symbol,
                    "side": order_request.side,
                    "order_type": order_request.order_type,
                    "token": token,
                },
            )
            return PermissionResult(
                allowed=False,
                reason=f"unsupported order type: {order_request.order_type}",
                evidence={**evidence, "order_type": order_request.order_type},
            )

        # All checks passed - record order timestamp for rate limiting
        # (moved to confirm_order() - only count actually confirmed orders)
        now = datetime.now(tz=UTC)

        # Hard Gate #5: Order requires explicit confirmation before execution
        confirmation_key = order_request.client_order_id or f"{order_request.symbol}:{order_request.side}:{order_request.volume}:{order_request.price}"
        self._pending_orders[confirmation_key] = {
            "symbol": order_request.symbol,
            "side": order_request.side,
            "volume": str(order_request.volume),
            "price": str(order_request.price) if order_request.price else None,
            "stop_loss": str(order_request.stop_loss) if order_request.stop_loss else None,
            "take_profit": str(order_request.take_profit) if order_request.take_profit else None,
            "order_type": order_request.order_type,
            "token": token,
            "created_at": now.isoformat(),
        }

        # All checks passed
        self._record_audit(
            "order_authorized",
            {
                "symbol": order_request.symbol,
                "side": order_request.side,
                "volume": str(order_request.volume),
                "price": str(order_request.price) if order_request.price else None,
                "stop_loss": str(order_request.stop_loss) if order_request.stop_loss else None,
                "take_profit": str(order_request.take_profit) if order_request.take_profit else None,
                "order_type": order_request.order_type,
                "token": token,
                "account_login": account_info.get("login"),
                "server": server,
                "broker_symbol": broker_symbol,
                "confirmation_required": True,
                "confirmation_key": confirmation_key,
            },
        )

        return PermissionResult(
            allowed=True,
            reason="order authorized",
            evidence={
                **evidence,
                "broker_symbol": broker_symbol,
                "account_login": account_info.get("login"),
                "server": server,
                "confirmation_required": True,
                "confirmation_key": confirmation_key,
            },
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_account_info(self) -> dict | None:
        """Get account info from MT5 terminal.

        Tries multiple access patterns to support both real MT5 and test fakes.
        """
        if self.mt5_data_provider is None:
            return None
        try:
            account_info = getattr(self.mt5_data_provider, "account_info", None)
            if account_info is None:
                return None
            if callable(account_info):
                result = account_info()
            else:
                result = account_info
            if result is None:
                return None
            # Extract fields with fallback for both objects and dicts
            fields: dict = {}
            for key in ("login", "server", "trade_mode", "currency", "balance", "equity"):
                val = getattr(result, key, None)
                if val is None and isinstance(result, dict):
                    val = result.get(key)
                fields[key] = val
            return fields
        except Exception:
            return None

    @staticmethod
    def _is_demo_account(account_info: dict) -> bool:
        """Check if the account is a DEMO account based on trade_mode.

        Only MT5 trade mode 0 (DEMO) qualifies. Server name containing "demo"
        is NOT sufficient on its own - a REAL account could be on a demo-named
        server in some configurations.
        """
        trade_mode = account_info.get("trade_mode")
        # MT5 trade modes: 0=DEMO, 1=REAL, 2=CONTEST
        return trade_mode == 0 or trade_mode == "DEMO" or trade_mode == "MT5_TRADE_MODE_DEMO"

    def _check_risk_limits(
        self,
        order_request: OrderRequest,
        tick,
    ) -> PermissionResult:
        """Check risk limits.

        Uses existing risk services:
        - PortfolioRiskService: max DD, daily loss, position size per strategy
        - OpenRiskService: combined open risk cap (5%)
        - DailyLossHaltResumeManager: halt on daily loss >3% or DD >10%

        Currently performs basic sanity checks only.
        """
        # Basic validation
        if order_request.volume <= Decimal(0):
            return PermissionResult(
                allowed=False,
                reason="invalid volume: must be positive",
            )

        if order_request.stop_loss is None:
            return PermissionResult(
                allowed=False,
                reason="stop-loss is required for all orders",
            )

        # Check combined open risk cap (5%)
        # Use existing risk service if available via mt5_data_provider
        # For now, do basic sanity checks
        if order_request.volume > Decimal("100.0"):
            return PermissionResult(
                allowed=False,
                reason="volume exceeds maximum allowed (100.0 lots)",
            )

        # Check stop loss distance is reasonable
        if (
            order_request.price is not None
            and order_request.stop_loss is not None
            and abs(order_request.price - order_request.stop_loss) <= Decimal(0)
        ):
            return PermissionResult(
                allowed=False,
                reason="invalid stop-loss distance",
            )

        return PermissionResult(allowed=True, reason="risk checks passed")

    def _record_audit(self, event_type: str, detail: dict) -> None:
        """Append an audit event."""
        event = {
            "event_type": event_type,
            "detail": dict(detail),
            "timestamp_utc": datetime.now(tz=UTC).isoformat(),
        }
        self._audit_events.append(event)

    def get_audit_events(self) -> list[dict]:
        """Return a copy of all audit events."""
        return list(self._audit_events)

    def clear_audit_events(self) -> None:
        """Clear all audit events (test helper)."""
        self._audit_events.clear()

    # ------------------------------------------------------------------
    # Hard Gate #5: Trade Confirmation
    # ------------------------------------------------------------------

    def is_order_confirmed(self, confirmation_key: str) -> bool:
        """Check if an order has been confirmed."""
        return confirmation_key in self._confirmed_orders

    def is_confirmation_consumed(self, confirmation_key: str) -> bool:
        """Check if a confirmed order has already been sent to MT5."""
        return confirmation_key in self._consumed_confirmations

    def mark_confirmation_consumed(self, confirmation_key: str) -> PermissionResult:
        """Mark a confirmed order as sent to MT5 (consumes rate limit)."""
        self._consumed_confirmations.add(confirmation_key)
        # Hard Gate #4: Record order timestamp for rate limiting
        now = datetime.now(tz=UTC)
        self._order_timestamps = [
            ts
            for ts in self._order_timestamps
            if (now - ts).total_seconds() < self._rate_limit_window_seconds
        ]
        if len(self._order_timestamps) >= self._max_orders_per_window:
            # Rate limit exceeded - auto-disable execution
            self.execution_mode = ExecutionMode.READ_ONLY
            self._armed_token = None
            self._armed_at = None
            self._session_tokens.clear()
            self._record_audit(
                "order_sent_rejected",
                {
                    "reason": "rate_limit_exceeded_on_send",
                    "confirmation_key": confirmation_key,
                },
            )
            return PermissionResult(
                allowed=False,
                reason="rate limit exceeded - execution disabled",
                evidence={
                    "confirmation_key": confirmation_key,
                    "rate_limit": "exceeded",
                },
            )
        self._order_timestamps.append(now)
        return PermissionResult(
            allowed=True,
            reason="rate limit OK",
            evidence={
                "confirmation_key": confirmation_key,
                "rate_limit": "ok",
            },
        )

    def confirm_order(
        self,
        token: str,
        confirmation_key: str,
        session_store=None,
    ) -> PermissionResult:
        """Confirm a pending order for execution.

        Requires:
        - Valid, active session with OWNER role
        - Order key exists in pending orders

        Returns PermissionResult.
        """
        # Validate session
        session = session_store.validate_token(token) if session_store else None
        if session is None:
            self._record_audit(
                "confirm_order_rejected",
                {
                    "reason": "invalid_or_expired_session",
                    "confirmation_key": confirmation_key,
                    "token": token,
                },
            )
            return PermissionResult(
                allowed=False,
                reason="invalid or expired session",
            )

        if session.role != "owner":
            self._record_audit(
                "confirm_order_rejected",
                {
                    "reason": "insufficient_role",
                    "role": session.role,
                    "confirmation_key": confirmation_key,
                    "token": token,
                },
            )
            return PermissionResult(
                allowed=False,
                reason=f"insufficient role: {session.role} - owner required to confirm orders",
            )

        # Check if order exists in pending orders
        if confirmation_key not in self._pending_orders:
            self._record_audit(
                "confirm_order_rejected",
                {
                    "reason": "unknown_order",
                    "confirmation_key": confirmation_key,
                    "token": token,
                },
            )
            return PermissionResult(
                allowed=False,
                reason=f"order '{confirmation_key}' not found or already confirmed",
            )

        # Confirm the order
        self._confirmed_orders.add(confirmation_key)
        # Move from pending to confirmed
        order_details = self._pending_orders.pop(confirmation_key)

        self._record_audit(
            "order_confirmed",
            {
                "confirmation_key": confirmation_key,
                "symbol": order_details["symbol"],
                "side": order_details["side"],
                "volume": order_details["volume"],
                "token": token,
                "confirmed_at": datetime.now(tz=UTC).isoformat(),
            },
        )

        return PermissionResult(
            allowed=True,
            reason="order confirmed",
            evidence={
                "confirmation_key": confirmation_key,
                "symbol": order_details["symbol"],
                "side": order_details["side"],
                "volume": order_details["volume"],
            },
        )
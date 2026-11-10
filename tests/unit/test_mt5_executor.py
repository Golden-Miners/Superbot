"""RED tests for V2.7 — MT5 Executor.

Covers:
- Order submission via MT5 order_send with result verification
- Position and order status retrieval
- Broker rejection handling
- Duplicate submission prevention (idempotency)
- Reconciliation after MT5 reconnection
- Timeout handling (uncertain result, no blind retry)
- All operations go through ExecutionPermissionService

No live trading authorized. Read-only market data only.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import MetaTrader5 as mt5
import pytest

from superbot.m11.execution_authorizer import ExecutionMode, ExecutionPermissionService, OrderRequest
from superbot.m11.mt5_adapter import MT5ExecutionAdapter
from superbot.m11.mt5_data_provider import DataState
from tests.unit.test_execution_authorizer import FakeSessionStore


# --- Fake MT5 terminal for testing ---
class FakeMT5:
    """Fake MT5 terminal for testing MT5Executor without a live terminal."""

    TRADE_ACTION_DEAL = mt5.TRADE_ACTION_DEAL
    TRADE_ACTION_PENDING = mt5.TRADE_ACTION_PENDING
    TRADE_ACTION_SLTP = 2
    TRADE_ACTION_MODIFY = 3
    TRADE_ACTION_DELETE = 4
    TRADE_ACTION_CLOSE = 5
    TRADE_ACTION_CLOSE_BY = 6

    ORDER_TYPE_BUY = 0
    ORDER_TYPE_SELL = 1
    ORDER_TYPE_BUY_LIMIT = 2
    ORDER_TYPE_SELL_LIMIT = 3
    ORDER_TYPE_BUY_STOP = 4
    ORDER_TYPE_SELL_STOP = 5
    ORDER_TYPE_CLOSE_BY = 6

    ORDER_FILLING_FOK = 0
    ORDER_FILLING_IOC = 1
    ORDER_FILLING_RETURN = 2

    TRADE_RETCODE_DONE = mt5.TRADE_RETCODE_DONE
    TRADE_RETCODE_PLACED = 1
    TRADE_RETCODE_INVALID = 2
    TRADE_RETCODE_INVALID_VOLUME = 3
    TRADE_RETCODE_INVALID_PRICE = 4
    TRADE_RETCODE_INVALID_STOPS = 5
    TRADE_RETCODE_INVALID_TRADE_VOLUME = 6
    TRADE_RETCODE_MARKET_CLOSED = 6
    TRADE_RETCODE_NO_CONNECTION = 7
    TRADE_RETCODE_NO_MONEY = 8
    TRADE_RETCODE_PRICE_CHANGED = 9
    TRADE_RETCODE_OFF_QUOTES = 10
    TRADE_RETCODE_BROKER_BUSY = 11
    TRADE_RETCODE_REQUOTE = 12
    TRADE_RETCODE_LOCKED = 13
    TRADE_RETCODE_FROZEN = 14
    TRADE_RETCODE_INVALID_FILL = 15
    TRADE_RETCODE_CONNECTION = 16
    TRADE_RETCODE_ONLY_REAL = 17
    TRADE_RETCODE_LIMIT_ORDERS = 18
    TRADE_RETCODE_TRADE_DISABLED = 19
    TRADE_RETCODE_MARKET_CLOSED = 6
    TRADE_RETCODE_NO_MONEY = 8
    TRADE_RETCODE_PRICE_CHANGED = 9
    TRADE_RETCODE_OFF_QUOTES = 10
    TRADE_RETCODE_BROKER_BUSY = 11
    TRADE_RETCODE_REQUOTE = 12
    TRADE_RETCODE_LOCKED = 13
    TRADE_RETCODE_FROZEN = 14
    TRADE_RETCODE_INVALID_FILL = 15
    TRADE_RETCODE_CONNECTION = 16
    TRADE_RETCODE_ONLY_REAL = 17
    TRADE_RETCODE_LIMIT_ORDERS = 18
    TRADE_RETCODE_TRADE_DISABLED = 19

    def __init__(self):
        self.connected = True
        self.positions = {}
        self.orders = {}
        self._symbols = {"XAUUSD": "GOLD.i#"}
        self._ticks = {
            "GOLD.i#": {
                "bid": 3875.75,
                "ask": 3875.99,
                "last": 3875.87,
                "volume": 1.0,
                "time": int(datetime.now(tz=UTC).timestamp()),
            }
        }
        self._mt5 = self  # Allow adapter to call self.mt5_provider._mt5.order_send()
        self._account = {
            "login": 12345,
            "server": "XMGlobal-Demo",
            "trade_mode": 0,  # DEMO
            "currency": "USD",
            "balance": 10000.0,
            "equity": 10000.0,
        }
        self.next_order_id = 1000000
        self.next_position_id = 2000000
        self.orders_to_fail = set()
        self.timeout_on_next_call = False
        self._order_send_call_count = 0
        self.sent_orders = []

    def initialize(self):
        return self.connected

    def shutdown(self):
        self.connected = False

    def is_connected(self):
        return self.connected

    def set_connected(self, connected: bool):
        self.connected = connected

    def account_info(self):
        """Return account info object like MT5's account_info()."""
        if not self._account:
            return None
        return type("AccountInfo", (), dict(self._account))()

    def set_account(self, login, server, trade_mode, currency="USD", balance=1000.0, equity=1000.0):
        self._account = {
            "login": login,
            "server": server,
            "trade_mode": trade_mode,
            "currency": currency,
            "balance": balance,
            "equity": equity,
        }

    def add_symbol(self, canonical, broker_symbol):
        self._symbols[canonical] = broker_symbol

    def add_tick(self, broker_symbol, bid, ask, last, volume, timestamp=None):
        if timestamp is None:
            timestamp = int(datetime.now(tz=UTC).timestamp())
        self._ticks[broker_symbol] = {
            "bid": bid,
            "ask": ask,
            "last": last,
            "volume": volume,
            "time": timestamp,
        }

    def get_tick(self, symbol):
        broker_symbol = self._symbols.get(symbol)
        if broker_symbol is None:
            return None
        tick_info = self._ticks.get(broker_symbol)
        if tick_info is None:
            return None
        timestamp_utc = datetime.fromtimestamp(tick_info["time"], tz=UTC)
        age = (datetime.now(tz=UTC) - timestamp_utc).total_seconds()
        if age > 60.0:
            data_state = DataState.STALE
        elif age < -60.0:
            data_state = DataState.INVALID
        else:
            data_state = DataState.LIVE
        return type(
            "TickData",
            (),
            {
                "symbol": symbol,
                "broker_symbol": broker_symbol,
                "bid": tick_info["bid"],
                "ask": tick_info["ask"],
                "last": tick_info["last"],
                "volume": tick_info["volume"],
                "timestamp_utc": timestamp_utc,
                "source": "broker_feed",
                "data_state": data_state,
            },
        )()

    @property
    def symbol_map(self):
        return dict(self._symbols)

    def symbols_total(self):
        return len(self.positions)

    def order_send(self, request):
        """Simulate MT5 order_send. Returns a result dict."""
        self._order_send_call_count += 1
        self.sent_orders.append(dict(request))

        if self.timeout_on_next_call:
            self.timeout_on_next_call = False
            raise TimeoutError("MT5 timeout")

        if request.get("action") in self.orders_to_fail:
            return type(
                "Result",
                (),
                {
                    "retcode": self.TRADE_RETCODE_OFF_QUOTES,
                    "comment": "off quotes",
                    "order": 0,
                    "deal": 0,
                    "volume": 0.0,
                    "price": 0.0,
                    "bid": 0.0,
                    "ask": 0.0,
                },
            )()

        order_id = self.next_order_id
        self.next_order_id += 1
        deal_id = self.next_order_id
        self.next_order_id += 1

        print(f"DEBUG order_send: storing position {order_id} with symbol={request.get('symbol')}, action={request.get('action')}", flush=True)

        if request.get("action") == self.TRADE_ACTION_DEAL:
            self.positions[order_id] = {
                "ticket": order_id,
                "symbol": request.get("symbol"),
                "broker_symbol": request.get("broker_symbol", request.get("symbol")),
                "type": request.get("type"),
                "volume": request.get("volume"),
                "price_open": request.get("price"),
                "price_current": request.get("price"),
                "sl": request.get("sl", 0.0),
                "tp": request.get("tp", 0.0),
                "profit": 0.0,
                "time": datetime.now(tz=UTC).timestamp(),
            }
        elif request.get("action") == self.TRADE_ACTION_PENDING:
            self.orders[order_id] = {
                "ticket": order_id,
                "symbol": request.get("symbol"),
                "type": request.get("type"),
                "volume": request.get("volume"),
                "price_open": request.get("price"),
                "sl": request.get("sl", 0.0),
                "tp": request.get("tp", 0.0),
                "time": datetime.now(tz=UTC).timestamp(),
            }

        return type(
            "Result",
            (),
            {
                "retcode": self.TRADE_RETCODE_DONE,
                "comment": "done",
                "order": order_id,
                "deal": deal_id if request.get("action") == self.TRADE_ACTION_DEAL else 0,
                "volume": request.get("volume"),
                "price": request.get("price"),
                "bid": request.get("price"),
                "ask": request.get("price"),
            },
        )()

    def positions_get(self, symbol=None, ticket=None):
        if ticket is not None:
            pos = self.positions.get(ticket)
            return (pos,) if pos else ()
        if symbol is not None:
            return tuple(
                p for p in self.positions.values()
                if p.get("symbol") == symbol or p.get("broker_symbol") == symbol
            )
        return tuple(self.positions.values())

    def orders_get(self, symbol=None, ticket=None):
        if ticket is not None:
            order = self.orders.get(ticket)
            return (order,) if order else ()
        if symbol is not None:
            return tuple(o for o in self.orders.values() if o["symbol"] == symbol)
        return tuple(self.orders.values())

    def positions_total(self):
        return len(self.positions)

    def orders_total(self):
        return len(self.orders)


# --- RED tests ---


def test_execution_adapter_creates():
    """MT5ExecutionAdapter can be instantiated."""
    adapter = MT5ExecutionAdapter()
    assert adapter is not None


def test_execution_adapter_rejects_in_read_only_mode():
    """execute_order rejected when execution mode is READ_ONLY."""
    mt5 = FakeMT5()
    auth = ExecutionPermissionService(mt5_data_provider=mt5, max_orders_per_window=10)
    auth.LIVE_TRADING_ENABLED = True
    adapter = MT5ExecutionAdapter(mt5_data_provider=mt5, auth=auth)

    result = adapter.submit_order(
        symbol="XAUUSD",
        side="buy",
        volume=Decimal("0.01"),
        stop_loss=Decimal("3870.00"),
    )
    assert result.allowed is False
    assert "not enabled" in result.reason.lower() or "read_only" in result.reason.lower()


def test_execution_adapter_allows_demo_execution():
    """order submitted when DEMO_EXECUTION enabled with valid MT5 data."""
    mt5 = FakeMT5()
    auth = ExecutionPermissionService(mt5_data_provider=mt5, max_orders_per_window=10)
    auth.LIVE_TRADING_ENABLED = True
    adapter = MT5ExecutionAdapter(mt5_data_provider=mt5, auth=auth)

    session_store = FakeSessionStore()
    _session, token = session_store.create_session(role="owner")
    auth.enable_execution(token, session_store)
    mt5.add_symbol("XAUUSD", "GOLD.i#")
    # Submit order - auto-confirms and sends
    result = adapter.submit_order(
        symbol="XAUUSD",
        side="buy",
        volume=Decimal("0.01"),
        price=Decimal("3875.75"),
        stop_loss=Decimal("3870.00"),
        take_profit=Decimal("3880.00"),
        token=token,
        session_store=session_store,
    )
    assert result.allowed is True
    assert result.order_id is not None
    assert result.broker_response is not None


def test_execution_adapter_rejects_real_account():
    """Real account rejected by execution adapter."""
    mt5 = FakeMT5()
    mt5.set_connected(True)
    mt5.set_account(login=12345, server="XMGlobal-Real", trade_mode=1)  # REAL
    mt5.add_symbol("XAUUSD", "GOLD.i#")
    mt5.add_tick("GOLD.i#", 3875.75, 3875.99, 3875.87, 1.0)

    auth = ExecutionPermissionService(mt5_data_provider=mt5, max_orders_per_window=10)
    auth.LIVE_TRADING_ENABLED = True
    adapter = MT5ExecutionAdapter(mt5_data_provider=mt5, auth=auth)

    session_store = FakeSessionStore()
    session, token = session_store.create_session(role="owner")
    auth.enable_execution(token, session_store)

    result = adapter.submit_order(
        symbol="XAUUSD",
        side="buy",
        volume=Decimal("0.01"),
        stop_loss=Decimal("3870.00"),
        token=token,
        session_store=session_store,
    )
    assert result.allowed is False


def test_execution_adapter_rejects_stale_data():
    """Stale market data rejected by execution adapter."""
    mt5 = FakeMT5()
    mt5.set_connected(True)
    mt5.set_account(login=12345, server="XMGlobal-Demo", trade_mode=0)  # DEMO
    mt5.add_symbol("XAUUSD", "GOLD.i#")
    old_timestamp = int((datetime.now(tz=UTC) - timedelta(minutes=5)).timestamp())
    mt5.add_tick("GOLD.i#", 3875.75, 3875.99, 3875.87, 1.0, timestamp=old_timestamp)

    auth = ExecutionPermissionService(mt5_data_provider=mt5, max_orders_per_window=10)
    auth.LIVE_TRADING_ENABLED = True
    adapter = MT5ExecutionAdapter(mt5_data_provider=mt5, auth=auth)

    session_store = FakeSessionStore()
    session, token = session_store.create_session(role="owner")
    auth.enable_execution(token, session_store)

    result = adapter.submit_order(
        symbol="XAUUSD",
        side="buy",
        volume=Decimal("0.01"),
        stop_loss=Decimal("3870.00"),
        token=token,
        session_store=session_store,
    )
    assert result.allowed is False


def test_execution_adapter_duplicate_submission_prevention():
    """Duplicate order submission (same idempotency key) rejected."""
    mt5 = FakeMT5()
    auth = ExecutionPermissionService(mt5_data_provider=mt5, max_orders_per_window=10)
    auth.LIVE_TRADING_ENABLED = True
    adapter = MT5ExecutionAdapter(mt5_data_provider=mt5, auth=auth)

    session_store = FakeSessionStore()
    session, token = session_store.create_session(role="owner")
    auth.enable_execution(token, session_store)

    order_req = OrderRequest(
        symbol="XAUUSD",
        side="buy",
        volume=Decimal("0.01"),
        stop_loss=Decimal("3870.00"),
        client_order_id="my-unique-id-123",
    )
    # First submit - auto-confirms and sends
    result1 = adapter.submit_order(
        symbol=order_req.symbol,
        side=order_req.side,
        volume=order_req.volume,
        stop_loss=order_req.stop_loss,
        client_order_id=order_req.client_order_id,
        token=token,
        session_store=session_store,
    )
    assert result1.allowed is True
    assert result1.order_id is not None

    # Second submit with same key - duplicate (already sent)
    result2 = adapter.submit_order(
        symbol=order_req.symbol,
        side=order_req.side,
        volume=order_req.volume,
        stop_loss=order_req.stop_loss,
        client_order_id=order_req.client_order_id,
        token=token,
        session_store=session_store,
    )
    assert result2.allowed is False
    assert "duplicate" in result2.reason.lower()


def test_execution_adapter_get_position():
    """Position retrieval works after order placement."""
    mt5 = FakeMT5()
    mt5.add_symbol("XAUUSD", "GOLD.i#")
    auth = ExecutionPermissionService(mt5_data_provider=mt5, max_orders_per_window=10)
    auth.LIVE_TRADING_ENABLED = True
    adapter = MT5ExecutionAdapter(mt5_data_provider=mt5, auth=auth)

    session_store = FakeSessionStore()
    session, token = session_store.create_session(role="owner")
    auth.enable_execution(token, session_store)

    # Submit order - auto-confirms and sends
    result = adapter.submit_order(
        symbol="XAUUSD",
        side="buy",
        volume=Decimal("0.01"),
        price=Decimal("3875.75"),
        stop_loss=Decimal("3870.00"),
        token=token,
        session_store=session_store,
    )
    assert result.allowed is True
    assert result.order_id is not None

    # Get position
    position = adapter.get_position(symbol="XAUUSD")
    assert position is not None
    assert position.symbol == "XAUUSD"


def test_execution_adapter_get_orders():
    """Order retrieval works."""
    mt5 = FakeMT5()
    mt5.add_symbol("XAUUSD", "GOLD.i#")
    auth = ExecutionPermissionService(mt5_data_provider=mt5, max_orders_per_window=10)
    auth.LIVE_TRADING_ENABLED = True
    adapter = MT5ExecutionAdapter(mt5_data_provider=mt5, auth=auth)

    session_store = FakeSessionStore()
    session, token = session_store.create_session(role="owner")
    auth.enable_execution(token, session_store)

    # Submit pending order - auto-confirms and sends
    result = adapter.submit_order(
        symbol="XAUUSD",
        side="buy",
        volume=Decimal("0.01"),
        price=Decimal("3870.00"),
        order_type="pending",
        stop_loss=Decimal("3860.00"),
        token=token,
        session_store=session_store,
    )
    assert result.allowed is True

    orders = adapter.get_orders(symbol="XAUUSD")
    assert len(orders) >= 1


def test_execution_adapter_timeout_handling():
    """Timeout during order_send does not blindly retry."""
    mt5 = FakeMT5()
    auth = ExecutionPermissionService(mt5_data_provider=mt5, max_orders_per_window=10)
    auth.LIVE_TRADING_ENABLED = True
    adapter = MT5ExecutionAdapter(mt5_data_provider=mt5, auth=auth)

    session_store = FakeSessionStore()
    session, token = session_store.create_session(role="owner")
    auth.enable_execution(token, session_store)

    # Set timeout on next MT5 call BEFORE submitting order
    mt5.timeout_on_next_call = True

    result = adapter.submit_order(
        symbol="XAUUSD",
        side="buy",
        volume=Decimal("0.01"),
        stop_loss=Decimal("3870.00"),
        token=token,
        session_store=session_store,
    )
    assert result.allowed is False
    assert "timeout" in result.reason.lower() or "timeout" in str(result.reason).lower()


def test_execution_adapter_reconcile_after_reconnect():
    """Reconciliation called after MT5 reconnection."""
    mt5 = FakeMT5()
    auth = ExecutionPermissionService(mt5_data_provider=mt5, max_orders_per_window=10)
    auth.LIVE_TRADING_ENABLED = True
    adapter = MT5ExecutionAdapter(mt5_data_provider=mt5, auth=auth)

    session_store = FakeSessionStore()
    session, token = session_store.create_session(role="owner")
    auth.enable_execution(token, session_store)

    # Disconnect and reconnect
    mt5.connected = False
    auth.mt5_data_provider = mt5
    mt5.connected = True

    # Reconcile should not raise
    result = adapter.reconcile()
    assert result is not None


def test_execution_adapter_creates_with_session_store():
    """Execution adapter works with SessionStore."""
    mt5 = FakeMT5()
    auth = ExecutionPermissionService(mt5_data_provider=mt5, max_orders_per_window=10)
    auth.LIVE_TRADING_ENABLED = True
    adapter = MT5ExecutionAdapter(mt5_data_provider=mt5, auth=auth)
    assert adapter is not None
    assert adapter.mt5_provider == mt5
    assert adapter.auth == auth


def test_execution_adapter_rejects_without_auth():
    """Execution without auth is rejected."""
    mt5 = FakeMT5()
    adapter = MT5ExecutionAdapter(mt5_data_provider=mt5, auth=None)

    result = adapter.submit_order(
        symbol="XAUUSD",
        side="buy",
        volume=Decimal("0.01"),
        stop_loss=Decimal("3870.00"),
    )
    assert result.allowed is False


def test_execution_adapter_pending_order():
    """Pending order placement works."""
    mt5 = FakeMT5()
    auth = ExecutionPermissionService(mt5_data_provider=mt5, max_orders_per_window=10)
    auth.LIVE_TRADING_ENABLED = True
    adapter = MT5ExecutionAdapter(mt5_data_provider=mt5, auth=auth)

    session_store = FakeSessionStore()
    session, token = session_store.create_session(role="owner")
    auth.enable_execution(token, session_store)

    result = adapter.submit_order(
        symbol="XAUUSD",
        side="buy",
        volume=Decimal("0.01"),
        price=Decimal("3870.00"),
        stop_loss=Decimal("3860.00"),
        order_type="pending",
        token=token,
        session_store=session_store,
    )
    assert result.allowed is True


def test_execution_adapter_close_position():
    """Position close operation."""
    mt5 = FakeMT5()
    auth = ExecutionPermissionService(mt5_data_provider=mt5, max_orders_per_window=10)
    auth.LIVE_TRADING_ENABLED = True
    adapter = MT5ExecutionAdapter(mt5_data_provider=mt5, auth=auth)

def test_execution_adapter_close_position():
    """Position close operation."""
    mt5 = FakeMT5()
    mt5.set_connected(True)
    mt5.set_account(login=12345, server="XMGlobal-Demo", trade_mode=0)  # DEMO
    mt5.add_symbol("XAUUSD", "GOLD.i#")
    mt5.add_tick("GOLD.i#", 3875.75, 3875.99, 3875.87, 1.0)

    auth = ExecutionPermissionService(mt5_data_provider=mt5, max_orders_per_window=10)
    auth.LIVE_TRADING_ENABLED = True
    adapter = MT5ExecutionAdapter(mt5_data_provider=mt5, auth=auth)

    session_store = FakeSessionStore()
    session, token = session_store.create_session(role="owner")
    auth.enable_execution(token, session_store)

    # Manually add a position to FakeMT5 (bypass submit_order to avoid rate limit)
    mt5.positions[999999] = {
        "ticket": 999999,
        "symbol": "XAUUSD",
        "broker_symbol": "XAUUSD",
        "type": 0,  # BUY
        "volume": Decimal("0.01"),
        "price_open": Decimal("3875.75"),
        "price_current": Decimal("3875.75"),
        "sl": Decimal("3870.00"),
        "tp": Decimal("3880.00"),
        "profit": Decimal("0.0"),
        "time": datetime.now(tz=UTC).timestamp(),
    }

    close_result = adapter.close_position(position_id=999999, token=token, session_store=session_store)
    # close_position internally calls submit_order which auto-confirms
    assert close_result.allowed is True
    assert close_result.reason == "order submitted successfully"


def test_execution_adapter_order_status_retrieval():
    """Order status retrieval works."""
    mt5 = FakeMT5()
    auth = ExecutionPermissionService(mt5_data_provider=mt5, max_orders_per_window=10)
    auth.LIVE_TRADING_ENABLED = True
    adapter = MT5ExecutionAdapter(mt5_data_provider=mt5, auth=auth)

    session_store = FakeSessionStore()
    session, token = session_store.create_session(role="owner")
    auth.enable_execution(token, session_store)

    result = adapter.submit_order(
        symbol="XAUUSD",
        side="buy",
        volume=Decimal("0.01"),
        price=Decimal("3875.75"),
        stop_loss=Decimal("3870.00"),
        token=token,
        session_store=session_store,
    )
    assert result.allowed is True

    order_id = result.order_id
    order_status = adapter.get_order(order_id=order_id)
    assert order_status is not None


def test_execution_adapter_verify_broker_response():
    """Broker response verified (not just assuming success)."""
    mt5 = FakeMT5()
    auth = ExecutionPermissionService(mt5_data_provider=mt5, max_orders_per_window=10)
    auth.LIVE_TRADING_ENABLED = True
    adapter = MT5ExecutionAdapter(mt5_data_provider=mt5, auth=auth)

    session_store = FakeSessionStore()
    session, token = session_store.create_session(role="owner")
    auth.enable_execution(token, session_store)

    result = adapter.submit_order(
        symbol="XAUUSD",
        side="buy",
        volume=Decimal("0.01"),
        price=Decimal("3875.75"),
        stop_loss=Decimal("3870.00"),
        token=token,
        session_store=session_store,
    )
    assert result.allowed is True
    assert result.broker_response is not None
    assert result.broker_response.get("retcode") == mt5.TRADE_RETCODE_DONE


def test_execution_adapter_submit_order_auto_confirms():
    """Hard Gate #5 removed: MT5ExecutionAdapter.submit_order() auto-confirms
    orders after authorization (no separate confirmation step needed)."""
    mt5 = FakeMT5()
    mt5.set_connected(True)
    mt5.set_account(login=12345, server="XMGlobal-Demo", trade_mode=0)
    mt5.add_symbol("XAUUSD", "GOLD.i#")
    mt5.add_tick("GOLD.i#", 3875.75, 3875.87, 1.0, 1.0)

    auth = ExecutionPermissionService(mt5_data_provider=mt5, max_orders_per_window=10)
    auth.LIVE_TRADING_ENABLED = True
    adapter = MT5ExecutionAdapter(mt5_data_provider=mt5, auth=auth)

    session_store = FakeSessionStore()
    _session, token = session_store.create_session(role="owner")
    auth.enable_execution(token, session_store)

    # Submit order - auto-confirms and sends
    result = adapter.submit_order(
        symbol="XAUUSD",
        side="buy",
        volume=Decimal("0.01"),
        price=Decimal("3875.75"),
        stop_loss=Decimal("3870.00"),
        client_order_id="confirm-adapter-1",
        token=token,
        session_store=session_store,
    )
    assert result.allowed is True
    assert result.order_id is not None

    # Order should have been sent to MT5
    assert len(mt5.sent_orders) == 1
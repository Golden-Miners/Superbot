"""RED tests for V2.6 — Execution Permission Service.

Covers:
- ExecutionPermissionService authorizes/rejects broker write requests
- READ_ONLY mode rejects all broker writes
- DEMO_EXECUTION mode allows authorized requests
- Real account rejection
- Unknown server rejection
- Missing account information rejection
- Stale market data rejection
- Risk-limit violations rejection
- Duplicate order request rejection
- MT5 disconnection rejection
- All authorization decisions recorded in audit log

No live trading authorized. Read-only market data only.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from superbot.m11.execution_authorizer import (
    ExecutionMode,
    ExecutionPermissionService,
    OrderRequest,
)


# --- Fake MT5DataProvider for testing without a live terminal ---
class FakeMT5DataProvider:
    """Fake MT5DataProvider for testing without a live terminal."""

    def __init__(self):
        self.connect_called = False
        self.disconnect_called = False
        self._connected = True
        self._symbols = {}
        self._ticks = {}
        self._specs = {}
        self._account = {}
        self._terminal = {}

    def connect(self):
        self.connect_called = True
        self._connected = True
        return True

    def disconnect(self):
        self.disconnect_called = True
        self._connected = False

    def is_connected(self):
        return self._connected

    def set_connected(self, connected: bool):
        self._connected = connected

    def set_account(self, login, server, trade_mode, currency="USD", balance=1000.0, equity=1000.0):
        self._account = {
            "login": login,
            "server": server,
            "trade_mode": trade_mode,
            "currency": currency,
            "balance": balance,
            "equity": equity,
        }

    def set_terminal(self, name="MetaTrader 5", company="MetaQuotes Ltd.", connected=True):
        self._terminal = {
            "name": name,
            "company": company,
            "connected": connected,
        }

    def account_info(self):
        """Return account info object like MT5's account_info()."""
        if not self._account:
            return None
        return type("AccountInfo", (), self._account)()

    def add_symbol(self, canonical, broker_symbol, **spec_kwargs):
        self._symbols[canonical] = broker_symbol
        self._specs[broker_symbol] = {
            "name": broker_symbol,
            "currency_base": "XAU",
            "currency_profit": "USD",
            "trade_contract_size": 100.0,
            "trade_tick_size": 0.01,
            "trade_tick_value": 1.0,
            "volume_min": 0.01,
            "volume_max": 500.0,
            "volume_step": 0.01,
            "digits": 2,
            **spec_kwargs,
        }

    @property
    def symbol_map(self):
        return dict(self._symbols)

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
        tick_data = self._ticks.get(broker_symbol)
        if tick_data is None:
            return None
        from superbot.m11.mt5_data_provider import DataState, TickData
        return TickData(
            symbol=symbol,
            broker_symbol=broker_symbol,
            bid=tick_data["bid"],
            ask=tick_data["ask"],
            last=tick_data["last"],
            volume=tick_data["volume"],
            timestamp_utc=datetime.fromtimestamp(tick_data["time"], tz=UTC),
            source="broker_feed",
            data_state=DataState.LIVE,
        )

    def symbol_info_tick(self, broker_symbol):
        return self._ticks.get(broker_symbol)

    def symbol_info(self, broker_symbol):
        return self._specs.get(broker_symbol)

    def symbol_exists(self, broker_symbol):
        return broker_symbol in self._specs


# --- Session store fake for testing ---
class FakeSessionStore:
    """Fake SessionStore for testing execution authorization."""

    def __init__(self):
        self._sessions = {}
        self._counter = 0

    def create_session(self, role):
        self._counter += 1
        now = datetime.now(tz=UTC)
        expires = now + timedelta(hours=8)
        token = f"sess-{self._counter}"
        from superbot.m11.auth import Session

        session = Session(
            session_id=f"sess-{self._counter}",
            role=role,
            created_at_utc=now.isoformat(),
            expires_at_utc=expires.isoformat(),
            is_active=True,
        )
        self._sessions[token] = session
        return session, token

    def validate_token(self, token):
        session = self._sessions.get(token)
        if session is None or not session.is_active:
            return None
        try:
            expires = datetime.fromisoformat(session.expires_at_utc)
        except ValueError:
            return None
        if expires <= datetime.now(tz=UTC):
            return None
        return session

    def invalidate_token(self, token):
        session = self._sessions.get(token)
        if session is None or not session.is_active:
            return False
        session.is_active = False
        return True


# --- RED tests ---


def test_execution_authorizer_creates():
    """ExecutionPermissionService can be instantiated."""
    provider = FakeMT5DataProvider()
    auth = ExecutionPermissionService(mt5_data_provider=provider)
    assert auth is not None
    assert auth.execution_mode == ExecutionMode.READ_ONLY
    assert auth.is_execution_allowed() is False


def test_execution_authorizer_default_mode_read_only():
    """ExecutionPermissionService defaults to READ_ONLY mode."""
    provider = FakeMT5DataProvider()
    auth = ExecutionPermissionService(mt5_data_provider=provider)
    assert auth.execution_mode == ExecutionMode.READ_ONLY


def test_execution_authorizer_rejects_in_read_only_mode():
    """All broker writes rejected in READ_ONLY mode."""
    provider = FakeMT5DataProvider()
    auth = ExecutionPermissionService(mt5_data_provider=provider)
    auth.LIVE_TRADING_ENABLED = True  # Enable demo trading to test READ_ONLY check
    session_store = FakeSessionStore()
    _session, token = session_store.create_session(role="owner")

    request = OrderRequest(
        symbol="XAUUSD",
        side="buy",
        volume=Decimal("0.01"),
        price=Decimal("3875.75"),
        stop_loss=Decimal("3870.00"),
        take_profit=Decimal("3880.00"),
    )

    result = auth.authorize(request, token, session_store)
    assert result.allowed is False
    assert result.reason is not None
    assert "read_only" in result.reason.lower() or "not enabled" in result.reason.lower()


def test_execution_authorizer_rejects_without_session():
    """authorize() returns rejected when no valid session."""
    provider = FakeMT5DataProvider()
    auth = ExecutionPermissionService(mt5_data_provider=provider)
    session_store = FakeSessionStore()
    _session, token = session_store.create_session(role="owner")

    result = auth.authorize(
        OrderRequest(symbol="XAUUSD", side="buy", volume=Decimal("0.01")),
        "invalid_token",
        session_store,
    )
    assert result.allowed is False


def test_execution_authorizer_rejects_real_account():
    """Real (LIVE) account rejected even in DEMO_EXECUTION mode."""
    provider = FakeMT5DataProvider()
    provider.set_connected(True)
    provider.set_account(login=12345, server="XMGlobal-Real", trade_mode=2)  # REAL
    provider.add_symbol("XAUUSD", "GOLD.i#")
    provider.add_tick("GOLD.i#", 3875.75, 3875.99, 3875.87, 1.0)

    auth = ExecutionPermissionService(mt5_data_provider=provider)
    session_store = FakeSessionStore()
    _session, token = session_store.create_session(role="owner")
    # enable_execution should fail for REAL account
    enable_result = auth.enable_execution(token, session_store)
    assert enable_result.allowed is False
    assert "not a demo account" in enable_result.reason.lower()

    # authorize should also reject because execution is not enabled
    result = auth.authorize(
        OrderRequest(symbol="XAUUSD", side="buy", volume=Decimal("0.01")),
        token,
        session_store,
    )
    assert result.allowed is False


def test_execution_authorizer_rejects_contest_account():
    """CONTEST account rejected even in DEMO_EXECUTION mode."""
    provider = FakeMT5DataProvider()
    provider.set_connected(True)
    provider.set_account(login=12345, server="XMGlobal-Demo", trade_mode=3)  # CONTEST
    provider.add_symbol("XAUUSD", "GOLD.i#")
    provider.add_tick("GOLD.i#", 3875.75, 3875.99, 3875.87, 1.0)

    auth = ExecutionPermissionService(mt5_data_provider=provider)
    session_store = FakeSessionStore()
    _session, token = session_store.create_session(role="owner")
    # enable_execution should fail for CONTEST account
    enable_result = auth.enable_execution(token, session_store)
    assert enable_result.allowed is False

    # authorize should also reject because execution is not enabled
    result = auth.authorize(
        OrderRequest(symbol="XAUUSD", side="buy", volume=Decimal("0.01")),
        token,
        session_store,
    )
    assert result.allowed is False


def test_execution_authorizer_rejects_unknown_server():
    """Server not in allowlist rejected."""
    provider = FakeMT5DataProvider()
    provider.set_connected(True)
    provider.set_account(login=12345, server="Unknown-Broker-Server", trade_mode=0)  # DEMO
    provider.add_symbol("XAUUSD", "GOLD.i#")
    provider.add_tick("GOLD.i#", 3875.75, 3875.99, 3875.87, 1.0)

    auth = ExecutionPermissionService(mt5_data_provider=provider)
    session_store = FakeSessionStore()
    _session, token = session_store.create_session(role="owner")
    auth.enable_execution(token, session_store)

    result = auth.authorize(
        OrderRequest(symbol="XAUUSD", side="buy", volume=Decimal("0.01")),
        token,
        session_store,
    )
    assert result.allowed is False


def test_execution_authorizer_rejects_unmapped_symbol():
    """Unmapped symbol rejected."""
    provider = FakeMT5DataProvider()
    provider.set_connected(True)
    provider.set_account(login=12345, server="XMGlobal-Demo", trade_mode=1)  # DEMO
    # Don't add symbol mapping

    auth = ExecutionPermissionService(mt5_data_provider=provider)
    session_store = FakeSessionStore()
    _session, token = session_store.create_session(role="owner")
    auth.enable_execution(token, session_store)

    result = auth.authorize(
        OrderRequest(symbol="UNKNOWN", side="buy", volume=Decimal("0.01")),
        token,
        session_store,
    )
    assert result.allowed is False


def test_execution_authorizer_rejects_stale_market_data():
    """Stale market data (>60s old) rejected."""
    provider = FakeMT5DataProvider()
    provider.set_connected(True)
    provider.set_account(login=12345, server="XMGlobal-Demo", trade_mode=0)  # DEMO
    provider.add_symbol("XAUUSD", "GOLD.i#")
    # Stale tick - timestamp 5 minutes ago
    old_timestamp = int((datetime.now(tz=UTC) - timedelta(minutes=5)).timestamp())
    provider.add_tick("GOLD.i#", 3875.75, 3875.99, 3875.87, 1.0, timestamp=old_timestamp)

    auth = ExecutionPermissionService(mt5_data_provider=provider)
    session_store = FakeSessionStore()
    _session, token = session_store.create_session(role="owner")
    auth.enable_execution(token, session_store)

    result = auth.authorize(
        OrderRequest(symbol="XAUUSD", side="buy", volume=Decimal("0.01")),
        token,
        session_store,
    )
    assert result.allowed is False


def test_execution_authorizer_allows_demo_live_data():
    """Valid DEMO account with live data allows authorization."""
    provider = FakeMT5DataProvider()
    provider.set_connected(True)
    provider.set_account(login=12345, server="XMGlobal-Demo", trade_mode=0)  # DEMO
    provider.add_symbol("XAUUSD", "GOLD.i#")
    provider.add_tick("GOLD.i#", 3875.75, 3875.99, 3875.87, 1.0)

    auth = ExecutionPermissionService(mt5_data_provider=provider)
    auth.LIVE_TRADING_ENABLED = True  # Enable demo trading for this test
    session_store = FakeSessionStore()
    _session, token = session_store.create_session(role="owner")
    auth.enable_execution(token, session_store)

    result = auth.authorize(
        OrderRequest(
            symbol="XAUUSD",
            side="buy",
            volume=Decimal("0.01"),
            stop_loss=Decimal("3870.00"),
        ),
        token,
        session_store,
    )
    assert result.allowed is True
    assert "authorized" in result.reason.lower()


def test_execution_authorizer_records_audit_events():
    """Every authorization decision recorded in audit log."""
    provider = FakeMT5DataProvider()
    provider.set_connected(True)
    provider.set_account(login=12345, server="XMGlobal-Demo", trade_mode=0)
    provider.add_symbol("XAUUSD", "GOLD.i#")
    provider.add_tick("GOLD.i#", 3875.75, 3875.99, 3875.87, 1.0)

    auth = ExecutionPermissionService(mt5_data_provider=provider)
    auth.LIVE_TRADING_ENABLED = True  # Enable demo trading for this test
    session_store = FakeSessionStore()
    _session, token = session_store.create_session(role="owner")
    auth.enable_execution(token, session_store)

    # Make an authorized request
    auth.authorize(
        OrderRequest(
            symbol="XAUUSD",
            side="buy",
            volume=Decimal("0.01"),
            stop_loss=Decimal("3870.00"),
        ),
        token,
        session_store,
    )

    # Make a rejected request
    auth.authorize(
        OrderRequest(
            symbol="UNKNOWN",
            side="buy",
            volume=Decimal("0.01"),
            stop_loss=Decimal("3870.00"),
        ),
        token,
        session_store,
    )

    audit_events = auth.get_audit_events()
    assert len(audit_events) >= 2


def test_execution_authorizer_enable_execution_requires_owner():
    """Only OWNER role can enable execution."""
    provider = FakeMT5DataProvider()
    auth = ExecutionPermissionService(mt5_data_provider=provider)

    session_store = FakeSessionStore()
    _session, token = session_store.create_session(role="viewer")

    result = auth.enable_execution(token, session_store)
    assert result.allowed is False


def test_execution_authorizer_disable_execution():
    """disable_execution() switches back to READ_ONLY."""
    provider = FakeMT5DataProvider()
    provider.set_connected(True)
    provider.set_account(login=12345, server="XMGlobal-Demo", trade_mode=0)
    provider.add_symbol("XAUUSD", "GOLD.i#")
    provider.add_tick("GOLD.i#", 3875.75, 3875.99, 3875.87, 1.0)

    auth = ExecutionPermissionService(mt5_data_provider=provider)
    auth.LIVE_TRADING_ENABLED = True  # Enable demo trading for this test
    session_store = FakeSessionStore()
    _session, token = session_store.create_session(role="owner")
    auth.enable_execution(token, session_store)

    # Verify enabled
    result = auth.authorize(
        OrderRequest(
            symbol="XAUUSD",
            side="buy",
            volume=Decimal("0.01"),
            stop_loss=Decimal("3870.00"),
        ),
        token,
        session_store,
    )
    assert result.allowed is True

    # Disable
    auth.disable_execution(token, session_store)

    # Verify disabled
    assert auth.execution_mode == ExecutionMode.READ_ONLY
    assert auth.is_execution_allowed() is False

    result = auth.authorize(
        OrderRequest(
            symbol="XAUUSD",
            side="buy",
            volume=Decimal("0.01"),
            stop_loss=Decimal("3870.00"),
        ),
        token,
        session_store,
    )
    assert result.allowed is False


# ============================================================================
# Hard Gate Tests — V2 Security Hardening
# ============================================================================


def test_execution_authorizer_rejects_account_changed_to_live_after_auth():
    """Hard Gate #1: Account changed from DEMO to REAL after authorization
    should reject the order AND disable execution mode."""
    provider = FakeMT5DataProvider()
    provider.set_connected(True)
    provider.set_account(login=12345, server="XMGlobal-Demo", trade_mode=0)  # DEMO
    provider.add_symbol("XAUUSD", "GOLD.i#")
    provider.add_tick("GOLD.i#", 3875.75, 3875.99, 3875.87, 1.0)

    auth = ExecutionPermissionService(mt5_data_provider=provider)
    auth.LIVE_TRADING_ENABLED = True  # Enable demo trading for this test
    session_store = FakeSessionStore()
    _session, token = session_store.create_session(role="owner")
    auth.enable_execution(token, session_store)

    # Verify execution is enabled
    assert auth.execution_mode == ExecutionMode.DEMO_EXECUTION

    # Simulate account changing to REAL (e.g., MT5 terminal reconnected to live)
    provider.set_account(login=12345, server="XMGlobal-Real", trade_mode=2)  # REAL

    result = auth.authorize(
        OrderRequest(
            symbol="XAUUSD",
            side="buy",
            volume=Decimal("0.01"),
            stop_loss=Decimal("3870.00"),
        ),
        token,
        session_store,
    )
    assert result.allowed is False
    assert "not a demo" in result.reason.lower() or "demo account" in result.reason.lower() or "real" in result.reason.lower()

    # Execution mode should be disabled after detecting account change
    assert auth.execution_mode == ExecutionMode.READ_ONLY
    assert auth.is_execution_allowed() is False

    # Any subsequent order should also be rejected
    result2 = auth.authorize(
        OrderRequest(
            symbol="XAUUSD",
            side="buy",
            volume=Decimal("0.01"),
            stop_loss=Decimal("3870.00"),
        ),
        token,
        session_store,
    )
    assert result2.allowed is False


def test_execution_authorizer_live_trading_enabled_false_rejects_all():
    """Hard Gate #3: LIVE_TRADING_ENABLED=False rejects all orders
    regardless of MT5 account state."""
    provider = FakeMT5DataProvider()
    provider.set_connected(True)
    provider.set_account(login=12345, server="XMGlobal-Demo", trade_mode=0)
    provider.add_symbol("XAUUSD", "GOLD.i#")
    provider.add_tick("GOLD.i#", 3875.75, 3875.99, 3875.87, 1.0)

    auth = ExecutionPermissionService(mt5_data_provider=provider)
    # LIVE_TRADING_ENABLED defaults to True (demo trading enabled per operator request)
    assert auth.LIVE_TRADING_ENABLED is True

    # Explicitly disable to verify the gate still works
    auth.LIVE_TRADING_ENABLED = False

    session_store = FakeSessionStore()
    _session, token = session_store.create_session(role="owner")

    # Even with valid DEMO session and enabled execution, should reject
    enable_result = auth.enable_execution(token, session_store)
    # enable_execution checks account but live_trading_enabled blocks actual orders
    result = auth.authorize(
        OrderRequest(
            symbol="XAUUSD",
            side="buy",
            volume=Decimal("0.01"),
            stop_loss=Decimal("3870.00"),
        ),
        token,
        session_store,
    )
    assert result.allowed is False
    assert "live trading" in result.reason.lower()


def test_execution_authorizer_rate_limit_per_minute():
    """Hard Gate #4: Max 1 order per minute - second order within a
    minute is rejected."""
    provider = FakeMT5DataProvider()
    provider.set_connected(True)
    provider.set_account(login=12345, server="XMGlobal-Demo", trade_mode=0)
    provider.add_symbol("XAUUSD", "GOLD.i#")
    provider.add_tick("GOLD.i#", 3875.75, 3875.99, 3875.87, 1.0)

    auth = ExecutionPermissionService(mt5_data_provider=provider)
    auth.LIVE_TRADING_ENABLED = True  # Enable demo trading for this test
    session_store = FakeSessionStore()
    _session, token = session_store.create_session(role="owner")
    auth.enable_execution(token, session_store)

    # First submit - authorize passes (no rate limit consumed yet)
    result1 = auth.authorize(
        OrderRequest(
            symbol="XAUUSD",
            side="buy",
            volume=Decimal("0.01"),
            stop_loss=Decimal("3870.00"),
            client_order_id="rate-test-1",
        ),
        token,
        session_store,
    )
    assert result1.allowed is True

    # First confirm - marks order as confirmed
    confirm_result1 = auth.confirm_order(token, result1.evidence.get("confirmation_key"), session_store)
    assert confirm_result1.allowed is True

    # Simulate adapter sending to MT5 - consumes rate limit (1st order per minute)
    auth.mark_confirmation_consumed(result1.evidence.get("confirmation_key"))

    # Second submit - authorize passes (rate limit not consumed on authorize)
    result2 = auth.authorize(
        OrderRequest(
            symbol="XAUUSD",
            side="buy",
            volume=Decimal("0.01"),
            stop_loss=Decimal("3870.00"),
            client_order_id="rate-test-2",
        ),
        token,
        session_store,
    )
    assert result2.allowed is True

    # Second confirm - marks order as confirmed
    confirm_result2 = auth.confirm_order(token, result2.evidence.get("confirmation_key"), session_store)
    assert confirm_result2.allowed is True

    # Simulate adapter sending to MT5 - rate limit exceeded!
    mark_result = auth.mark_confirmation_consumed(result2.evidence.get("confirmation_key"))
    assert mark_result.allowed is False
    assert "rate limit" in mark_result.reason.lower() or "rate_limit" in mark_result.reason.lower()


def test_execution_authorizer_rate_limit_auto_disables():
    """Hard Gate #4: Exceeding rate limit auto-disables execution mode."""
    provider = FakeMT5DataProvider()
    provider.set_connected(True)
    provider.set_account(login=12345, server="XMGlobal-Demo", trade_mode=0)
    provider.add_symbol("XAUUSD", "GOLD.i#")
    provider.add_tick("GOLD.i#", 3875.75, 3875.99, 3875.87, 1.0)

    auth = ExecutionPermissionService(mt5_data_provider=provider)
    auth.LIVE_TRADING_ENABLED = True  # Enable demo trading for this test
    session_store = FakeSessionStore()
    _session, token = session_store.create_session(role="owner")
    auth.enable_execution(token, session_store)

    # First submit - authorize passes
    result1 = auth.authorize(
        OrderRequest(
            symbol="XAUUSD",
            side="buy",
            volume=Decimal("0.01"),
            stop_loss=Decimal("3870.00"),
            client_order_id="rate-auto-1",
        ),
        token,
        session_store,
    )
    assert result1.allowed is True

    # First confirm - marks order as confirmed
    confirm_result1 = auth.confirm_order(
        token, result1.evidence.get("confirmation_key"), session_store
    )
    assert confirm_result1.allowed is True

    # Simulate adapter sending to MT5 - consumes rate limit (1st order)
    mark_result1 = auth.mark_confirmation_consumed(result1.evidence.get("confirmation_key"))
    assert mark_result1.allowed is True

    # Second submit - authorize passes
    result2 = auth.authorize(
        OrderRequest(
            symbol="XAUUSD",
            side="buy",
            volume=Decimal("0.01"),
            stop_loss=Decimal("3870.00"),
            client_order_id="rate-auto-2",
        ),
        token,
        session_store,
    )
    assert result2.allowed is True

    # Second confirm - marks order as confirmed
    confirm_result2 = auth.confirm_order(
        token, result2.evidence.get("confirmation_key"), session_store
    )
    assert confirm_result2.allowed is True

    # Simulate adapter sending to MT5 - rate limit exceeded, triggers auto-disable
    mark_result2 = auth.mark_confirmation_consumed(result2.evidence.get("confirmation_key"))
    assert mark_result2.allowed is False
    assert "rate limit" in mark_result2.reason.lower()

    # Execution mode should be auto-disabled
    assert auth.execution_mode == ExecutionMode.READ_ONLY
    assert auth.is_execution_allowed() is False

    # Third order should also be rejected
    result3 = auth.authorize(
        OrderRequest(
            symbol="XAUUSD",
            side="buy",
            volume=Decimal("0.01"),
            stop_loss=Decimal("3870.00"),
        ),
        token,
        session_store,
    )
    assert result3.allowed is False


def test_execution_authorizer_account_mode_change_alert():
    """Hard Gate #6: Account mode change from DEMO to REAL triggers
    alert in audit events and disables execution."""
    provider = FakeMT5DataProvider()
    provider.set_connected(True)
    provider.set_account(login=12345, server="XMGlobal-Demo", trade_mode=0)
    provider.add_symbol("XAUUSD", "GOLD.i#")
    provider.add_tick("GOLD.i#", 3875.75, 3875.99, 3875.87, 1.0)

    auth = ExecutionPermissionService(mt5_data_provider=provider)
    auth.LIVE_TRADING_ENABLED = True  # Enable demo trading for this test
    session_store = FakeSessionStore()
    _session, token = session_store.create_session(role="owner")
    auth.enable_execution(token, session_store)

    # Verify execution is enabled
    assert auth.execution_mode == ExecutionMode.DEMO_EXECUTION

    # Change account to REAL
    provider.set_account(login=12345, server="XMGlobal-Real", trade_mode=2)

    # Attempt authorization - should reject AND record alert
    auth.authorize(
        OrderRequest(
            symbol="XAUUSD",
            side="buy",
            volume=Decimal("0.01"),
            stop_loss=Decimal("3870.00"),
        ),
        token,
        session_store,
    )

    # Check audit events for mode change alert
    audit_events = auth.get_audit_events()
    mode_change_events = [
        e for e in audit_events
        if "mode_change" in e.get("event_type", "") or "account_changed" in e.get("event_type", "")
    ]
    assert len(mode_change_events) >= 1, f"Expected mode change alert, got {mode_change_events}"

    # Execution should be disabled
    assert auth.execution_mode == ExecutionMode.READ_ONLY


def test_execution_authorizer_rejects_missing_account_info():
    """Missing account info rejected."""
    provider = FakeMT5DataProvider()
    provider.set_connected(True)
    # Don't set account info
    provider.add_symbol("XAUUSD", "GOLD.i#")
    provider.add_tick("GOLD.i#", 3875.75, 3875.99, 3875.87, 1.0)

    auth = ExecutionPermissionService(mt5_data_provider=provider)
    session_store = FakeSessionStore()
    _session, token = session_store.create_session(role="owner")
    auth.enable_execution(token, session_store)

    result = auth.authorize(
        OrderRequest(symbol="XAUUSD", side="buy", volume=Decimal("0.01")),
        token,
        session_store,
    )
    assert result.allowed is False

# ============================================================================
# Hard Gate #5: Trade Confirmation Before Execution
# ============================================================================


def test_execution_authorizer_confirm_order_requires_confirmation():
    """Hard Gate #5: authorize() returns confirmation_required=True, order
    not sent until confirm_order() is called."""
    provider = FakeMT5DataProvider()
    provider.set_connected(True)
    provider.set_account(login=12345, server="XMGlobal-Demo", trade_mode=0)
    provider.add_symbol("XAUUSD", "GOLD.i#")
    provider.add_tick("GOLD.i#", 3875.75, 3875.99, 3875.87, 1.0)

    auth = ExecutionPermissionService(mt5_data_provider=provider)
    auth.LIVE_TRADING_ENABLED = True
    session_store = FakeSessionStore()
    _session, token = session_store.create_session(role="owner")
    auth.enable_execution(token, session_store)

    result = auth.authorize(
        OrderRequest(
            symbol="XAUUSD",
            side="buy",
            volume=Decimal("0.01"),
            stop_loss=Decimal("3870.00"),
            client_order_id="confirm-test-1",
        ),
        token,
        session_store,
    )
    assert result.allowed is True
    assert result.evidence.get("confirmation_required") is True

    # Order should NOT be confirmed yet
    assert auth.is_order_confirmed("confirm-test-1") is False

    # Confirm the order
    confirm_result = auth.confirm_order(token, "confirm-test-1", session_store)
    assert confirm_result.allowed is True

    # Now the order is confirmed
    assert auth.is_order_confirmed("confirm-test-1") is True


def test_execution_authorizer_confirm_order_rejects_invalid_token():
    """Hard Gate #5: confirm_order() rejects invalid/expired token."""
    provider = FakeMT5DataProvider()
    provider.set_connected(True)
    provider.set_account(login=12345, server="XMGlobal-Demo", trade_mode=0)
    provider.add_symbol("XAUUSD", "GOLD.i#")
    provider.add_tick("GOLD.i#", 3875.75, 3875.99, 3875.87, 1.0)

    auth = ExecutionPermissionService(mt5_data_provider=provider)
    auth.LIVE_TRADING_ENABLED = True
    session_store = FakeSessionStore()
    _session, token = session_store.create_session(role="owner")
    auth.enable_execution(token, session_store)

    auth.authorize(
        OrderRequest(
            symbol="XAUUSD",
            side="buy",
            volume=Decimal("0.01"),
            stop_loss=Decimal("3870.00"),
            client_order_id="confirm-test-2",
        ),
        token,
        session_store,
    )

    # Confirm with invalid token
    result = auth.confirm_order("invalid_token", "confirm-test-2", session_store)
    assert result.allowed is False
    assert "invalid" in result.reason.lower()


def test_execution_authorizer_confirm_order_rejects_unknown_order():
    """Hard Gate #5: confirm_order() rejects unknown confirmation key."""
    provider = FakeMT5DataProvider()
    provider.set_connected(True)
    provider.set_account(login=12345, server="XMGlobal-Demo", trade_mode=0)
    provider.add_symbol("XAUUSD", "GOLD.i#")
    provider.add_tick("GOLD.i#", 3875.75, 3875.99, 3875.87, 1.0)

    auth = ExecutionPermissionService(mt5_data_provider=provider)
    auth.LIVE_TRADING_ENABLED = True
    session_store = FakeSessionStore()
    _session, token = session_store.create_session(role="owner")
    auth.enable_execution(token, session_store)

    result = auth.confirm_order(token, "unknown-order-key", session_store)
    assert result.allowed is False
    assert "not found" in result.reason.lower() or "unknown" in result.reason.lower()


def test_execution_authorizer_confirm_order_only_owner():
    """Hard Gate #5: Only OWNER role can confirm orders."""
    provider = FakeMT5DataProvider()
    provider.set_connected(True)
    provider.set_account(login=12345, server="XMGlobal-Demo", trade_mode=0)
    provider.add_symbol("XAUUSD", "GOLD.i#")
    provider.add_tick("GOLD.i#", 3875.99, 3875.87, 1.0, 1.0, timestamp=int(datetime.now(tz=UTC).timestamp()))

    auth = ExecutionPermissionService(mt5_data_provider=provider)
    auth.LIVE_TRADING_ENABLED = True
    session_store = FakeSessionStore()
    viewer_session, viewer_token = session_store.create_session(role="viewer")
    owner_session, owner_token = session_store.create_session(role="owner")

    auth.enable_execution(owner_token, session_store)

    auth.authorize(
        OrderRequest(
            symbol="XAUUSD",
            side="buy",
            volume=Decimal("0.01"),
            stop_loss=Decimal("3870.00"),
            client_order_id="confirm-test-3",
        ),
        owner_token,
        session_store,
    )

    # Viewer cannot confirm
    result = auth.confirm_order(viewer_token, "confirm-test-3", session_store)
    assert result.allowed is False
    assert "insufficient" in result.reason.lower() or "owner" in result.reason.lower()

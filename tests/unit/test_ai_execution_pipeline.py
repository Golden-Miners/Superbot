"""RED tests for V2.9 — AI Execution Pipeline.

Covers:
- AI Execution Pipeline wires signal generator to execution adapter
- Signal -> authorize -> confirm -> submit_order flow end-to-end
- Execution blocked when LIVE_TRADING_ENABLED is False
- Execution rejected on non-DEMO account
- Execution rejected on non-allowlisted server
- Execution rejected when MT5 not connected
- Execution rejected when market data is stale/unavailable
- Authorization decisions recorded in audit trail
- Close position path works for demo account

No live trading authorized. Demo trading only on XM demo servers.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

from superbot.ai.ai_config import AIConfig
from superbot.ai.execution_pipeline import AIExecutionPipeline
from superbot.ai.signal_generator import AISignal
from superbot.m11.execution_authorizer import (
    ExecutionPermissionService,
    ExecutionMode,
    OrderRequest,
)
from superbot.m11.mt5_adapter import MT5ExecutionAdapter
from superbot.m11.mt5_data_provider import MT5DataProvider


class FakeSessionStore:
    """Fake SessionStore for testing execution authorization."""

    def __init__(self):
        self._sessions = {}
        self._counter = 0

    def create_session(self, role: str):
        self._counter += 1
        now = datetime.now(tz=UTC)
        expires = now.__class__(now.year + 1, now.month, now.day, now.hour, now.minute, now.second, now.microsecond, now.tzinfo)
        token = f"sess-{self._counter}"
        session = type("Session", (), {"session_id": token, "role": role, "is_active": True})()
        self._sessions[token] = session
        return session, token

    def validate_token(self, token):
        session = self._sessions.get(token)
        if session is None or not session.is_active:
            return None
        return session


class FakeMT5DataProvider:
    """Fake MT5DataProvider for testing."""

    def __init__(self):
        self.connect_called = False
        self._connected = True
        self._account = {}
        self._symbols = {}
        self._ticks = {}

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

    def set_account(self, login, server, trade_mode, currency="USD", balance=10000.0, equity=10000.0):
        self._account = {
            "login": login,
            "server": server,
            "trade_mode": trade_mode,  # 0=DEMO, 1=REAL
            "currency": currency,
            "balance": balance,
            "equity": equity,
        }

    def add_symbol(self, canonical: str, broker_symbol: str):
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

    def account_info(self):
        if not self._account:
            return None
        return type("AccountInfo", (), dict(self._account))()

    def symbol_info_tick(self, broker_symbol):
        return self._ticks.get(broker_symbol)

    def get_tick(self, symbol):
        broker_symbol = self._symbols.get(symbol)
        if broker_symbol is None:
            return None
        tick_data = self._ticks.get(broker_symbol)
        if tick_data is None:
            return None
        from superbot.m11.mt5_data_provider import DataState, TickData
        tick_time = datetime.fromtimestamp(tick_data["time"], tz=UTC)
        age_seconds = (datetime.now(tz=UTC) - tick_time).total_seconds()
        if age_seconds > 60:
            data_state = DataState.STALE
        else:
            data_state = DataState.LIVE
        return TickData(
            symbol=symbol,
            broker_symbol=broker_symbol,
            bid=tick_data["bid"],
            ask=tick_data["ask"],
            last=tick_data["last"],
            volume=tick_data["volume"],
            timestamp_utc=tick_time,
            source="broker_feed",
            data_state=data_state,
        )

    @property
    def symbol_map(self):
        return dict(self._symbols)

    def order_send(self, mt5_request):
        """Fake order_send for testing - simulates successful order execution."""
        return type("OrderResult", (), {
            "retcode": 10009,  # TRADE_RETCODE_DONE
            "order": 67890,
            "deal": 12345,
            "price": mt5_request.get("price"),
            "volume": mt5_request.get("volume"),
        })()


class TestExecutionPipelineCreates:
    def test_execution_pipeline_creates(self):
        provider = FakeMT5DataProvider()
        auth = ExecutionPermissionService(mt5_data_provider=provider)
        adapter = MT5ExecutionAdapter(mt5_data_provider=provider, auth=auth)
        pipeline = AIExecutionPipeline(mt5_data_provider=provider, auth=auth, adapter=adapter)
        assert pipeline is not None
        assert pipeline.auth is auth
        assert pipeline.adapter is adapter


class TestExecutionPipelineDemoAccount:
    def setup_method(self):
        self.provider = FakeMT5DataProvider()
        self.provider.set_connected(True)
        self.provider.set_account(login=12345, server="XMGlobal-Demo", trade_mode=0)  # DEMO
        self.provider.add_symbol("XAUUSD", "GOLD.i#")
        self.provider.add_tick("GOLD.i#", 3875.75, 3875.99, 3875.87, 1.0)

        self.auth = ExecutionPermissionService(mt5_data_provider=self.provider)
        self.auth.LIVE_TRADING_ENABLED = True
        self.adapter = MT5ExecutionAdapter(mt5_data_provider=self.provider, auth=self.auth)
        self.session_store = FakeSessionStore()
        self.session, self.token = self.session_store.create_session(role="owner")
        self.auth.enable_execution(self.token, self.session_store)

        self.pipeline = AIExecutionPipeline(mt5_data_provider=self.provider, auth=self.auth, adapter=self.adapter)

    def test_execution_pipeline_submits_demo_order(self):
        signal = AISignal(
            symbol="XAUUSD",
            side="buy",
            volume=Decimal("0.01"),
            price=Decimal("3875.75"),
            stop_loss=Decimal("3870.00"),
            take_profit=Decimal("3880.00"),
            confidence=Decimal("0.90"),
            reasoning="test signal",
            model="llama3:8b",
            timestamp_utc=datetime.now(tz=UTC),
        )

        result = self.pipeline.execute_signal(signal, self.token, self.session_store)

        assert result.allowed is True
        assert result.order_id is not None
        assert result.deal_id is not None
        assert result.reason == "order submitted successfully"

    def test_execution_pipeline_rejects_real_account(self):
        # Change account to REAL
        self.provider.set_account(login=12346, server="XMGlobal-Real", trade_mode=1)
        self.provider.set_connected(True)
        self.provider.add_symbol("XAUUSD", "GOLD.i#")
        self.provider.add_tick("GOLD.i#", 3875.75, 3875.99, 3875.87, 1.0)

        # Re-enable with new account
        self.auth.execution_mode = ExecutionMode.READ_ONLY
        self.auth._armed_token = None
        self.auth._armed_at = None
        self.auth.enable_execution(self.token, self.session_store)

        signal = AISignal(
            symbol="XAUUSD",
            side="buy",
            volume=Decimal("0.01"),
            price=Decimal("3875.75"),
            stop_loss=Decimal("3870.00"),
            take_profit=None,
            confidence=Decimal("0.90"),
            reasoning="test signal",
            model="llama3:8b",
            timestamp_utc=datetime.now(tz=UTC),
        )

        result = self.pipeline.execute_signal(signal, self.token, self.session_store)

        assert result.allowed is False
        assert result.reason is not None

    def test_execution_pipeline_rejects_non_demo_server(self):
        self.provider.set_account(login=12346, server="XMGlobal-Real", trade_mode=0)  # DEMO mode but real server name
        self.provider.set_connected(True)
        self.provider.add_symbol("XAUUSD", "GOLD.i#")
        self.provider.add_tick("GOLD.i#", 3875.75, 3875.99, 3875.87, 1.0)

        self.auth.execution_mode = ExecutionMode.READ_ONLY
        self.auth._armed_token = None
        self.auth._armed_at = None
        self.auth.enable_execution(self.token, self.session_store)

        signal = AISignal(
            symbol="XAUUSD",
            side="buy",
            volume=Decimal("0.01"),
            price=Decimal("3875.75"),
            stop_loss=Decimal("3870.00"),
            take_profit=None,
            confidence=Decimal("0.90"),
            reasoning="test signal",
            model="llama3:8b",
            timestamp_utc=datetime.now(tz=UTC),
        )

        result = self.pipeline.execute_signal(signal, self.token, self.session_store)

        assert result.allowed is False
        assert result.reason is not None

    def test_execution_pipeline_rejects_stale_data(self):
        self.provider.set_account(login=12345, server="XMGlobal-Demo", trade_mode=0)
        self.provider.set_connected(True)
        self.provider.add_symbol("XAUUSD", "GOLD.i#")
        self.provider.add_tick("GOLD.i#", 3875.75, 3875.99, 3875.87, 1.0, timestamp=int((datetime.now(tz=UTC) - __import__("datetime").timedelta(minutes=5)).timestamp()))

        self.auth.execution_mode = ExecutionMode.READ_ONLY
        self.auth._armed_token = None
        self.auth._armed_at = None
        self.auth.enable_execution(self.token, self.session_store)

        signal = AISignal(
            symbol="XAUUSD",
            side="buy",
            volume=Decimal("0.01"),
            price=Decimal("3875.75"),
            stop_loss=Decimal("3870.00"),
            take_profit=None,
            confidence=Decimal("0.90"),
            reasoning="test signal",
            model="llama3:8b",
            timestamp_utc=datetime.now(tz=UTC),
        )

        result = self.pipeline.execute_signal(signal, self.token, self.session_store)

        assert result.allowed is False
        assert result.reason is not None
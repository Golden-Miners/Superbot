"""RED tests for AI signal-to-order translation pipeline.

Covers:
- AISignal → OrderRequest translation
- Confidence threshold gating
- Invalid signal rejection
- Full pipeline: signal → authorize → OrderRequest

No live trading authorized. Read-only market data only.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from superbot.ai.ai_config import AIConfig
from superbot.ai.ollama_client import OllamaClient
from superbot.ai.signal_generator import AISignal, AISignalGenerator
from superbot.m11.execution_authorizer import (
    ExecutionPermissionService,
    OrderRequest,
)
from superbot.m11.mt5_data_provider import MT5DataProvider


class FakeMT5DataProvider:
    """Fake MT5DataProvider for testing AI signal translation."""

    def __init__(self):
        self.connect_called = False
        self.disconnect_called = False
        self._connected = True
        self._symbols = {}
        self._ticks = {}
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
        return type("AccountInfo", (), dict(self._account))()

    def add_symbol(self, canonical, broker_symbol, **spec_kwargs):
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
        return self._specs.get(broker_symbol) if hasattr(self, "_specs") else None

    def symbol_exists(self, broker_symbol):
        return broker_symbol in self._specs if hasattr(self, "_specs") else False

    @property
    def symbol_map(self):
        return dict(self._symbols)


class FakeSessionStore:
    """Fake SessionStore for testing execution authorization."""

    def __init__(self):
        self._sessions = {}
        self._counter = 0

    def create_session(self, role):
        self._counter += 1
        now = datetime.now(tz=UTC)
        expires = now + __import__("datetime").timedelta(hours=8)
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


def test_ai_signal_translator_creates():
    """AIOrderTranslator can be instantiated."""
    from superbot.ai.signal_translator import AIOrderTranslator
    translator = AIOrderTranslator()
    assert translator is not None


def test_ai_signal_to_order_request_translator():
    """AISignal with valid data translates to OrderRequest."""
    from superbot.ai.signal_translator import AIOrderTranslator
    translator = AIOrderTranslator()

    signal = AISignal(
        symbol="XAUUSD",
        side="buy",
        volume=Decimal("0.01"),
        price=Decimal("3875.75"),
        stop_loss=Decimal("3870.00"),
        take_profit=Decimal("3880.00"),
        confidence=Decimal("0.85"),
        reasoning="bullish engulfing pattern",
        model="llama3:8b",
        timestamp_utc=datetime.now(tz=UTC),
    )

    request = translator.translate(signal)

    assert request.symbol == "XAUUSD"
    assert request.side == "buy"
    assert request.volume == Decimal("0.01")
    assert request.price == Decimal("3875.75")
    assert request.stop_loss == Decimal("3870.00")
    assert request.take_profit == Decimal("3880.00")
    assert request.order_type == "market"
    assert request.client_order_id is not None


def test_ai_signal_translator_minimal_volume():
    """AISignal with minimal volume translates correctly."""
    from superbot.ai.signal_translator import AIOrderTranslator
    translator = AIOrderTranslator()

    signal = AISignal(
        symbol="BTCUSD",
        side="sell",
        volume=Decimal("0.001"),
        price=Decimal("65000.00"),
        stop_loss=None,
        take_profit=None,
        confidence=Decimal("0.90"),
        reasoning="resistance level reached",
        model="llama3:8b",
        timestamp_utc=datetime.now(tz=UTC),
    )

    request = translator.translate(signal)

    assert request.symbol == "BTCUSD"
    assert request.side == "sell"
    assert request.volume == Decimal("0.001")
    assert request.price == Decimal("65000.00")
    assert request.stop_loss is None
    assert request.take_profit is None


def test_ai_signal_translator_full_pipeline():
    """AISignal → authorize → pending_confirmation via full pipeline."""
    provider = FakeMT5DataProvider()
    provider.set_connected(True)
    provider.set_account(login=12345, server="XMGlobal-Demo", trade_mode=0)
    provider.add_symbol("XAUUSD", "GOLD.i#")
    provider.add_tick("GOLD.i#", 3875.75, 3875.99, 3875.87, 1.0)

    auth = ExecutionPermissionService(mt5_data_provider=provider)
    auth.LIVE_TRADING_ENABLED = True

    session_store = FakeSessionStore()
    session, token = session_store.create_session(role="owner")
    auth.enable_execution(token, session_store)

    from superbot.ai.signal_translator import AIOrderTranslator
    translator = AIOrderTranslator()

    signal = AISignal(
        symbol="XAUUSD",
        side="buy",
        volume=Decimal("0.01"),
        price=Decimal("3875.75"),
        stop_loss=Decimal("3870.00"),
        take_profit=Decimal("3880.00"),
        confidence=Decimal("0.85"),
        reasoning="test signal",
        model="llama3:8b",
        timestamp_utc=datetime.now(tz=UTC),
    )

    request = translator.translate(signal)

    auth_result = auth.authorize(order_request=request, token=token, session_store=session_store)

    assert auth_result.allowed is True
    assert auth_result.reason == "order authorized"
    assert auth_result.evidence.get("confirmation_key") is not None


def test_ai_signal_translator_confidence_below_threshold():
    """AISignal with confidence below threshold is rejected."""
    from superbot.ai.signal_translator import AIOrderTranslator
    translator = AIOrderTranslator()

    signal = AISignal(
        symbol="XAUUSD",
        side="buy",
        volume=Decimal("0.01"),
        price=Decimal("3875.75"),
        stop_loss=Decimal("3870.00"),
        take_profit=None,
        confidence=Decimal("0.30"),  # Below 0.80 threshold
        reasoning="weak signal",
        model="llama3:8b",
        timestamp_utc=datetime.now(tz=UTC),
    )

    request = translator.translate(signal)
    assert request.allowed is False  # RED: AISignal doesn't have .allowed


def test_ai_signal_translator_real_account_rejected():
    """AISignal on REAL account is rejected."""
    provider = FakeMT5DataProvider()
    provider.set_connected(True)
    provider.set_account(login=12345, server="XMGlobal-Real", trade_mode=1)
    provider.add_symbol("XAUUSD", "GOLD.i#")
    provider.add_tick("GOLD.i#", 3875.75, 3875.99, 3875.87, 1.0)

    auth = ExecutionPermissionService(mt5_data_provider=provider)
    auth.LIVE_TRADING_ENABLED = True

    session_store = FakeSessionStore()
    session, token = session_store.create_session(role="owner")
    auth.enable_execution(token, session_store)

    from superbot.ai.signal_translator import AIOrderTranslator
    translator = AIOrderTranslator()

    signal = AISignal(
        symbol="XAUUSD",
        side="buy",
        volume=Decimal("0.01"),
        price=Decimal("3875.75"),
        stop_loss=Decimal("3870.00"),
        take_profit=None,
        confidence=Decimal("0.95"),
        reasoning="strong buy",
        model="llama3:8b",
        timestamp_utc=datetime.now(tz=UTC),
    )

    request = translator.translate(signal)
    auth_result = auth.authorize(order_request=request, token=token, session_store=session_store)

    assert auth_result.allowed is False

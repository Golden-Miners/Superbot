"""RED tests for V2.8 — Signal-to-Order Execution Pipeline.

Covers:
- SignalToOrderRequestTranslator.translate() maps PullbackSignal + Signal → OrderCandidate
- OrderSubmissionPipeline.submit_signal() → authorize → pending confirmation
- OrderSubmissionPipeline.confirm_and_send() → confirm → send to MT5
- Hard Gate #5: order requires explicit owner confirmation before MT5 submission
- Hard Gate #4: rate limit consumed on actual MT5 send (mark_confirmation_consumed)
- End-to-end: trend_following_entry() → Signal → pipeline → MT5 order_send

No live trading authorized. Read-only market data only; DEMO execution gated by
ExecutionPermissionService with owner confirmation required per order.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from superbot.execution.signal_to_order import (
    OrderSubmissionPipeline,
    SignalToOrderRequestTranslator,
    SubmissionResult,
)
from superbot.m11.execution_authorizer import ExecutionPermissionService, OrderRequest
from superbot.m11.mt5_data_provider import MT5DataProvider, DataState
from superbot.risk.signal_ranking import Signal
from superbot.strategy.trend_following import PullbackSignal, trend_following_entry


# --- Fake MT5DataProvider for testing without a live terminal ---
class FakeMT5DataProvider:
    """Fake MT5DataProvider for testing without a live terminal."""

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

    def set_account(self, login, server, trade_mode, currency="USD", balance=1000.0, equity=10000.0):
        self._account = {
            "login": login,
            "server": server,
            "trade_mode": trade_mode,
            "currency": currency,
            "balance": balance,
            "equity": equity,
        }

    def account_info(self):
        """Return account info object like MT5's account_info()."""
        if not self._account:
            return None
        return type("AccountInfo", (), self._account)()

    def add_symbol(self, canonical, broker_symbol, **spec_kwargs):
        self._symbols[canonical] = broker_symbol
        self._specs = getattr(self, "_specs", {})
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

    def order_send(self, request):
        """Simulate MT5 order_send. Returns a result dict."""
        return type(
            "Result",
            (),
            {
                "retcode": 0,  # TRADE_RETCODE_DONE
                "comment": "done",
                "order": 12345,
                "deal": 12346,
                "volume": request.get("volume", 0.0),
                "price": request.get("price", 0.0),
                "bid": request.get("price", 0.0),
                "ask": request.get("price", 0.0),
            },
        )()


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


# --- RED tests ---


def test_signal_to_order_translator_translates_buy_signal():
    """SignalToOrderRequestTranslator maps entry_long to buy order candidate."""
    translator = SignalToOrderRequestTranslator()

    pullback_signal = PullbackSignal(
        signal_type="entry_long",
        entry_price=Decimal("3875.75"),
        stop_price=Decimal("3870.00"),
        depth_pct=Decimal("25.0"),
    )

    ranked_signal = Signal(
        symbol="XAUUSD",
        side="buy",
        score=Decimal("0.85"),
        size=Decimal("0.02"),
    )

    candidate = translator.translate(pullback_signal, ranked_signal)

    assert candidate.symbol == "XAUUSD"
    assert candidate.side == "buy"
    assert candidate.volume == Decimal("0.02")
    assert candidate.price == Decimal("3875.75")
    assert candidate.stop_loss == Decimal("3870.00")
    # 2:1 reward-to-risk: risk=5.75, take_profit = entry + 2*risk = 3875.75 + 11.50 = 3887.25
    assert candidate.take_profit == Decimal("3887.25")
    assert candidate.client_order_id is not None
    assert candidate.source_signal_id is None
    assert candidate.source_strategy == "trend_following_v1"


def test_signal_to_order_translator_translates_sell_signal():
    """SignalToOrderRequestTranslator maps entry_short to sell order candidate."""
    translator = SignalToOrderRequestTranslator()

    pullback_signal = PullbackSignal(
        signal_type="entry_short",
        entry_price=Decimal("3875.75"),
        stop_price=Decimal("3880.00"),
        depth_pct=Decimal("25.0"),
    )

    ranked_signal = Signal(
        symbol="XAUUSD",
        side="sell",
        score=Decimal("0.90"),
        size=Decimal("0.01"),
    )

    candidate = translator.translate(pullback_signal, ranked_signal)

    assert candidate.symbol == "XAUUSD"
    assert candidate.side == "sell"
    assert candidate.volume == Decimal("0.01")
    assert candidate.price == Decimal("3875.75")
    assert candidate.stop_loss == Decimal("3880.00")
    # 2:1 reward-to-risk: risk=4.25, take_profit = entry - 2*risk = 3875.75 - 8.50 = 3867.25
    assert candidate.take_profit == Decimal("3867.25")


def test_signal_to_order_translator_default_volume():
    """Translator uses default_volume when signal size is zero."""
    translator = SignalToOrderRequestTranslator(default_volume=Decimal("0.05"))

    pullback_signal = PullbackSignal(
        signal_type="entry_long",
        entry_price=Decimal("3875.75"),
        stop_price=Decimal("3870.00"),
        depth_pct=Decimal("25.0"),
    )

    ranked_signal = Signal(
        symbol="XAUUSD",
        side="buy",
        score=Decimal("0.85"),
        size=Decimal("0"),  # zero volume → use default
    )

    candidate = translator.translate(pullback_signal, ranked_signal)
    assert candidate.volume == Decimal("0.05")


def test_signal_to_order_translator_no_take_profit_when_no_stops():
    """Translator skips take_profit when price or stop_loss is missing."""
    translator = SignalToOrderRequestTranslator()

    pullback_signal = PullbackSignal(
        signal_type="entry_long",
        entry_price=Decimal("3875.75"),
        stop_price=Decimal("0"),  # invalid stop
        depth_pct=Decimal("25.0"),
    )

    ranked_signal = Signal(
        symbol="XAUUSD",
        side="buy",
        score=Decimal("0.85"),
        size=Decimal("0.01"),
    )

    candidate = translator.translate(pullback_signal, ranked_signal)
    assert candidate.take_profit is None


def test_order_submission_pipeline_creates():
    """OrderSubmissionPipeline can be instantiated with auth and adapter."""
    auth = ExecutionPermissionService(mt5_data_provider=FakeMT5DataProvider())
    adapter = object()  # Fake adapter not needed for just creation
    pipeline = OrderSubmissionPipeline(auth=auth, adapter=adapter)
    assert pipeline is not None
    assert pipeline.auth is auth
    assert pipeline.adapter is adapter


def test_order_submission_pipeline_submit_signal_pending_confirmation():
    """submit_signal() returns pending_confirmation with confirmation_key."""
    provider = FakeMT5DataProvider()
    provider.set_connected(True)
    provider.set_account(login=12345, server="XMGlobal-Demo", trade_mode=0)
    provider.add_symbol("XAUUSD", "GOLD.i#")
    provider.add_tick("GOLD.i#", 3875.75, 3875.99, 3875.87, 1.0)

    auth = ExecutionPermissionService(mt5_data_provider=provider)
    auth.LIVE_TRADING_ENABLED = True
    adapter = FakeMT5Adapter()
    pipeline = OrderSubmissionPipeline(auth=auth, adapter=adapter)

    session_store = FakeSessionStore()
    _session, token = session_store.create_session(role="owner")
    auth.enable_execution(token, session_store)

    pullback_signal = PullbackSignal(
        signal_type="entry_long",
        entry_price=Decimal("3875.75"),
        stop_price=Decimal("3870.00"),
        depth_pct=Decimal("25.0"),
    )

    ranked_signal = Signal(
        symbol="XAUUSD",
        side="buy",
        score=Decimal("0.85"),
        size=Decimal("0.01"),
    )

    result = pipeline.submit_signal(pullback_signal, ranked_signal, token, session_store)

    assert result.status == "pending_confirmation"
    assert result.confirmation_key is not None
    assert result.symbol == "XAUUSD"
    assert result.side == "buy"
    assert result.volume == "0.01"
    assert result.price == "3875.75"
    assert result.stop_loss == "3870.00"
    # Order stored internally for later confirmation
    assert pipeline.get_pending(result.confirmation_key) is not None


def test_order_submission_pipeline_submit_signal_rejected():
    """submit_signal() returns rejected when authorization fails (e.g., READ_ONLY)."""
    provider = FakeMT5DataProvider()
    provider.set_connected(True)
    provider.set_account(login=12345, server="XMGlobal-Demo", trade_mode=0)
    provider.add_symbol("XAUUSD", "GOLD.i#")
    provider.add_tick("GOLD.i#", 3875.75, 3875.99, 3875.87, 1.0)

    auth = ExecutionPermissionService(mt5_data_provider=provider)
    # LIVE_TRADING_ENABLED defaults to True per operator decision, but disable
    # to test rejection path
    auth.LIVE_TRADING_ENABLED = False
    adapter = FakeMT5Adapter()
    pipeline = OrderSubmissionPipeline(auth=auth, adapter=adapter)

    session_store = FakeSessionStore()
    _session, token = session_store.create_session(role="owner")
    auth.enable_execution(token, session_store)

    pullback_signal = PullbackSignal(
        signal_type="entry_long",
        entry_price=Decimal("3875.75"),
        stop_price=Decimal("3870.00"),
        depth_pct=Decimal("25.0"),
    )

    ranked_signal = Signal(
        symbol="XAUUSD",
        side="buy",
        score=Decimal("0.85"),
        size=Decimal("0.01"),
    )

    result = pipeline.submit_signal(pullback_signal, ranked_signal, token, session_store)

    assert result.status == "rejected"
    assert "live trading" in result.reason.lower()
    # Nothing stored internally when rejected
    assert pipeline.get_pending(result.confirmation_key) is None if result.confirmation_key else True


def test_order_submission_pipeline_confirm_and_send():
    """confirm_and_send() confirms order and sends to MT5."""
    provider = FakeMT5DataProvider()
    provider.set_connected(True)
    provider.set_account(login=12345, server="XMGlobal-Demo", trade_mode=0)
    provider.add_symbol("XAUUSD", "GOLD.i#")
    provider.add_tick("GOLD.i#", 3875.75, 3875.99, 3875.87, 1.0)

    auth = ExecutionPermissionService(mt5_data_provider=provider)
    auth.LIVE_TRADING_ENABLED = True
    adapter = FakeMT5Adapter()
    pipeline = OrderSubmissionPipeline(auth=auth, adapter=adapter)

    session_store = FakeSessionStore()
    _session, token = session_store.create_session(role="owner")
    auth.enable_execution(token, session_store)

    pullback_signal = PullbackSignal(
        signal_type="entry_long",
        entry_price=Decimal("3875.75"),
        stop_price=Decimal("3870.00"),
        depth_pct=Decimal("25.0"),
    )

    ranked_signal = Signal(
        symbol="XAUUSD",
        side="buy",
        score=Decimal("0.85"),
        size=Decimal("0.01"),
    )

    # Submit → pending confirmation
    result = pipeline.submit_signal(pullback_signal, ranked_signal, token, session_store)
    assert result.status == "pending_confirmation"
    confirmation_key = result.confirmation_key

    # Confirm → send to MT5
    final = pipeline.confirm_and_send(confirmation_key, token, session_store)

    assert final.status == "submitted"
    assert final.reason == "order sent"
    assert final.symbol == "XAUUSD"
    assert final.side == "buy"
    # Confirmation consumed → rate limit tracking updated
    assert pipeline.get_pending(confirmation_key) is None


def test_order_submission_pipeline_confirm_and_send_rejects_invalid_token():
    """confirm_and_send() rejects with invalid/expired token."""
    provider = FakeMT5DataProvider()
    provider.set_connected(True)
    provider.set_account(login=12345, server="XMGlobal-Demo", trade_mode=0)
    provider.add_symbol("XAUUSD", "GOLD.i#")
    provider.add_tick("GOLD.i#", 3875.75, 3875.99, 3875.87, 1.0)

    auth = ExecutionPermissionService(mt5_data_provider=provider)
    auth.LIVE_TRADING_ENABLED = True
    adapter = FakeMT5Adapter()
    pipeline = OrderSubmissionPipeline(auth=auth, adapter=adapter)

    session_store = FakeSessionStore()
    _session, token = session_store.create_session(role="owner")
    auth.enable_execution(token, session_store)

    pullback_signal = PullbackSignal(
        signal_type="entry_long",
        entry_price=Decimal("3875.75"),
        stop_price=Decimal("3870.00"),
        depth_pct=Decimal("25.0"),
    )

    ranked_signal = Signal(
        symbol="XAUUSD",
        side="buy",
        score=Decimal("0.85"),
        size=Decimal("0.01"),
    )

    result = pipeline.submit_signal(pullback_signal, ranked_signal, token, session_store)
    confirmation_key = result.confirmation_key

    # Confirm with invalid token
    final = pipeline.confirm_and_send(confirmation_key, "invalid_token", session_store)

    assert final.status == "rejected"
    assert "invalid" in final.reason.lower()
    # Confirmation not consumed
    assert pipeline.get_pending(confirmation_key) is not None


def test_order_submission_pipeline_confirm_and_send_rejects_unknown_key():
    """confirm_and_send() rejects unknown confirmation key."""
    provider = FakeMT5DataProvider()
    provider.set_connected(True)
    provider.set_account(login=12345, server="XMGlobal-Demo", trade_mode=0)
    provider.add_symbol("XAUUSD", "GOLD.i#")
    provider.add_tick("GOLD.i#", 3875.75, 3875.99, 3875.87, 1.0)

    auth = ExecutionPermissionService(mt5_data_provider=provider)
    auth.LIVE_TRADING_ENABLED = True
    adapter = FakeMT5Adapter()
    pipeline = OrderSubmissionPipeline(auth=auth, adapter=adapter)

    session_store = FakeSessionStore()
    _session, token = session_store.create_session(role="owner")
    auth.enable_execution(token, session_store)

    final = pipeline.confirm_and_send("unknown-key", token, session_store)

    assert final.status == "rejected"
    assert "not found" in final.reason.lower() or "unknown" in final.reason.lower()


def test_end_to_end_signal_to_order_execution():
    """Full pipeline: trend_following_entry() → Signal → pipeline → MT5 order."""
    provider = FakeMT5DataProvider()
    provider.set_connected(True)
    provider.set_account(login=12345, server="XMGlobal-Demo", trade_mode=0)
    provider.add_symbol("XAUUSD", "GOLD.i#")
    provider.add_tick("GOLD.i#", 3875.75, 3875.99, 3875.87, 1.0)

    auth = ExecutionPermissionService(mt5_data_provider=provider)
    auth.LIVE_TRADING_ENABLED = True
    adapter = FakeMT5Adapter()
    pipeline = OrderSubmissionPipeline(auth=auth, adapter=adapter)

    session_store = FakeSessionStore()
    _session, token = session_store.create_session(role="owner")
    auth.enable_execution(token, session_store)

    # Step 1: Generate signal from trend following analysis
    bars = [
        (1, Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0")),
        (2, Decimal("101.0"), Decimal("103.0"), Decimal("100.0"), Decimal("102.0")),
        (3, Decimal("102.0"), Decimal("104.0"), Decimal("101.0"), Decimal("103.0")),
        (4, Decimal("103.0"), Decimal("105.0"), Decimal("102.0"), Decimal("104.0")),
        (5, Decimal("104.0"), Decimal("106.0"), Decimal("103.0"), Decimal("105.0")),
        (6, Decimal("105.0"), Decimal("105.5"), Decimal("102.0"), Decimal("102.5")),
    ]
    trend_spec = type("TrendSpec", (), {
        "schema_version": "1.0.0",
        "rule_id": "e2e_001",
        "lookback_bars": 5,
        "ma_period": 3,
    })()
    pullback_spec = type("PullbackSpec", (), {
        "schema_version": "1.0.0",
        "rule_id": "e2e_002",
        "min_depth_pct": Decimal("10"),
        "max_depth_pct": Decimal("60"),
        "require_bounce": True,
    })()

    signal = trend_following_entry(bars, trend_spec, pullback_spec)
    assert signal is not None
    assert signal.signal_type == "entry_long"

    # Step 2: Rank the signal
    ranked = Signal(
        symbol="XAUUSD",
        side="buy",
        score=Decimal("0.85"),
        size=Decimal("0.01"),
    )

    # Step 3: Submit through pipeline (pending confirmation)
    result = pipeline.submit_signal(signal, ranked, token, session_store)
    assert result.status == "pending_confirmation"
    confirmation_key = result.confirmation_key

    # Step 4: Owner confirms (Hard Gate #5)
    confirm_result = auth.confirm_order(token, confirmation_key, session_store)
    assert confirm_result.allowed is True

    # Step 5: Send to MT5
    final = pipeline.confirm_and_send(confirmation_key, token, session_store)
    assert final.status == "submitted"
    assert final.symbol == "XAUUSD"
    assert final.side == "buy"
    assert len(adapter.sent_orders) == 1


class FakeMT5Adapter:
    """Fake MT5ExecutionAdapter that records sent orders without real MT5."""

    def __init__(self):
        self.sent_orders = []

    def send_confirmed_order(self, order_request, confirmation_key):
        """Simulate sending confirmed order to MT5."""
        self.sent_orders.append({
            "symbol": order_request.symbol,
            "side": order_request.side,
            "volume": order_request.volume,
            "price": order_request.price,
            "stop_loss": order_request.stop_loss,
            "take_profit": order_request.take_profit,
            "confirmation_key": confirmation_key,
        })
        return type(
            "OrderResult",
            (),
            {
                "allowed": True,
                "reason": "order sent",
                "order_id": 12345,
                "deal_id": 12346,
                "volume": order_request.volume,
                "price": order_request.price,
                "broker_response": {"retcode": 0, "comment": "done"},
                "evidence": {"confirmation_key": confirmation_key},
            },
        )()


def test_signal_to_order_translator_no_take_profit_when_invalid_stop():
    """Translator skips take_profit when stop_loss is invalid (zero or negative)."""
    translator = SignalToOrderRequestTranslator()

    pullback_signal = PullbackSignal(
        signal_type="entry_long",
        entry_price=Decimal("3875.75"),
        stop_price=Decimal("0"),  # invalid stop
        depth_pct=Decimal("25.0"),
    )

    ranked_signal = Signal(
        symbol="XAUUSD",
        side="buy",
        score=Decimal("0.85"),
        size=Decimal("0.01"),
    )

    candidate = translator.translate(pullback_signal, ranked_signal)
    assert candidate.take_profit is None


def test_signal_to_order_translator_client_order_id_format():
    """Client order ID follows format: strategy_id:symbol:side."""
    translator = SignalToOrderRequestTranslator()

    pullback_signal = PullbackSignal(
        signal_type="entry_long",
        entry_price=Decimal("3875.75"),
        stop_price=Decimal("3870.00"),
        depth_pct=Decimal("25.0"),
    )

    ranked_signal = Signal(
        symbol="BTCUSD",
        side="buy",
        score=Decimal("0.90"),
        size=Decimal("0.01"),
    )

    candidate = translator.translate(
        pullback_signal, ranked_signal, strategy_id="trend_v2"
    )

    assert candidate.client_order_id == "trend_v2:BTCUSD:buy"


def test_order_submission_pipeline_clear_pending():
    """clear_pending() removes a pending order."""
    provider = FakeMT5DataProvider()
    provider.set_connected(True)
    provider.set_account(login=12345, server="XMGlobal-Demo", trade_mode=0)
    provider.add_symbol("XAUUSD", "GOLD.i#")
    provider.add_tick("GOLD.i#", 3875.75, 3875.99, 3875.87, 1.0)

    auth = ExecutionPermissionService(mt5_data_provider=provider)
    auth.LIVE_TRADING_ENABLED = True
    adapter = FakeMT5Adapter()
    pipeline = OrderSubmissionPipeline(auth=auth, adapter=adapter)

    session_store = FakeSessionStore()
    _session, token = session_store.create_session(role="owner")
    auth.enable_execution(token, session_store)

    pullback_signal = PullbackSignal(
        signal_type="entry_long",
        entry_price=Decimal("3875.75"),
        stop_price=Decimal("3870.00"),
        depth_pct=Decimal("25.0"),
    )

    ranked_signal = Signal(
        symbol="XAUUSD",
        side="buy",
        score=Decimal("0.85"),
        size=Decimal("0.01"),
    )

    result = pipeline.submit_signal(pullback_signal, ranked_signal, token, session_store)
    confirmation_key = result.confirmation_key

    assert pipeline.get_pending(confirmation_key) is not None

    pipeline.clear_pending(confirmation_key)
    assert pipeline.get_pending(confirmation_key) is None

"""Debug end-to-end pipeline."""
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from superbot.execution.signal_to_order import OrderSubmissionPipeline, SignalToOrderRequestTranslator, SubmissionResult
from superbot.m11.execution_authorizer import ExecutionPermissionService, OrderRequest
from superbot.m11.mt5_data_provider import DataState, TickData, MT5DataProvider
from superbot.risk.signal_ranking import Signal
from superbot.strategy.trend_following import PullbackSignal, trend_following_entry


class FakeSessionStore:
    def __init__(self):
        self._sessions = {}
        self._counter = 0
    def create_session(self, role):
        self._counter += 1
        now = datetime.now(tz=UTC)
        expires = now + timedelta(hours=8)
        token = f'sess-{self._counter}'
        from superbot.m11.auth import Session
        session = Session(session_id=f'sess-{self._counter}', role=role, created_at_utc=now.isoformat(), expires_at_utc=expires.isoformat(), is_active=True)
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


class FakeMT5DataProvider:
    def __init__(self):
        self._connected = True
        self._symbols = {}
        self._ticks = {}
        self._account = {}
    def connect(self): self._connected = True; return True
    def disconnect(self): self._connected = False
    def is_connected(self): return self._connected
    def set_connected(self, c): self._connected = c
    def set_account(self, login, server, trade_mode, currency='USD', balance=10000.0, equity=10000.0):
        self._account = {'login': login, 'server': server, 'trade_mode': trade_mode, 'currency': currency, 'balance': balance, 'equity': equity}
    def account_info(self):
        if not self._account: return None
        return type('AccountInfo', (), self._account)()
    def add_symbol(self, canonical, broker_symbol, **kw):
        self._symbols[canonical] = broker_symbol
        self._specs = getattr(self, '_specs', {})
        self._specs[broker_symbol] = {'name': broker_symbol, 'currency_base': 'XAU', 'currency_profit': 'USD', 'trade_contract_size': 100.0, 'trade_tick_size': 0.01, 'trade_tick_value': 1.0, 'volume_min': 0.01, 'volume_max': 500.0, 'volume_step': 0.01, 'digits': 2, **kw}
    @property
    def symbol_map(self): return dict(self._symbols)
    def add_tick(self, broker_symbol, bid, ask, last, volume, timestamp=None):
        if timestamp is None: timestamp = int(datetime.now(tz=UTC).timestamp())
        self._ticks[broker_symbol] = {'bid': bid, 'ask': ask, 'last': last, 'volume': volume, 'time': timestamp}
    def get_tick(self, symbol):
        broker_symbol = self._symbols.get(symbol)
        if broker_symbol is None: return None
        tick_data = self._ticks.get(broker_symbol)
        if tick_data is None: return None
        return TickData(symbol=symbol, broker_symbol=broker_symbol, bid=tick_data['bid'], ask=tick_data['ask'], last=tick_data['last'], volume=tick_data['volume'], timestamp_utc=datetime.fromtimestamp(tick_data['time'], tz=UTC), source='broker_feed', data_state=DataState.LIVE)


class FakeMT5Adapter:
    def __init__(self): self.sent_orders = []
    def send_confirmed_order(self, order_request, confirmation_key):
        self.sent_orders.append({'symbol': order_request.symbol, 'side': order_request.side, 'volume': order_request.volume, 'confirmation_key': confirmation_key})
        return type('OrderResult', (), {'allowed': True, 'reason': 'order sent', 'order_id': 12345, 'deal_id': 12346, 'volume': order_request.volume, 'price': order_request.price, 'broker_response': {'retcode': 0, 'comment': 'done'}, 'evidence': {'confirmation_key': confirmation_key}})()


provider = FakeMT5DataProvider()
provider.set_connected(True)
provider.set_account(login=12345, server='XMGlobal-Demo', trade_mode=0)
provider.add_symbol('XAUUSD', 'GOLD.i#')
provider.add_tick('GOLD.i#', 3875.75, 3875.99, 3875.87, 1.0)

auth = ExecutionPermissionService(mt5_data_provider=provider)
auth.LIVE_TRADING_ENABLED = True
adapter = FakeMT5Adapter()
pipeline = OrderSubmissionPipeline(auth=auth, adapter=adapter)

session_store = FakeSessionStore()
session, token = session_store.create_session(role='owner')
print('enable:', auth.enable_execution(token, session_store).allowed)

pullback_signal = PullbackSignal(signal_type='entry_long', entry_price=Decimal('3875.75'), stop_price=Decimal('3870.00'), depth_pct=Decimal('25.0'))
ranked_signal = Signal(symbol='XAUUSD', side='buy', score=Decimal('0.85'), size=Decimal('0.01'))

result = pipeline.submit_signal(pullback_signal, ranked_signal, token, session_store)
print('submit:', result.status, result.reason, result.confirmation_key)

if result.status == 'pending_confirmation':
    cr = auth.confirm_order(token, result.confirmation_key, session_store)
    print('confirm:', cr.allowed, cr.reason)
    
    final = pipeline.confirm_and_send(result.confirmation_key, token, session_store)
    print('final:', final.status, final.reason)
    print('sent_orders:', len(adapter.sent_orders))

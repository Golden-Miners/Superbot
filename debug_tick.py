"""Debug MT5 tick data state calculation."""
from datetime import UTC, datetime
from superbot.m11.mt5_data_provider import MT5DataProvider, DataState
import MetaTrader5 as mt5

mt5.initialize()
provider = MT5DataProvider()
provider._mt5 = mt5
provider._connected = True

tick_info = mt5.symbol_info_tick('GOLD.i#')
print(f'tick_info.time (raw): {tick_info.time}')
print(f'tick_info.time type: {type(tick_info.time)}')

ts = provider._timestamp_from_raw(tick_raw_time=tick_info.time)
print(f'parsed timestamp: {ts}')

now = datetime.now(tz=UTC)
age = (now - ts).total_seconds()
print(f'now: {now}')
print(f'age seconds: {age}')
print(f'abs(age) <= 60: {abs(age) <= 60.0}')
print(f'age > 60: {age > 60.0}')

bid = getattr(tick_info, 'bid', None)
ask = getattr(tick_info, 'ask', None)
print(f'bid: {bid}, ask: {ask}')
print(f'bid is None: {bid is None}, ask is None: {ask is None}')
if bid is not None:
    print(f'bid <= 0: {bid <= 0}')
if ask is not None:
    print(f'ask <= 0: {ask <= 0}')

provider.disconnect()
mt5.shutdown()

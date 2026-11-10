"""Check current MT5 state and signal generation capability."""
import MetaTrader5 as mt5

mt5.initialize()
print("=== ACCOUNT INFO ===")
info = mt5.account_info()
print(f"Login: {info.login}")
print(f"Server: {info.server}")
print(f"Trade mode: {info.trade_mode} (0=DEMO, 1=REAL, 2=CONTEST)")
print(f"Balance: {info.balance}")
print(f"Equity: {info.equity}")
print(f"Trade allowed: {info.trade_allowed}")

print()
print("=== OPEN POSITIONS ===")
positions = mt5.positions_get()
if positions:
    for p in positions:
        ttype = "BUY" if p.type == 0 else "SELL"
        print(f"Ticket: {p.ticket}, Symbol: {p.symbol}, Type: {ttype}, Volume: {p.volume}, Price: {p.price_open}, Profit: {p.profit}")
else:
    print("No open positions")

print()
print("=== PENDING ORDERS ===")
orders = mt5.orders_get()
if orders:
    for o in orders:
        print(f"Ticket: {o.ticket}, Symbol: {o.symbol}, Type: {o.type}, Volume: {o.volume}, Price: {o.price_open}, State: {o.state}")
else:
    print("No pending orders")

print()
print("=== SYMBOLS WITH LIVE DATA ===")
for sym in ["GOLD.i#", "XAUUSD", "BTCUSD#", "ETHUSD#", "GBPUSD", "EURUSD"]:
    tick = mt5.symbol_info_tick(sym)
    if tick:
        print(f"{sym}: bid={tick.bid}, ask={tick.ask}, time={tick.time}")
    else:
        print(f"{sym}: NOT AVAILABLE")

mt5.shutdown()
print()
print("=== MT5 CONNECTION: ACTIVE ===")

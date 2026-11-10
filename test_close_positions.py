"""Close all open positions on GOLD.i#."""
import MetaTrader5 as mt5

mt5.initialize()
positions = mt5.positions_get()
if positions:
    gold_positions = [p for p in positions if p.symbol == 'GOLD.i#']
    tick = mt5.symbol_info_tick('GOLD.i#')
    for p in gold_positions:
        close_type = mt5.ORDER_TYPE_BUY if p.type == 1 else mt5.ORDER_TYPE_SELL
        close_price = tick.ask if p.type == 1 else tick.bid
        request = {
            'action': mt5.TRADE_ACTION_DEAL,
            'symbol': 'GOLD.i#',
            'volume': p.volume,
            'type': close_type,
            'position': p.ticket,
            'price': close_price,
            'deviation': 10,
            'type_filling': mt5.ORDER_FILLING_IOC,
        }
        result = mt5.order_send(request)
        print(f'Close position {p.ticket}: retcode={result.retcode}, comment={result.comment}')
else:
    print('No open positions')
mt5.shutdown()

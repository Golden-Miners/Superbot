lines = open('src/superbot/m11/trading_loop.py','r').readlines()
lines[156] = '                f"Orders: {self._orders_submitted}"\n            )\n'
with open('src/superbot/m11/trading_loop.py','w') as f:
    f.writelines(lines)
print('Done')

import json
from datetime import datetime

with open('output/hot_stocks.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
    stocks = data.get('stocks', [])

print('Data timestamp:', data.get('timestamp'))
print('Total stocks:', len(stocks))

up = [s for s in stocks if float(s.get('change_pct', 0)) > 0]
down = [s for s in stocks if float(s.get('change_pct', 0)) < 0]
zt = [s for s in stocks if float(s.get('change_pct', 0)) >= 9.5]

print('Up:', len(up), 'Down:', len(down), 'ZT:', len(zt))
print('Top 3:')
for s in stocks[:3]:
    code = s.get('code')
    name = s.get('name')
    pct = s.get('change_pct')
    print(' ', code, name, pct)

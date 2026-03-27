import json

with open('output/hot_stocks.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
    stocks = data.get('stocks', [])

print(f"Total stocks: {len(stocks)}")
print(f"Timestamp: {data.get('timestamp', 'N/A')}")

# 统计涨跌
up = [s for s in stocks if float(s.get('change_pct', 0)) > 0]
down = [s for s in stocks if float(s.get('change_pct', 0)) < 0]
zt = [s for s in stocks if float(s.get('change_pct', 0)) >= 9.5]
dt = [s for s in stocks if float(s.get('change_pct', 0)) <= -9.5]

print(f"\nUp: {len(up)}")
print(f"Down: {len(down)}")
print(f"涨停(>=9.5%): {len(zt)}")
print(f"跌停(<=-9.5%): {len(dt)}")
print(f"涨停跌停合计: {len(zt) + len(dt)}")

# 显示涨停股票
print("\n涨停股票:")
for s in zt[:10]:
    print(f"  {s['code']} {s['name']}: +{s['change_pct']:.2f}%")

# 显示跌停股票
print("\n跌停股票:")
for s in dt[:10]:
    print(f"  {s['code']} {s['name']}: {s['change_pct']:.2f}%")

import json
with open('output/hot_stocks.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
    stocks = data.get('stocks', [])
    
for s in stocks:
    if s['code'] in ['000539', '601016', '600758']:
        print(f"{s['code']} {s['name']}: {s['change_pct']:+.2f}%, rank={s['rank']}")

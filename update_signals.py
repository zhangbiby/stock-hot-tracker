from signal_engine import SignalEngine
import json
from datetime import datetime

# 直接加载现有的hot_stocks.json
with open('output/hot_stocks.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
    stocks = data.get('stocks', [])

print(f'Loaded {len(stocks)} stocks from hot_stocks.json')

# 计算信号
engine = SignalEngine()
signals = engine.process_all(stocks)

# 保存
with open('output/signals_latest.json', 'w', encoding='utf-8') as f:
    json.dump({'signals': signals, 'timestamp': datetime.now().isoformat()}, f, ensure_ascii=False, indent=2)

print(f'Signals saved: {len(signals)}')

# 检查ML状态
ml_count = sum(1 for s in signals if s.get('has_ml'))
print(f'ML enabled: {ml_count}/{len(signals)}')

# 显示前5个
print('\nTop 5 signals:')
for s in signals[:5]:
    ml_str = f" [ML:{s['up_proba']*100:.0f}%]" if s.get('up_proba') else ''
    print(f"  {s['code']} {s['name']}: {s['signal']} ({s['score']}){ml_str}")

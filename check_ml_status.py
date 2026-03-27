import json
with open('output/signals_latest.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
    signals = data.get('signals', [])

# 检查ML相关字段
print('Total signals:', len(signals))

# 统计有up_proba的信号
with_proba = [s for s in signals if s.get('up_proba') is not None]
print('Signals with up_proba:', len(with_proba))

# 检查前5个信号
print('\nFirst 5 signals:')
for s in signals[:5]:
    print(f"  {s.get('code')} {s.get('name')}: up_proba={s.get('up_proba')}, has_ml={s.get('has_ml')}")

import json
with open('output/signals_latest.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
    signals = data.get('signals', [])

# 统计各信号类型
signal_counts = {}
for s in signals:
    sig = s.get('signal', 'N/A')
    signal_counts[sig] = signal_counts.get(sig, 0) + 1

print('Signal distribution:')
for sig, count in sorted(signal_counts.items(), key=lambda x: -x[1]):
    print(f'  {sig}: {count}')

# 检查Strong Buy和Buy
strong_buy = [s for s in signals if s.get('signal') == 'Strong Buy']
buy = [s for s in signals if s.get('signal') == 'Buy']

print(f'\nStrong Buy: {len(strong_buy)}')
print(f'Buy: {len(buy)}')

if strong_buy:
    print('\nStrong Buy signals:')
    for s in strong_buy[:5]:
        print(f"  {s.get('code')} {s.get('name')}: score={s.get('score')}")

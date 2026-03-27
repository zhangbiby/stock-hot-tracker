import json
with open('output/signals_latest.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
    signals = data.get('signals', [])

print('Total signals:', len(signals))
print('Multi-agent enabled:', data.get('multi_agent_enabled', False))

# 检查第一个信号的结构
if signals:
    s = signals[0]
    print('\nSample signal:')
    print('  Code:', s.get('code'))
    print('  Name:', s.get('name'))
    print('  Signal:', s.get('signal'))
    print('  Multi-agent:', s.get('multi_agent'))
    
    # 检查agent_details
    details = s.get('agent_details', {})
    if details:
        print('\n  Agent details keys:', list(details.keys())[:5])

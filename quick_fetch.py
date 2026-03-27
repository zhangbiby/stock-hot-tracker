#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""完整数据采集脚本"""
import urllib.request
import json
import ssl
import re
from datetime import datetime
from pathlib import Path

OUTPUT_DIR = Path('output')

def fetch_all():
    print('开始采集人气榜TOP100...')
    
    # 1. 采集人气榜列表
    url = 'https://emappdata.eastmoney.com/stockrank/getAllCurrentList'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Content-Type': 'application/json',
    }
    
    all_items = []
    for page in range(1, 3):
        data = f'{{"appId":"app","globalId":"786e4856d39b4298964a0de38a0d77fc","marketType":"","pageNo":{page},"pageSize":50}}'.encode()
        req = urllib.request.Request(url, data=data, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read().decode())
                items = result.get('data', [])
                all_items.extend(items)
                print(f'  第{page}页: {len(items)}条')
        except Exception as e:
            print(f'  第{page}页失败: {e}')
    
    print(f'共采集 {len(all_items)} 条记录')
    
    # 2. 获取详细行情
    print('获取详细行情...')
    stocks = []
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE
    
    for i, item in enumerate(all_items[:100]):
        sc = item.get('sc', '')  # 格式: SH600396
        if not sc:
            continue
        code = sc[2:]  # 去掉SH/SZ前缀
        rank = item.get('rk', i+1)
        
        # 腾讯财经API
        prefix = 'sh' if code.startswith('6') else 'sz'
        qq_url = f"https://web.sqt.gtimg.cn/q={prefix}{code}"
        
        try:
            req = urllib.request.Request(qq_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5, context=ssl_ctx) as resp:
                text = resp.read().decode('gbk')
            
            for line in text.split(';'):
                if not line.strip():
                    continue
                match = re.match(r'v_(\w+)="(.+)"', line.strip())
                if match:
                    parts = match.group(2).split('~')
                    if len(parts) > 38:
                        stocks.append({
                            'code': code,
                            'name': parts[1],
                            'price': float(parts[3]) if parts[3] else 0,
                            'change': float(parts[31]) if parts[31] else 0,
                            'change_pct': float(parts[32]) if parts[32] else 0,
                            'volume': int(float(parts[6])) if parts[6] else 0,
                            'turnover_rate': float(parts[38]) if parts[38] else 0,
                            'rank': rank,
                        })
                        break
        except Exception as e:
            continue
        
        if (i+1) % 20 == 0:
            print(f'  已处理 {i+1}/{min(len(all_items), 100)}')
    
    # 3. 保存数据
    data = {
        'timestamp': datetime.now().isoformat(),
        'stocks': stocks
    }
    
    output_file = OUTPUT_DIR / 'hot_stocks.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f'\n保存 {len(stocks)} 只股票到 {output_file}')
    return stocks

def generate_signals():
    print('\n生成信号...')
    import sys
    sys.path.insert(0, '.')
    from signal_engine import SignalEngine, save_signals_to_json
    from history_store import init_storage
    
    init_storage()
    
    with open(OUTPUT_DIR / 'hot_stocks.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    stocks = data.get('stocks', [])
    
    engine = SignalEngine()
    signals = engine.process_all(stocks)
    save_signals_to_json(signals)
    print(f'生成 {len(signals)} 个信号')

def generate_page():
    print('\n生成页面...')
    import sys
    sys.path.insert(0, '.')
    from generate_page import main as gen_main
    gen_main()
    print('页面生成完成')

if __name__ == '__main__':
    print('=' * 50)
    print('股票数据采集')
    print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print('=' * 50)
    
    stocks = fetch_all()
    if stocks:
        generate_signals()
        generate_page()
        print('\n' + '=' * 50)
        print('完成！刷新 http://localhost:8080')
        print('=' * 50)

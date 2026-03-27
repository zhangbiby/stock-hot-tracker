#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票人气榜采集脚本（仅采集）
从东方财富股吧人气榜获取前100名股票数据，保存到JSON文件
"""

import json
import sys
import os
import re
import ssl
import urllib.request
from datetime import datetime
from pathlib import Path

# Fix stdout encoding for Windows
if sys.platform == 'win32':
    try:
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
    except:
        pass

# Import local modules
sys.path.insert(0, os.path.dirname(__file__))
from history_store import save_snapshot, init_storage
from signal_engine import SignalEngine, save_signals_to_json
from portfolio import Portfolio

CONFIG = {
    "output_dir": Path(__file__).parent / "output",
    "data_file": "hot_stocks.json",
    "html_file": "index.html",
}

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': '*/*',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}

def fetch_stock_details(stock_codes):
    """从腾讯财经批量获取完整数据"""
    if not stock_codes:
        return []
    
    stocks_with_details = []
    try:
        tencent_codes = []
        for s in stock_codes:
            code = s.get('code', '')
            if code.startswith('6'):
                tencent_codes.append(f'sh{code}')
            else:
                tencent_codes.append(f'sz{code}')
        
        url = f"https://web.sqt.gtimg.cn/q={','.join(tencent_codes)}"
        req = urllib.request.Request(url, headers=HEADERS)
        
        with urllib.request.urlopen(req, timeout=15, context=SSL_CTX) as resp:
            text = resp.read().decode('gbk')
        
        code_to_data = {}
        for line in text.split(';'):
            if not line.strip():
                continue
            match = re.match(r'v_(\w+)="(.+)"', line.strip())
            if match:
                data = match.group(2).split('~')
                if len(data) > 50:
                    code = data[2]
                    code_to_data[code] = {
                        'name': data[1],
                        'price': data[3],
                        'change_pct': data[32],
                        'volume': data[36],
                        'turnover_rate': data[38],
                        'volume_ratio': data[39],
                        'amplitude': data[43],
                    }
        
        for s in stock_codes:
            code = s.get('code', '')
            if code in code_to_data:
                detail = code_to_data[code]
                s['name'] = detail['name']
                s['price'] = detail['price']
                s['change_pct'] = float(detail['change_pct']) if detail['change_pct'] else 0
                s['volume'] = int(detail['volume']) if detail['volume'].isdigit() else 0
                s['turnover_rate'] = float(detail['turnover_rate']) if detail['turnover_rate'] else 0
                s['volume_ratio'] = float(detail['volume_ratio']) if detail['volume_ratio'] else 1
                s['amplitude'] = float(detail['amplitude']) if detail['amplitude'] else 0
                stocks_with_details.append(s)
            else:
                stocks_with_details.append(s)
    
    except Exception as e:
        print(f"    Error fetching details: {e}")
        stocks_with_details = stock_codes
    
    return stocks_with_details

def fetch_from_eastmoney_guba_rank(top_n=100):
    """从东方财富股吧人气榜获取真实数据"""
    stocks = []
    try:
        print("  Fetching from EastMoney Guba rank...")
        url = "https://emappdata.eastmoney.com/stockrank/getAllCurrentList"
        
        payload = {
            "appId": "appId01",
            "globalId": "786e4c21-70dc-435a-93bb-38",
            "marketType": "",
            "pageNo": 1,
            "pageSize": top_n,
        }
        
        headers = HEADERS.copy()
        headers['Content-Type'] = 'application/json'
        
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers=headers,
            method='POST'
        )
        
        with urllib.request.urlopen(req, timeout=15, context=SSL_CTX) as resp:
            content = resp.read().decode('utf-8')
            data = json.loads(content)
        
        rank_list = data.get('data', [])
        for item in rank_list[:top_n]:
            code_raw = item.get('sc', '')
            stock_code = code_raw.replace('SH', '').replace('SZ', '').zfill(6)
            stocks.append({
                "rank": int(item.get('rk', 0)),
                "code": stock_code,
                "name": "",
                "price": 0,
                "change_pct": 0,
                "volume": 0,
                "turnover_rate": 0,
                "volume_ratio": 1,
                "amplitude": 0,
                "source": "EastMoney Guba",
            })
        
        print(f"    Got {len(stocks)} stocks, fetching details...")
        if stocks:
            stocks = fetch_stock_details(stocks)
    
    except Exception as e:
        print(f"    EastMoney API failed: {e}")
    
    return stocks

def is_trading_hours():
    """检查是否在交易时间内"""
    now = datetime.now()
    if now.weekday() >= 5:
        return False
    hour, minute = now.hour, now.minute
    if hour == 9 and minute >= 30:
        return True
    elif hour >= 10 and hour < 15:
        return True
    elif hour == 15 and minute == 0:
        return True
    return False

def should_collect():
    """判断是否应该执行采集"""
    if is_trading_hours():
        return True
    now = datetime.now()
    if now.minute in [0, 30]:
        return True
    return False

def main():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 股票人气榜采集开始")
    
    # 初始化存储
    init_storage()
    
    # 采集数据
    stocks = fetch_from_eastmoney_guba_rank(100)
    if not stocks:
        print("  采集失败，无数据")
        return
    
    print(f"  采集到 {len(stocks)} 只股票")
    
    # 生成买卖信号
    signal_engine = SignalEngine()
    signals = signal_engine.process_all(stocks)
    
    # 保存数据
    output_dir = CONFIG["output_dir"]
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 保存原始数据
    raw_data = {
        "timestamp": datetime.now().isoformat(),
        "stocks": stocks
    }
    raw_file = output_dir / "hot_stocks.json"
    with open(raw_file, 'w', encoding='utf-8') as f:
        json.dump(raw_data, f, ensure_ascii=False, indent=2)
    print(f"  原始数据保存到: {raw_file}")
    
    # 保存信号数据
    signals_file = save_signals_to_json(signals)
    print(f"  信号数据保存到: {signals_file}")
    
    # 保存历史快照
    save_snapshot(stocks)
    print("  历史快照已保存")
    
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 采集完成")

if __name__ == "__main__":
    main()
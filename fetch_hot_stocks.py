#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stock Rank Collector v4.0 - with Portfolio Management
采集东方财富股吧人气榜前100，计算买卖信号，支持自定义持仓管理和T+1卖出规则
"""

import json
import sys
import os

# Fix stdout encoding for Windows
if sys.platform == 'win32':
    try:
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
    except:
        pass

import re
import ssl
import urllib.request
from datetime import datetime

from history_store import save_snapshot, init_storage
from signal_engine import SignalEngine, save_signals_to_json
from portfolio import Portfolio

CONFIG = {
    "output_dir": __import__('pathlib').Path(__file__).parent / "output",
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


def fetch_stock_info(code):
    """获取单个股票信息"""
    try:
        prefix = 'sh' if code.startswith('6') else 'sz'
        url = f"https://web.sqt.gtimg.cn/q={prefix}{code}"
        req = urllib.request.Request(url, headers=HEADERS)
        
        with urllib.request.urlopen(req, timeout=10, context=SSL_CTX) as resp:
            text = resp.read().decode('gbk')
        
        for line in text.split(';'):
            if not line.strip():
                continue
            match = re.match(r'v_(\w+)="(.+)"', line.strip())
            if match:
                data = match.group(2).split('~')
                if len(data) > 3:
                    return {
                        'code': code,
                        'name': data[1],
                        'price': data[3],
                        'change_pct': float(data[32]) if data[32] else 0,
                    }
    except:
        pass
    return None


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


def generate_html(stocks, signals, update_time):
    """生成带买卖建议和持仓管理的HTML页面"""
    signal_map = {s['code']: s for s in signals}
    portfolio = Portfolio()
    holdings = portfolio.get_holdings_with_status()
    holding_codes = {h['code']: h for h in holdings}
    
    # 持仓总盈亏
    total_profit = 0
    holdings_html = ""
    holdings_js_data = []
    
    if holdings:
        for h in holdings:
            code = h['code']
            current_price = 0
            for s in stocks:
                if s.get('code') == code:
                    current_price = float(s.get('price', 0)) or 0
                    break
            
            profit = (current_price - h['buy_price']) * h['quantity']
            profit_pct = ((current_price - h['buy_price']) / h['buy_price'] * 100) if h['buy_price'] > 0 else 0
            total_profit += profit
            
            can_sell = h['can_sell']
            sell_status = h['sell_status']
            profit_class = "profit-up" if profit >= 0 else "profit-down"
            
            badge = '<span class="sell-ready">Can Sell</span>' if can_sell else f'<span class="sell-wait">{sell_status}</span>'
            
            holdings_html += f'''
            <div class="holding-card" onclick="showHoldingDetail('{code}')">
                <div class="holding-header">
                    <span class="holding-name">{h['name']}({code})</span>
                    {badge}
                </div>
                <div class="holding-info">
                    <span>Buy: {h['buy_price']:.2f}</span>
                    <span>Qty: {h['quantity']}</span>
                    <span>Cur: {current_price:.2f}</span>
                </div>
                <div class="holding-profit {profit_class}">
                    {f"+{profit:.0f} ({profit_pct:+.1f}%)" if profit >= 0 else f"{profit:.0f} ({profit_pct:.1f}%)"}
                </div>
            </div>'''
            
            holdings_js_data.append({
                'code': code,
                'name': h['name'],
                'buy_price': h['buy_price'],
                'quantity': h['quantity'],
                'current_price': current_price,
                'profit': profit,
                'profit_pct': profit_pct,
                'can_sell': can_sell,
                'sell_status': sell_status,
            })
    else:
        holdings_html = '<div class="no-holdings">No holdings. Add below to track.</div>'
    
    # 股票行
    stock_rows = ""
    for s in stocks:
        sig = signal_map.get(s.get('code', ''), {})
        code = s.get('code', '')
        in_portfolio = code in holding_codes
        
        # 信号样式
        signal = sig.get('signal', 'Hold')
        strength = sig.get('strength', 0)
        signal_class_map = {
            'Strong Buy': 'signal-strong-buy',
            'Buy': 'signal-buy',
            'Hold': 'signal-hold',
            'Caution': 'signal-caution',
            'Risk': 'signal-risk',
        }
        signal_class = signal_class_map.get(signal, 'signal-hold')
        stars = "★" * strength + "☆" * (5 - strength)
        
        change_pct = s.get('change_pct', 0)
        change_display = f"+{change_pct:.2f}%" if change_pct > 0 else f"{change_pct:.2f}%"
        change_class = "up" if change_pct > 0 else "down" if change_pct < 0 else ""
        
        volume = s.get('volume', 0)
        volume_display = f"{volume/10000:.1f}W" if volume > 10000 else str(volume)
        turnover = s.get('turnover_rate', 0)
        turnover_display = f"{turnover:.2f}%" if turnover else "-"
        
        # 持仓标记
        portfolio_badge = ""
        sell_warning = ""
        profit_info = ""
        
        if in_portfolio:
            h = holding_codes[code]
            can_sell = h['can_sell']
            current_price = float(s.get('price', 0)) or 0
            profit = (current_price - h['buy_price']) * h['quantity']
            profit_pct = ((current_price - h['buy_price']) / h['buy_price'] * 100) if h['buy_price'] > 0 else 0
            
            badge_class = "sell-ready-badge" if can_sell else "owned-badge"
            badge_text = "Can Sell" if can_sell else "Holding"
            portfolio_badge = f'<span class="{badge_class}">{badge_text}</span>'
            
            profit_class = "up" if profit >= 0 else "down"
            profit_info = f'<span class="profit-tag {profit_class}">{f"+{profit_pct:.1f}%" if profit >= 0 else f"{profit_pct:.1f}%"}</span>'
            
            # 如果可卖出且信号不好，提示卖出
            if can_sell and signal in ['Hold', 'Caution', 'Risk']:
                sell_warning = '<span class="sell-warning" title="Sell signal">SELL</span>'
        
        # 悬浮提示
        reasons = sig.get('reasons', [])
        risks = sig.get('risks', [])
        reasons_html = "<br>".join([f"+ {r}" for r in reasons]) if reasons else "None"
        risks_html = "<br>".join([f"- {r}" for r in risks]) if risks else "None"
        
        stock_rows += f'''
        <tr class="stock-row {'in-holding' if in_portfolio else ''}" data-code="{code}">
            <td class="rank-col"><span class="rank-badge rank-{s.get('rank', 1) if s.get('rank', 1) <= 3 else 'other'}">{s.get('rank', '')}</span></td>
            <td class="code-col">{code}</td>
            <td class="name-col" onclick="openGuba('{code}')">
                {s.get('name', '')} {portfolio_badge} {sell_warning} {profit_info}
            </td>
            <td class="price-col">{s.get('price', '-')}</td>
            <td class="change-col {change_class}">{change_display}</td>
            <td class="turnover-col">{turnover_display}</td>
            <td class="volume-col">{volume_display}</td>
            <td class="signal-col">
                <span class="signal-badge {signal_class}" title="Reasons: {reasons_html}\nRisks: {risks_html}">
                    {signal}
                </span>
                <span class="strength-stars">{stars}</span>
            </td>
        </tr>'''
    
    if not stocks:
        stock_rows = '<tr><td colspan="8" class="no-data">No data...</td></tr>'
    
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Stock Rank + Trading Signals</title>
    <meta http-equiv="refresh" content="300">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #0c1929 0%, #1a2a4a 50%, #0f2744 100%);
            min-height: 100vh;
            color: #e8e8e8;
            padding: 20px;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{
            text-align: center;
            margin-bottom: 25px;
            padding: 20px;
            background: rgba(255,255,255,0.03);
            border-radius: 20px;
        }}
        .title {{
            font-size: 1.8rem;
            margin-bottom: 8px;
        }}
        .title-text {{
            background: linear-gradient(90deg, #ff6b6b, #ffd93d, #6bcb77);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .live-badge {{
            background: #ff4444;
            color: white;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.7rem;
            animation: pulse 2s infinite;
        }}
        @keyframes pulse {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0.7; }} }}
        .disclaimer {{
            background: rgba(255,193,7,0.15);
            color: #ffc107;
            padding: 10px 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            text-align: center;
            font-size: 0.85rem;
        }}
        .signal-summary {{
            display: flex;
            justify-content: center;
            gap: 30px;
            margin: 20px 0;
        }}
        .signal-stat {{
            text-align: center;
            padding: 12px 20px;
            border-radius: 12px;
        }}
        .signal-stat.strong-buy {{ background: rgba(255,50,50,0.15); }}
        .signal-stat.buy {{ background: rgba(255,100,100,0.15); }}
        .signal-stat.hold {{ background: rgba(128,128,128,0.15); }}
        .signal-stat.risk {{ background: rgba(0,200,0,0.15); }}
        .signal-stat-value {{ font-size: 1.5rem; font-weight: 700; }}
        .signal-stat-label {{ font-size: 0.75rem; color: #aaa; margin-top: 3px; }}
        
        /* Holdings Panel */
        .holdings-panel {{
            background: rgba(255,255,255,0.03);
            border-radius: 15px;
            padding: 15px;
            margin-bottom: 20px;
            border: 1px solid rgba(0,212,255,0.2);
        }}
        .holdings-title {{
            font-size: 1rem;
            color: #00d4ff;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .holdings-title .total-profit {{
            margin-left: auto;
            font-size: 0.9rem;
        }}
        .holdings-title .total-profit.up {{ color: #ff4757; }}
        .holdings-title .total-profit.down {{ color: #2ed573; }}
        .holdings-list {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }}
        .holding-card {{
            background: rgba(0,0,0,0.3);
            border-radius: 10px;
            padding: 10px 15px;
            cursor: pointer;
            border: 1px solid rgba(255,255,255,0.1);
            min-width: 150px;
        }}
        .holding-card:hover {{ border-color: rgba(0,212,255,0.5); }}
        .holding-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 5px;
        }}
        .holding-name {{ font-weight: 600; color: #fff; font-size: 0.9rem; }}
        .sell-ready {{ background: #ff4757; color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.7rem; }}
        .sell-wait {{ background: rgba(255,255,255,0.1); color: #888; padding: 2px 8px; border-radius: 10px; font-size: 0.7rem; }}
        .holding-info {{ font-size: 0.75rem; color: #7a8fa6; margin-bottom: 5px; }}
        .holding-info span {{ margin-right: 8px; }}
        .holding-profit {{ font-weight: 600; font-size: 0.9rem; }}
        .holding-profit.profit-up {{ color: #ff4757; }}
        .holding-profit.profit-down {{ color: #2ed573; }}
        .no-holdings {{ color: #7a8fa6; text-align: center; padding: 20px; }}
        
        /* Add Holding Form */
        .add-holding-form {{
            background: rgba(255,255,255,0.03);
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 20px;
            border: 1px solid rgba(0,212,255,0.2);
        }}
        .form-title {{
            font-size: 1rem;
            color: #00d4ff;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .form-row {{
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            margin-bottom: 10px;
        }}
        .form-group {{
            display: flex;
            flex-direction: column;
            gap: 5px;
        }}
        .form-group label {{
            font-size: 0.75rem;
            color: #7a8fa6;
        }}
        .form-group input {{
            background: rgba(0,0,0,0.3);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 8px;
            padding: 8px 12px;
            color: #fff;
            font-size: 0.9rem;
            width: 120px;
        }}
        .form-group input:focus {{
            outline: none;
            border-color: #00d4ff;
        }}
        .btn {{
            padding: 10px 20px;
            border: none;
            border-radius: 10px;
            font-size: 0.9rem;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.2s;
        }}
        .btn-add {{
            background: linear-gradient(135deg, #00d4ff, #0099cc);
            color: white;
            align-self: flex-end;
        }}
        .btn:hover {{ transform: scale(1.05); }}
        .btn-delete {{
            background: rgba(255,71,87,0.3);
            color: #ff4757;
            padding: 5px 10px;
            font-size: 0.75rem;
        }}
        
        /* Table */
        .table-container {{
            background: rgba(255,255,255,0.02);
            border-radius: 20px;
            overflow: hidden;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            max-height: 60vh;
            overflow-y: auto;
        }}
        table {{ width: 100%; border-collapse: collapse; }}
        th {{
            background: rgba(255,107,107,0.1);
            padding: 14px 10px;
            text-align: left;
            font-weight: 600;
            color: #ff6b6b;
            font-size: 0.85rem;
            position: sticky;
            top: 0;
        }}
        td {{ padding: 12px 10px; border-bottom: 1px solid rgba(255,255,255,0.03); font-size: 0.9rem; }}
        tr:hover td {{ background: rgba(255,255,255,0.03); }}
        tr.in-holding td {{ background: rgba(0,212,255,0.05) !important; }}
        
        .rank-col {{ width: 50px; text-align: center; }}
        .rank-badge {{
            display: inline-flex;
            width: 28px;
            height: 28px;
            border-radius: 50%;
            font-weight: 700;
            font-size: 0.8rem;
            align-items: center;
            justify-content: center;
        }}
        .rank-1 {{ background: linear-gradient(135deg, #ffd700, #ff8c00); color: #000; }}
        .rank-2 {{ background: linear-gradient(135deg, #c0c0c0, #a8a8a8); color: #000; }}
        .rank-3 {{ background: linear-gradient(135deg, #cd7f32, #b8860b); color: #fff; }}
        .rank-other {{ background: rgba(255,255,255,0.08); }}
        
        .code-col {{ font-family: monospace; color: #7a8fa6; }}
        .name-col {{ font-weight: 600; cursor: pointer; }}
        .name-col:hover {{ color: #00d4ff; text-decoration: underline; }}
        .price-col {{ font-family: monospace; }}
        .change-col {{ font-weight: 600; font-family: monospace; }}
        .change-col.up {{ color: #ff4757; }}
        .change-col.down {{ color: #2ed573; }}
        .turnover-col, .volume-col {{ color: #7a8fa6; font-size: 0.85rem; }}
        
        .signal-col {{ min-width: 120px; }}
        .signal-badge {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 15px;
            font-size: 0.75rem;
            font-weight: 600;
            cursor: help;
        }}
        .signal-strong-buy {{ background: linear-gradient(135deg, #ff4444, #cc0000); color: white; }}
        .signal-buy {{ background: rgba(255,80,80,0.8); color: white; }}
        .signal-hold {{ background: rgba(128,128,128,0.5); color: #ddd; }}
        .signal-caution {{ background: rgba(255,165,0,0.5); color: #ffd700; }}
        .signal-risk {{ background: rgba(0,200,0,0.5); color: white; }}
        .strength-stars {{ display: block; font-size: 0.65rem; color: #ffd700; margin-top: 2px; }}
        
        /* Portfolio badges */
        .owned-badge {{ background: rgba(0,212,255,0.3); color: #00d4ff; padding: 2px 6px; border-radius: 8px; font-size: 0.65rem; margin-left: 5px; }}
        .sell-ready-badge {{ background: #ff4757; color: white; padding: 2px 6px; border-radius: 8px; font-size: 0.65rem; margin-left: 5px; animation: pulse 1s infinite; }}
        .sell-warning {{ background: #ff4757; color: white; padding: 2px 8px; border-radius: 8px; font-size: 0.65rem; margin-left: 5px; font-weight: bold; }}
        .profit-tag {{ font-size: 0.75rem; margin-left: 5px; padding: 1px 5px; border-radius: 5px; font-weight: 600; }}
        .profit-tag.up {{ background: rgba(255,71,87,0.2); color: #ff4757; }}
        .profit-tag.down {{ background: rgba(46,213,115,0.2); color: #2ed573; }}
        
        /* Modal */
        .modal {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 1000; justify-content: center; align-items: center; }}
        .modal.active {{ display: flex; }}
        .modal-content {{ background: linear-gradient(135deg, #1a2a4a, #0c1929); border-radius: 20px; padding: 30px; max-width: 500px; width: 90%; border: 1px solid rgba(0,212,255,0.3); }}
        .modal-header {{ display: flex; justify-content: space-between; margin-bottom: 20px; }}
        .modal-title {{ font-size: 1.3rem; color: #fff; }}
        .modal-close {{ background: none; border: none; color: #7a8fa6; font-size: 1.5rem; cursor: pointer; }}
        .action-buttons {{ display: flex; gap: 10px; margin-top: 20px; }}
        .btn-sell {{ background: linear-gradient(135deg, #2ed573, #26c064); color: white; }}
        .btn-cancel {{ background: rgba(255,255,255,0.1); color: #fff; }}
        
        .footer {{ text-align: center; margin-top: 30px; padding: 20px; color: #5a6a7a; font-size: 0.8rem; }}
        .auto-refresh {{ position: fixed; top: 20px; right: 20px; background: rgba(0,0,0,0.6); padding: 10px 15px; border-radius: 10px; font-size: 0.8rem; }}
        
        @media (max-width: 900px) {{ .turnover-col, .volume-col {{ display: none; }} }}
    </style>
</head>
<body>
    <div class="auto-refresh">Auto-refresh: 5min | Press R to reload</div>
    <div class="container">
        <div class="header">
            <div class="title">
                <span class="title-text">Stock Rank + Trading Signals</span>
                <span class="live-badge">LIVE</span>
            </div>
            <div style="color: #7a8fa6; margin-top: 8px;">Update: {update_time}</div>
        </div>
        
        <div class="disclaimer">
            Signals are for reference only. Not investment advice. Trade at your own risk!
        </div>
        
        <div class="signal-summary">
            <div class="signal-stat strong-buy">
                <div class="signal-stat-value">{len([s for s in signals if s.get('signal') == 'Strong Buy'])}</div>
                <div class="signal-stat-label">Strong Buy</div>
            </div>
            <div class="signal-stat buy">
                <div class="signal-stat-value">{len([s for s in signals if s.get('signal') == 'Buy'])}</div>
                <div class="signal-stat-label">Buy</div>
            </div>
            <div class="signal-stat hold">
                <div class="signal-stat-value">{len([s for s in signals if s.get('signal') in ['Hold', 'Caution']])}</div>
                <div class="signal-stat-label">Hold/Caution</div>
            </div>
            <div class="signal-stat risk">
                <div class="signal-stat-value">{len([s for s in signals if s.get('signal') == 'Risk'])}</div>
                <div class="signal-stat-label">Risk</div>
            </div>
        </div>
        
        <!-- Add Holding Form -->
        <div class="add-holding-form">
            <div class="form-title">
                <span>+ Add Holding</span>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Stock Code</label>
                    <input type="text" id="addCode" placeholder="e.g. 600519" maxlength="6">
                </div>
                <div class="form-group">
                    <label>Buy Price (CNY)</label>
                    <input type="number" id="addPrice" placeholder="e.g. 100.00" step="0.01" min="0">
                </div>
                <div class="form-group">
                    <label>Quantity (shares)</label>
                    <input type="number" id="addQty" placeholder="e.g. 100" min="1">
                </div>
                <div class="form-group">
                    <label>Buy Date</label>
                    <input type="date" id="addDate">
                </div>
                <button class="btn btn-add" onclick="addHolding()">Add</button>
            </div>
        </div>
        
        <!-- Holdings Panel -->
        <div class="holdings-panel">
            <div class="holdings-title">
                <span>Portfolio ({len(holdings)} stocks)</span>
                <span class="total-profit {'up' if total_profit >= 0 else 'down'}">{f'+{total_profit:.0f}' if total_profit >= 0 else f'{total_profit:.0f}'} CNY</span>
            </div>
            <div class="holdings-list">
                {holdings_html}
            </div>
        </div>
        
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>#</th><th>Code</th><th>Name</th><th>Price</th><th>Change</th><th>Turnover</th><th>Volume</th><th>Signal</th>
                    </tr>
                </thead>
                <tbody>
                    {stock_rows}
                </tbody>
            </table>
        </div>
        
        <div class="footer">
            <p>Source: EastMoney Guba | T+1 Trading Rules Apply | Signals for reference only</p>
            <p>Trading involves risk. Trade responsibly.</p>
        </div>
    </div>
    
    <script>
        const holdingsData = {json.dumps(holdings_js_data)};
        const allStocks = {json.dumps([{'code': s.get('code'), 'name': s.get('name'), 'price': s.get('price'), 'change_pct': s.get('change_pct')} for s in stocks])};
        
        function openGuba(code) {{
            if (code && code.length === 6) {{
                window.open('https://guba.eastmoney.com/list,' + code + '.html', '_blank');
            }}
        }}
        
        function showHoldingDetail(code) {{
            const h = holdingsData.find(x => x.code === code);
            if (!h) return;
            const m = document.getElementById('holdingModal');
            m.querySelector('.modal-body').innerHTML = `
                <div style="margin-bottom:15px;font-size:1.5rem;font-weight:bold;color:#fff;">${{h.name}} (${{h.code}})</div>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:15px;margin-bottom:20px;">
                    <div><div style="color:#7a8fa6;font-size:0.8rem;">Buy Price</div><div style="font-size:1.2rem;">${{h.buy_price.toFixed(2)}} CNY</div></div>
                    <div><div style="color:#7a8fa6;font-size:0.8rem;">Current Price</div><div style="font-size:1.2rem;">${{h.current_price.toFixed(2)}} CNY</div></div>
                    <div><div style="color:#7a8fa6;font-size:0.8rem;">Quantity</div><div style="font-size:1.2rem;">${{h.quantity}} shares</div></div>
                    <div><div style="color:#7a8fa6;font-size:0.8rem;">P/L</div><div style="font-size:1.2rem;color:${{h.profit >= 0 ? '#ff4757' : '#2ed573'}};">${{h.profit >= 0 ? '+' : ''}}${{h.profit.toFixed(2)}} (${{h.profit_pct >= 0 ? '+' : ''}}${{h.profit_pct.toFixed(2)}}%)</div></div>
                    <div><div style="color:#7a8fa6;font-size:0.8rem;">T+1 Status</div><div style="font-size:1.2rem;color:${{h.can_sell ? '#2ed573' : '#ffc107'}};">${{h.sell_status}}</div></div>
                </div>

'''
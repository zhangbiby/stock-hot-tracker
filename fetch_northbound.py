#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
北向资金数据采集模块
数据来源：东方财富
"""

import urllib.request
import json
import ssl
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# SSL上下文
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json',
}


def fetch_northbound_daily() -> Dict:
    """
    获取当日北向资金净流入数据
    
    Returns:
        {
            'date': '2026-03-27',
            'total_inflow': 45.67,  # 总净流入（亿元）
            'shanghai_inflow': 23.45,  # 沪股通
            'shenzhen_inflow': 22.22,  # 深股通
            'top_buy': [...],  # 买入前10
            'top_sell': [...]  # 卖出前10
        }
    """
    try:
        # 东方财富北向资金API
        url = 'https://push2.eastmoney.com/api/qt/kamt.rtmin/get'
        
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10, context=SSL_CTX) as resp:
            data = json.loads(resp.read().decode())
        
        if data.get('data'):
            d = data['data']
            return {
                'date': datetime.now().strftime('%Y-%m-%d'),
                'total_inflow': float(d.get('s2n', 0)),  # 当日净流入
                'shanghai_inflow': float(d.get('s2n', 0)),  # 沪股通
                'shenzhen_inflow': float(d.get('s2n', 0)),  # 深股通
                'timestamp': datetime.now().isoformat()
            }
        
        return {}
    except Exception as e:
        print(f"[Northbound] Error fetching daily: {e}")
        return {}


def fetch_northbound_top10() -> Dict:
    """
    获取北向资金买入/卖出前10股票
    
    Returns:
        {
            'top_buy': [
                {'code': '000001', 'name': '平安银行', 'amount': 5.67},
                ...
            ],
            'top_sell': [
                {'code': '000002', 'name': '万科A', 'amount': -3.45},
                ...
            ]
        }
    """
    try:
        # 沪股通Top10
        url_sh = 'https://push2.eastmoney.com/api/qt/stock/get?secid=1.000001&fields=f184,f185,f186,f187,f188,f189,f190,f191,f192,f193'
        
        req = urllib.request.Request(url_sh, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10, context=SSL_CTX) as resp:
            data = json.loads(resp.read().decode())
        
        top_buy = []
        top_sell = []
        
        if data.get('data'):
            # 解析买入前10
            for i in range(1, 11):
                code_key = f'f{i+183}'  # f184-f193
                name_key = f'f{i+193}'  # f194-f203
                amount_key = f'f{i+203}'  # f204-f213
                
                code = data['data'].get(code_key, '')
                name = data['data'].get(name_key, '')
                amount = float(data['data'].get(amount_key, 0))
                
                if code and amount > 0:
                    top_buy.append({
                        'code': code[2:] if code.startswith('1.') or code.startswith('0.') else code,
                        'name': name,
                        'amount': round(amount / 10000, 2)  # 转换为亿元
                    })
                elif code and amount < 0:
                    top_sell.append({
                        'code': code[2:] if code.startswith('1.') or code.startswith('0.') else code,
                        'name': name,
                        'amount': round(amount / 10000, 2)
                    })
        
        return {
            'top_buy': sorted(top_buy, key=lambda x: x['amount'], reverse=True)[:10],
            'top_sell': sorted(top_sell, key=lambda x: x['amount'])[:10],
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        print(f"[Northbound] Error fetching top10: {e}")
        return {'top_buy': [], 'top_sell': []}


def fetch_northbound_history(days: int = 30) -> List[Dict]:
    """
    获取北向资金历史数据
    
    Args:
        days: 天数
        
    Returns:
        [
            {'date': '2026-03-27', 'inflow': 45.67},
            ...
        ]
    """
    try:
        # 东方财富历史数据API
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        url = f'https://push2.eastmoney.com/api/qt/kamt.kline/get?fields1=f1,f2,f3,f4&fields2=f51,f52,f53,f54,f55,f56'
        
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10, context=SSL_CTX) as resp:
            data = json.loads(resp.read().decode())
        
        history = []
        if data.get('data') and data['data'].get('klines'):
            for line in data['data']['klines']:
                # 格式: date,inflow,sh_inflow,sz_inflow,cumulative
                parts = line.split(',')
                if len(parts) >= 4:
                    history.append({
                        'date': parts[0],
                        'inflow': float(parts[1]),
                        'shanghai_inflow': float(parts[2]),
                        'shenzhen_inflow': float(parts[3])
                    })
        
        return history
    except Exception as e:
        print(f"[Northbound] Error fetching history: {e}")
        return []


def analyze_northbound_trend(history: List[Dict]) -> Dict:
    """
    分析北向资金趋势
    
    Args:
        history: 历史数据列表
        
    Returns:
        {
            'trend': 'increasing' | 'decreasing' | 'stable',
            '5d_avg': 45.6,
            '10d_avg': 40.2,
            'momentum': 'strong_inflow' | 'inflow' | 'neutral' | 'outflow' | 'strong_outflow'
        }
    """
    if not history or len(history) < 5:
        return {'trend': 'unknown', 'momentum': 'neutral'}
    
    # 计算5日/10日均值
    recent_5 = [h['inflow'] for h in history[-5:]]
    recent_10 = [h['inflow'] for h in history[-10:]]
    
    avg_5d = sum(recent_5) / len(recent_5)
    avg_10d = sum(recent_10) / len(recent_10)
    
    # 判断趋势
    if avg_5d > avg_10d * 1.2:
        trend = 'increasing'
    elif avg_5d < avg_10d * 0.8:
        trend = 'decreasing'
    else:
        trend = 'stable'
    
    # 判断动量
    latest = recent_5[-1]
    if latest > 100:
        momentum = 'strong_inflow'
    elif latest > 50:
        momentum = 'inflow'
    elif latest > -50:
        momentum = 'neutral'
    elif latest > -100:
        momentum = 'outflow'
    else:
        momentum = 'strong_outflow'
    
    return {
        'trend': trend,
        '5d_avg': round(avg_5d, 2),
        '10d_avg': round(avg_10d, 2),
        'momentum': momentum
    }


def save_northbound_data(data: Dict):
    """保存北向资金数据"""
    output_file = OUTPUT_DIR / 'northbound_data.json'
    
    # 加载现有数据
    existing = []
    if output_file.exists():
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                existing = json.load(f)
        except:
            existing = []
    
    # 添加新数据
    existing.append(data)
    
    # 只保留最近30天
    existing = existing[-30:]
    
    # 保存
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    
    print(f"[Northbound] 数据已保存: {output_file}")


def get_northbound_factor(stock_code: str) -> float:
    """
    获取单只股票的北向资金因子得分
    
    Args:
        stock_code: 股票代码
        
    Returns:
        因子得分 (0-100)
    """
    try:
        # 获取Top10数据
        top_data = fetch_northbound_top10()
        
        # 检查是否在买入前10
        for item in top_data.get('top_buy', []):
            if item['code'] == stock_code:
                # 根据排名计算得分
                return max(20, 50 - top_data['top_buy'].index(item) * 3)
        
        # 检查是否在卖出前10
        for item in top_data.get('top_sell', []):
            if item['code'] == stock_code:
                return min(30, 20 + top_data['top_sell'].index(item) * 2)
        
        return 30  # 默认中性
    except:
        return 30


def main():
    """主函数"""
    print("=" * 60)
    print("Northbound Capital Data Collection")
    print("=" * 60)
    
    # Get daily data
    daily = fetch_northbound_daily()
    print(f"\nDaily Net Inflow: {daily.get('total_inflow', 0):.2f} billion CNY")
    
    # Get Top10
    top10 = fetch_northbound_top10()
    print(f"\nTop 10 Buy:")
    for i, item in enumerate(top10.get('top_buy', [])[:5], 1):
        print(f"  {i}. {item['name']} ({item['code']}): +{item['amount']:.2f}B")
    
    # Get history trend
    history = fetch_northbound_history(10)
    if history:
        trend = analyze_northbound_trend(history)
        print(f"\nTrend Analysis:")
        print(f"  5D Avg: {trend.get('5d_avg', 0):.2f}B")
        print(f"  10D Avg: {trend.get('10d_avg', 0):.2f}B")
        print(f"  Trend: {trend.get('trend', 'unknown')}")
    
    # Save data
    save_data = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'daily': daily,
        'top10': top10,
        'history_count': len(history),
        'timestamp': datetime.now().isoformat()
    }
    save_northbound_data(save_data)
    
    print("\n" + "=" * 60)
    print("Collection Complete")
    print("=" * 60)


if __name__ == '__main__':
    main()

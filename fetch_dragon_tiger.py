#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
龙虎榜数据采集模块
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

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json',
}

# 知名游资席位
FAMOUS_SEATS = {
    '章盟主': ['国泰君安上海江苏路', '中信证券杭州延安路'],
    '赵老哥': ['中国银河绍兴', '浙商证券绍兴分公司'],
    '方新侠': ['兴业证券陕西分公司', '中信证券西安朱雀大街'],
    '作手新一': ['国泰君安南京太平南路'],
    '炒股养家': ['华鑫证券上海宛平南路', '华鑫证券上海茅台路'],
    '小鳄鱼': ['南京证券南京大钟亭', '国泰君安南京金融城'],
    '上塘路': ['财通证券杭州上塘路'],
    '桑田路': ['国盛证券宁波桑田路'],
    '佛山系': ['光大证券佛山绿景路', '长江证券佛山普澜二路'],
    '思明南路': ['东亚前海证券上海分公司'],
}


def fetch_dragon_tiger_list(date: str = None) -> List[Dict]:
    """
    获取每日龙虎榜数据
    
    Args:
        date: '2026-03-27', 默认当天
        
    Returns:
        [
            {
                'code': '000001',
                'name': '平安银行',
                'close_price': 10.5,
                'change_pct': 10.02,
                'turnover': 15.8,  # 成交额（亿）
                'reason': '日涨幅偏离值达7%',
                'buy_seats': [
                    {'seat': '机构专用', 'amount': 1.5},
                    {'seat': '国泰君安上海江苏路', 'amount': 0.8},
                ],
                'sell_seats': [
                    {'seat': '机构专用', 'amount': -0.6},
                ],
                'net_amount': 2.3,  # 净买入（亿）
            }
        ]
    """
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')
    
    try:
        # 东方财富龙虎榜API
        url = f'https://datacenter-web.eastmoney.com/api/data/v1/get?sortColumns=SECURITY_CODE&sortTypes=-1&pageSize=500&pageNumber=1&reportName=RPT_DAILYBILLBOARD_DETAILS&columns=ALL&filter=(TRADE_DATE%3D%27{date}%27)'
        
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15, context=SSL_CTX) as resp:
            data = json.loads(resp.read().decode())
        
        results = []
        if data.get('result') and data['result'].get('data'):
            for item in data['result']['data']:
                code = item.get('SECURITY_CODE', '')
                name = item.get('SECURITY_NAME_ABBR', '')
                
                # 解析买卖席位
                buy_seats = []
                sell_seats = []
                
                # 买1-买5
                for i in range(1, 6):
                    seat = item.get(f'BUYER_{i}_NAME', '')
                    amount = item.get(f'BUYER_{i}_AMOUNT', 0)
                    if seat and amount:
                        buy_seats.append({
                            'seat': seat,
                            'amount': round(amount / 100000000, 2),  # 转换为亿
                            'is_famous': any(seat in seats for seats in FAMOUS_SEATS.values()),
                            'famous_name': next((k for k, v in FAMOUS_SEATS.items() if seat in v), None)
                        })
                
                # 卖1-卖5
                for i in range(1, 6):
                    seat = item.get(f'SELLER_{i}_NAME', '')
                    amount = item.get(f'SELLER_{i}_AMOUNT', 0)
                    if seat and amount:
                        sell_seats.append({
                            'seat': seat,
                            'amount': -round(amount / 100000000, 2),
                            'is_famous': any(seat in seats for seats in FAMOUS_SEATS.values()),
                            'famous_name': next((k for k, v in FAMOUS_SEATS.items() if seat in v), None)
                        })
                
                results.append({
                    'code': code,
                    'name': name,
                    'close_price': item.get('CLOSE_PRICE', 0),
                    'change_pct': item.get('CHANGE_RATE', 0),
                    'turnover': round(item.get('TURNOVER', 0) / 100000000, 2),
                    'reason': item.get('EXPLANATION', ''),
                    'buy_seats': buy_seats,
                    'sell_seats': sell_seats,
                    'net_amount': round(item.get('NET_AMOUNT', 0) / 100000000, 2),
                    'date': date
                })
        
        return results
    except Exception as e:
        print(f"[DragonTiger] Error: {e}")
        return []


def analyze_seat_behavior(seat_name: str, days: int = 30) -> Dict:
    """
    分析特定席位的操作风格
    
    Args:
        seat_name: 席位名称
        days: 分析天数
        
    Returns:
        {
            'total_appearances': 50,  # 出现次数
            'buy_success_rate': 65.5,  # 买入后3日上涨概率
            'avg_hold_days': 2.5,  # 平均持仓天数
            'favorite_sectors': ['科技', '医药'],  # 偏好板块
            'style': '打板' | '趋势' | '波段'
        }
    """
    # 简化实现，实际应该查询历史龙虎榜数据
    return {
        'seat_name': seat_name,
        'total_appearances': 0,
        'buy_success_rate': 0,
        'avg_hold_days': 0,
        'favorite_sectors': [],
        'style': 'unknown'
    }


def get_dragon_tiger_factor(stock_code: str) -> Dict:
    """
    获取股票的龙虎榜因子
    
    Args:
        stock_code: 股票代码
        
    Returns:
        {
            'score': 75,  # 0-100
            'is_on_list': True,  # 是否上榜
            'net_amount': 1.5,  # 净买入（亿）
            'famous_seats': ['章盟主', '赵老哥'],  # 知名游资
            'institutional': True,  # 是否有机构参与
            'signal': 'strong_buy' | 'buy' | 'neutral' | 'sell'
        }
    """
    # 获取今日龙虎榜
    today_list = fetch_dragon_tiger_list()
    
    # 查找股票
    stock_data = next((s for s in today_list if s['code'] == stock_code), None)
    
    if not stock_data:
        return {
            'score': 30,
            'is_on_list': False,
            'net_amount': 0,
            'famous_seats': [],
            'institutional': False,
            'signal': 'neutral'
        }
    
    # 计算得分
    score = 30  # 基础分（上榜就有一定关注度）
    
    # 净买入加分
    net = stock_data['net_amount']
    if net > 2:
        score += 30
    elif net > 1:
        score += 20
    elif net > 0:
        score += 10
    else:
        score -= 10
    
    # 知名游资加分
    famous_buyers = [s for s in stock_data['buy_seats'] if s.get('is_famous')]
    famous_sellers = [s for s in stock_data['sell_seats'] if s.get('is_famous')]
    
    score += len(famous_buyers) * 10
    score -= len(famous_sellers) * 5
    
    # 机构参与加分
    institutional_buy = any('机构' in s['seat'] for s in stock_data['buy_seats'])
    institutional_sell = any('机构' in s['seat'] for s in stock_data['sell_seats'])
    
    if institutional_buy:
        score += 15
    if institutional_sell:
        score -= 10
    
    # 确定信号
    if score >= 70:
        signal = 'strong_buy'
    elif score >= 50:
        signal = 'buy'
    elif score >= 30:
        signal = 'neutral'
    else:
        signal = 'sell'
    
    return {
        'score': min(100, max(0, score)),
        'is_on_list': True,
        'net_amount': net,
        'famous_seats': list(set([s['famous_name'] for s in famous_buyers if s.get('famous_name')])),
        'institutional': institutional_buy or institutional_sell,
        'signal': signal,
        'raw_data': stock_data
    }


def save_dragon_tiger_data(data: List[Dict]):
    """保存龙虎榜数据"""
    output_file = OUTPUT_DIR / 'dragon_tiger_data.json'
    
    # 加载现有数据
    existing = []
    if output_file.exists():
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                existing = json.load(f)
        except:
            existing = []
    
    # 添加新数据
    today = datetime.now().strftime('%Y-%m-%d')
    existing = [d for d in existing if d.get('date') != today]  # 去重
    existing.extend(data)
    
    # 只保留最近30天
    existing = existing[-500:]  # 限制数量
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    
    print(f"[DragonTiger] Data saved: {len(data)} stocks")


def main():
    """主函数"""
    print("=" * 60)
    print("Dragon Tiger List Data Collection")
    print("=" * 60)
    
    # 获取今日龙虎榜
    data = fetch_dragon_tiger_list()
    print(f"\nTotal: {len(data)} stocks on list today")
    
    # 显示前5
    for i, item in enumerate(data[:5], 1):
        print(f"\n{i}. {item['name']} ({item['code']})")
        print(f"   Change: +{item['change_pct']:.2f}%")
        print(f"   Net Buy: {item['net_amount']:.2f}B CNY")
        print(f"   Reason: {item['reason']}")
        
        # 显示知名游资
        famous = [s for s in item['buy_seats'] if s.get('is_famous')]
        if famous:
            print(f"   Famous Buyers: {', '.join([s['famous_name'] for s in famous if s.get('famous_name')])}")
    
    # 保存数据
    save_dragon_tiger_data(data)
    
    # 测试因子计算
    if data:
        test_code = data[0]['code']
        factor = get_dragon_tiger_factor(test_code)
        print(f"\n[Test] Factor for {test_code}:")
        print(f"   Score: {factor['score']}")
        print(f"   Signal: {factor['signal']}")
        print(f"   Famous Seats: {factor['famous_seats']}")
    
    print("\n" + "=" * 60)
    print("Collection Complete")
    print("=" * 60)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
行业资金流数据采集模块
数据来源：东方财富
"""

import urllib.request
import json
import ssl
from datetime import datetime
from pathlib import Path
from typing import List, Dict

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
}


def fetch_industry_capital_flow() -> List[Dict]:
    """
    获取行业资金净流入排名
    
    Returns:
        [
            {
                'industry_code': 'BK0428',
                'industry_name': '电力行业',
                'change_pct': 2.35,
                'main_inflow': 15.67,  # 主力净流入（亿）
                'large_inflow': 12.45,  # 大单净流入
                'medium_inflow': 3.22,  # 中单净流入
                'small_outflow': -5.43,  # 小单净流出
                'top_stocks': ['600396', '601016']  # 领涨股
            }
        ]
    """
    try:
        # 东方财富行业资金流API
        url = 'https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=100&po=1&np=1&fltt=2&invt=2&fid=f62&fs=m:90+t:2+f:!50&fields=f12,f13,f14,f20,f21,f22,f23,f24,f25,f26,f33,f34,f35,f36,f37,f38,f39,f40,f41,f42,f43,f44,f45,f46,f47,f48,f49,f50,f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65,f66,f67,f68,f69,f70,f71,f72,f73,f74,f75,f76,f77,f78,f79,f80,f81,f82,f83,f84,f85,f86,f87,f88,f89,f90,f91,f92,f93,f94,f95,f96,f97,f98,f99,f100'
        
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15, context=SSL_CTX) as resp:
            data = json.loads(resp.read().decode())
        
        results = []
        if data.get('data') and data['data'].get('diff'):
            for item in data['data']['diff']:
                results.append({
                    'industry_code': item.get('f12', ''),
                    'industry_name': item.get('f14', ''),
                    'change_pct': float(item.get('f3', 0)),
                    'main_inflow': round(float(item.get('f62', 0)) / 10000, 2),  # 转换为亿
                    'large_inflow': round(float(item.get('f66', 0)) / 10000, 2),
                    'medium_inflow': round(float(item.get('f70', 0)) / 10000, 2),
                    'small_outflow': round(float(item.get('f74', 0)) / 10000, 2),
                    'leading_stock': item.get('f128', ''),  # 领涨股
                    'leading_change': float(item.get('f136', 0))
                })
        
        return sorted(results, key=lambda x: x['main_inflow'], reverse=True)
    except Exception as e:
        print(f"[IndustryFlow] Error: {e}")
        return []


def get_industry_strength_ranking() -> Dict:
    """
    获取行业强度排名
    
    Returns:
        {
            'strongest': ['电力', '煤炭', '银行'],  # 最强
            'strong': ['医药', '科技'],
            'weak': ['房地产', '建筑'],
            'weakest': ['旅游', '餐饮']
        }
    """
    flow_data = fetch_industry_capital_flow()
    
    if not flow_data:
        return {}
    
    # 按资金流入排序
    sorted_by_flow = sorted(flow_data, key=lambda x: x['main_inflow'], reverse=True)
    
    # 按涨跌幅排序
    sorted_by_change = sorted(flow_data, key=lambda x: x['change_pct'], reverse=True)
    
    n = len(flow_data) // 4
    
    return {
        'strongest': [s['industry_name'] for s in sorted_by_flow[:n]],
        'strong': [s['industry_name'] for s in sorted_by_flow[n:2*n]],
        'weak': [s['industry_name'] for s in sorted_by_flow[2*n:3*n]],
        'weakest': [s['industry_name'] for s in sorted_by_flow[3*n:]],
        'top5_inflow': sorted_by_flow[:5],
        'top5_change': sorted_by_change[:5]
    }


def get_industry_factor(stock_code: str, stock_name: str = '') -> Dict:
    """
    获取股票所属行业的因子得分
    
    Args:
        stock_code: 股票代码
        stock_name: 股票名称（用于识别行业）
        
    Returns:
        {
            'score': 75,
            'industry_name': '电力',
            'industry_rank': 3,  # 行业排名
            'industry_change': 2.35,  # 行业涨跌幅
            'signal': 'strong' | 'good' | 'neutral' | 'weak'
        }
    """
    # 获取行业数据
    industries = fetch_industry_capital_flow()
    
    if not industries:
        return {'score': 30, 'signal': 'neutral'}
    
    # 简化：根据股票名称关键词匹配行业
    # 实际应该查询股票所属行业
    industry_keywords = {
        '电力': ['电', '能源', '风电', '水电', '火电'],
        '银行': ['银行'],
        '医药': ['药', '医', '生物'],
        '科技': ['科技', '电子', '芯片', '软件'],
        '煤炭': ['煤', '炭'],
        '房地产': ['地产', '房'],
    }
    
    # 尝试匹配行业
    matched_industry = None
    for industry_name, keywords in industry_keywords.items():
        if any(kw in stock_name for kw in keywords):
            matched_industry = next((i for i in industries if industry_name in i['industry_name']), None)
            break
    
    # 如果没匹配到，使用整体市场情况
    if not matched_industry:
        # 取前3名行业的平均
        top3 = industries[:3]
        avg_change = sum(i['change_pct'] for i in top3) / 3
        avg_inflow = sum(i['main_inflow'] for i in top3) / 3
        
        score = 30
        if avg_inflow > 50:
            score += 30
        elif avg_inflow > 20:
            score += 20
        elif avg_inflow > 0:
            score += 10
        
        return {
            'score': min(100, score),
            'industry_name': 'Unknown',
            'industry_rank': 0,
            'industry_change': avg_change,
            'signal': 'strong' if score >= 60 else 'good' if score >= 45 else 'neutral'
        }
    
    # 计算得分
    rank = industries.index(matched_industry) + 1
    inflow = matched_industry['main_inflow']
    change = matched_industry['change_pct']
    
    score = 30  # 基础分
    
    # 排名加分
    if rank <= 5:
        score += 40
    elif rank <= 10:
        score += 30
    elif rank <= 20:
        score += 20
    elif rank <= 30:
        score += 10
    
    # 资金流入加分
    if inflow > 20:
        score += 20
    elif inflow > 10:
        score += 10
    elif inflow > 0:
        score += 5
    else:
        score -= 10
    
    # 涨跌幅加分
    if change > 3:
        score += 10
    elif change > 1:
        score += 5
    elif change < -2:
        score -= 10
    
    # 确定信号
    if score >= 70:
        signal = 'strong'
    elif score >= 50:
        signal = 'good'
    elif score >= 35:
        signal = 'neutral'
    else:
        signal = 'weak'
    
    return {
        'score': min(100, max(0, score)),
        'industry_name': matched_industry['industry_name'],
        'industry_rank': rank,
        'industry_change': change,
        'industry_inflow': inflow,
        'signal': signal
    }


def save_industry_data(data: List[Dict]):
    """保存行业数据"""
    output_file = OUTPUT_DIR / 'industry_flow.json'
    
    save_data = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'industries': data,
        'timestamp': datetime.now().isoformat()
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(save_data, f, ensure_ascii=False, indent=2)
    
    print(f"[IndustryFlow] Data saved: {len(data)} industries")


def main():
    """主函数"""
    print("=" * 60)
    print("Industry Capital Flow Collection")
    print("=" * 60)
    
    # 获取行业资金流
    data = fetch_industry_capital_flow()
    print(f"\nTotal: {len(data)} industries")
    
    # 显示前10
    print("\nTop 10 Inflow:")
    for i, item in enumerate(data[:10], 1):
        print(f"{i:2d}. {item['industry_name']:8s} "
              f"Change: {item['change_pct']:+6.2f}% "
              f"Inflow: {item['main_inflow']:+8.2f}B")
    
    # 获取强度排名
    ranking = get_industry_strength_ranking()
    print(f"\nStrongest Industries: {', '.join(ranking.get('strongest', [])[:5])}")
    print(f"Weakest Industries: {', '.join(ranking.get('weakest', [])[:5])}")
    
    # 保存数据
    save_industry_data(data)
    
    print("\n" + "=" * 60)
    print("Collection Complete")
    print("=" * 60)


if __name__ == '__main__':
    main()

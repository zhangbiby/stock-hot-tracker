#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成模拟历史数据用于ML模型训练
基于真实市场模式生成合理的模拟数据
"""

import sys
import json
import random
from pathlib import Path
from datetime import datetime, timedelta
import csv

if sys.platform == 'win32':
    try:
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    except:
        pass

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"

def generate_history_data():
    """生成模拟历史数据"""
    print("=" * 50)
    print("Generating simulated history data...")
    print("=" * 50)
    
    # 热门股票列表
    stocks = [
        {'code': '600396', 'name': '华电辽能'},
        {'code': '601016', 'name': '节能风电'},
        {'code': '002361', 'name': '恒锋信息'},
        {'code': '600666', 'name': '奥马电器'},
        {'code': '600905', 'name': '长江电力'},
        {'code': '601628', 'name': '中国卫通'},
        {'code': '600171', 'name': '上海石化'},
        {'code': '601186', 'name': '中国中车'},
        {'code': '600036', 'name': '招商银行'},
        {'code': '600519', 'name': '贵州茅台'},
    ]
    
    # 生成过去30天的历史快照
    base_time = datetime.now()
    total_snapshots = 0
    
    # 特征列
    FEATURE_COLS = [
        'rank', 'change_pct', 'turnover_rate', 'volume_ratio',
        'amplitude', 'rsi', 'macd', 'bb_position', 'ma5_diff', 'ma20_diff'
    ]
    
    training_data = []
    
    for day_offset in range(30, 0, -1):
        # 每天生成多个时间点快照
        timestamps_per_day = random.randint(5, 10)
        
        for minute_offset in range(timestamps_per_day):
            # 创建时间点
            snapshot_time = base_time - timedelta(days=day_offset, minutes=minute_offset * 30)
            time_str = snapshot_time.strftime("%Y-%m-%d %H:%M:%S")
            
            # 为每只股票生成数据
            snapshots = []
            for rank, stock in enumerate(stocks[:10], 1):
                # 基于排名生成合理的特征
                # 排名越靠前，涨幅概率越高，换手率越高
                
                # 基础价格 (5-50元)
                base_price = random.uniform(5, 50)
                
                # 涨跌幅 (-10% 到 +10%)
                # 排名好的更容易正涨
                rank_bias = (11 - rank) * 0.5  # 排名1有+5%偏差
                change_pct = random.uniform(-8, 8) + rank_bias
                change_pct = max(-10, min(10, change_pct))
                
                # 换手率 (5% - 50%)
                # 排名好的换手率更高
                turnover_rate = random.uniform(5, 30) + (11 - rank) * 2
                turnover_rate = min(50, turnover_rate)
                
                # 量比 (0.5 - 3)
                volume_ratio = random.uniform(0.5, 2.5)
                
                # 振幅 (1% - 15%)
                amplitude = random.uniform(2, 12)
                
                # RSI (20 - 80)
                rsi = random.uniform(25, 75)
                
                # MACD (-2 到 2)
                macd = random.uniform(-1.5, 1.5)
                
                # 布林带位置 (0 - 1)
                bb_position = random.uniform(0.2, 0.8)
                
                # MA差值
                ma5_diff = random.uniform(-3, 3)
                ma20_diff = random.uniform(-5, 5)
                
                # 生成未来1天收益率 (用于标签)
                # 基于当前特征的合理预测
                future_return = 0
                if rank <= 3 and change_pct > 0:
                    future_return = 1  # 上涨
                elif rank >= 8 and change_pct < -3:
                    future_return = 0  # 下跌
                else:
                    future_return = random.choice([0, 1])  # 随机
                
                stock_data = {
                    'code': stock['code'],
                    'name': stock['name'],
                    'price': round(base_price * (1 + change_pct/100), 2),
                    'change': round(base_price * change_pct / 100, 2),
                    'change_pct': round(change_pct, 2),
                    'volume': int(random.uniform(1000000, 50000000)),
                    'turnover_rate': round(turnover_rate, 2),
                    'rank': rank,
                    'rsi': round(rsi, 2),
                    'macd': round(macd, 4),
                    'bb_position': round(bb_position, 2),
                    'volume_ratio': round(volume_ratio, 2),
                    'amplitude': round(amplitude, 2),
                    'ma5_diff': round(ma5_diff, 2),
                    'ma20_diff': round(ma20_diff, 2),
                    'time': time_str,
                }
                snapshots.append(stock_data)
                
                # 添加到训练数据
                training_data.append({
                    'rank': rank,
                    'change_pct': round(change_pct, 2),
                    'turnover_rate': round(turnover_rate, 2),
                    'volume_ratio': round(volume_ratio, 2),
                    'amplitude': round(amplitude, 2),
                    'rsi': round(rsi, 2),
                    'macd': round(macd, 4),
                    'bb_position': round(bb_position, 2),
                    'ma5_diff': round(ma5_diff, 2),
                    'ma20_diff': round(ma20_diff, 2),
                    'target': future_return,
                })
            
            # 保存到数据库
            try:
                from db_manager import db_manager
                for stock in snapshots:
                    db_manager.save_snapshot([stock])
                total_snapshots += len(snapshots)
            except Exception as e:
                print(f"DB save error: {e}")
    
    # 保存训练数据CSV
    csv_file = OUTPUT_DIR / "training_data.csv"
    with open(csv_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=FEATURE_COLS + ['target'])
        writer.writeheader()
        writer.writerows(training_data)
    
    print(f"\nGenerated:")
    print(f"  Snapshots: {total_snapshots}")
    print(f"  Training samples: {len(training_data)}")
    print(f"  Up samples: {sum(1 for x in training_data if x['target'] == 1)}")
    print(f"  Down samples: {sum(1 for x in training_data if x['target'] == 0)}")
    print(f"\nSaved to:")
    print(f"  - {csv_file}")
    print(f"  - Database snapshots table")
    
    return True


if __name__ == "__main__":
    success = generate_history_data()
    sys.exit(0 if success else 1)

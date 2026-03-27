#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速生成训练数据用于ML模型训练
"""

import csv
import random
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent / "output"

# 特征列
FEATURE_COLS = [
    'rank', 'change_pct', 'turnover_rate', 'volume_ratio',
    'amplitude', 'rsi', 'macd', 'bb_position', 'ma5_diff', 'ma20_diff'
]

def generate_training_data(n_samples=500):
    """生成训练数据"""
    print(f"Generating {n_samples} training samples...")
    
    data = []
    for i in range(n_samples):
        # 排名 (1-100)
        rank = random.randint(1, 100)
        
        # 基于排名的特征偏差（排名好的股票特征更好）
        rank_factor = (101 - rank) / 100  # 1.0 for rank 1, 0.01 for rank 100
        
        # 涨跌幅 (-10% 到 +10%)
        change_pct = random.uniform(-8, 8) + rank_factor * 3
        change_pct = max(-10, min(10, change_pct))
        
        # 换手率 (5% - 50%)
        turnover_rate = random.uniform(5, 30) + rank_factor * 15
        
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
        
        # 标签: 未来是否上涨
        # 基于特征计算上涨概率
        up_prob = 0.5
        if rank <= 10:
            up_prob += 0.3
        if change_pct > 3:
            up_prob += 0.2
        if turnover_rate > 20:
            up_prob += 0.1
        if rsi > 50:
            up_prob += 0.1
        if macd > 0:
            up_prob += 0.1
        
        target = 1 if random.random() < up_prob else 0
        
        data.append({
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
            'target': target,
        })
    
    # 保存CSV
    csv_file = OUTPUT_DIR / "training_data.csv"
    with open(csv_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=FEATURE_COLS + ['target'])
        writer.writeheader()
        writer.writerows(data)
    
    up_count = sum(1 for x in data if x['target'] == 1)
    down_count = len(data) - up_count
    
    print(f"Generated {n_samples} samples")
    print(f"   Up: {up_count} ({up_count/len(data)*100:.1f}%)")
    print(f"   Down: {down_count} ({down_count/len(data)*100:.1f}%)")
    print(f"   Saved to: {csv_file}")
    
    return True


if __name__ == "__main__":
    generate_training_data(500)

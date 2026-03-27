#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
构建机器学习训练数据集
遍历历史快照，计算特征和标签（未来1日收益率）
输出: output/training_data.csv
"""

import sys
import json
import csv
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

if sys.platform == 'win32':
    try:
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    except:
        pass

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"

from history_store import load_history, get_latest_snapshot
from db_manager import db_manager


def load_all_snapshots():
    """从数据库加载所有历史快照，按时间排序"""
    all_snapshots = []
    
    try:
        # 从数据库获取所有快照
        with db_manager._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT timestamp, code, name, price, change_pct, volume, rank
                FROM snapshots ORDER BY timestamp
            ''')
            rows = cursor.fetchall()
            
            # 按时间分组
            snapshots_by_time = defaultdict(list)
            for row in rows:
                timestamp, code, name, price, change_pct, volume, rank = row
                snapshots_by_time[timestamp].append({
                    'code': code,
                    'name': name,
                    'price': price,
                    'change_pct': change_pct,
                    'volume': volume,
                    'rank': rank
                })
            
            # 构建快照列表
            for timestamp, stocks in snapshots_by_time.items():
                all_snapshots.append({
                    'time': timestamp,
                    'stocks': stocks
                })
    except Exception as e:
        print(f"Database error: {e}")
        # 回退到JSON文件
        history_dir = OUTPUT_DIR / "history_data"
        if history_dir.exists():
            for filepath in history_dir.glob("history_*.json"):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    for snap in data.get("snapshots", []):
                        all_snapshots.append(snap)
                except Exception as e2:
                    print(f"Skip {filepath}: {e2}")
    
    all_snapshots.sort(key=lambda x: x.get("time", ""))
    print(f"Loaded {len(all_snapshots)} snapshots")
    return all_snapshots


def build_price_map(snapshots):
    """
    构建 {code: [(time, price), ...]} 映射
    用于查找未来价格
    """
    price_map = defaultdict(list)
    
    for snap in snapshots:
        t = snap.get("time", "")
        for stock in snap.get("stocks", []):
            code = stock.get("code", "")
            price = stock.get("price")
            if code and price:
                try:
                    price_map[code].append((t, float(price)))
                except (ValueError, TypeError):
                    pass
    
    # 每个股票按时间排序
    for code in price_map:
        price_map[code].sort(key=lambda x: x[0])
    
    return price_map


def get_future_price(price_map, code, current_time, hours_ahead=24):
    """获取 N 小时后的价格"""
    prices = price_map.get(code, [])
    if not prices:
        return None
    
    try:
        current_dt = datetime.strptime(current_time, "%Y-%m-%d %H:%M:%S")
        target_dt  = current_dt + timedelta(hours=hours_ahead)
        target_str = target_dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return None
    
    # 找第一个 >= target_time 的价格
    for t, p in prices:
        if t >= target_str:
            return p
    
    return None


def extract_features(stock: dict) -> dict:
    """从股票数据提取特征"""
    def safe_float(v, default=0.0):
        try:
            return float(v) if v is not None else default
        except (ValueError, TypeError):
            return default
    
    return {
        'rank':          safe_float(stock.get('rank'), 100),
        'change_pct':    safe_float(stock.get('change_pct'), 0),
        'turnover_rate': safe_float(stock.get('turnover_rate'), 0),
        'volume_ratio':  safe_float(stock.get('volume_ratio'), 1),
        'amplitude':     safe_float(stock.get('amplitude'), 0),
        'rsi':           safe_float(stock.get('rsi'), 50),       # 缺失填中性值
        'macd':          safe_float(stock.get('macd'), 0),
        'bb_position':   safe_float(stock.get('bb_position'), 0.5),
        'ma5_diff':      safe_float(stock.get('ma5_diff'), 0),
        'ma20_diff':     safe_float(stock.get('ma20_diff'), 0),
    }


def build_training_data():
    """构建训练数据集"""
    print("=" * 50)
    print("Building training dataset...")
    print("=" * 50)
    
    snapshots = load_all_snapshots()
    if not snapshots:
        print("No snapshots found. Run fetch_hot_stocks.py first.")
        return 0
    
    price_map = build_price_map(snapshots)
    
    rows = []
    skipped = 0
    
    for snap in snapshots:
        snap_time = snap.get("time", "")
        
        for stock in snap.get("stocks", []):
            code = stock.get("code", "")
            if not code:
                continue
            
            current_price = stock.get("price")
            if not current_price:
                continue
            
            try:
                current_price = float(current_price)
            except:
                continue
            
            # 获取未来价格（24小时后）
            future_price = get_future_price(price_map, code, snap_time, hours_ahead=24)
            
            if future_price is None:
                skipped += 1
                continue
            
            # 计算未来收益率
            future_return = (future_price - current_price) / current_price * 100
            
            # 分类标签：上涨=1，下跌=0
            target = 1 if future_return > 0 else 0
            
            # 提取特征
            features = extract_features(stock)
            
            row = {
                'time':         snap_time,
                'code':         code,
                'name':         stock.get('name', ''),
                'current_price':current_price,
                'future_price': future_price,
                'future_return':round(future_return, 4),
                'target':       target,
                **features
            }
            rows.append(row)
    
    print(f"Generated {len(rows)} samples ({skipped} skipped, no future price)")
    
    if not rows:
        print("No training data generated.")
        return 0
    
    # 保存 CSV
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / "training_data.csv"
    
    fieldnames = list(rows[0].keys())
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"Saved to: {output_file}")
    
    # 统计
    up_count   = sum(1 for r in rows if r['target'] == 1)
    down_count = len(rows) - up_count
    print(f"Label distribution: Up={up_count} ({up_count/len(rows)*100:.1f}%), Down={down_count} ({down_count/len(rows)*100:.1f}%)")
    
    return len(rows)


if __name__ == "__main__":
    count = build_training_data()
    if count > 0:
        print(f"\nDone! {count} training samples ready.")
        print("Next step: python train_model.py")
    else:
        print("\nNeed more data. Keep running the collector.")

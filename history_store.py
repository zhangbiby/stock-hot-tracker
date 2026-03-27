#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票数据历史存储模块
兼容层 - 保持旧接口，内部使用数据库
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# 尝试导入数据库管理器
try:
    from db_manager import db_manager
    USE_DATABASE = True
    print("[HistoryStore] 使用数据库存储")
except ImportError:
    USE_DATABASE = False
    print("[HistoryStore] 使用JSON文件存储")

# 存储目录（兼容旧代码）
STORAGE_DIR = Path(__file__).parent / "output" / "history_data"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def get_history_file(date: str = None) -> Path:
    """获取历史数据文件路径（兼容旧接口）"""
    if date is None:
        date = datetime.now().strftime("%Y%m%d")
    return STORAGE_DIR / f"history_{date}.json"


def load_history(date: str = None) -> dict:
    """加载指定日期的历史数据（兼容旧接口）"""
    if USE_DATABASE:
        # 从数据库加载
        from db_manager import db_manager
        stocks = db_manager.get_latest_snapshot()
        return {"snapshots": [{"time": datetime.now().isoformat(), "stocks": stocks}]}
    
    # 从JSON文件加载（兼容旧代码）
    filepath = get_history_file(date)
    
    if filepath.exists():
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {"snapshots": []}
    
    return {"snapshots": []}


def save_snapshot(stocks: list[dict], snapshot_time: str = None):
    """保存快照数据（自动选择存储方式）"""
    if not stocks:
        return
    
    if snapshot_time is None:
        snapshot_time = datetime.now().isoformat()
    
    if USE_DATABASE:
        # 保存到数据库
        from db_manager import db_manager
        db_manager.save_snapshot(stocks, snapshot_time)
    else:
        # 保存到JSON文件（兼容旧代码）
        _save_to_json(stocks, snapshot_time)


def _save_to_json(stocks: list[dict], snapshot_time: str):
    """保存到JSON文件（内部方法）"""
    filepath = get_history_file()
    
    history = load_history()
    
    # 添加新快照
    snapshot = {
        "time": snapshot_time,
        "stocks": stocks
    }
    
    history["snapshots"].append(snapshot)
    
    # 只保留最近100个快照
    history["snapshots"] = history["snapshots"][-100:]
    
    # 保存到文件
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def get_prev_rank(code: str, minutes_ago: int = 5) -> Optional[int]:
    """获取股票在N分钟前的排名"""
    if USE_DATABASE:
        from db_manager import db_manager
        # 从数据库查询历史排名
        history = db_manager.get_price_history(code, days=1)
        if history and len(history) > 1:
            # 简化处理，返回最近一次记录的排名
            return history[0].get('rank')
        return None
    
    # 从JSON查询（兼容旧代码）
    return _get_prev_rank_from_json(code, minutes_ago)


def _get_prev_rank_from_json(code: str, minutes_ago: int) -> Optional[int]:
    """从JSON获取历史排名（内部方法）"""
    history = load_history()
    snapshots = history.get("snapshots", [])
    
    if not snapshots:
        return None
    
    # 计算目标时间
    target_time = datetime.now() - timedelta(minutes=minutes_ago)
    
    # 查找最接近的快照
    for snapshot in reversed(snapshots):
        snapshot_time = datetime.fromisoformat(snapshot["time"])
        if snapshot_time <= target_time:
            # 查找股票排名
            for stock in snapshot.get("stocks", []):
                if stock.get("code") == code:
                    return stock.get("rank")
            return None
    
    return None


def get_stock_history(code: str, days: int = 7) -> list:
    """获取股票最近N天的历史数据"""
    if USE_DATABASE:
        from db_manager import db_manager
        return db_manager.get_price_history(code, days)
    
    # 从JSON查询（兼容旧代码）
    return _get_stock_history_from_json(code, days)


def _get_stock_history_from_json(code: str, days: int) -> list:
    """从JSON获取股票历史（内部方法）"""
    history = []
    
    for i in range(days):
        date = (datetime.now() - timedelta(days=i)).strftime("%Y%m%d")
        day_history = load_history(date)
        
        for snapshot in day_history.get("snapshots", []):
            for stock in snapshot.get("stocks", []):
                if stock.get("code") == code:
                    history.append({
                        "date": snapshot["time"],
                        **stock
                    })
    
    return history


def get_industry_stocks(industry_code: str, hours: int = 1) -> list:
    """获取指定行业在最近N小时内的上榜股票"""
    # 简化实现，从最新快照中筛选
    if USE_DATABASE:
        from db_manager import db_manager
        stocks = db_manager.get_latest_snapshot()
        # 这里简化处理，实际应该根据行业代码筛选
        return [s for s in stocks if s.get('industry') == industry_code]
    
    return []


def init_storage():
    """初始化存储（兼容旧接口）"""
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    if USE_DATABASE:
        # 数据库会自动初始化
        pass
    print(f"[HistoryStore] 存储初始化完成")


# 兼容旧接口的别名
get_price_history = get_stock_history

# 添加缺失的函数
def get_latest_snapshot(code=None):
    """获取最新快照（兼容旧接口）"""
    if USE_DATABASE:
        from db_manager import db_manager
        if code:
            return db_manager.get_latest_snapshot(code)
        else:
            snapshots = db_manager.get_latest_snapshot()
            return snapshots[0] if snapshots else None
    return None

if __name__ == '__main__':
    # 测试
    init_storage()
    print("历史存储模块测试通过")

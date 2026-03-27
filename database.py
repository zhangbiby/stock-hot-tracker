#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票人气榜数据库模块
SQLite 数据库存储历史数据，支持趋势分析
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional
import threading

# 数据库路径
DB_PATH = Path(__file__).parent / "output" / "stock_data.db"

# 线程锁
_lock = threading.Lock()


def get_connection() -> sqlite3.Connection:
    """获取数据库连接"""
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """初始化数据库表结构"""
    with _lock:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 1. 热门股快照表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS hot_stocks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_time TIMESTAMP NOT NULL,
                rank INTEGER NOT NULL,
                prev_rank INTEGER,
                code TEXT NOT NULL,
                name TEXT,
                price REAL,
                change_pct REAL,
                change_amount REAL,
                volume INTEGER,
                amount REAL,
                turnover_rate REAL,
                volume_ratio REAL,
                amplitude REAL,
                pe_ratio REAL,
                market_cap REAL,
                industry TEXT,
                board TEXT,
                source TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 2. 信号表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_time TIMESTAMP NOT NULL,
                code TEXT NOT NULL,
                name TEXT,
                signal TEXT NOT NULL,
                strength INTEGER,
                score INTEGER,
                factors JSON,
                reasons JSON,
                risks JSON,
                price REAL,
                change_pct REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 3. 信号复盘表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS signal_review (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_id INTEGER NOT NULL,
                code TEXT NOT NULL,
                signal_time TIMESTAMP NOT NULL,
                signal_type TEXT NOT NULL,
                entry_price REAL,
                price_1d REAL,
                return_1d REAL,
                price_3d REAL,
                return_3d REAL,
                price_5d REAL,
                return_5d REAL,
                reviewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (signal_id) REFERENCES signals(id)
            )
        ''')
        
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_snapshot_time ON hot_stocks(snapshot_time)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_code ON hot_stocks(code)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_signal_time ON signals(signal_time)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_signal_code ON signals(code)')
        
        conn.commit()
        conn.close()
    
    print("✅ 数据库初始化完成")


def save_snapshot(stocks: list[dict], snapshot_time: str = None):
    """保存快照数据"""
    if not stocks:
        return
    
    if snapshot_time is None:
        snapshot_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with _lock:
        conn = get_connection()
        cursor = conn.cursor()
        
        for s in stocks:
            cursor.execute('''
                INSERT INTO hot_stocks (
                    snapshot_time, rank, code, name, price,
                    change_pct, change_amount, volume, amount,
                    turnover_rate, volume_ratio, amplitude,
                    pe_ratio, market_cap, industry, board, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                snapshot_time,
                s.get('rank'),
                s.get('code'),
                s.get('name'),
                s.get('price'),
                s.get('change_pct'),
                s.get('change_amount'),
                s.get('volume'),
                s.get('amount'),
                s.get('turnover_rate'),
                s.get('volume_ratio'),
                s.get('amplitude'),
                s.get('pe_ratio'),
                s.get('market_cap'),
                s.get('industry'),
                s.get('board'),
                s.get('source'),
            ))
        
        conn.commit()
        conn.close()


def get_prev_rank(code: str, minutes_ago: int = 5) -> Optional[int]:
    """获取N分钟前的排名"""
    from datetime import datetime, timedelta
    
    with _lock:
        conn = get_connection()
        cursor = conn.cursor()
        
        target_time = (datetime.now() - timedelta(minutes=minutes_ago)).strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute('''
            SELECT rank FROM hot_stocks
            WHERE code = ? AND snapshot_time >= ?
            ORDER BY snapshot_time ASC
            LIMIT 1
        ''', (code, target_time))
        
        row = cursor.fetchone()
        conn.close()
        
        return row['rank'] if row else None


def get_stock_history(code: str, hours: int = 24) -> list[dict]:
    """获取股票历史数据"""
    from datetime import datetime, timedelta
    
    with _lock:
        conn = get_connection()
        cursor = conn.cursor()
        
        start_time = (datetime.now() - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute('''
            SELECT * FROM hot_stocks
            WHERE code = ? AND snapshot_time >= ?
            ORDER BY snapshot_time ASC
        ''', (code, start_time))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]


def get_industry_stocks_count(industry: str, hours: int = 1) -> int:
    """获取同一行业上榜股票数量"""
    from datetime import datetime, timedelta
    
    if not industry:
        return 0
    
    with _lock:
        conn = get_connection()
        cursor = conn.cursor()
        
        start_time = (datetime.now() - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute('''
            SELECT COUNT(DISTINCT code) as cnt FROM hot_stocks
            WHERE industry = ? AND snapshot_time >= ?
        ''', (industry, start_time))
        
        row = cursor.fetchone()
        conn.close()
        
        return row['cnt'] if row else 0


def get_latest_snapshot() -> list[dict]:
    """获取最新的快照数据"""
    with _lock:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM hot_stocks
            WHERE snapshot_time = (
                SELECT MAX(snapshot_time) FROM hot_stocks
            )
            ORDER BY rank ASC
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]


def save_signal(signal: dict):
    """保存信号"""
    with _lock:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO signals (
                signal_time, code, name, signal, strength, score,
                factors, reasons, risks, price, change_pct
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            signal.get('signal_time'),
            signal.get('code'),
            signal.get('name'),
            signal.get('signal'),
            signal.get('strength'),
            signal.get('score'),
            json.dumps(signal.get('factors', {}), ensure_ascii=False),
            json.dumps(signal.get('reasons', []), ensure_ascii=False),
            json.dumps(signal.get('risks', []), ensure_ascii=False),
            signal.get('price'),
            signal.get('change_pct'),
        ))
        
        conn.commit()
        conn.close()


def get_latest_signals() -> list[dict]:
    """获取最新信号"""
    with _lock:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM signals
            WHERE signal_time = (
                SELECT MAX(signal_time) FROM signals
            )
            ORDER BY strength DESC
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        result = []
        for row in rows:
            s = dict(row)
            s['factors'] = json.loads(s['factors']) if s['factors'] else {}
            s['reasons'] = json.loads(s['reasons']) if s['reasons'] else []
            s['risks'] = json.loads(s['risks']) if s['risks'] else []
            result.append(s)
        
        return result


def get_signal_history(code: str, days: int = 30) -> list[dict]:
    """获取股票历史信号"""
    from datetime import datetime, timedelta
    
    with _lock:
        conn = get_connection()
        cursor = conn.cursor()
        
        start_time = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute('''
            SELECT * FROM signals
            WHERE code = ? AND signal_time >= ?
            ORDER BY signal_time DESC
        ''', (code, start_time))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]


if __name__ == "__main__":
    init_database()
    print("数据库路径:", DB_PATH)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库管理模块 - 统一数据存储
替代原有的JSON文件存储
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from contextlib import contextmanager

BASE_DIR = Path(__file__).parent
DB_FILE = BASE_DIR / "output" / "stock_tracker.db"

class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, db_path: str = None):
        self.db_path = str(db_path or DB_FILE)
        self._init_db()
    
    @contextmanager
    def _get_connection(self):
        """获取数据库连接上下文"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def _init_db(self):
        """初始化数据库表结构"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 历史快照表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    code TEXT NOT NULL,
                    name TEXT,
                    price REAL,
                    change_pct REAL,
                    volume INTEGER,
                    turnover_rate REAL,
                    rank INTEGER,
                    pe_ratio REAL,
                    pb_ratio REAL,
                    rsi REAL,
                    macd REAL,
                    bb_position REAL,
                    data TEXT
                )
            ''')
            
            # 信号记录表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    code TEXT NOT NULL,
                    name TEXT,
                    signal TEXT,
                    score INTEGER,
                    strength INTEGER,
                    up_proba REAL,
                    reasons TEXT,
                    agent_details TEXT,
                    multi_agent BOOLEAN DEFAULT 0
                )
            ''')
            
            # 持仓表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS holdings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT NOT NULL UNIQUE,
                    name TEXT,
                    buy_price REAL,
                    quantity INTEGER,
                    buy_date TEXT,
                    can_sell BOOLEAN DEFAULT 0,
                    created_at TEXT,
                    updated_at TEXT
                )
            ''')
            
            # 交易记录表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    code TEXT NOT NULL,
                    name TEXT,
                    action TEXT,
                    price REAL,
                    quantity INTEGER,
                    amount REAL,
                    fee REAL,
                    profit REAL,
                    profit_pct REAL
                )
            ''')
            
            # 60分钟K线表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS hourly_kline (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT NOT NULL,
                    datetime TEXT NOT NULL,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume INTEGER,
                    UNIQUE(code, datetime)
                )
            ''')
            
            # 回测记录表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS backtests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    strategy_name TEXT,
                    start_date TEXT,
                    end_date TEXT,
                    initial_capital REAL,
                    final_capital REAL,
                    total_return REAL,
                    win_rate REAL,
                    profit_factor REAL,
                    max_drawdown REAL,
                    sharpe_ratio REAL,
                    trades_count INTEGER,
                    report_path TEXT
                )
            ''')
            
            # 创建索引
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_snapshots_code ON snapshots(code)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_snapshots_time ON snapshots(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_signals_code ON signals(code)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_signals_time ON signals(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_hourly_kline_code ON hourly_kline(code)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_hourly_kline_datetime ON hourly_kline(datetime)')
            
            conn.commit()
            print(f"[Database] 数据库初始化完成: {self.db_path}")
    
    # ========== 快照相关操作 ==========
    
    def save_snapshot(self, stocks: List[Dict], timestamp: str = None):
        """保存股票快照"""
        if not timestamp:
            timestamp = datetime.now().isoformat()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for stock in stocks:
                cursor.execute('''
                    INSERT INTO snapshots 
                    (timestamp, code, name, price, change_pct, volume, turnover_rate, 
                     rank, pe_ratio, pb_ratio, rsi, macd, bb_position, data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    timestamp,
                    stock.get('code'),
                    stock.get('name'),
                    stock.get('price'),
                    stock.get('change_pct'),
                    stock.get('volume'),
                    stock.get('turnover_rate'),
                    stock.get('rank'),
                    stock.get('pe_ratio'),
                    stock.get('pb_ratio'),
                    stock.get('rsi'),
                    stock.get('macd'),
                    stock.get('bb_position'),
                    json.dumps(stock, ensure_ascii=False)
                ))
            conn.commit()
            print(f"[Database] 保存 {len(stocks)} 条快照记录")
    
    def get_latest_snapshot(self, code: str = None) -> List[Dict]:
        """获取最新快照"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            if code:
                cursor.execute('''
                    SELECT * FROM snapshots 
                    WHERE code = ? 
                    ORDER BY timestamp DESC LIMIT 1
                ''', (code,))
                row = cursor.fetchone()
                return dict(row) if row else None
            else:
                # 获取每个股票的最新记录
                cursor.execute('''
                    SELECT s.* FROM snapshots s
                    INNER JOIN (
                        SELECT code, MAX(timestamp) as max_time 
                        FROM snapshots 
                        GROUP BY code
                    ) m ON s.code = m.code AND s.timestamp = m.max_time
                ''')
                return [dict(row) for row in cursor.fetchall()]
    
    def get_price_history(self, code: str, days: int = 30) -> List[Dict]:
        """获取价格历史"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT timestamp, price, change_pct, volume 
                FROM snapshots 
                WHERE code = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (code, days))
            return [dict(row) for row in cursor.fetchall()]
    
    # ========== 信号相关操作 ==========
    
    def save_signal(self, signal: Dict, timestamp: str = None):
        """保存信号"""
        if not timestamp:
            timestamp = datetime.now().isoformat()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO signals 
                (timestamp, code, name, signal, score, strength, up_proba, 
                 reasons, agent_details, multi_agent)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                timestamp,
                signal.get('code'),
                signal.get('name'),
                signal.get('signal'),
                signal.get('score'),
                signal.get('strength'),
                signal.get('up_proba'),
                json.dumps(signal.get('reasons', []), ensure_ascii=False),
                json.dumps(signal.get('agent_details', {}), ensure_ascii=False),
                signal.get('multi_agent', False)
            ))
            conn.commit()
    
    def get_signals(self, code: str = None, limit: int = 100) -> List[Dict]:
        """获取信号记录"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            if code:
                cursor.execute('''
                    SELECT * FROM signals 
                    WHERE code = ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (code, limit))
            else:
                cursor.execute('''
                    SELECT * FROM signals 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (limit,))
            
            results = []
            for row in cursor.fetchall():
                data = dict(row)
                data['reasons'] = json.loads(data['reasons']) if data['reasons'] else []
                data['agent_details'] = json.loads(data['agent_details']) if data['agent_details'] else {}
                results.append(data)
            return results
    
    # ========== 持仓相关操作 ==========
    
    def add_holding(self, code: str, name: str, buy_price: float, 
                    quantity: int, buy_date: str, can_sell: bool = False):
        """添加持仓"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            cursor.execute('''
                INSERT OR REPLACE INTO holdings 
                (code, name, buy_price, quantity, buy_date, can_sell, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (code, name, buy_price, quantity, buy_date, can_sell, now, now))
            conn.commit()
    
    def get_holdings(self) -> List[Dict]:
        """获取所有持仓"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM holdings ORDER BY created_at DESC')
            return [dict(row) for row in cursor.fetchall()]
    
    def update_holding(self, code: str, **kwargs):
        """更新持仓"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 构建更新语句
            fields = []
            values = []
            for key, value in kwargs.items():
                fields.append(f"{key} = ?")
                values.append(value)
            
            fields.append("updated_at = ?")
            values.append(datetime.now().isoformat())
            values.append(code)
            
            sql = f"UPDATE holdings SET {', '.join(fields)} WHERE code = ?"
            cursor.execute(sql, values)
            conn.commit()
    
    def delete_holding(self, code: str):
        """删除持仓"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM holdings WHERE code = ?', (code,))
            conn.commit()
    
    # ========== 交易记录操作 ==========
    
    def record_trade(self, code: str, name: str, action: str, 
                     price: float, quantity: int, fee: float = 0,
                     profit: float = None, profit_pct: float = None):
        """记录交易"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            amount = price * quantity
            timestamp = datetime.now().isoformat()
            
            cursor.execute('''
                INSERT INTO trades 
                (timestamp, code, name, action, price, quantity, amount, fee, profit, profit_pct)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (timestamp, code, name, action, price, quantity, amount, fee, profit, profit_pct))
            conn.commit()
    
    def get_trades(self, code: str = None, limit: int = 100) -> List[Dict]:
        """获取交易记录"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            if code:
                cursor.execute('''
                    SELECT * FROM trades 
                    WHERE code = ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (code, limit))
            else:
                cursor.execute('''
                    SELECT * FROM trades 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    # ========== 60分钟K线操作 ==========
    
    def save_hourly_kline(self, code: str, datetime_str: str, 
                          open_price: float, high: float, low: float, 
                          close: float, volume: int):
        """保存60分钟K线"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO hourly_kline 
                (code, datetime, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (code, datetime_str, open_price, high, low, close, volume))
            conn.commit()
    
    def get_hourly_kline(self, code: str, limit: int = 100) -> List[Dict]:
        """获取60分钟K线"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM hourly_kline 
                WHERE code = ? 
                ORDER BY datetime DESC 
                LIMIT ?
            ''', (code, limit))
            return [dict(row) for row in cursor.fetchall()]
    
    # ========== 回测记录操作 ==========
    
    def save_backtest_result(self, result: Dict):
        """保存回测结果"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO backtests 
                (timestamp, strategy_name, start_date, end_date, initial_capital,
                 final_capital, total_return, win_rate, profit_factor, max_drawdown,
                 sharpe_ratio, trades_count, report_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(),
                result.get('strategy_name'),
                result.get('start_date'),
                result.get('end_date'),
                result.get('initial_capital'),
                result.get('final_capital'),
                result.get('total_return'),
                result.get('win_rate'),
                result.get('profit_factor'),
                result.get('max_drawdown'),
                result.get('sharpe_ratio'),
                result.get('trades_count'),
                result.get('report_path')
            ))
            conn.commit()

# 全局实例
db_manager = DatabaseManager()

# 兼容旧接口的函数
def save_snapshot(stocks, timestamp=None):
    """兼容旧接口"""
    return db_manager.save_snapshot(stocks, timestamp)

def get_latest_snapshot(code=None):
    """兼容旧接口"""
    return db_manager.get_latest_snapshot(code)

def get_price_history(code, days=30):
    """兼容旧接口"""
    return db_manager.get_price_history(code, days)

if __name__ == '__main__':
    # 测试
    db = DatabaseManager()
    print("数据库管理器测试通过")

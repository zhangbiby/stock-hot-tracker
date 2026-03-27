#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P0 优化实施脚本
快速修复关键问题
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent
DB_FILE = BASE_DIR / "output" / "stock_tracker.db"

def init_database():
    """初始化数据库"""
    print("初始化数据库...")
    
    conn = sqlite3.connect(DB_FILE)
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
            data TEXT  -- JSON格式存储完整数据
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
            reasons TEXT,  -- JSON数组
            agent_details TEXT,  -- JSON对象
            multi_agent BOOLEAN
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
            can_sell BOOLEAN,
            created_at TEXT
        )
    ''')
    
    # 交易记录表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            code TEXT NOT NULL,
            name TEXT,
            action TEXT,  -- buy/sell
            price REAL,
            quantity INTEGER,
            profit REAL,
            profit_pct REAL
        )
    ''')
    
    # 创建索引
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_snapshots_code ON snapshots(code)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_snapshots_time ON snapshots(timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_signals_code ON signals(code)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_signals_time ON signals(timestamp)')
    
    conn.commit()
    conn.close()
    print(f"数据库初始化完成: {DB_FILE}")

def migrate_json_to_db():
    """迁移现有JSON数据到数据库"""
    print("\n迁移现有数据...")
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 迁移持仓数据
    holdings_file = BASE_DIR / "output" / "holdings.json"
    if holdings_file.exists():
        with open(holdings_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            holdings = data.get('holdings', [])
        
        for h in holdings:
            cursor.execute('''
                INSERT OR REPLACE INTO holdings 
                (code, name, buy_price, quantity, buy_date, can_sell, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                h.get('code'),
                h.get('name'),
                h.get('buy_price'),
                h.get('quantity'),
                h.get('buy_date'),
                h.get('can_sell', False),
                datetime.now().isoformat()
            ))
        print(f"  迁移 {len(holdings)} 条持仓记录")
    
    conn.commit()
    conn.close()

def create_collector_service():
    """创建采集服务脚本"""
    print("\n创建采集服务脚本...")
    
    service_code = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据采集服务 - 常驻进程"""
import time
import sys
from datetime import datetime

sys.path.insert(0, '.')

def is_trading_time():
    """判断是否在交易时间"""
    now = datetime.now()
    h, m = now.hour, now.minute
    weekday = now.weekday()
    
    # 周末不交易
    if weekday >= 5:
        return False
    
    # 交易时间 9:30-11:30, 13:00-15:00
    if h == 9 and m >= 30:
        return True
    if h == 10 or h == 11:
        return True
    if h == 13 or h == 14:
        return True
    if h == 11 and m <= 30:
        return True
    
    return False

def run_collector():
    """运行采集"""
    try:
        from quick_fetch import fetch_all, generate_signals, generate_page
        
        print(f"[{datetime.now()}] 开始采集...")
        stocks = fetch_all()
        if stocks:
            generate_signals()
            generate_page()
            print(f"[{datetime.now()}] 采集完成: {len(stocks)}只股票")
            return True
    except Exception as e:
        print(f"[{datetime.now()}] 采集失败: {e}")
        return False

def main():
    print("=" * 50)
    print("数据采集服务启动")
    print("=" * 50)
    
    while True:
        # 执行采集
        success = run_collector()
        
        # 计算下次采集时间
        if is_trading_time():
            interval = 3 * 60  # 3分钟
            print(f"下次采集: 3分钟后 (交易时间)")
        else:
            interval = 30 * 60  # 30分钟
            print(f"下次采集: 30分钟后 (非交易时间)")
        
        time.sleep(interval)

if __name__ == '__main__':
    main()
'''
    
    service_file = BASE_DIR / "collector_service.py"
    with open(service_file, 'w', encoding='utf-8') as f:
        f.write(service_code)
    
    print(f"  创建: {service_file}")

def create_backtest_stub():
    """创建回测模块框架"""
    print("\n创建回测模块框架...")
    
    backtest_code = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
回测引擎 - 框架
"""
import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).parent
DB_FILE = BASE_DIR / "output" / "stock_tracker.db"

class BacktestEngine:
    """回测引擎"""
    
    def __init__(self, initial_capital=100000):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.positions = {}  # 持仓
        self.trades = []     # 交易记录
        
    def run(self, start_date, end_date, strategy_config):
        """
        运行回测
        
        Args:
            start_date: '2026-03-01'
            end_date: '2026-03-27'
            strategy_config: {
                'signal_threshold': 50,  # 信号阈值
                'stop_loss': 0.03,       # 止损3%
                'take_profit': 0.05,     # 止盈5%
                'max_holding_days': 3    # 最大持仓3天
            }
        """
        print(f"回测区间: {start_date} ~ {end_date}")
        print(f"初始资金: {self.initial_capital}")
        
        # TODO: 实现回测逻辑
        # 1. 遍历历史信号
        # 2. 按策略买入卖出
        # 3. 计算收益
        
        return {
            'total_return': 0,
            'win_rate': 0,
            'profit_factor': 0,
            'max_drawdown': 0,
            'trades': []
        }
    
    def generate_report(self, results):
        """生成回测报告"""
        # TODO: 生成HTML报告
        pass

if __name__ == '__main__':
    engine = BacktestEngine(initial_capital=100000)
    results = engine.run('2026-03-01', '2026-03-27', {
        'signal_threshold': 50,
        'stop_loss': 0.03,
        'take_profit': 0.05
    })
    print(results)
'''
    
    backtest_file = BASE_DIR / "backtest.py"
    with open(backtest_file, 'w', encoding='utf-8') as f:
        f.write(backtest_code)
    
    print(f"  创建: {backtest_file}")

def main():
    print("=" * 60)
    print("P0 优化实施")
    print("=" * 60)
    
    # 1. 初始化数据库
    init_database()
    
    # 2. 迁移数据
    migrate_json_to_db()
    
    # 3. 创建采集服务
    create_collector_service()
    
    # 4. 创建回测框架
    create_backtest_stub()
    
    print("\n" + "=" * 60)
    print("P0 基础优化完成!")
    print("=" * 60)
    print("\n下一步:")
    print("1. 运行采集服务: python collector_service.py")
    print("2. 启动Web服务器: python server.py")
    print("3. 访问 http://localhost:8080")

if __name__ == '__main__':
    main()

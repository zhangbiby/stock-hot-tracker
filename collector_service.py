#!/usr/bin/env python3
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

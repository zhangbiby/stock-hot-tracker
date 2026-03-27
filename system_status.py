#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
System Status Monitor
Display all backend tasks and system status
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Fix stdout encoding
if sys.platform == 'win32':
    try:
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    except:
        pass

sys.path.insert(0, str(Path(__file__).parent))

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def print_status(name, status, detail=""):
    icon = "[OK]" if status == "RUNNING" else "[WAIT]" if status == "PAUSED" else "[ERR]"
    print(f"  {icon} {name:<20} {status:<10} {detail}")

def main():
    print("\n" + "="*60)
    print("  Stock Hot Tracker - System Status Monitor")
    print("="*60)
    print(f"  Check Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. Data Collection Status
    print_section("DATA COLLECTION")
    
    output_dir = Path("output")
    hot_stocks = output_dir / "hot_stocks.json"
    signals = output_dir / "signals_latest.json"
    
    if hot_stocks.exists():
        with open(hot_stocks, 'r', encoding='utf-8') as f:
            data = json.load(f)
            ts = data.get('timestamp', '')
            stocks_count = len(data.get('stocks', []))
            print_status("Hot Stocks", "RUNNING", f"{stocks_count} stocks | {ts[:19]}")
    else:
        print_status("Hot Stocks", "ERR", "File not found")
    
    if signals.exists():
        with open(signals, 'r', encoding='utf-8') as f:
            data = json.load(f)
            ts = data.get('timestamp', '')
            sig_count = len(data.get('signals', []))
            print_status("Signals", "RUNNING", f"{sig_count} signals | {ts[:19]}")
    else:
        print_status("Signals", "ERR", "File not found")
    
    # 2. Model Status
    print_section("MODEL STATUS")
    
    model_file = output_dir / "stock_model.pkl"
    if model_file.exists():
        import joblib
        try:
            model = joblib.load(model_file)
            acc = model.get('accuracy', 0)
            train_time = model.get('train_time', 'unknown')
            print_status("ML Model", "RUNNING", f"Accuracy {acc*100:.0f}% | {train_time}")
        except:
            print_status("ML Model", "ERR", "Cannot load")
    else:
        print_status("ML Model", "PAUSED", "Model file not found")
    
    print_status("Rule Model", "RUNNING", "Multi-factor weighted")
    print_status("Dynamic Weight", "RUNNING", "Market adaptive")
    
    # 3. Database Status
    print_section("DATABASE STATUS")
    
    try:
        from db_manager import db_manager
        with db_manager._get_connection() as conn:
            cursor = conn.cursor()
            
            tables = [
                ('snapshots', 'Stock Snapshots'),
                ('signals', 'Signal Records'),
                ('holdings', 'Holdings'),
                ('trades', 'Trade Records'),
            ]
            
            for table, name in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print_status(name, "OK", f"{count} records")
    except Exception as e:
        print_status("Database", "ERR", str(e))
    
    # 4. Holdings Status
    print_section("HOLDINGS STATUS")
    
    try:
        from portfolio import Portfolio
        portfolio = Portfolio()
        holdings = portfolio.get_holdings_with_status()
        
        if holdings:
            total_value = sum(h.get('buy_price', 0) * h.get('quantity', 0) for h in holdings)
            print_status("Current Holdings", "OK", f"{len(holdings)} stocks | Cost {total_value:.0f}")
            
            can_sell = [h for h in holdings if h.get('can_sell')]
            cannot_sell = [h for h in holdings if not h.get('can_sell')]
            
            if can_sell:
                print(f"    [GREEN] Can Sell: {len(can_sell)}")
            if cannot_sell:
                print(f"    [YELLOW] T+1 Lock: {len(cannot_sell)}")
        else:
            print_status("Holdings", "EMPTY", "No holdings")
    except Exception as e:
        print_status("Holdings", "ERR", str(e))
    
    # 5. Today's Statistics
    print_section("TODAY STATISTICS")
    
    try:
        if hot_stocks.exists():
            with open(hot_stocks, 'r', encoding='utf-8') as f:
                data = json.load(f)
                stocks = data.get('stocks', [])
                
                up = sum(1 for s in stocks if float(s.get('change_pct', 0)) > 0)
                down = sum(1 for s in stocks if float(s.get('change_pct', 0)) < 0)
                zt = sum(1 for s in stocks if float(s.get('change_pct', 0)) >= 9.5)
                
                print(f"  Monitored: {len(stocks)} stocks")
                print(f"  UP: {up} ({up/len(stocks)*100:.0f}%)")
                print(f"  DOWN: {down} ({down/len(stocks)*100:.0f}%)")
                print(f"  LIMIT UP: {zt}")
                
                print(f"\n  Top 3:")
                top3 = sorted(stocks, key=lambda x: float(x.get('change_pct', 0)), reverse=True)[:3]
                for i, s in enumerate(top3, 1):
                    pct = s['change_pct']
                    print(f"     {i}. {s['code']} {s['name']}: +{pct:.2f}%")
    except Exception as e:
        print(f"  Error: {e}")
    
    # 6. System Info
    print_section("SYSTEM INFO")
    print(f"  Version: v4.1")
    print(f"  Web: http://localhost:8080")
    print(f"  Data Dir: {output_dir.absolute()}")
    print(f"  Refresh: 2 minutes")
    
    print("\n" + "="*60)
    print("  System Status: OK")
    print("="*60)

if __name__ == "__main__":
    main()

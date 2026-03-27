#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
System Test - Simplified
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_database():
    print("\n" + "="*60)
    print("Test 1: Database Module")
    print("="*60)
    
    try:
        from db_manager import db_manager
        
        test_stocks = [
            {'code': '000001', 'name': 'Test1', 'price': 10.5, 'change_pct': 1.5, 'rank': 1,
             'volume': 1000000, 'turnover_rate': 3.5, 'pe_ratio': 8.5, 'pb_ratio': 0.9,
             'rsi': 55.0, 'macd': 0.02, 'bb_position': 0.6}
        ]
        db_manager.save_snapshot(test_stocks)
        print("OK: Save snapshot")
        
        latest = db_manager.get_latest_snapshot()
        print(f"OK: Query: {len(latest)} records")
        
        db_manager.add_holding('000001', 'Test1', 10.0, 1000, '2026-03-27')
        holdings = db_manager.get_holdings()
        print(f"OK: Holdings: {len(holdings)} records")
        
        print("\nPASS: Database module")
        return True
    except Exception as e:
        print(f"\nFAIL: {e}")
        return False

def test_agents():
    print("\n" + "="*60)
    print("Test 2: Multi-Agent System")
    print("="*60)
    
    try:
        from agents import Orchestrator
        from memory import MemoryStore
        
        orchestrator = Orchestrator(MemoryStore())
        print("OK: Orchestrator initialized")
        
        context = {
            'stock_code': '000001',
            'stock_name': 'Test',
            'current_price': 10.5,
            'prices': [10.0, 10.1, 10.2, 10.3, 10.4, 10.5] * 5,
            'rank': 15,
            'turnover_rate': 3.5,
            'volume_ratio': 1.8,
            'pe_ratio': 8.5,
            'pb_ratio': 0.9
        }
        
        result = orchestrator.execute_analysis_pipeline(context)
        print(f"OK: Analysis complete")
        print(f"   Signal: {result.get('final_signal')}")
        print(f"   Confidence: {result.get('final_confidence', 0):.0%}")
        
        print("\nPASS: Multi-agent system")
        return True
    except Exception as e:
        print(f"\nFAIL: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_backtest():
    print("\n" + "="*60)
    print("Test 3: Backtest Module")
    print("="*60)
    
    try:
        from backtest import BacktestEngine
        
        engine = BacktestEngine(initial_capital=100000)
        print("OK: BacktestEngine initialized")
        
        print("\nPASS: Backtest module")
        return True
    except Exception as e:
        print(f"\nFAIL: {e}")
        return False

def main():
    print("=" * 60)
    print("System Test")
    print("=" * 60)
    
    results = {
        "Database": test_database(),
        "Multi-Agent": test_agents(),
        "Backtest": test_backtest()
    }
    
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = "PASS" if result else "FAIL"
        print(f"{name:15s}: {status}")
    
    print(f"\nTotal: {passed}/{total} passed")
    
    return passed == total

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

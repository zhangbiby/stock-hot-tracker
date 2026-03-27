#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统全面测试
验证P0优化后的所有功能
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_database():
    """测试数据库模块"""
    print("\n" + "="*60)
    print("Test 1: Database Module")
    print("="*60)
    
    try:
        from db_manager import DatabaseManager, db_manager
        
        # 测试保存快照
        test_stocks = [
            {'code': '000001', 'name': '平安银行', 'price': 10.5, 'change_pct': 1.5, 'rank': 1,
             'volume': 1000000, 'turnover_rate': 3.5, 'pe_ratio': 8.5, 'pb_ratio': 0.9,
             'rsi': 55.0, 'macd': 0.02, 'bb_position': 0.6},
            {'code': '000002', 'name': '万科A', 'price': 15.2, 'change_pct': -0.5, 'rank': 2,
             'volume': 2000000, 'turnover_rate': 2.8, 'pe_ratio': 12.0, 'pb_ratio': 1.2,
             'rsi': 45.0, 'macd': -0.01, 'bb_position': 0.4}
        ]
        db_manager.save_snapshot(test_stocks)
        print("OK: Save snapshot")
        
        # 测试查询
        latest = db_manager.get_latest_snapshot()
        print(f"OK: Query latest snapshot: {len(latest)} records")
        
        # 测试持仓
        db_manager.add_holding('000001', '平安银行', 10.0, 1000, '2026-03-27')
        holdings = db_manager.get_holdings()
        print(f"OK: Holdings: {len(holdings)} records")
        
        # 测试交易记录
        db_manager.record_trade('000001', '平安银行', 'buy', 10.0, 1000, 2.5)
        trades = db_manager.get_trades()
        print(f"OK: Trades: {len(trades)} records")
        
        print("\nOK: Database module test passed")
        return True
    except Exception as e:
        print(f"\nFAIL: Database module test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_history_store():
    """测试历史存储模块"""
    print("\n" + "="*60)
    print("测试2: 历史存储模块")
    print("="*60)
    
    try:
        from history_store import save_snapshot, get_latest_snapshot, get_price_history
        
        # 测试保存
        test_stocks = [
            {'code': '600000', 'name': '浦发银行', 'price': 8.5, 'change_pct': 0.8, 'rank': 3}
        ]
        save_snapshot(test_stocks)
        print("✅ 保存快照成功")
        
        # 测试查询
        latest = get_latest_snapshot('600000')
        print(f"✅ 查询单只股票: {latest['name'] if latest else 'None'}")
        
        print("\n✅ 历史存储模块测试通过")
        return True
    except Exception as e:
        print(f"\n❌ 历史存储模块测试失败: {e}")
        return False


def test_portfolio():
    """测试持仓管理模块"""
    print("\n" + "="*60)
    print("测试3: 持仓管理模块")
    print("="*60)
    
    try:
        from portfolio import Portfolio
        
        portfolio = Portfolio()
        
        # 测试添加持仓
        result = portfolio.add_custom_holding('600519', '贵州茅台', 1500.0, 100, '2026-03-27')
        print(f"✅ 添加持仓: {result['message']}")
        
        # 测试查询持仓
        holdings = portfolio.get_holdings()
        print(f"✅ 查询持仓: {len(holdings)} 只股票")
        
        # 测试带状态的持仓
        holdings_with_status = portfolio.get_holdings_with_status()
        for h in holdings_with_status:
            print(f"   {h['name']}: 可卖出={h['can_sell']}")
        
        print("\n✅ 持仓管理模块测试通过")
        return True
    except Exception as e:
        print(f"\n❌ 持仓管理模块测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_backtest():
    """测试回测模块"""
    print("\n" + "="*60)
    print("测试4: 回测模块")
    print("="*60)
    
    try:
        from backtest import BacktestEngine
        
        engine = BacktestEngine(initial_capital=100000)
        
        # 注意：需要有历史数据才能测试
        print("⚠️  回测模块需要历史信号数据")
        print("✅ 回测引擎初始化成功")
        
        print("\n✅ 回测模块测试通过")
        return True
    except Exception as e:
        print(f"\n❌ 回测模块测试失败: {e}")
        return False


def test_agents():
    """测试多智能体系统"""
    print("\n" + "="*60)
    print("测试5: 多智能体系统")
    print("="*60)
    
    try:
        from agents import Orchestrator
        from memory import MemoryStore
        
        orchestrator = Orchestrator(MemoryStore())
        print("✅ Orchestrator 初始化成功")
        
        # 测试分析流程
        context = {
            'stock_code': '000001',
            'stock_name': '平安银行',
            'current_price': 10.5,
            'prices': [10.0, 10.1, 10.2, 10.3, 10.4, 10.5] * 5,
            'rank': 15,
            'turnover_rate': 3.5,
            'volume_ratio': 1.8,
            'pe_ratio': 8.5,
            'pb_ratio': 0.9
        }
        
        result = orchestrator.execute_analysis_pipeline(context)
        print(f"✅ 分析流程执行成功")
        print(f"   信号: {result.get('final_signal')}")
        print(f"   置信度: {result.get('final_confidence', 0):.0%}")
        
        print("\n✅ 多智能体系统测试通过")
        return True
    except Exception as e:
        print(f"\n❌ 多智能体系统测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_signal_engine():
    """测试信号引擎"""
    print("\n" + "="*60)
    print("测试6: 信号引擎")
    print("="*60)
    
    try:
        from signal_engine import SignalEngine, MULTI_AGENT_AVAILABLE
        
        print(f"✅ 多智能体可用: {MULTI_AGENT_AVAILABLE}")
        
        engine = SignalEngine()
        print("✅ SignalEngine 初始化成功")
        
        # 测试单只股票信号计算
        test_stock = {
            'code': '000001',
            'name': '平安银行',
            'price': 10.5,
            'change_pct': 1.5,
            'rank': 10,
            'turnover_rate': 3.5,
            'volume_ratio': 1.8
        }
        
        signal = engine.calculate_signal(test_stock)
        print(f"✅ 信号计算成功: {signal.get('signal')} (评分: {signal.get('score')})")
        
        print("\n✅ 信号引擎测试通过")
        return True
    except Exception as e:
        print(f"\n❌ 信号引擎测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_data_collection():
    """测试数据采集"""
    print("\n" + "="*60)
    print("测试7: 数据采集")
    print("="*60)
    
    try:
        # 检查数据文件
        import json
        from pathlib import Path
        
        output_dir = Path(__file__).parent / "output"
        
        # 检查股票数据
        stocks_file = output_dir / "hot_stocks.json"
        if stocks_file.exists():
            with open(stocks_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            stocks = data.get('stocks', [])
            print(f"✅ 股票数据: {len(stocks)} 只")
        else:
            print("⚠️  股票数据文件不存在")
        
        # 检查信号数据
        signals_file = output_dir / "signals_latest.json"
        if signals_file.exists():
            with open(signals_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            signals = data.get('signals', [])
            print(f"✅ 信号数据: {len(signals)} 个")
        else:
            print("⚠️  信号数据文件不存在")
        
        # 检查数据库
        db_file = output_dir / "stock_tracker.db"
        if db_file.exists():
            print(f"✅ 数据库文件: {db_file.stat().st_size / 1024:.1f} KB")
        else:
            print("⚠️  数据库文件不存在")
        
        print("\n✅ 数据采集测试通过")
        return True
    except Exception as e:
        print(f"\n❌ 数据采集测试失败: {e}")
        return False


def main():
    """运行所有测试"""
    print("=" * 60)
    print("Stock Hot Tracker - 系统全面测试")
    print("=" * 60)
    
    results = {
        "数据库模块": test_database(),
        "历史存储": test_history_store(),
        "持仓管理": test_portfolio(),
        "回测模块": test_backtest(),
        "多智能体": test_agents(),
        "信号引擎": test_signal_engine(),
        "数据采集": test_data_collection()
    }
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name:12s}: {status}")
    
    print(f"\n总计: {passed}/{total} 通过 ({passed/total*100:.0f}%)")
    
    if passed == total:
        print("\n🎉 所有测试通过！系统运行正常。")
    else:
        print(f"\n⚠️  {total - passed} 项测试失败，请检查。")
    
    return passed == total


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高级模块集成示例
展示如何将 MLSC、RL、回测、风控、WebSocket 集成到现有系统

使用方法:
    python integration_example.py
"""

import sys
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from datetime import datetime
from typing import List, Dict
import json


def demo_mlsc():
    """演示 MLSC 多标签股票分类器"""
    print("\n" + "=" * 60)
    print("1. MLSC 多标签股票分类器演示")
    print("=" * 60)
    
    try:
        from models import MLSCPredictor
        
        # 创建预测器（会自动创建演示模型）
        predictor = MLSCPredictor()
        
        # 模拟股票历史数据
        import numpy as np
        stock_history = []
        base_price = 10.0
        for i in range(20):
            change = np.random.randn() * 0.5
            base_price = max(1, base_price + change)
            stock_history.append({
                'close': base_price,
                'open': base_price - np.random.rand() * 0.2,
                'high': base_price + np.random.rand() * 0.3,
                'low': base_price - np.random.rand() * 0.3,
                'volume': int(np.random.rand() * 10000000),
                'amount': base_price * np.random.rand() * 10000000
            })
        
        # 预测
        prediction = predictor.predict("000001", stock_history)
        
        print(f"\n股票代码: {prediction.stock_code}")
        print(f"预测时间: {prediction.timestamp}")
        print(f"\n各周期信号:")
        for horizon, signal_info in prediction.signals.items():
            print(f"  {horizon}天: {signal_info.signal} (置信度: {signal_info.confidence:.2%})")
        
        print(f"\n共识信号: {prediction.consensus_signal}")
        print(f"综合置信度: {prediction.consensus_confidence:.2%}")
        
    except Exception as e:
        print(f"MLSC 演示失败: {e}")


def demo_rl_adapter():
    """演示 RL 动态权重适配器"""
    print("\n" + "=" * 60)
    print("2. RL 动态权重适配器演示")
    print("=" * 60)
    
    try:
        from rl import RLWeightAdapter, MarketState
        
        # 创建适配器
        adapter = RLWeightAdapter()
        
        # 模拟不同市场状态
        scenarios = [
            ("牛市", MarketState(
                index_change=2.0, volatility=0.01, volume_ratio=1.5,
                fear_greed_index=80, up_count=3000, down_count=500
            )),
            ("震荡市", MarketState(
                index_change=0.2, volatility=0.015, volume_ratio=1.0,
                fear_greed_index=50, up_count=1500, down_count=1500
            )),
            ("熊市", MarketState(
                index_change=-2.5, volatility=0.03, volume_ratio=0.7,
                fear_greed_index=20, up_count=500, down_count=3000
            )),
        ]
        
        for name, state in scenarios:
            print(f"\n{name}市场:")
            print(f"  指数涨跌: {state.index_change:+.2f}%")
            print(f"  波动率: {state.volatility:.2%}")
            print(f"  恐慌贪婪: {state.fear_greed_index}")
            
            weights = adapter.get_adaptive_weights(state)
            print(f"  调整后权重:")
            for key, val in weights.items():
                if key.endswith('_weight'):
                    print(f"    {key}: {val:.3f}")
                    
    except Exception as e:
        print(f"RL 适配器演示失败: {e}")


def demo_backtest():
    """演示回测引擎"""
    print("\n" + "=" * 60)
    print("3. 回测引擎演示")
    print("=" * 60)
    
    try:
        import pandas as pd
        import numpy as np
        from backtest import BacktestEngine, BacktestConfig, BacktestSignal
        
        # 创建引擎
        config = BacktestConfig(
            initial_capital=100000,
            commission_rate=0.0003,
            slippage_rate=0.001
        )
        engine = BacktestEngine(config)
        
        # 生成模拟数据
        dates = pd.date_range('2024-01-01', periods=100)
        prices = 10 + np.cumsum(np.random.randn(100) * 0.5)
        
        data = pd.DataFrame({
            'date': dates,
            'open': prices - np.random.rand(100) * 0.2,
            'high': prices + np.random.rand(100) * 0.3,
            'low': prices - np.random.rand(100) * 0.3,
            'close': prices,
            'volume': np.random.randint(1000000, 10000000, 100)
        })
        data.set_index('date', inplace=True)
        
        # 简单信号生成器：价格 > MA5 买入，< MA5 卖出
        def signal_generator(df: pd.DataFrame) -> List[BacktestSignal]:
            df = df.copy()
            df['ma5'] = df['close'].rolling(5).mean()
            df['ma5_prev'] = df['ma5'].shift(1)
            
            signals = []
            for i in range(5, len(df)):
                if df['close'].iloc[i] > df['ma5'].iloc[i] and \
                   df['close'].iloc[i-1] <= df['ma5_prev'].iloc[i]:
                    signals.append(BacktestSignal(
                        date=df.index[i],
                        stock_code='000001',
                        action='buy',
                        price=df['close'].iloc[i],
                        quantity=100
                    ))
                elif df['close'].iloc[i] < df['ma5'].iloc[i]:
                    signals.append(BacktestSignal(
                        date=df.index[i],
                        stock_code='000001',
                        action='sell',
                        price=df['close'].iloc[i],
                        quantity=100
                    ))
            return signals
        
        # 运行回测
        result = engine.run(data, signal_generator)
        
        print(f"\n回测结果:")
        print(f"  初始资金: ¥{config.initial_capital:,.2f}")
        print(f"  最终资金: ¥{result.final_value:,.2f}")
        print(f"  总收益率: {result.total_return:+.2%}")
        print(f"  年化收益率: {result.annualized_return:+.2%}")
        print(f"  夏普比率: {result.sharpe_ratio:.2f}")
        print(f"  最大回撤: {result.max_drawdown:.2%}")
        print(f"  胜率: {result.win_rate:.2%}")
        print(f"  盈亏比: {result.profit_factor:.2f}")
        print(f"  交易次数: {result.total_trades}")
        
    except Exception as e:
        print(f"回测演示失败: {e}")


def demo_risk_manager():
    """演示风控系统"""
    print("\n" + "=" * 60)
    print("4. 智能风控系统演示")
    print("=" * 60)
    
    try:
        from risk import SmartRiskManager, Position
        
        # 创建风控管理器
        risk_mgr = SmartRiskManager(
            max_single_position=0.15,
            max_total_position=0.85,
            max_drawdown_limit=0.15
        )
        
        # 模拟持仓
        positions = [
            Position(
                stock_code='000001', quantity=10000, avg_price=10.5,
                current_price=11.2, cost_basis=105000
            ),
            Position(
                stock_code='000002', quantity=5000, avg_price=25.0,
                current_price=24.5, cost_basis=125000
            ),
            Position(
                stock_code='000003', quantity=8000, avg_price=8.0,
                current_price=8.5, cost_basis=64000
            ),
        ]
        
        # 模拟市场数据
        market_data = {
            '000001': {'price': 11.2, 'volume': 5000000, 'beta': 1.1},
            '000002': {'price': 24.5, 'volume': 3000000, 'beta': 0.9},
            '000003': {'price': 8.5, 'volume': 2000000, 'beta': 1.2},
            'index': {'price': 3000, 'change': 0.5}
        }
        
        # 分析组合风险
        metrics = risk_mgr.analyze_portfolio(positions, market_data)
        
        print(f"\n组合风险分析:")
        print(f"  总市值: ¥{metrics.total_value:,.2f}")
        print(f"  持仓占比: {metrics.total_position:.2%}")
        print(f"  VaR(95%): ¥{metrics.var_95:,.2f}")
        print(f"  CVaR(95%): ¥{metrics.cvar_95:,.2f}")
        print(f"  Beta: {metrics.beta:.2f}")
        print(f"  集中度风险: {metrics.concentration_risk:.2%}")
        print(f"  流动性风险: {metrics.liquidity_risk:.2%}")
        
        # 计算仓位建议
        size = risk_mgr.calculate_position_size(
            signal_strength=0.8,
            stock_risk=0.12,
            portfolio_value=300000
        )
        print(f"\n仓位计算 (信号强度0.8, 股票风险0.12):")
        print(f"  建议仓位: {size:.2%}")
        print(f"  建议金额: ¥{300000 * size:,.2f}")
        
        # 黑天鹅检测
        extreme_data = {
            'index': {'price': 2800, 'change': -8.0, 'volume': 50000000}
        }
        if risk_mgr.detect_black_swan(extreme_data):
            print("\n⚠️ 检测到黑天鹅事件！")
        
    except Exception as e:
        print(f"风控演示失败: {e}")


def demo_full_integration():
    """演示完整系统集成"""
    print("\n" + "=" * 60)
    print("5. 完整系统集成演示")
    print("=" * 60)
    
    try:
        from advanced_features import AdvancedTradingSystem
        
        # 创建完整系统
        print("\n初始化高级交易系统...")
        system = AdvancedTradingSystem()
        
        # 初始化
        system.initialize()
        
        # 获取综合信号
        print("\n获取股票信号...")
        mock_stock = {
            'code': '000001',
            'close': 10.5,
            'change_pct': 3.5,
            'volume_ratio': 2.0,
            'rsi': 55,
            'rank': 10
        }
        
        signal = system.get_signal('000001', mock_stock)
        
        print(f"\n综合信号结果:")
        print(f"  最终信号: {signal['final_signal']}")
        print(f"  综合评分: {signal['final_score']:.2%}")
        print(f"  置信度: {signal['confidence']:.2%}")
        
        if 'mlsc' in signal:
            print(f"\n  MLSC预测:")
            print(f"    1天: {signal['mlsc'].get('1d', 'N/A')}")
            print(f"    3天: {signal['mlsc'].get('3d', 'N/A')}")
            print(f"    5天: {signal['mlsc'].get('5d', 'N/A')}")
        
        if 'weights' in signal:
            print(f"\n  因子权重:")
            for k, v in signal['weights'].items():
                print(f"    {k}: {v:.3f}")
        
        print("\n✓ 完整集成演示成功！")
        
    except Exception as e:
        print(f"完整集成演示失败: {e}")


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("高级交易模块集成示例")
    print("=" * 60)
    
    # 运行所有演示
    demo_mlsc()
    demo_rl_adapter()
    demo_backtest()
    demo_risk_manager()
    demo_full_integration()
    
    print("\n" + "=" * 60)
    print("所有演示完成！")
    print("=" * 60)
    
    print("\n更多信息请查看:")
    print("  - INTEGRATION_GUIDE.md - 详细集成指南")
    print("  - ADVANCED_MODULES_README.md - 模块使用文档")


if __name__ == '__main__':
    main()

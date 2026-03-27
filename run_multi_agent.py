#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
启用多智能体系统的信号计算脚本
"""

import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from signal_engine import SignalEngine, init_storage
from history_store import get_price_history
from indicators import add_technical_indicators
from portfolio import Portfolio

# 检查多智能体是否可用
try:
    from agents import Orchestrator
    from memory import MemoryStore
    MULTI_AGENT_AVAILABLE = True
    print("[MultiAgent] 多智能体系统可用")
except ImportError as e:
    MULTI_AGENT_AVAILABLE = False
    print(f"[MultiAgent] 多智能体系统不可用: {e}")

def calculate_signals_with_multi_agent():
    """使用多智能体系统计算信号"""
    print("=" * 60)
    print("使用多智能体系统计算信号")
    print("=" * 60)
    
    init_storage()
    
    # 加载股票数据
    with open('output/hot_stocks.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        stocks = data.get('stocks', [])
    
    print(f"加载了 {len(stocks)} 只股票")
    
    # 创建多智能体协调器
    if not MULTI_AGENT_AVAILABLE:
        print("错误: 多智能体系统不可用")
        return None
    
    orchestrator = Orchestrator(MemoryStore())
    engine = SignalEngine()
    
    # 先添加技术指标
    print("\n[1/3] 计算技术指标...")
    for stock in stocks:
        code = stock.get('code', '')
        if code:
            price_history = get_price_history(code, days=60)
            if price_history and isinstance(price_history[0], dict):
                prices = [p.get('price', 0) for p in price_history]
            else:
                prices = price_history
            add_technical_indicators(stock, prices)
    
    # 计算信号
    print("\n[2/3] 多智能体分析...")
    signals = []
    portfolio = Portfolio()
    holdings = portfolio.get_holdings_with_status()
    holding_codes = {h['code']: h for h in holdings}
    
    for i, stock in enumerate(stocks):
        code = stock.get('code', '')
        name = stock.get('name', code)
        
        # 构建上下文（包含所有智能体需要的字段）
        context = {
            'stock': stock,
            'stock_code': code,
            'stock_name': name,
            'code': code,
            'name': name,
            'price': stock.get('price', 0),
            'prices': [stock.get('price', 0)],  # 价格历史
            'change_pct': stock.get('change_pct', 0),
            'volume': stock.get('volume', 0),
            'turnover_rate': stock.get('turnover_rate', 0),
            'rank': stock.get('rank', 100),
            'rsi': stock.get('rsi', 50),
            'macd': stock.get('macd', 0),
            'bb_position': stock.get('bb_position', 0.5),
        }
        
        # 尝试使用多智能体分析
        try:
            result = orchestrator.execute_analysis_pipeline(context)
            
            if result:
                # 提取信号
                signal = result.get('final_decision', {})
                signal['code'] = code
                signal['name'] = name
                signal['multi_agent'] = True
                signal['agent_details'] = result
                
                # 添加持仓信息
                if code in holding_codes:
                    signal['in_portfolio'] = True
                    signal['holding_info'] = holding_codes[code]
                else:
                    signal['in_portfolio'] = False
                    signal['holding_info'] = None
                
                signals.append(signal)
                print(f"  [{i+1}/{len(stocks)}] {name}: {signal.get('signal', 'N/A')}")
            else:
                # 回退到传统引擎
                sig = engine.calculate_signal(stock)
                signals.append(sig)
                print(f"  [{i+1}/{len(stocks)}] {name}: {sig.get('signal', 'N/A')} (传统)")
        except Exception as e:
            print(f"  [{i+1}/{len(stocks)}] {name}: 错误 - {e}")
            # 回退到传统引擎
            sig = engine.calculate_signal(stock)
            signals.append(sig)
    
    # 排序
    signals.sort(key=lambda x: (x.get('strength', 0), x.get('score', 0)), reverse=True)
    
    # 保存
    print("\n[3/3] 保存信号...")
    output = {
        'signals': signals,
        'timestamp': datetime.now().isoformat(),
        'multi_agent_enabled': True,
    }
    
    with open('output/signals_latest.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n完成! 保存了 {len(signals)} 个信号")
    
    # 统计
    multi_agent_count = sum(1 for s in signals if s.get('multi_agent'))
    print(f"多智能体分析: {multi_agent_count}/{len(signals)}")
    
    return signals

if __name__ == "__main__":
    calculate_signals_with_multi_agent()

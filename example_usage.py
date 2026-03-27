# -*- coding: utf-8 -*-
"""
多智能体股票分析系统 - 示例使用
Multi-Agent Stock Analysis System - Example Usage
"""

import logging
import json
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(name)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

from agents.orchestrator import Orchestrator
from memory import MemoryStore, ReflectionSystem
from history_store import HistoryStore


def create_sample_context():
    """
    创建示例分析上下文
    
    Returns:
        示例上下文数据
    """
    context = {
        'stock_code': '000001',
        'stock_name': '平安银行',
        'current_price': 10.5,
        
        # 技术面数据
        'prices': [10.0, 10.1, 10.2, 10.3, 10.4, 10.5] * 5,  # 30天收盘价
        'high_prices': [10.1, 10.2, 10.3, 10.4, 10.5, 10.6] * 5,
        'low_prices': [9.9, 10.0, 10.1, 10.2, 10.3, 10.4] * 5,
        
        # 情绪面数据
        'rank': 15,  # 人气榜排名
        'turnover_rate': 3.5,  # 换手率
        'volume_ratio': 1.8,  # 量比
        'price_change': 2.5,  # 价格变化百分比
        
        # 基本面数据
        'pe_ratio': 8.5,
        'pb_ratio': 0.9,
        'industry_pe': 10.0,
        'industry_pb': 1.2,
        'roe': 18.5,
        'eps_growth': 15.0,
        
        # 投资组合信息
        'portfolio_info': {
            'total_value': 100000,
            'available_capital': 20000,
            'current_positions': {}
        },
        
        # 市场信息
        'market_volatility': 0.025
    }
    
    return context


def run_analysis_example():
    """
    运行分析示例
    """
    print("=" * 60)
    print("多智能体股票分析系统 - 示例运行")
    print("=" * 60)
    print()
    
    # 初始化组件
    print("初始化系统组件...")
    memory_store = MemoryStore()
    reflection_system = ReflectionSystem()
    history_store = HistoryStore()
    orchestrator = Orchestrator(memory_store)
    
    # 创建示例上下文
    print("准备分析数据...")
    context = create_sample_context()
    
    # 执行分析流程
    print("执行多智能体分析流程...")
    print()
    
    result = orchestrator.execute_analysis_pipeline(context)
    
    # 输出摘要
    print(orchestrator.get_summary(result))
    print()
    
    # 保存决策记录
    if 'error' not in result:
        decision_record = {
            'stock_code': context['stock_code'],
            'timestamp': datetime.now().isoformat(),
            'signal': result.get('final_signal'),
            'confidence': result.get('final_confidence'),
            'action': result.get('trade_order', {}).get('trade_order', {}).get('action'),
            'target_price': result.get('research_decision', {}).get('investment_plan', {}).get('target_price_range'),
            'entry_price': context['current_price']
        }
        
        memory_store.save_decision(context['stock_code'], decision_record)
        
        # 保存反思
        reflection = {
            'analysis_result': result,
            'timestamp': datetime.now().isoformat()
        }
        reflection_system.save_reflection(context['stock_code'], reflection)
    
    # 输出详细报告
    print("=" * 60)
    print("详细分析报告")
    print("=" * 60)
    print()
    
    # 分析师报告
    print("【分析师报告】")
    for report in result.get('analyst_reports', []):
        print(f"\n{report.get('agent_name')}:")
        print(f"  信号: {report.get('signal')}")
        print(f"  置信度: {report.get('confidence'):.0%}")
        print(f"  报告: {report.get('report', '')[:200]}...")
    
    # 研究决策
    print("\n【研究决策】")
    research_decision = result.get('research_decision', {})
    print(f"  信号: {research_decision.get('signal')}")
    print(f"  置信度: {research_decision.get('confidence'):.0%}")
    
    investment_plan = research_decision.get('investment_plan', {})
    print(f"  行动: {investment_plan.get('action')}")
    print(f"  仓位: {investment_plan.get('position_size')}")
    if investment_plan.get('target_price_range'):
        target = investment_plan['target_price_range']
        print(f"  目标价格: {target['lower']} - {target['upper']}")
    
    # 交易指令
    print("\n【交易指令】")
    trade_order = result.get('trade_order', {}).get('trade_order', {})
    print(f"  行动: {trade_order.get('action')}")
    print(f"  数量: {trade_order.get('quantity')}")
    print(f"  价格: {trade_order.get('price')}")
    print(f"  止损: {trade_order.get('stop_loss')}")
    print(f"  止盈: {trade_order.get('take_profit')}")
    
    # 风险评估
    print("\n【风险评估】")
    risk_assessment = result.get('risk_assessment', {}).get('risk_assessment', {})
    print(f"  风险等级: {risk_assessment.get('risk_level')}")
    print(f"  风险评分: {risk_assessment.get('risk_score'):.2f}")
    print(f"  仓位占比: {risk_assessment.get('position_ratio'):.2%}")
    
    print("\n" + "=" * 60)
    print(f"分析完成，耗时: {result.get('execution_time', 0):.2f}秒")
    print("=" * 60)


def run_historical_analysis():
    """
    运行历史分析示例
    """
    print("\n" + "=" * 60)
    print("历史决策分析")
    print("=" * 60)
    print()
    
    memory_store = MemoryStore()
    reflection_system = ReflectionSystem()
    
    stock_code = '000001'
    
    # 获取历史决策
    decisions = memory_store.get_decisions(stock_code, limit=20)
    
    if decisions:
        print(f"股票 {stock_code} 的最近20条决策:")
        print()
        
        for i, decision in enumerate(decisions[-5:], 1):  # 显示最后5条
            print(f"{i}. {decision.get('timestamp')}")
            print(f"   信号: {decision.get('signal')}")
            print(f"   置信度: {decision.get('confidence'):.0%}")
            print(f"   行动: {decision.get('action')}")
            print()
        
        # 计算成功率
        success_rate = memory_store.calculate_success_rate(stock_code)
        print(f"总体成功率: {success_rate:.0%}")
        
        bullish_rate = memory_store.calculate_success_rate(stock_code, 'bullish')
        print(f"看涨信号成功率: {bullish_rate:.0%}")
        
        bearish_rate = memory_store.calculate_success_rate(stock_code, 'bearish')
        print(f"看跌信号成功率: {bearish_rate:.0%}")
    else:
        print(f"股票 {stock_code} 暂无历史决策")
    
    print()


if __name__ == '__main__':
    # 运行分析示例
    run_analysis_example()
    
    # 运行历史分析
    run_historical_analysis()

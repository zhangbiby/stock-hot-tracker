# -*- coding: utf-8 -*-
"""
协调器智能体
Orchestrator Agent
"""

import logging
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from .technical_analyst import TechnicalAnalyst
from .sentiment_analyst import SentimentAnalyst
from .news_analyst import NewsAnalyst
from .fundamental_analyst import FundamentalAnalyst
from .bull_researcher import BullResearcher
from .bear_researcher import BearResearcher
from .research_manager import ResearchManager
from .trader import Trader
from .risk_manager import RiskManager


class Orchestrator:
    """
    协调器
    协调所有智能体的执行流程
    """
    
    def __init__(self, memory_store=None):
        """
        初始化协调器
        
        Args:
            memory_store: 记忆存储实例
        """
        self.logger = logging.getLogger("Orchestrator")
        self.memory_store = memory_store
        
        # 初始化所有智能体
        self.technical_analyst = TechnicalAnalyst()
        self.sentiment_analyst = SentimentAnalyst()  # 使用模块函数，不需要实例
        self.news_analyst = NewsAnalyst()
        self.fundamental_analyst = FundamentalAnalyst()
        self.bull_researcher = BullResearcher()
        self.bear_researcher = BearResearcher()
        self.research_manager = ResearchManager()
        self.trader = Trader(memory_store)
        self.risk_manager = RiskManager()
        
        self.logger.info("协调器初始化完成")
    
    def execute_analysis_pipeline(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行完整的分析流程
        
        Args:
            context: 分析上下文，包含股票数据和市场信息
            
        Returns:
            完整的分析结果
        """
        self.logger.info(f"开始分析流程: {context.get('stock_code', 'Unknown')}")
        
        start_time = datetime.now()
        
        try:
            # 第一阶段：并行调用所有分析师
            self.logger.info("第一阶段: 并行调用分析师...")
            analyst_reports = self._run_analysts_parallel(context)
            
            # 第二阶段：看涨/看跌研究员分析
            self.logger.info("第二阶段: 看涨/看跌研究员分析...")
            bull_research = self.bull_researcher.analyze({'analyst_reports': analyst_reports})
            bear_research = self.bear_researcher.analyze({'analyst_reports': analyst_reports})
            
            # 第三阶段：研究经理综合决策
            self.logger.info("第三阶段: 研究经理综合决策...")
            research_context = {
                'bull_research': bull_research,
                'bear_research': bear_research,
                'current_price': context.get('current_price', 0),
                'stock_code': context.get('stock_code')
            }
            research_decision = self.research_manager.analyze(research_context)
            
            # 第四阶段：交易员执行
            self.logger.info("第四阶段: 交易员执行...")
            trader_context = {
                'investment_plan': research_decision.get('investment_plan', {}),
                'stock_code': context.get('stock_code'),
                'current_price': context.get('current_price', 0),
                'portfolio_info': context.get('portfolio_info', {})
            }
            trade_order = self.trader.analyze(trader_context)
            
            # 第五阶段：风险经理风控
            self.logger.info("第五阶段: 风险经理风控...")
            risk_context = {
                'investment_plan': research_decision.get('investment_plan', {}),
                'trade_order': trade_order.get('trade_order', {}),
                'portfolio_info': context.get('portfolio_info', {}),
                'market_volatility': context.get('market_volatility', 0.02)
            }
            risk_assessment = self.risk_manager.analyze(risk_context)
            
            # 汇总结果
            elapsed_time = (datetime.now() - start_time).total_seconds()
            
            final_result = {
                'stock_code': context.get('stock_code'),
                'timestamp': datetime.now().isoformat(),
                'execution_time': elapsed_time,
                'analyst_reports': analyst_reports,
                'bull_research': bull_research,
                'bear_research': bear_research,
                'research_decision': research_decision,
                'trade_order': trade_order,
                'risk_assessment': risk_assessment,
                'final_signal': risk_assessment.get('signal', 'neutral'),
                'final_confidence': risk_assessment.get('confidence', 0)
            }
            
            self.logger.info(f"分析流程完成: {final_result['final_signal']}, 耗时: {elapsed_time:.2f}秒")
            
            return final_result
            
        except Exception as e:
            self.logger.error(f"分析流程出错: {e}", exc_info=True)
            return {
                'stock_code': context.get('stock_code'),
                'error': str(e),
                'final_signal': 'neutral',
                'final_confidence': 0
            }
    
    def _run_analysts_parallel(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        并行运行所有分析师
        
        Args:
            context: 分析上下文
            
        Returns:
            所有分析师的报告列表
        """
        analysts = [
            ('TechnicalAnalyst', self.technical_analyst),
            ('SentimentAnalyst', self.sentiment_analyst),
            ('NewsAnalyst', self.news_analyst),
            ('FundamentalAnalyst', self.fundamental_analyst),
        ]
        
        reports = []
        
        # 使用线程池并行执行
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {}
            
            for name, analyst in analysts:
                future = executor.submit(analyst.analyze, context)
                futures[future] = name
            
            # 收集结果
            for future in as_completed(futures):
                name = futures[future]
                try:
                    report = future.result()
                    reports.append(report)
                    self.logger.info(f"{name} 分析完成")
                except Exception as e:
                    self.logger.error(f"{name} 分析失败: {e}")
        
        return reports
    
    def get_summary(self, analysis_result: Dict[str, Any]) -> str:
        """
        生成分析摘要
        
        Args:
            analysis_result: 完整的分析结果
            
        Returns:
            摘要文本
        """
        if 'error' in analysis_result:
            return f"分析失败: {analysis_result['error']}"
        
        summary_lines = [
            "=" * 50,
            "多智能体股票分析系统 - 最终报告",
            "=" * 50,
            "",
            f"股票代码: {analysis_result.get('stock_code', 'N/A')}",
            f"分析时间: {analysis_result.get('timestamp', 'N/A')}",
            f"执行耗时: {analysis_result.get('execution_time', 0):.2f}秒",
            "",
            "最终决策:",
            f"  信号: {analysis_result.get('final_signal', 'neutral')}",
            f"  置信度: {analysis_result.get('final_confidence', 0):.0%}",
            "",
            "分析师报告摘要:",
        ]
        
        for report in analysis_result.get('analyst_reports', []):
            agent_name = report.get('agent_name', 'Unknown')
            signal = report.get('signal', 'neutral')
            confidence = report.get('confidence', 0)
            summary_lines.append(f"  {agent_name}: {signal} ({confidence:.0%})")
        
        summary_lines.extend([
            "",
            "研究决策:",
            f"  看涨置信度: {analysis_result.get('bull_research', {}).get('confidence', 0):.0%}",
            f"  看跌置信度: {analysis_result.get('bear_research', {}).get('confidence', 0):.0%}",
            "",
            "交易指令:",
            f"  行动: {analysis_result.get('trade_order', {}).get('trade_order', {}).get('action', 'hold')}",
            f"  数量: {analysis_result.get('trade_order', {}).get('trade_order', {}).get('quantity', 0)}",
            "",
            "风险评估:",
            f"  风险等级: {analysis_result.get('risk_assessment', {}).get('risk_assessment', {}).get('risk_level', 'unknown')}",
            f"  风险评分: {analysis_result.get('risk_assessment', {}).get('risk_assessment', {}).get('risk_score', 0):.2f}",
            "",
            "=" * 50,
        ])
        
        return "\n".join(summary_lines)

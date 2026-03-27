# -*- coding: utf-8 -*-
"""
研究经理智能体
Research Manager Agent
"""

from typing import Dict, Any, List
from .base_agent import BaseAgent


class ResearchManager(BaseAgent):
    """
    研究经理
    组织看涨/看跌研究员的辩论，综合决策，生成投资计划
    """
    
    def __init__(self):
        super().__init__(
            name="ResearchManager",
            role="研究经理"
        )
    
    def analyze(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行研究管理和决策
        
        Args:
            context: 包含以下字段的上下文
                - bull_research: 看涨研究报告 (必需)
                - bear_research: 看跌研究报告 (必需)
                - current_price: 当前价格 (可选)
                - stock_code: 股票代码 (可选)
                
        Returns:
            投资决策结果
        """
        if not self._validate_context(context, ['bull_research', 'bear_research']):
            return self._create_result('neutral', 0, '缺少研究报告')
        
        try:
            bull_research = context['bull_research']
            bear_research = context['bear_research']
            current_price = context.get('current_price', 0)
            
            # 组织辩论
            debate_result = self._organize_debate(bull_research, bear_research)
            
            # 综合决策
            final_decision = self._make_decision(debate_result)
            
            # 生成投资计划
            investment_plan = self._generate_investment_plan(
                final_decision,
                current_price
            )
            
            # 生成报告
            report = self._generate_report(debate_result, final_decision, investment_plan)
            
            self.log(f"研究决策完成: {final_decision['signal']}, 置信度: {final_decision['confidence']:.2%}")
            
            return self._create_result(
                signal=final_decision['signal'],
                confidence=final_decision['confidence'],
                report=report,
                debate_result=debate_result,
                investment_plan=investment_plan
            )
            
        except Exception as e:
            self.log(f"研究决策出错: {e}", "ERROR")
            return self._create_result('neutral', 0, f'决策出错: {str(e)}')
    
    def _organize_debate(
        self,
        bull_research: Dict[str, Any],
        bear_research: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        组织看涨/看跌研究员的辩论
        
        Args:
            bull_research: 看涨研究报告
            bear_research: 看跌研究报告
            
        Returns:
            辩论结果
        """
        bull_confidence = bull_research.get('confidence', 0)
        bear_confidence = bear_research.get('confidence', 0)
        
        bull_arguments = bull_research.get('bullish_arguments', [])
        bear_arguments = bear_research.get('bearish_arguments', [])
        
        debate = {
            'bull_side': {
                'confidence': bull_confidence,
                'arguments_count': len(bull_arguments),
                'top_arguments': bull_arguments[:3]
            },
            'bear_side': {
                'confidence': bear_confidence,
                'arguments_count': len(bear_arguments),
                'top_arguments': bear_arguments[:3]
            },
            'debate_score': bull_confidence - bear_confidence,
            'winner': 'bull' if bull_confidence > bear_confidence else ('bear' if bear_confidence > bull_confidence else 'tie')
        }
        
        return debate
    
    def _make_decision(self, debate_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        基于辩论结果做出最终决策
        
        Args:
            debate_result: 辩论结果
            
        Returns:
            最终决策
        """
        debate_score = debate_result['debate_score']
        winner = debate_result['winner']
        
        # 根据辩论分数确定信号和置信度
        if winner == 'bull':
            signal = 'bullish'
            confidence = min(0.95, debate_result['bull_side']['confidence'])
        elif winner == 'bear':
            signal = 'bearish'
            confidence = min(0.95, debate_result['bear_side']['confidence'])
        else:
            signal = 'neutral'
            confidence = 0.5
        
        # 如果分数接近，降低置信度
        if abs(debate_score) < 0.2:
            confidence *= 0.7
        
        return {
            'signal': signal,
            'confidence': confidence,
            'debate_score': debate_score,
            'winner': winner
        }
    
    def _generate_investment_plan(
        self,
        final_decision: Dict[str, Any],
        current_price: float
    ) -> Dict[str, Any]:
        """
        生成投资计划
        
        Args:
            final_decision: 最终决策
            current_price: 当前价格
            
        Returns:
            投资计划
        """
        signal = final_decision['signal']
        confidence = final_decision['confidence']
        
        plan = {
            'action': 'hold',
            'target_price_range': None,
            'stop_loss': None,
            'take_profit': None,
            'position_size': 'neutral',
            'time_horizon': 'medium_term'
        }
        
        if current_price <= 0:
            return plan
        
        if signal == 'bullish':
            plan['action'] = 'buy'
            
            # 目标价格范围
            upside = 0.05 + confidence * 0.15  # 5% - 20%
            plan['target_price_range'] = {
                'lower': round(current_price * (1 + upside * 0.5), 2),
                'upper': round(current_price * (1 + upside), 2)
            }
            
            # 止损位
            plan['stop_loss'] = round(current_price * 0.95, 2)
            
            # 止盈位
            plan['take_profit'] = plan['target_price_range']['upper']
            
            # 仓位建议
            if confidence > 0.8:
                plan['position_size'] = 'large'
            elif confidence > 0.6:
                plan['position_size'] = 'medium'
            else:
                plan['position_size'] = 'small'
        
        elif signal == 'bearish':
            plan['action'] = 'sell'
            
            # 目标价格范围
            downside = 0.05 + confidence * 0.15  # 5% - 20%
            plan['target_price_range'] = {
                'lower': round(current_price * (1 - downside), 2),
                'upper': round(current_price * (1 - downside * 0.5), 2)
            }
            
            # 止损位
            plan['stop_loss'] = round(current_price * 1.05, 2)
            
            # 止盈位
            plan['take_profit'] = plan['target_price_range']['lower']
            
            # 仓位建议
            if confidence > 0.8:
                plan['position_size'] = 'large'
            elif confidence > 0.6:
                plan['position_size'] = 'medium'
            else:
                plan['position_size'] = 'small'
        
        else:  # neutral
            plan['action'] = 'hold'
            plan['position_size'] = 'neutral'
        
        return plan
    
    def _generate_report(
        self,
        debate_result: Dict[str, Any],
        final_decision: Dict[str, Any],
        investment_plan: Dict[str, Any]
    ) -> str:
        """
        生成研究经理报告
        
        Returns:
            报告文本
        """
        report_lines = [
            "=== 研究经理决策报告 ===",
            "",
            "辩论结果:",
            f"  看涨方置信度: {debate_result['bull_side']['confidence']:.0%}",
            f"  看跌方置信度: {debate_result['bear_side']['confidence']:.0%}",
            f"  辩论分数: {debate_result['debate_score']:.2f}",
            f"  获胜方: {debate_result['winner']}",
            "",
            "最终决策:",
            f"  信号: {final_decision['signal']}",
            f"  置信度: {final_decision['confidence']:.0%}",
            "",
            "投资计划:",
            f"  行动: {investment_plan['action']}",
            f"  仓位: {investment_plan['position_size']}",
            f"  时间周期: {investment_plan['time_horizon']}",
        ]
        
        if investment_plan['target_price_range']:
            target = investment_plan['target_price_range']
            report_lines.append(f"  目标价格: {target['lower']} - {target['upper']}")
        
        if investment_plan['stop_loss']:
            report_lines.append(f"  止损位: {investment_plan['stop_loss']}")
        
        if investment_plan['take_profit']:
            report_lines.append(f"  止盈位: {investment_plan['take_profit']}")
        
        return "\n".join(report_lines)

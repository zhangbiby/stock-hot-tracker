# -*- coding: utf-8 -*-
"""
风险经理智能体
Risk Manager Agent
"""

from typing import Dict, Any
from .base_agent import BaseAgent


class RiskManager(BaseAgent):
    """
    风险经理
    评估投资计划风险，调整仓位建议，设置止损位
    """
    
    def __init__(self):
        super().__init__(
            name="RiskManager",
            role="风险管理专家"
        )
        
        # 风险阈值
        self.max_single_position = 0.15  # 单个头寸最多占投资组合15%
        self.max_portfolio_risk = 0.05   # 投资组合最大风险5%
        self.max_drawdown = 0.20         # 最大回撤20%
    
    def analyze(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行风险评估
        
        Args:
            context: 包含以下字段的上下文
                - investment_plan: 投资计划 (必需)
                - trade_order: 交易指令 (必需)
                - portfolio_info: 投资组合信息 (可选)
                - market_volatility: 市场波动率 (可选)
                
        Returns:
            风险评估结果
        """
        if not self._validate_context(context, ['investment_plan', 'trade_order']):
            return self._create_result('neutral', 0, '缺少必要的风险评估数据')
        
        try:
            investment_plan = context['investment_plan']
            trade_order = context['trade_order']
            portfolio_info = context.get('portfolio_info', {})
            market_volatility = context.get('market_volatility', 0.02)
            
            # 评估风险
            risk_assessment = self._assess_risk(
                investment_plan,
                trade_order,
                portfolio_info,
                market_volatility
            )
            
            # 调整仓位
            adjusted_position = self._adjust_position(
                trade_order,
                risk_assessment,
                portfolio_info
            )
            
            # 优化止损止盈
            optimized_stops = self._optimize_stops(
                trade_order,
                risk_assessment,
                market_volatility
            )
            
            # 生成报告
            report = self._generate_report(
                risk_assessment,
                adjusted_position,
                optimized_stops
            )
            
            # 确定最终信号
            final_signal = self._determine_final_signal(risk_assessment)
            
            self.log(f"风险评估完成: 风险等级 {risk_assessment['risk_level']}")
            
            return self._create_result(
                signal=final_signal,
                confidence=trade_order.get('confidence', 0.5),
                report=report,
                risk_assessment=risk_assessment,
                adjusted_position=adjusted_position,
                optimized_stops=optimized_stops
            )
            
        except Exception as e:
            self.log(f"风险评估出错: {e}", "ERROR")
            return self._create_result('neutral', 0, f'评估出错: {str(e)}')
    
    def _assess_risk(
        self,
        investment_plan: Dict[str, Any],
        trade_order: Dict[str, Any],
        portfolio_info: Dict[str, Any],
        market_volatility: float
    ) -> Dict[str, Any]:
        """
        评估投资风险
        
        Args:
            investment_plan: 投资计划
            trade_order: 交易指令
            portfolio_info: 投资组合信息
            market_volatility: 市场波动率
            
        Returns:
            风险评估结果
        """
        risk_score = 0
        risk_factors = []
        
        # 1. 仓位风险
        position_size = investment_plan.get('position_size', 'neutral')
        if position_size == 'large':
            risk_score += 0.3
            risk_factors.append('大仓位风险')
        elif position_size == 'medium':
            risk_score += 0.15
        
        # 2. 市场波动率风险
        if market_volatility > 0.03:
            risk_score += 0.2
            risk_factors.append('高波动率风险')
        elif market_volatility > 0.02:
            risk_score += 0.1
        
        # 3. 置信度风险
        confidence = trade_order.get('confidence', 0.5)
        if confidence < 0.5:
            risk_score += 0.2
            risk_factors.append('低置信度风险')
        
        # 4. 投资组合集中度风险
        portfolio_value = portfolio_info.get('total_value', 100000)
        position_value = trade_order.get('price', 0) * trade_order.get('quantity', 0)
        
        if portfolio_value > 0:
            position_ratio = position_value / portfolio_value
            if position_ratio > self.max_single_position:
                risk_score += 0.25
                risk_factors.append('仓位过度集中')
        
        # 5. 止损设置风险
        stop_loss = investment_plan.get('stop_loss')
        current_price = trade_order.get('price', 0)
        
        if stop_loss and current_price > 0:
            max_loss_ratio = abs(stop_loss - current_price) / current_price
            if max_loss_ratio > 0.1:
                risk_score += 0.1
                risk_factors.append('止损距离过远')
        
        # 限制风险评分在0-1之间
        risk_score = min(1.0, risk_score)
        
        # 确定风险等级
        if risk_score > 0.7:
            risk_level = 'very_high'
        elif risk_score > 0.5:
            risk_level = 'high'
        elif risk_score > 0.3:
            risk_level = 'medium'
        elif risk_score > 0.1:
            risk_level = 'low'
        else:
            risk_level = 'very_low'
        
        return {
            'risk_score': risk_score,
            'risk_level': risk_level,
            'risk_factors': risk_factors,
            'position_ratio': position_ratio if portfolio_value > 0 else 0,
            'max_loss_ratio': max_loss_ratio if stop_loss and current_price > 0 else 0
        }
    
    def _adjust_position(
        self,
        trade_order: Dict[str, Any],
        risk_assessment: Dict[str, Any],
        portfolio_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        根据风险调整仓位
        
        Args:
            trade_order: 交易指令
            risk_assessment: 风险评估
            portfolio_info: 投资组合信息
            
        Returns:
            调整后的仓位
        """
        original_quantity = trade_order.get('quantity', 0)
        risk_level = risk_assessment['risk_level']
        
        # 根据风险等级调整数量
        adjustment_factors = {
            'very_high': 0.3,
            'high': 0.6,
            'medium': 0.8,
            'low': 0.95,
            'very_low': 1.0
        }
        
        adjustment_factor = adjustment_factors.get(risk_level, 0.8)
        adjusted_quantity = int(original_quantity * adjustment_factor)
        
        return {
            'original_quantity': original_quantity,
            'adjusted_quantity': adjusted_quantity,
            'adjustment_factor': adjustment_factor,
            'reason': f'根据{risk_level}风险等级调整'
        }
    
    def _optimize_stops(
        self,
        trade_order: Dict[str, Any],
        risk_assessment: Dict[str, Any],
        market_volatility: float
    ) -> Dict[str, Any]:
        """
        优化止损止盈位
        
        Args:
            trade_order: 交易指令
            risk_assessment: 风险评估
            market_volatility: 市场波动率
            
        Returns:
            优化后的止损止盈
        """
        current_price = trade_order.get('price', 0)
        original_stop_loss = trade_order.get('stop_loss')
        original_take_profit = trade_order.get('take_profit')
        
        if current_price <= 0:
            return {
                'optimized_stop_loss': original_stop_loss,
                'optimized_take_profit': original_take_profit
            }
        
        # 基于波动率调整止损距离
        volatility_adjustment = 1 + market_volatility * 5
        
        # 调整止损
        if original_stop_loss:
            loss_distance = abs(original_stop_loss - current_price) / current_price
            optimized_loss_distance = loss_distance * volatility_adjustment
            
            if trade_order.get('action') == 'buy':
                optimized_stop_loss = round(current_price * (1 - optimized_loss_distance), 2)
            else:
                optimized_stop_loss = round(current_price * (1 + optimized_loss_distance), 2)
        else:
            optimized_stop_loss = None
        
        # 调整止盈
        if original_take_profit:
            profit_distance = abs(original_take_profit - current_price) / current_price
            optimized_profit_distance = profit_distance * volatility_adjustment
            
            if trade_order.get('action') == 'buy':
                optimized_take_profit = round(current_price * (1 + optimized_profit_distance), 2)
            else:
                optimized_take_profit = round(current_price * (1 - optimized_profit_distance), 2)
        else:
            optimized_take_profit = None
        
        return {
            'optimized_stop_loss': optimized_stop_loss,
            'optimized_take_profit': optimized_take_profit,
            'volatility_adjustment': volatility_adjustment
        }
    
    def _determine_final_signal(self, risk_assessment: Dict[str, Any]) -> str:
        """
        根据风险评估确定最终信号
        
        Args:
            risk_assessment: 风险评估
            
        Returns:
            最终信号
        """
        risk_level = risk_assessment['risk_level']
        
        if risk_level in ['very_high', 'high']:
            return 'bearish'  # 风险过高，建议回避
        else:
            return 'bullish'  # 风险可控，可以执行
    
    def _generate_report(
        self,
        risk_assessment: Dict[str, Any],
        adjusted_position: Dict[str, Any],
        optimized_stops: Dict[str, Any]
    ) -> str:
        """
        生成风险管理报告
        
        Returns:
            报告文本
        """
        report_lines = [
            "=== 风险管理报告 ===",
            "",
            "风险评估:",
            f"  风险评分: {risk_assessment['risk_score']:.2f}",
            f"  风险等级: {risk_assessment['risk_level']}",
            f"  仓位占比: {risk_assessment['position_ratio']:.2%}",
            f"  最大亏损: {risk_assessment['max_loss_ratio']:.2%}",
            "",
            "风险因素:",
        ]
        
        for factor in risk_assessment['risk_factors']:
            report_lines.append(f"  - {factor}")
        
        report_lines.extend([
            "",
            "仓位调整:",
            f"  原始数量: {adjusted_position['original_quantity']}",
            f"  调整后: {adjusted_position['adjusted_quantity']}",
            f"  调整系数: {adjusted_position['adjustment_factor']:.0%}",
            "",
            "止损止盈优化:",
            f"  止损位: {optimized_stops['optimized_stop_loss']}",
            f"  止盈位: {optimized_stops['optimized_take_profit']}",
        ])
        
        return "\n".join(report_lines)

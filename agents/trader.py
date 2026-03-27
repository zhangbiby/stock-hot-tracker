# -*- coding: utf-8 -*-
"""
交易员智能体
Trader Agent
"""

from typing import Dict, Any, List
from .base_agent import BaseAgent


class Trader(BaseAgent):
    """
    交易员
    接收投资计划，查询历史记忆，生成交易指令
    """
    
    def __init__(self, memory_store=None):
        super().__init__(
            name="Trader",
            role="交易执行员"
        )
        self.memory_store = memory_store
    
    def analyze(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行交易决策
        
        Args:
            context: 包含以下字段的上下文
                - investment_plan: 投资计划 (必需)
                - stock_code: 股票代码 (必需)
                - current_price: 当前价格 (可选)
                - portfolio_info: 投资组合信息 (可选)
                
        Returns:
            交易指令
        """
        if not self._validate_context(context, ['investment_plan', 'stock_code']):
            return self._create_result('neutral', 0, '缺少必要的交易信息')
        
        try:
            investment_plan = context['investment_plan']
            stock_code = context['stock_code']
            current_price = context.get('current_price', 0)
            portfolio_info = context.get('portfolio_info', {})
            
            # 查询历史记忆
            historical_context = self._query_historical_context(stock_code)
            
            # 生成交易指令
            trade_order = self._generate_trade_order(
                investment_plan,
                current_price,
                portfolio_info,
                historical_context
            )
            
            # 生成报告
            report = self._generate_report(trade_order, historical_context)
            
            self.log(f"交易指令生成: {trade_order['action']}, 数量: {trade_order['quantity']}")
            
            return self._create_result(
                signal=trade_order['action'],
                confidence=trade_order['confidence'],
                report=report,
                trade_order=trade_order,
                historical_context=historical_context
            )
            
        except Exception as e:
            self.log(f"交易决策出错: {e}", "ERROR")
            return self._create_result('neutral', 0, f'交易出错: {str(e)}')
    
    def _query_historical_context(self, stock_code: str) -> Dict[str, Any]:
        """
        查询历史记忆，找到相似的历史案例
        
        Args:
            stock_code: 股票代码
            
        Returns:
            历史上下文
        """
        context = {
            'has_history': False,
            'similar_cases': [],
            'success_rate': 0,
            'avg_return': 0
        }
        
        if not self.memory_store:
            return context
        
        try:
            # 获取历史记录
            history = self.memory_store.get_history(stock_code, limit=90)
            
            if history:
                context['has_history'] = True
                context['similar_cases'] = history[-5:]  # 最近5条
                
                # 计算成功率
                successful = sum(1 for h in history if h.get('result') == 'success')
                context['success_rate'] = successful / len(history) if history else 0
                
                # 计算平均收益
                returns = [h.get('return', 0) for h in history if 'return' in h]
                context['avg_return'] = sum(returns) / len(returns) if returns else 0
        
        except Exception as e:
            self.log(f"查询历史记忆失败: {e}", "WARNING")
        
        return context
    
    def _generate_trade_order(
        self,
        investment_plan: Dict[str, Any],
        current_price: float,
        portfolio_info: Dict[str, Any],
        historical_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        生成交易指令
        
        Args:
            investment_plan: 投资计划
            current_price: 当前价格
            portfolio_info: 投资组合信息
            historical_context: 历史上下文
            
        Returns:
            交易指令
        """
        action = investment_plan.get('action', 'hold')
        position_size = investment_plan.get('position_size', 'neutral')
        confidence = investment_plan.get('confidence', 0.5)
        
        # 根据历史成功率调整置信度
        if historical_context['has_history']:
            success_rate = historical_context['success_rate']
            confidence = confidence * (0.5 + success_rate * 0.5)
        
        # 计算交易数量
        quantity = self._calculate_quantity(
            action,
            position_size,
            current_price,
            portfolio_info
        )
        
        order = {
            'action': action,
            'quantity': quantity,
            'price': current_price,
            'confidence': confidence,
            'stop_loss': investment_plan.get('stop_loss'),
            'take_profit': investment_plan.get('take_profit'),
            'time_horizon': investment_plan.get('time_horizon', 'medium_term'),
            'reason': self._generate_order_reason(investment_plan, historical_context)
        }
        
        return order
    
    def _calculate_quantity(
        self,
        action: str,
        position_size: str,
        current_price: float,
        portfolio_info: Dict[str, Any]
    ) -> int:
        """
        计算交易数量
        
        Args:
            action: 交易行动
            position_size: 仓位大小
            current_price: 当前价格
            portfolio_info: 投资组合信息
            
        Returns:
            交易数量
        """
        if action == 'hold' or current_price <= 0:
            return 0
        
        # 获取可用资金
        available_capital = portfolio_info.get('available_capital', 10000)
        
        # 根据仓位大小确定投入比例
        position_ratios = {
            'small': 0.05,
            'medium': 0.10,
            'large': 0.20,
            'neutral': 0
        }
        
        ratio = position_ratios.get(position_size, 0)
        
        if ratio == 0:
            return 0
        
        # 计算数量
        investment_amount = available_capital * ratio
        quantity = int(investment_amount / current_price)
        
        # 最小数量限制
        if quantity < 1:
            quantity = 1
        
        return quantity
    
    def _generate_order_reason(
        self,
        investment_plan: Dict[str, Any],
        historical_context: Dict[str, Any]
    ) -> str:
        """
        生成交易理由
        
        Args:
            investment_plan: 投资计划
            historical_context: 历史上下文
            
        Returns:
            交易理由文本
        """
        reasons = []
        
        action = investment_plan.get('action', 'hold')
        if action == 'buy':
            reasons.append("基于多方面分析，看好后市")
        elif action == 'sell':
            reasons.append("基于多方面分析，看空后市")
        else:
            reasons.append("市场信号不明确，保持观望")
        
        # 添加历史参考
        if historical_context['has_history']:
            success_rate = historical_context['success_rate']
            if success_rate > 0.6:
                reasons.append(f"历史成功率{success_rate:.0%}，参考价值高")
            elif success_rate < 0.4:
                reasons.append(f"历史成功率{success_rate:.0%}，需谨慎")
        
        return "；".join(reasons)
    
    def _generate_report(
        self,
        trade_order: Dict[str, Any],
        historical_context: Dict[str, Any]
    ) -> str:
        """
        生成交易报告
        
        Returns:
            报告文本
        """
        report_lines = [
            "=== 交易指令报告 ===",
            "",
            "交易指令:",
            f"  行动: {trade_order['action']}",
            f"  数量: {trade_order['quantity']}",
            f"  价格: {trade_order['price']}",
            f"  置信度: {trade_order['confidence']:.0%}",
            "",
            "风险管理:",
            f"  止损位: {trade_order['stop_loss']}",
            f"  止盈位: {trade_order['take_profit']}",
            f"  时间周期: {trade_order['time_horizon']}",
            "",
            "交易理由:",
            f"  {trade_order['reason']}",
        ]
        
        if historical_context['has_history']:
            report_lines.append("")
            report_lines.append("历史参考:")
            report_lines.append(f"  历史成功率: {historical_context['success_rate']:.0%}")
            report_lines.append(f"  平均收益: {historical_context['avg_return']:.2%}")
            report_lines.append(f"  相似案例: {len(historical_context['similar_cases'])}个")
        
        return "\n".join(report_lines)

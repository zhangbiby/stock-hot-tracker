# -*- coding: utf-8 -*-
"""
情绪分析师智能体
Sentiment Analyst Agent
"""

from typing import Dict, Any
from .base_agent import BaseAgent
import history_store as hs


class SentimentAnalyst(BaseAgent):
    """
    情绪分析师
    分析市场情绪：人气榜排名、换手率、量比等
    """
    
    def __init__(self, history_store=None):
        super().__init__(
            name="SentimentAnalyst",
            role="市场情绪分析专家"
        )
        self.history_store = history_store  # 可选，用于兼容
    
    def analyze(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行情绪分析
        
        Args:
            context: 包含以下字段的上下文
                - stock_code: 股票代码 (必需)
                - rank: 人气榜排名 (必需)
                - turnover_rate: 换手率 (可选)
                - volume_ratio: 量比 (可选)
                - price_change: 价格变化 (可选)
                
        Returns:
            情绪分析结果
        """
        if not self._validate_context(context, ['stock_code', 'rank']):
            return self._create_result('neutral', 0, '缺少必要的情绪数据')
        
        try:
            stock_code = context['stock_code']
            current_rank = context['rank']
            
            # 使用 history_store 模块函数分析排名变化
            prev_rank_5m = hs.get_prev_rank(stock_code, minutes_ago=5)
            prev_rank_1h = hs.get_prev_rank(stock_code, minutes_ago=60)
            
            rank_change = 0
            if prev_rank_5m:
                rank_change = prev_rank_5m - current_rank
            
            # 分析情绪指标
            turnover_rate = context.get('turnover_rate', 0)
            volume_ratio = context.get('volume_ratio', 1.0)
            price_change = context.get('price_change', 0)
            
            # 综合情绪评分
            sentiment_score = self._calculate_sentiment_score_simple(
                rank_change, turnover_rate, volume_ratio, price_change
            )
            
            # 转换为信号
            signal = self._score_to_signal(sentiment_score)
            confidence = abs(sentiment_score)
            
            # 生成报告
            report = f"排名变化: {rank_change:+d}, 换手率: {turnover_rate:.1f}%, 量比: {volume_ratio:.2f}"
            
            self.log(f"情绪分析完成: {signal}, 情绪评分: {sentiment_score:.2f}")
            
            return self._create_result(
                signal=signal,
                confidence=confidence,
                report=report,
                sentiment_score=sentiment_score,
                rank_change=rank_change
            )
            
        except Exception as e:
            self.log(f"情绪分析出错: {e}", "ERROR")
            return self._create_result('neutral', 0, f'分析出错: {str(e)}')
    
    def _calculate_sentiment_score_simple(
        self,
        rank_change: int,
        turnover_rate: float,
        volume_ratio: float,
        price_change: float
    ) -> float:
        """简化的情绪评分计算"""
        score = 0
        
        # 1. 排名变化贡献 (权重: 0.3)
        if rank_change > 10:
            score += 0.3
        elif rank_change > 5:
            score += 0.2
        elif rank_change < -10:
            score -= 0.3
        elif rank_change < -5:
            score -= 0.2
        
        # 2. 换手率和量比贡献 (权重: 0.3)
        if turnover_rate > 10 and volume_ratio > 2:
            score += 0.2  # 高度活跃
        elif turnover_rate > 5 and volume_ratio > 1.5:
            score += 0.1
        elif turnover_rate > 15:
            score -= 0.1  # 过度活跃风险
        
        # 3. 价格变化贡献 (权重: 0.4)
        if price_change > 5:
            score += 0.3
        elif price_change > 2:
            score += 0.15
        elif price_change < -5:
            score -= 0.3
        elif price_change < -2:
            score -= 0.15
        
        return max(-1, min(1, score))
    
    def _score_to_signal(self, score: float) -> str:
        """
        将情绪评分转换为信号
        
        Args:
            score: 情绪评分
            
        Returns:
            信号 (bullish/bearish/neutral)
        """
        if score > 0.3:
            return 'bullish'
        elif score < -0.3:
            return 'bearish'
        else:
            return 'neutral'
    
    def _generate_report(
        self,
        rank_analysis: Dict[str, Any],
        sentiment_analysis: Dict[str, Any],
        sentiment_score: float
    ) -> str:
        """
        生成情绪分析报告
        
        Returns:
            报告文本
        """
        report_lines = [
            "=== 情绪分析报告 ===",
            "",
            "排名分析:",
            f"  - 排名变化趋势: {rank_analysis['trend']}",
            f"  - 排名变化: {rank_analysis['rank_change']}",
            f"  - 平均排名: {rank_analysis['avg_rank']}",
            f"  - 最佳排名: {rank_analysis['best_rank']}",
            f"  - 最差排名: {rank_analysis['worst_rank']}",
            "",
            "情绪指标:",
            f"  - 换手率: {sentiment_analysis['turnover_rate']:.2f}% ({sentiment_analysis['turnover_signal']})",
            f"  - 量比: {sentiment_analysis['volume_ratio']:.2f}x ({sentiment_analysis['volume_signal']})",
            f"  - 热度等级: {sentiment_analysis['heat_level']}",
            "",
            f"综合情绪评分: {sentiment_score:.2f}",
        ]
        
        return "\n".join(report_lines)

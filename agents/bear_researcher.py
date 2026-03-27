# -*- coding: utf-8 -*-
"""
看跌研究员智能体
Bear Researcher Agent
"""

from typing import Dict, Any, List
from .base_agent import BaseAgent


class BearResearcher(BaseAgent):
    """
    看跌研究员
    聚合所有分析师的看跌论据，生成看跌观点
    """
    
    def __init__(self):
        super().__init__(
            name="BearResearcher",
            role="看跌研究员"
        )
    
    def analyze(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行看跌分析
        
        Args:
            context: 包含以下字段的上下文
                - analyst_reports: 各分析师的报告列表 (必需)
                - stock_code: 股票代码 (可选)
                
        Returns:
            看跌分析结果
        """
        if not self._validate_context(context, ['analyst_reports']):
            return self._create_result('neutral', 0, '缺少分析师报告')
        
        try:
            analyst_reports = context['analyst_reports']
            
            # 提取看跌论据
            bearish_arguments = self._extract_bearish_arguments(analyst_reports)
            
            # 计算看跌置信度
            bearish_confidence = self._calculate_bearish_confidence(analyst_reports)
            
            # 生成看跌观点
            bearish_view = self._generate_bearish_view(bearish_arguments)
            
            # 生成报告
            report = self._generate_report(bearish_arguments, bearish_confidence)
            
            self.log(f"看跌分析完成: 置信度 {bearish_confidence:.2%}")
            
            return self._create_result(
                signal='bearish',
                confidence=bearish_confidence,
                report=report,
                bearish_arguments=bearish_arguments,
                bearish_view=bearish_view
            )
            
        except Exception as e:
            self.log(f"看跌分析出错: {e}", "ERROR")
            return self._create_result('neutral', 0, f'分析出错: {str(e)}')
    
    def _extract_bearish_arguments(self, analyst_reports: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        从分析师报告中提取看跌论据
        
        Args:
            analyst_reports: 分析师报告列表
            
        Returns:
            看跌论据列表
        """
        arguments = []
        
        for report in analyst_reports:
            agent_name = report.get('agent_name', 'Unknown')
            signal = report.get('signal', 'neutral')
            confidence = report.get('confidence', 0)
            report_text = report.get('report', '')
            
            # 如果信号是看跌，提取论据
            if signal == 'bearish':
                argument = {
                    'source': agent_name,
                    'confidence': confidence,
                    'reasoning': self._extract_reasoning(report_text),
                    'indicators': self._extract_indicators(report)
                }
                arguments.append(argument)
        
        # 按置信度排序
        arguments.sort(key=lambda x: x['confidence'], reverse=True)
        
        return arguments
    
    def _extract_reasoning(self, report_text: str) -> str:
        """
        从报告文本中提取推理逻辑
        
        Args:
            report_text: 报告文本
            
        Returns:
            推理逻辑摘要
        """
        # 简单的文本提取，实际应用中可以使用NLP
        lines = report_text.split('\n')
        
        # 查找关键信息行
        key_lines = []
        for line in lines:
            if any(keyword in line for keyword in ['信号', '趋势', '下降', '弱势', '破位']):
                key_lines.append(line.strip())
        
        return ' '.join(key_lines[:3]) if key_lines else report_text[:100]
    
    def _extract_indicators(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """
        从报告中提取关键指标
        
        Args:
            report: 分析师报告
            
        Returns:
            关键指标字典
        """
        indicators = {}
        
        # 技术分析师的指标
        if 'indicators' in report:
            indicators['technical'] = report['indicators']
        
        # 情绪分析师的指标
        if 'sentiment_score' in report:
            indicators['sentiment'] = report['sentiment_score']
        
        # 新闻分析师的指标
        if 'news_sentiment_score' in report:
            indicators['news'] = report['news_sentiment_score']
        
        # 基本面分析师的指标
        if 'pe_analysis' in report:
            indicators['valuation'] = report['pe_analysis']
        
        return indicators
    
    def _calculate_bearish_confidence(self, analyst_reports: List[Dict[str, Any]]) -> float:
        """
        计算看跌置信度
        
        Args:
            analyst_reports: 分析师报告列表
            
        Returns:
            看跌置信度 (0-1)
        """
        if not analyst_reports:
            return 0
        
        bearish_count = 0
        total_confidence = 0
        
        for report in analyst_reports:
            signal = report.get('signal', 'neutral')
            confidence = report.get('confidence', 0)
            
            if signal == 'bearish':
                bearish_count += 1
                total_confidence += confidence
        
        if bearish_count == 0:
            return 0
        
        # 看跌置信度 = (看跌分析师数 / 总分析师数) * (平均置信度)
        analyst_ratio = bearish_count / len(analyst_reports)
        avg_confidence = total_confidence / bearish_count
        
        bearish_confidence = analyst_ratio * avg_confidence
        
        return min(1.0, bearish_confidence)
    
    def _generate_bearish_view(self, bearish_arguments: List[Dict[str, Any]]) -> str:
        """
        生成看跌观点
        
        Args:
            bearish_arguments: 看跌论据列表
            
        Returns:
            看跌观点文本
        """
        if not bearish_arguments:
            return "暂无看跌论据"
        
        view_lines = [
            "看跌观点:",
            ""
        ]
        
        for i, arg in enumerate(bearish_arguments[:3], 1):
            view_lines.append(f"{i}. {arg['source']} (置信度: {arg['confidence']:.0%})")
            view_lines.append(f"   {arg['reasoning']}")
        
        return "\n".join(view_lines)
    
    def _generate_report(
        self,
        bearish_arguments: List[Dict[str, Any]],
        bearish_confidence: float
    ) -> str:
        """
        生成看跌分析报告
        
        Returns:
            报告文本
        """
        report_lines = [
            "=== 看跌研究报告 ===",
            "",
            f"看跌置信度: {bearish_confidence:.0%}",
            f"看跌论据数量: {len(bearish_arguments)}",
            "",
            "主要看跌论据:",
        ]
        
        for i, arg in enumerate(bearish_arguments[:5], 1):
            report_lines.append(f"  {i}. {arg['source']}")
            report_lines.append(f"     置信度: {arg['confidence']:.0%}")
            report_lines.append(f"     理由: {arg['reasoning']}")
        
        if len(bearish_arguments) > 5:
            report_lines.append(f"  ... 还有 {len(bearish_arguments) - 5} 个论据")
        
        return "\n".join(report_lines)

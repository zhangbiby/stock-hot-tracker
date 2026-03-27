# -*- coding: utf-8 -*-
"""
基本面分析师智能体
Fundamental Analyst Agent
"""

from typing import Dict, Any
from .base_agent import BaseAgent


class FundamentalAnalyst(BaseAgent):
    """
    基本面分析师
    分析估值指标：PE、PB、板块相对估值等
    """
    
    def __init__(self):
        super().__init__(
            name="FundamentalAnalyst",
            role="基本面分析专家"
        )
        
        # 估值阈值
        self.pe_thresholds = {
            'undervalued': 15,      # PE < 15 低估
            'fair': 25,             # 15 <= PE < 25 合理
            'overvalued': 35        # PE >= 35 高估
        }
        
        self.pb_thresholds = {
            'undervalued': 1.5,
            'fair': 3.0,
            'overvalued': 5.0
        }
    
    def analyze(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行基本面分析
        
        Args:
            context: 包含以下字段的上下文
                - stock_code: 股票代码 (必需)
                - pe_ratio: PE比率 (可选)
                - pb_ratio: PB比率 (可选)
                - industry_pe: 行业平均PE (可选)
                - industry_pb: 行业平均PB (可选)
                - roe: 净资产收益率 (可选)
                - eps_growth: EPS增长率 (可选)
                
        Returns:
            基本面分析结果
        """
        if not self._validate_context(context, ['stock_code']):
            return self._create_result('neutral', 0, '缺少必要的基本面数据')
        
        try:
            # 分析PE估值
            pe_analysis = self._analyze_pe(
                context.get('pe_ratio'),
                context.get('industry_pe')
            )
            
            # 分析PB估值
            pb_analysis = self._analyze_pb(
                context.get('pb_ratio'),
                context.get('industry_pb')
            )
            
            # 分析盈利能力
            profitability = self._analyze_profitability(
                context.get('roe'),
                context.get('eps_growth')
            )
            
            # 综合基本面信号
            signal, confidence = self._aggregate_fundamental_signals(
                pe_analysis,
                pb_analysis,
                profitability
            )
            
            # 生成报告
            report = self._generate_report(
                pe_analysis,
                pb_analysis,
                profitability
            )
            
            self.log(f"基本面分析完成: {signal}, 置信度: {confidence:.2%}")
            
            return self._create_result(
                signal=signal,
                confidence=confidence,
                report=report,
                pe_analysis=pe_analysis,
                pb_analysis=pb_analysis,
                profitability=profitability
            )
            
        except Exception as e:
            self.log(f"基本面分析出错: {e}", "ERROR")
            return self._create_result('neutral', 0, f'分析出错: {str(e)}')
    
    def _analyze_pe(self, pe_ratio: float = None, industry_pe: float = None) -> Dict[str, Any]:
        """
        分析PE估值
        
        Args:
            pe_ratio: 股票PE比率
            industry_pe: 行业平均PE
            
        Returns:
            PE分析结果
        """
        result = {
            'pe_ratio': pe_ratio,
            'industry_pe': industry_pe,
            'valuation': 'unknown',
            'signal': 'neutral',
            'confidence': 0
        }
        
        if pe_ratio is None:
            return result
        
        # 绝对估值判断
        if pe_ratio < self.pe_thresholds['undervalued']:
            result['valuation'] = 'undervalued'
            result['signal'] = 'bullish'
            result['confidence'] = 0.6
        elif pe_ratio < self.pe_thresholds['fair']:
            result['valuation'] = 'fair'
            result['signal'] = 'neutral'
            result['confidence'] = 0.3
        elif pe_ratio < self.pe_thresholds['overvalued']:
            result['valuation'] = 'slightly_overvalued'
            result['signal'] = 'bearish'
            result['confidence'] = 0.4
        else:
            result['valuation'] = 'overvalued'
            result['signal'] = 'bearish'
            result['confidence'] = 0.7
        
        # 相对估值判断
        if industry_pe and pe_ratio < industry_pe * 0.8:
            result['relative_valuation'] = 'below_industry'
            result['signal'] = 'bullish'
            result['confidence'] = max(result['confidence'], 0.5)
        elif industry_pe and pe_ratio > industry_pe * 1.2:
            result['relative_valuation'] = 'above_industry'
            result['signal'] = 'bearish'
            result['confidence'] = max(result['confidence'], 0.5)
        else:
            result['relative_valuation'] = 'in_line_with_industry'
        
        return result
    
    def _analyze_pb(self, pb_ratio: float = None, industry_pb: float = None) -> Dict[str, Any]:
        """
        分析PB估值
        
        Args:
            pb_ratio: 股票PB比率
            industry_pb: 行业平均PB
            
        Returns:
            PB分析结果
        """
        result = {
            'pb_ratio': pb_ratio,
            'industry_pb': industry_pb,
            'valuation': 'unknown',
            'signal': 'neutral',
            'confidence': 0
        }
        
        if pb_ratio is None:
            return result
        
        # 绝对估值判断
        if pb_ratio < self.pb_thresholds['undervalued']:
            result['valuation'] = 'undervalued'
            result['signal'] = 'bullish'
            result['confidence'] = 0.5
        elif pb_ratio < self.pb_thresholds['fair']:
            result['valuation'] = 'fair'
            result['signal'] = 'neutral'
            result['confidence'] = 0.3
        elif pb_ratio < self.pb_thresholds['overvalued']:
            result['valuation'] = 'slightly_overvalued'
            result['signal'] = 'bearish'
            result['confidence'] = 0.4
        else:
            result['valuation'] = 'overvalued'
            result['signal'] = 'bearish'
            result['confidence'] = 0.6
        
        # 相对估值判断
        if industry_pb and pb_ratio < industry_pb * 0.8:
            result['relative_valuation'] = 'below_industry'
            result['signal'] = 'bullish'
            result['confidence'] = max(result['confidence'], 0.4)
        elif industry_pb and pb_ratio > industry_pb * 1.2:
            result['relative_valuation'] = 'above_industry'
            result['signal'] = 'bearish'
            result['confidence'] = max(result['confidence'], 0.4)
        else:
            result['relative_valuation'] = 'in_line_with_industry'
        
        return result
    
    def _analyze_profitability(self, roe: float = None, eps_growth: float = None) -> Dict[str, Any]:
        """
        分析盈利能力
        
        Args:
            roe: 净资产收益率
            eps_growth: EPS增长率
            
        Returns:
            盈利能力分析结果
        """
        result = {
            'roe': roe,
            'eps_growth': eps_growth,
            'signal': 'neutral',
            'confidence': 0
        }
        
        signals = []
        
        # ROE分析
        if roe is not None:
            if roe > 15:
                result['roe_level'] = 'excellent'
                signals.append(('bullish', 0.6))
            elif roe > 10:
                result['roe_level'] = 'good'
                signals.append(('bullish', 0.4))
            elif roe > 5:
                result['roe_level'] = 'fair'
                signals.append(('neutral', 0.2))
            else:
                result['roe_level'] = 'poor'
                signals.append(('bearish', 0.4))
        
        # EPS增长率分析
        if eps_growth is not None:
            if eps_growth > 20:
                result['eps_growth_level'] = 'high'
                signals.append(('bullish', 0.7))
            elif eps_growth > 10:
                result['eps_growth_level'] = 'moderate'
                signals.append(('bullish', 0.5))
            elif eps_growth > 0:
                result['eps_growth_level'] = 'low'
                signals.append(('neutral', 0.2))
            else:
                result['eps_growth_level'] = 'negative'
                signals.append(('bearish', 0.5))
        
        # 聚合信号
        if signals:
            bullish_score = sum(conf for sig, conf in signals if sig == 'bullish')
            bearish_score = sum(conf for sig, conf in signals if sig == 'bearish')
            
            if bullish_score > bearish_score:
                result['signal'] = 'bullish'
                result['confidence'] = bullish_score / len(signals)
            elif bearish_score > bullish_score:
                result['signal'] = 'bearish'
                result['confidence'] = bearish_score / len(signals)
            else:
                result['signal'] = 'neutral'
                result['confidence'] = 0.3
        
        return result
    
    def _aggregate_fundamental_signals(
        self,
        pe_analysis: Dict[str, Any],
        pb_analysis: Dict[str, Any],
        profitability: Dict[str, Any]
    ) -> tuple:
        """
        聚合基本面信号
        
        Returns:
            (综合信号, 置信度)
        """
        signals = []
        confidences = []
        
        # PE信号
        if pe_analysis['signal'] != 'neutral':
            signals.append(pe_analysis['signal'])
            confidences.append(pe_analysis['confidence'])
        
        # PB信号
        if pb_analysis['signal'] != 'neutral':
            signals.append(pb_analysis['signal'])
            confidences.append(pb_analysis['confidence'])
        
        # 盈利能力信号
        if profitability['signal'] != 'neutral':
            signals.append(profitability['signal'])
            confidences.append(profitability['confidence'])
        
        if not signals:
            return 'neutral', 0.3
        
        bullish_count = signals.count('bullish')
        bearish_count = signals.count('bearish')
        
        if bullish_count > bearish_count:
            final_signal = 'bullish'
        elif bearish_count > bullish_count:
            final_signal = 'bearish'
        else:
            final_signal = 'neutral'
        
        final_confidence = sum(confidences) / len(confidences) if confidences else 0.3
        
        return final_signal, final_confidence
    
    def _generate_report(
        self,
        pe_analysis: Dict[str, Any],
        pb_analysis: Dict[str, Any],
        profitability: Dict[str, Any]
    ) -> str:
        """
        生成基本面分析报告
        
        Returns:
            报告文本
        """
        report_lines = [
            "=== 基本面分析报告 ===",
            "",
            "PE估值分析:",
            f"  - PE比率: {pe_analysis['pe_ratio']}",
            f"  - 估值水平: {pe_analysis['valuation']}",
            f"  - 相对行业: {pe_analysis.get('relative_valuation', 'N/A')}",
            "",
            "PB估值分析:",
            f"  - PB比率: {pb_analysis['pb_ratio']}",
            f"  - 估值水平: {pb_analysis['valuation']}",
            f"  - 相对行业: {pb_analysis.get('relative_valuation', 'N/A')}",
            "",
            "盈利能力:",
            f"  - ROE: {profitability['roe']} ({profitability.get('roe_level', 'N/A')})",
            f"  - EPS增长率: {profitability['eps_growth']}% ({profitability.get('eps_growth_level', 'N/A')})",
        ]
        
        return "\n".join(report_lines)

# -*- coding: utf-8 -*-
"""
技术分析师智能体
Technical Analyst Agent
"""

from typing import Dict, Any, List, Optional
from .base_agent import BaseAgent
from indicators import calc_rsi, calc_macd, calc_bollinger_position, calc_ma_diff


class TechnicalAnalyst(BaseAgent):
    """
    技术分析师
    分析技术面信号：RSI、MACD、布林带、均线等
    """
    
    def __init__(self):
        super().__init__(
            name="TechnicalAnalyst",
            role="技术面分析专家"
        )
        
        # 技术指标阈值配置
        self.rsi_overbought = 70
        self.rsi_oversold = 30
        self.rsi_neutral_range = (40, 60)
    
    def analyze(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行技术分析
        
        Args:
            context: 包含以下字段的上下文
                - prices: 收盘价序列 (必需)
                - high_prices: 最高价序列 (可选)
                - low_prices: 最低价序列 (可选)
                - current_price: 当前价格 (可选)
                
        Returns:
            技术分析结果
        """
        # 验证必要数据
        if not self._validate_context(context, ['prices']):
            return self._create_result('neutral', 0, '缺少必要的价格数据')
        
        prices = context['prices']
        if len(prices) < 20:
            return self._create_result('neutral', 0, '数据不足，无法进行技术分析')
        
        try:
            # 计算技术指标
            indicators = {}
            
            # 1. RSI
            indicators['rsi'] = calc_rsi(prices)
            
            # 2. MACD
            indicators['macd'] = calc_macd(prices)
            
            # 3. 布林带位置
            indicators['bollinger'] = calc_bollinger_position(prices)
            
            # 4. 均线偏离
            indicators['ma5_diff'] = calc_ma_diff(prices, 5)
            indicators['ma20_diff'] = calc_ma_diff(prices, 20)
            
            # 分析各指标信号
            signals = []
            confidences = []
            
            # 1. RSI分析
            rsi_signal, rsi_conf = self._analyze_rsi(indicators['rsi'])
            signals.append(rsi_signal)
            confidences.append(rsi_conf)
            
            # 2. MACD分析
            macd_signal, macd_conf = self._analyze_macd_value(indicators['macd'])
            signals.append(macd_signal)
            confidences.append(macd_conf)
            
            # 3. 布林带分析
            bb_signal, bb_conf = self._analyze_bollinger_position(indicators['bollinger'])
            signals.append(bb_signal)
            confidences.append(bb_conf)
            
            # 4. 均线分析
            ma_signal, ma_conf = self._analyze_ma_diff(
                indicators['ma5_diff'],
                indicators['ma20_diff']
            )
            signals.append(ma_signal)
            confidences.append(ma_conf)
            
            # 综合信号
            final_signal = self._aggregate_signals(signals)
            final_confidence = sum(confidences) / len(confidences)
            
            # 生成报告
            report = self._generate_report(indicators, signals)
            
            self.log(f"技术分析完成: {final_signal}, 置信度: {final_confidence:.2%}")
            
            return self._create_result(
                signal=final_signal,
                confidence=final_confidence,
                report=report,
                indicators=indicators,
                signals_breakdown=dict(zip(
                    ['RSI', 'MACD', 'BollingerBands', 'MovingAverages'],
                    signals
                ))
            )
            
        except Exception as e:
            self.log(f"技术分析出错: {e}", "ERROR")
            return self._create_result('neutral', 0, f'分析出错: {str(e)}')
    
    def _analyze_rsi(self, rsi: float) -> tuple:
        """
        分析RSI指标
        
        Returns:
            (信号, 置信度)
        """
        if rsi is None:
            return 'neutral', 0.0
        if rsi > self.rsi_overbought:
            return 'bearish', 0.7  # 超买
        elif rsi < self.rsi_oversold:
            return 'bullish', 0.7  # 超卖
        elif rsi > self.rsi_neutral_range[1]:
            return 'bearish', 0.4  # 偏弱
        elif rsi < self.rsi_neutral_range[0]:
            return 'bullish', 0.4  # 偏强
        else:
            return 'neutral', 0.3  # 中性
    
    def _analyze_macd_value(self, macd_value: Optional[float]) -> tuple:
        """
        分析MACD值
        
        Returns:
            (信号, 置信度)
        """
        if macd_value is None:
            return 'neutral', 0.0
        if macd_value > 0.01:
            return 'bullish', 0.6
        elif macd_value < -0.01:
            return 'bearish', 0.6
        else:
            return 'neutral', 0.4
    
    def _analyze_bollinger_position(self, bb_pos: Optional[float]) -> tuple:
        """
        分析布林带位置
        
        Returns:
            (信号, 置信度)
        """
        if bb_pos is None:
            return 'neutral', 0.0
        # bb_pos: 0=下轨, 0.5=中轨, 1=上轨
        if bb_pos > 0.8:
            return 'bearish', 0.5  # 接近上轨
        elif bb_pos < 0.2:
            return 'bullish', 0.5  # 接近下轨
        else:
            return 'neutral', 0.3
    
    def _analyze_ma_diff(self, ma5_diff: Optional[float], ma20_diff: Optional[float]) -> tuple:
        """
        分析均线偏离
        
        Returns:
            (信号, 置信度)
        """
        signals = []
        confidences = []
        
        if ma5_diff is not None:
            if ma5_diff > 2:
                signals.append('bullish')
                confidences.append(0.4)
            elif ma5_diff < -2:
                signals.append('bearish')
                confidences.append(0.4)
            else:
                signals.append('neutral')
                confidences.append(0.3)
        
        if ma20_diff is not None:
            if ma20_diff > 5:
                signals.append('bullish')
                confidences.append(0.5)
            elif ma20_diff < -5:
                signals.append('bearish')
                confidences.append(0.5)
            else:
                signals.append('neutral')
                confidences.append(0.3)
        
        if not signals:
            return 'neutral', 0.0
        
        return self._aggregate_signals(signals), sum(confidences) / len(confidences)
        
        if total == 0:
            return 'neutral', 0.2
        
        # 价格在所有均线上方 -> 看涨
        if above_count == total:
            return 'bullish', 0.7
        # 价格在所有均线下方 -> 看跌
        elif below_count == total:
            return 'bearish', 0.7
        # 混合 -> 中性
        else:
            ratio = above_count / total
            if ratio > 0.7:
                return 'bullish', 0.5
            elif ratio < 0.3:
                return 'bearish', 0.5
            else:
                return 'neutral', 0.4
    
    def _aggregate_signals(self, signals: List[str]) -> str:
        """
        聚合多个信号
        
        Args:
            signals: 信号列表
            
        Returns:
            聚合后的信号
        """
        bullish_count = signals.count('bullish')
        bearish_count = signals.count('bearish')
        
        if bullish_count > bearish_count:
            return 'bullish'
        elif bearish_count > bullish_count:
            return 'bearish'
        else:
            return 'neutral'
    
    def _generate_report(self, indicators: Dict[str, Any], signals: List[str]) -> str:
        """
        生成技术分析报告
        
        Returns:
            报告文本
        """
        report_lines = [
            "=== 技术分析报告 ===",
            "",
            f"RSI指标: {indicators['rsi']:.2f}",
            f"MACD: {indicators['macd']['macd']:.4f}, 信号线: {indicators['macd']['signal']:.4f}",
            f"布林带: 上轨{indicators['bollinger']['upper']:.2f}, 中轨{indicators['bollinger']['middle']:.2f}, 下轨{indicators['bollinger']['lower']:.2f}",
            f"均线: MA5={indicators['ma'].get('ma5')}, MA10={indicators['ma'].get('ma10')}, MA20={indicators['ma'].get('ma20')}",
            "",
            f"综合信号: {signals}",
        ]
        
        return "\n".join(report_lines)

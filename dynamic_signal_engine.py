#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
动态权重信号引擎 v4.0
集成市场状态检测、资金流因子、决策透明化
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

# 导入原有模块
from history_store import (
    get_prev_rank, get_stock_history,
    get_industry_stocks, save_snapshot,
    get_latest_snapshot, init_storage,
    get_price_history
)
from portfolio import Portfolio
from indicators import add_technical_indicators, get_indicator_features

# 导入新模块
try:
    from market_state import MarketStateDetector, MarketState
    MARKET_STATE_AVAILABLE = True
except ImportError:
    MARKET_STATE_AVAILABLE = False

try:
    from fetch_northbound import get_northbound_factor
    NORTHBOUND_AVAILABLE = True
except ImportError:
    NORTHBOUND_AVAILABLE = False

try:
    from fetch_dragon_tiger import get_dragon_tiger_factor
    DRAGON_TIGER_AVAILABLE = True
except ImportError:
    DRAGON_TIGER_AVAILABLE = False

try:
    from fetch_industry_flow import get_industry_factor
    INDUSTRY_FLOW_AVAILABLE = True
except ImportError:
    INDUSTRY_FLOW_AVAILABLE = False

try:
    from agents import Orchestrator
    from memory import MemoryStore
    MULTI_AGENT_AVAILABLE = True
except ImportError:
    MULTI_AGENT_AVAILABLE = False

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"


class DynamicSignalEngine:
    """
    动态权重信号引擎
    
    特性：
    1. 根据市场状态动态调整因子权重
    2. 集成北向资金、龙虎榜、行业资金流因子
    3. 决策过程完全透明化
    4. 支持多智能体分析
    """
    
    def __init__(self, use_dynamic_weights: bool = True):
        self.use_dynamic_weights = use_dynamic_weights
        
        # 初始化市场状态检测器
        if MARKET_STATE_AVAILABLE and use_dynamic_weights:
            self.state_detector = MarketStateDetector()
            self.current_state = self.state_detector.detect()
            self.factor_weights = self.state_detector.get_factor_weights(self.current_state)
        else:
            self.state_detector = None
            self.current_state = None
            # 默认权重
            self.factor_weights = {
                'volume_price': 0.20,
                'rank_trend': 0.20,
                'technical': 0.20,
                'capital_flow': 0.15,
                'industry': 0.15,
                'sentiment': 0.10,
                'risk': 0.00
            }
        
        # 多智能体系统
        if MULTI_AGENT_AVAILABLE:
            self.orchestrator = Orchestrator()
        else:
            self.orchestrator = None
    
    def calculate_signal(self, stock: dict) -> dict:
        """
        计算股票信号（完全透明化版本）
        
        Returns:
            {
                'code': '000001',
                'name': '平安银行',
                'signal': 'Buy',
                'score': 65,
                'strength': 3,
                'up_proba': 0.65,
                'factor_scores': {
                    'volume_price': {'score': 70, 'weight': 0.20, 'details': [...]},
                    'rank_trend': {'score': 60, 'weight': 0.20, 'details': [...]},
                    ...
                },
                'capital_flow': {
                    'northbound': {'score': 75, 'details': [...]},
                    'dragon_tiger': {'score': 50, 'details': [...]},
                    'industry': {'score': 80, 'details': [...]}
                },
                'reasons': [...],
                'risks': [...],
                'suggestions': {
                    'entry_price': 10.50,
                    'stop_loss': 10.20,
                    'take_profit': 11.00,
                    'position_size': 0.20
                }
            }
        """
        code = stock.get('code', '')
        name = stock.get('name', '')
        
        # 初始化因子得分详情
        factor_details = {}
        all_reasons = []
        all_risks = []
        
        # 1. 量价因子 (20%)
        vp_score, vp_details, vp_reasons, vp_risks = self._calculate_volume_price_factor(stock)
        factor_details['volume_price'] = {
            'score': vp_score,
            'weight': self.factor_weights['volume_price'],
            'weighted_score': vp_score * self.factor_weights['volume_price'],
            'details': vp_details
        }
        all_reasons.extend(vp_reasons)
        all_risks.extend(vp_risks)
        
        # 2. 排名趋势因子 (20%)
        rt_score, rt_details, rt_reasons, rt_risks = self._calculate_rank_trend_factor(stock)
        factor_details['rank_trend'] = {
            'score': rt_score,
            'weight': self.factor_weights['rank_trend'],
            'weighted_score': rt_score * self.factor_weights['rank_trend'],
            'details': rt_details
        }
        all_reasons.extend(rt_reasons)
        all_risks.extend(rt_risks)
        
        # 3. 技术指标因子 (20%)
        tech_score, tech_details, tech_reasons, tech_risks = self._calculate_technical_factor(stock)
        factor_details['technical'] = {
            'score': tech_score,
            'weight': self.factor_weights['technical'],
            'weighted_score': tech_score * self.factor_weights['technical'],
            'details': tech_details
        }
        all_reasons.extend(tech_reasons)
        all_risks.extend(tech_risks)
        
        # 4. 资金流因子 (15%)
        cf_score, cf_details = self._calculate_capital_flow_factor(stock)
        factor_details['capital_flow'] = {
            'score': cf_score,
            'weight': self.factor_weights['capital_flow'],
            'weighted_score': cf_score * self.factor_weights['capital_flow'],
            'details': cf_details
        }
        
        # 5. 行业因子 (15%)
        ind_score, ind_details = self._calculate_industry_factor(stock)
        factor_details['industry'] = {
            'score': ind_score,
            'weight': self.factor_weights['industry'],
            'weighted_score': ind_score * self.factor_weights['industry'],
            'details': ind_details
        }
        
        # 6. 情绪因子 (10%)
        sent_score, sent_details = self._calculate_sentiment_factor(stock)
        factor_details['sentiment'] = {
            'score': sent_score,
            'weight': self.factor_weights['sentiment'],
            'weighted_score': sent_score * self.factor_weights['sentiment'],
            'details': sent_details
        }
        
        # 7. 风险因子 (动态)
        risk_score, risk_details, risk_warnings = self._calculate_risk_factor(stock)
        factor_details['risk'] = {
            'score': risk_score,
            'weight': self.factor_weights['risk'],
            'weighted_score': risk_score * self.factor_weights['risk'],
            'details': risk_details
        }
        all_risks.extend(risk_warnings)
        
        # 计算总分
        total_score = sum(
            factor_details[k]['weighted_score'] 
            for k in factor_details
        )
        
        # 确定信号
        signal, strength = self._score_to_signal(total_score)
        
        # 计算上涨概率
        up_proba = min(0.95, max(0.05, total_score / 100))
        
        # 生成交易建议
        suggestions = self._generate_suggestions(stock, total_score)
        
        return {
            'code': code,
            'name': name,
            'price': stock.get('price', 0),
            'change_pct': stock.get('change_pct', 0),
            'signal': signal,
            'score': round(total_score),
            'strength': strength,
            'up_proba': round(up_proba, 2),
            'factor_scores': factor_details,
            'market_state': self.current_state.value if self.current_state else 'unknown',
            'reasons': all_reasons[:5],  # 前5个理由
            'risks': all_risks[:5],  # 前5个风险
            'suggestions': suggestions,
            'timestamp': datetime.now().isoformat()
        }
    
    def _calculate_volume_price_factor(self, stock: dict) -> Tuple[int, dict, list, list]:
        """量价因子计算"""
        score = 30  # 基础分
        details = {}
        reasons = []
        risks = []
        
        change_pct = stock.get('change_pct', 0)
        volume_ratio = stock.get('volume_ratio', 1.0)
        turnover = stock.get('turnover_rate', 0)
        
        # 涨幅得分
        if 3 <= change_pct <= 7:
            score += 20
            details['change_bonus'] = 20
            reasons.append(f"涨幅适中({change_pct:.1f}%)，量价配合良好")
        elif 7 < change_pct <= 10:
            score += 15
            details['change_bonus'] = 15
            reasons.append(f"强势上涨({change_pct:.1f}%)")
        elif change_pct > 10:
            score += 10
            details['change_bonus'] = 10
            risks.append(f"涨幅过大({change_pct:.1f}%)，注意追高风险")
        elif change_pct < -3:
            score -= 15
            details['change_penalty'] = -15
            risks.append(f"下跌{abs(change_pct):.1f}%，趋势偏弱")
        
        # 量比得分
        if volume_ratio > 2:
            score += 15
            details['volume_bonus'] = 15
            reasons.append(f"放量({volume_ratio:.1f}倍)，资金关注")
        elif volume_ratio > 1.5:
            score += 10
            details['volume_bonus'] = 10
        elif volume_ratio < 0.8:
            score -= 5
            details['volume_penalty'] = -5
            risks.append("缩量，活跃度不足")
        
        # 换手率得分
        if 5 <= turnover <= 15:
            score += 10
            details['turnover_bonus'] = 10
        elif turnover > 20:
            score -= 10
            details['turnover_penalty'] = -10
            risks.append(f"换手率过高({turnover:.1f}%)，可能出货")
        
        details['raw_metrics'] = {
            'change_pct': change_pct,
            'volume_ratio': volume_ratio,
            'turnover': turnover
        }
        
        return min(100, max(0, score)), details, reasons, risks
    
    def _calculate_rank_trend_factor(self, stock: dict) -> Tuple[int, dict, list, list]:
        """排名趋势因子计算"""
        score = 30
        details = {}
        reasons = []
        risks = []
        
        code = stock.get('code', '')
        current_rank = stock.get('rank', 100)
        
        # 当前排名得分
        if current_rank <= 10:
            score += 25
            details['rank_bonus'] = 25
            reasons.append(f"人气排名TOP10(第{current_rank}位)")
        elif current_rank <= 30:
            score += 20
            details['rank_bonus'] = 20
            reasons.append(f"人气排名靠前(第{current_rank}位)")
        elif current_rank <= 50:
            score += 10
            details['rank_bonus'] = 10
        elif current_rank > 80:
            score -= 10
            details['rank_penalty'] = -10
            risks.append(f"人气排名靠后(第{current_rank}位)")
        
        # 排名变化
        prev_5m = get_prev_rank(code, minutes_ago=5)
        if prev_5m:
            delta = prev_5m - current_rank
            details['rank_change_5m'] = delta
            if delta >= 10:
                score += 15
                reasons.append(f"5分钟排名上升{delta}位，快速升温")
            elif delta >= 5:
                score += 8
                reasons.append(f"5分钟排名上升{delta}位")
            elif delta <= -10:
                score -= 15
                risks.append(f"5分钟排名下降{abs(delta)}位，快速降温")
        
        prev_1h = get_prev_rank(code, minutes_ago=60)
        if prev_1h:
            delta = prev_1h - current_rank
            details['rank_change_1h'] = delta
            if delta >= 20:
                score += 10
                reasons.append(f"1小时排名上升{delta}位")
        
        details['current_rank'] = current_rank
        
        return min(100, max(0, score)), details, reasons, risks
    
    def _calculate_technical_factor(self, stock: dict) -> Tuple[int, dict, list, list]:
        """技术指标因子计算"""
        score = 30
        details = {}
        reasons = []
        risks = []
        
        rsi = stock.get('rsi')
        macd = stock.get('macd')
        bb_position = stock.get('bb_position')
        
        # RSI得分
        if rsi is not None:
            details['rsi'] = rsi
            if 40 <= rsi <= 60:
                score += 15
                reasons.append(f"RSI适中({rsi:.1f})，趋势健康")
            elif 30 <= rsi < 40:
                score += 10
                reasons.append(f"RSI偏低({rsi:.1f})，可能反弹")
            elif rsi < 30:
                score += 5
                reasons.append(f"RSI超卖({rsi:.1f})，反弹机会")
            elif rsi > 70:
                score -= 15
                risks.append(f"RSI超买({rsi:.1f})，注意回调")
        
        # MACD得分
        if macd is not None:
            details['macd'] = macd
            if macd > 0:
                score += 10
                details['macd_signal'] = 'bullish'
                if macd > 0.02:
                    score += 5
                    reasons.append("MACD金叉，多头信号")
            else:
                details['macd_signal'] = 'bearish'
                score -= 5
        
        # 布林带得分
        if bb_position is not None:
            details['bb_position'] = bb_position
            if 0.3 <= bb_position <= 0.7:
                score += 10
                reasons.append("价格位于布林带中轨，趋势稳定")
            elif bb_position < 0.2:
                score += 5
                reasons.append("价格接近布林带下轨，支撑较强")
            elif bb_position > 0.8:
                score -= 10
                risks.append("价格接近布林带上轨，压力较大")
        
        return min(100, max(0, score)), details, reasons, risks
    
    def _calculate_capital_flow_factor(self, stock: dict) -> Tuple[int, dict]:
        """资金流因子计算"""
        score = 30
        details = {
            'northbound': {'available': False, 'score': 30},
            'dragon_tiger': {'available': False, 'score': 30},
        }
        
        code = stock.get('code', '')
        
        # 北向资金因子
        if NORTHBOUND_AVAILABLE:
            try:
                nb_factor = get_northbound_factor(code)
                details['northbound'] = {
                    'available': True,
                    'score': nb_factor,
                    'signal': 'positive' if nb_factor > 50 else 'neutral' if nb_factor > 30 else 'negative'
                }
                score += (nb_factor - 30) * 0.3
            except:
                pass
        
        # 龙虎榜因子
        if DRAGON_TIGER_AVAILABLE:
            try:
                dt_data = get_dragon_tiger_factor(code)
                details['dragon_tiger'] = {
                    'available': dt_data.get('is_on_list', False),
                    'score': dt_data.get('score', 30),
                    'famous_seats': dt_data.get('famous_seats', []),
                    'signal': dt_data.get('signal', 'neutral')
                }
                score += (dt_data.get('score', 30) - 30) * 0.4
            except:
                pass
        
        return min(100, max(0, score)), details
    
    def _calculate_industry_factor(self, stock: dict) -> Tuple[int, dict]:
        """行业因子计算"""
        score = 30
        details = {'available': False}
        
        if INDUSTRY_FLOW_AVAILABLE:
            try:
                ind_factor = get_industry_factor(
                    stock.get('code', ''),
                    stock.get('name', '')
                )
                details = {
                    'available': True,
                    'industry_name': ind_factor.get('industry_name', 'Unknown'),
                    'industry_rank': ind_factor.get('industry_rank', 0),
                    'industry_change': ind_factor.get('industry_change', 0),
                    'signal': ind_factor.get('signal', 'neutral')
                }
                score = ind_factor.get('score', 30)
            except:
                pass
        
        return score, details
    
    def _calculate_sentiment_factor(self, stock: dict) -> Tuple[int, dict]:
        """情绪因子计算"""
        score = 30
        details = {}
        
        # 基于排名变化的情绪
        rank = stock.get('rank', 100)
        if rank <= 20:
            score += 20
            details['sentiment'] = 'very_positive'
        elif rank <= 50:
            score += 10
            details['sentiment'] = 'positive'
        elif rank <= 80:
            score += 0
            details['sentiment'] = 'neutral'
        else:
            score -= 10
            details['sentiment'] = 'negative'
        
        return score, details
    
    def _calculate_risk_factor(self, stock: dict) -> Tuple[int, dict, list]:
        """风险因子计算"""
        score = 50  # 风险因子基础分高
        details = {}
        warnings = []
        
        change_pct = stock.get('change_pct', 0)
        turnover = stock.get('turnover_rate', 0)
        pe = stock.get('pe_ratio', 0)
        
        # 涨幅风险
        if change_pct > 10:
            score -= 20
            details['change_risk'] = -20
            warnings.append(f"单日涨幅{change_pct:.1f}%，追高风险")
        elif change_pct > 7:
            score -= 10
            details['change_risk'] = -10
        
        # 换手率风险
        if turnover > 25:
            score -= 15
            details['turnover_risk'] = -15
            warnings.append(f"换手率{turnover:.1f}%，异常活跃")
        
        # 估值风险
        if pe > 100 or pe < 0:
            score -= 10
            details['pe_risk'] = -10
            warnings.append("估值过高或为负，注意风险")
        
        return score, details, warnings
    
    def _score_to_signal(self, score: float) -> Tuple[str, int]:
        """分数转换为信号"""
        if score >= 70:
            return 'Strong Buy', 5
        elif score >= 55:
            return 'Buy', 4
        elif score >= 40:
            return 'Hold', 3
        elif score >= 25:
            return 'Caution', 2
        else:
            return 'Risk', 1
    
    def _generate_suggestions(self, stock: dict, score: float) -> dict:
        """生成交易建议"""
        price = stock.get('price', 0)
        change_pct = stock.get('change_pct', 0)
        
        # 止损位：买入价下浮3%或当日最低价
        stop_loss = price * 0.97
        
        # 止盈位
        if score >= 70:
            take_profit_1 = price * 1.05
            take_profit_2 = price * 1.10
        elif score >= 55:
            take_profit_1 = price * 1.03
            take_profit_2 = price * 1.05
        else:
            take_profit_1 = price * 1.02
            take_profit_2 = price * 1.03
        
        # 仓位建议
        if score >= 70:
            position = 0.25
        elif score >= 55:
            position = 0.20
        elif score >= 40:
            position = 0.10
        else:
            position = 0.0
        
        return {
            'entry_price': round(price, 2),
            'stop_loss': round(stop_loss, 2),
            'take_profit_1': round(take_profit_1, 2),
            'take_profit_2': round(take_profit_2, 2),
            'position_size': position,
            'max_holding_days': 3
        }


# 兼容旧接口
def calculate_signal_with_factors(stock: dict) -> dict:
    """新接口：带完整因子分析的信号计算"""
    engine = DynamicSignalEngine()
    return engine.calculate_signal(stock)


if __name__ == '__main__':
    # 测试
    print("=" * 60)
    print("Dynamic Signal Engine Test")
    print("=" * 60)
    
    test_stock = {
        'code': '000001',
        'name': '平安银行',
        'price': 10.5,
        'change_pct': 3.5,
        'rank': 15,
        'turnover_rate': 8.5,
        'volume_ratio': 1.8,
        'rsi': 55,
        'macd': 0.02,
        'bb_position': 0.6,
        'pe_ratio': 8.5
    }
    
    engine = DynamicSignalEngine()
    result = engine.calculate_signal(test_stock)
    
    print(f"\nSignal: {result['signal']}")
    print(f"Score: {result['score']}")
    print(f"Probability: {result['up_proba']*100:.0f}%")
    print(f"\nFactor Scores:")
    for factor, data in result['factor_scores'].items():
        print(f"  {factor:15s}: {data['score']:3.0f} (weight: {data['weight']:.0%})")
    print(f"\nReasons: {result['reasons']}")
    print(f"Risks: {result['risks']}")
    print(f"\nSuggestions: {result['suggestions']}")
    
    print("\n" + "=" * 60)

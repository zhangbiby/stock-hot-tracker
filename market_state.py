#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
市场状态检测器
动态调整因子权重
"""

import json
import statistics
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List
from enum import Enum

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"


class MarketState(Enum):
    """市场状态枚举"""
    STRONG_BULL = "strong_bull"  # 强势牛市
    BULL = "bull"                # 牛市
    NEUTRAL = "neutral"          # 震荡
    BEAR = "bear"                # 熊市
    STRONG_BEAR = "strong_bear"  # 强势熊市


class MarketStateDetector:
    """市场状态检测器"""
    
    def __init__(self):
        self.state_weights = {
            MarketState.STRONG_BULL: {
                'volume_price': 0.30,
                'rank_trend': 0.25,
                'technical': 0.20,
                'capital_flow': 0.15,
                'sentiment': 0.10,
                'risk': 0.00
            },
            MarketState.BULL: {
                'volume_price': 0.25,
                'rank_trend': 0.25,
                'technical': 0.20,
                'capital_flow': 0.15,
                'sentiment': 0.10,
                'risk': 0.05
            },
            MarketState.NEUTRAL: {
                'volume_price': 0.20,
                'rank_trend': 0.20,
                'technical': 0.20,
                'capital_flow': 0.15,
                'sentiment': 0.15,
                'risk': 0.10
            },
            MarketState.BEAR: {
                'volume_price': 0.15,
                'rank_trend': 0.15,
                'technical': 0.20,
                'capital_flow': 0.10,
                'sentiment': 0.10,
                'risk': 0.30
            },
            MarketState.STRONG_BEAR: {
                'volume_price': 0.10,
                'rank_trend': 0.10,
                'technical': 0.15,
                'capital_flow': 0.05,
                'sentiment': 0.10,
                'risk': 0.50
            }
        }
    
    def detect(self, market_data: Dict = None) -> MarketState:
        """
        检测当前市场状态
        
        Args:
            market_data: 市场数据，包含指数信息
            
        Returns:
            MarketState 枚举值
        """
        if market_data is None:
            market_data = self._fetch_market_data()
        
        # 计算各项指标
        trend_score = self._calculate_trend_score(market_data)
        volatility_score = self._calculate_volatility_score(market_data)
        breadth_score = self._calculate_breadth_score(market_data)
        volume_score = self._calculate_volume_score(market_data)
        
        # 综合评分 (-100 到 +100)
        composite_score = (
            trend_score * 0.35 +
            volatility_score * 0.25 +
            breadth_score * 0.25 +
            volume_score * 0.15
        )
        
        # 确定状态
        if composite_score > 60:
            return MarketState.STRONG_BULL
        elif composite_score > 30:
            return MarketState.BULL
        elif composite_score > -30:
            return MarketState.NEUTRAL
        elif composite_score > -60:
            return MarketState.BEAR
        else:
            return MarketState.STRONG_BEAR
    
    def _fetch_market_data(self) -> Dict:
        """获取市场数据"""
        # 尝试从数据库获取
        try:
            from db_manager import db_manager
            # 获取上证指数最近20天数据
            sh_index = db_manager.get_price_history('000001', days=20)
            
            if sh_index:
                closes = [s['price'] for s in sh_index]
                return {
                    'closes': closes,
                    'volumes': [s.get('volume', 0) for s in sh_index],
                    'latest_price': closes[0] if closes else 0
                }
        except:
            pass
        
        # 默认数据
        return {
            'closes': [3000] * 20,
            'volumes': [1000000] * 20,
            'latest_price': 3000
        }
    
    def _calculate_trend_score(self, data: Dict) -> float:
        """计算趋势得分 (-100 to +100)"""
        closes = data.get('closes', [])
        if len(closes) < 20:
            return 0
        
        # 计算均线
        ma5 = statistics.mean(closes[:5])
        ma10 = statistics.mean(closes[:10])
        ma20 = statistics.mean(closes[:20])
        
        # 趋势强度
        score = 0
        
        # 价格在均线上方
        if closes[0] > ma5:
            score += 20
        if closes[0] > ma10:
            score += 20
        if closes[0] > ma20:
            score += 20
        
        # 均线多头排列
        if ma5 > ma10 > ma20:
            score += 30
        elif ma5 < ma10 < ma20:
            score -= 30
        
        # 20日涨跌幅
        change_20d = (closes[0] - closes[-1]) / closes[-1] * 100
        if change_20d > 10:
            score += 10
        elif change_20d < -10:
            score -= 10
        
        return max(-100, min(100, score))
    
    def _calculate_volatility_score(self, data: Dict) -> float:
        """计算波动率得分 (-100 to +100)"""
        closes = data.get('closes', [])
        if len(closes) < 10:
            return 0
        
        # 计算日收益率
        returns = []
        for i in range(len(closes) - 1):
            r = (closes[i] - closes[i + 1]) / closes[i + 1]
            returns.append(r)
        
        if not returns:
            return 0
        
        # 计算波动率 (标准差)
        volatility = statistics.stdev(returns) * 100  # 转换为百分比
        
        # 波动率评分
        # 低波动率 = 市场稳定 = 中性偏正面
        # 高波动率 = 市场动荡 = 负面
        if volatility < 1.0:
            return 20  # 低波动，稳定
        elif volatility < 2.0:
            return 0   # 正常波动
        elif volatility < 3.0:
            return -20  # 较高波动
        else:
            return -40  # 高波动，动荡
    
    def _calculate_breadth_score(self, data: Dict) -> float:
        """计算市场广度得分 (-100 to +100)"""
        # 简化：使用涨跌停家数比
        # 实际应该查询全市场涨跌家数
        
        # 从行业数据推断
        try:
            from fetch_industry_flow import fetch_industry_capital_flow
            industries = fetch_industry_capital_flow()
            
            if industries:
                up_count = sum(1 for i in industries if i['change_pct'] > 0)
                down_count = sum(1 for i in industries if i['change_pct'] < 0)
                total = len(industries)
                
                if total > 0:
                    ratio = (up_count - down_count) / total
                    return ratio * 100
        except:
            pass
        
        return 0
    
    def _calculate_volume_score(self, data: Dict) -> float:
        """计算成交量得分 (-100 to +100)"""
        volumes = data.get('volumes', [])
        if len(volumes) < 10:
            return 0
        
        # 计算均量
        avg_volume = statistics.mean(volumes)
        recent_volume = statistics.mean(volumes[:3])
        
        # 量比
        if avg_volume > 0:
            volume_ratio = recent_volume / avg_volume
            
            if volume_ratio > 1.5:
                return 30  # 放量，活跃
            elif volume_ratio > 1.2:
                return 15
            elif volume_ratio > 0.8:
                return 0   # 正常
            elif volume_ratio > 0.5:
                return -15
            else:
                return -30  # 缩量，低迷
        
        return 0
    
    def get_factor_weights(self, state: MarketState = None) -> Dict[str, float]:
        """
        获取因子权重
        
        Args:
            state: 市场状态，默认自动检测
            
        Returns:
            因子权重字典
        """
        if state is None:
            state = self.detect()
        
        return self.state_weights.get(state, self.state_weights[MarketState.NEUTRAL])
    
    def get_state_description(self, state: MarketState) -> str:
        """获取状态描述"""
        descriptions = {
            MarketState.STRONG_BULL: "强势牛市 - 积极做多",
            MarketState.BULL: "牛市 - 趋势向上",
            MarketState.NEUTRAL: "震荡市 - 谨慎操作",
            MarketState.BEAR: "熊市 - 控制仓位",
            MarketState.STRONG_BEAR: "强势熊市 - 空仓观望"
        }
        return descriptions.get(state, "未知状态")
    
    def save_state(self, state: MarketState, details: Dict):
        """保存市场状态记录"""
        output_file = OUTPUT_DIR / 'market_state.json'
        
        record = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'state': state.value,
            'description': self.get_state_description(state),
            'weights': self.get_factor_weights(state),
            'details': details,
            'timestamp': datetime.now().isoformat()
        }
        
        # 加载现有记录
        history = []
        if output_file.exists():
            try:
                with open(output_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            except:
                history = []
        
        # 添加新记录
        history.append(record)
        
        # 只保留最近30天
        history = history[-30:]
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)


def main():
    """测试"""
    print("=" * 60)
    print("Market State Detector Test")
    print("=" * 60)
    
    detector = MarketStateDetector()
    
    # 检测当前状态
    state = detector.detect()
    print(f"\nCurrent State: {state.value}")
    print(f"Description: {detector.get_state_description(state)}")
    
    # 获取权重
    weights = detector.get_factor_weights(state)
    print(f"\nFactor Weights:")
    for factor, weight in weights.items():
        print(f"  {factor:15s}: {weight*100:5.1f}%")
    
    # 保存状态
    detector.save_state(state, {
        'trend_score': 50,
        'volatility_score': 20,
        'breadth_score': 30,
        'volume_score': 10
    })
    
    print("\n" + "=" * 60)


if __name__ == '__main__':
    main()

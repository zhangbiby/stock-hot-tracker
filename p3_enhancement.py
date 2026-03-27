#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P3 锦上添花模块
- 新闻情感分析
- 智能预警系统
- 高级可视化
"""

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Tuple
from collections import Counter

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"


class NewsSentimentAnalyzer:
    """新闻情感分析器"""
    
    def __init__(self):
        # 正面词库
        self.positive_words = [
            '涨停', '大涨', '飙升', '突破', '利好', '增长', '盈利', '超预期',
            '创新高', '强势', '反弹', '回升', '上涨', '买入', '增持', '推荐',
            '看好', '乐观', '积极', '改善', '提升', '扩大', '增加', '成功',
            '合作', '订单', '中标', '获批', '认证', '专利', '创新', '领先'
        ]
        
        # 负面词库
        self.negative_words = [
            '跌停', '大跌', '暴跌', '跌破', '利空', '亏损', '下滑', '不及预期',
            '创新低', '弱势', '下跌', '回落', '调整', '卖出', '减持', '回避',
            '看空', '悲观', '消极', '恶化', '下降', '缩减', '减少', '失败',
            '违规', '处罚', '调查', '诉讼', '退市', '风险', '警告', '警惕'
        ]
        
        # 程度副词
        self.intensifiers = {
            '大幅': 1.5, '剧烈': 1.5, '明显': 1.3, '显著': 1.3,
            '略微': 0.7, '轻微': 0.7, '稍有': 0.8, '基本': 0.9
        }
    
    def analyze(self, text: str) -> Dict:
        """
        分析单条新闻的情感
        
        Returns:
            {
                'sentiment': 'positive' | 'neutral' | 'negative',
                'score': 75,  # 0-100
                'confidence': 0.85,
                'keywords': ['涨停', '利好'],
                'intensity': 'strong' | 'moderate' | 'weak'
            }
        """
        if not text:
            return {'sentiment': 'neutral', 'score': 50, 'confidence': 0}
        
        text = text.lower()
        
        # 统计正负词
        pos_count = 0
        neg_count = 0
        found_keywords = []
        intensity_multiplier = 1.0
        
        # 检查程度副词
        for word, mult in self.intensifiers.items():
            if word in text:
                intensity_multiplier = max(intensity_multiplier, mult)
        
        # 统计正面词
        for word in self.positive_words:
            if word in text:
                pos_count += 1
                found_keywords.append(word)
        
        # 统计负面词
        for word in self.negative_words:
            if word in text:
                neg_count += 1
                found_keywords.append(word)
        
        # 计算得分
        total = pos_count + neg_count
        if total == 0:
            return {
                'sentiment': 'neutral',
                'score': 50,
                'confidence': 0.3,
                'keywords': [],
                'intensity': 'weak'
            }
        
        # 基础得分
        base_score = 50 + (pos_count - neg_count) * 10
        
        # 应用强度
        if pos_count > neg_count:
            score = min(100, base_score * intensity_multiplier)
        else:
            score = max(0, base_score / intensity_multiplier)
        
        # 确定情感
        if score >= 60:
            sentiment = 'positive'
        elif score <= 40:
            sentiment = 'negative'
        else:
            sentiment = 'neutral'
        
        # 确定强度
        if abs(score - 50) > 30:
            intensity = 'strong'
        elif abs(score - 50) > 15:
            intensity = 'moderate'
        else:
            intensity = 'weak'
        
        # 置信度
        confidence = min(0.95, 0.5 + total * 0.1)
        
        return {
            'sentiment': sentiment,
            'score': round(score),
            'confidence': round(confidence, 2),
            'keywords': found_keywords[:5],
            'intensity': intensity
        }
    
    def analyze_batch(self, news_list: List[Dict]) -> Dict:
        """
        批量分析新闻
        
        Returns:
            {
                'overall_sentiment': 'positive',
                'average_score': 65,
                'positive_ratio': 0.6,
                'negative_ratio': 0.2,
                'neutral_ratio': 0.2,
                'hot_keywords': ['涨停', '利好'],
                'trend': 'improving' | 'stable' | 'worsening'
            }
        """
        if not news_list:
            return {
                'overall_sentiment': 'neutral',
                'average_score': 50,
                'positive_ratio': 0,
                'negative_ratio': 0,
                'neutral_ratio': 1,
                'hot_keywords': [],
                'trend': 'stable'
            }
        
        results = []
        all_keywords = []
        
        for news in news_list:
            text = news.get('title', '') + ' ' + news.get('content', '')
            result = self.analyze(text)
            results.append(result)
            all_keywords.extend(result['keywords'])
        
        # 统计
        scores = [r['score'] for r in results]
        avg_score = sum(scores) / len(scores)
        
        sentiments = [r['sentiment'] for r in results]
        positive_ratio = sentiments.count('positive') / len(sentiments)
        negative_ratio = sentiments.count('negative') / len(sentiments)
        neutral_ratio = sentiments.count('neutral') / len(sentiments)
        
        # 热门关键词
        keyword_counts = Counter(all_keywords)
        hot_keywords = [k for k, c in keyword_counts.most_common(5)]
        
        # 趋势判断
        if len(scores) >= 3:
            first_half = sum(scores[:len(scores)//2]) / (len(scores)//2)
            second_half = sum(scores[len(scores)//2:]) / (len(scores) - len(scores)//2)
            
            if second_half > first_half + 10:
                trend = 'improving'
            elif second_half < first_half - 10:
                trend = 'worsening'
            else:
                trend = 'stable'
        else:
            trend = 'stable'
        
        # 整体情感
        if positive_ratio > 0.5:
            overall = 'positive'
        elif negative_ratio > 0.5:
            overall = 'negative'
        else:
            overall = 'neutral'
        
        return {
            'overall_sentiment': overall,
            'average_score': round(avg_score),
            'positive_ratio': round(positive_ratio, 2),
            'negative_ratio': round(negative_ratio, 2),
            'neutral_ratio': round(neutral_ratio, 2),
            'hot_keywords': hot_keywords,
            'trend': trend,
            'news_count': len(news_list)
        }


class SmartAlertSystem:
    """智能预警系统"""
    
    def __init__(self):
        self.alerts = []
        self.alert_history = []
    
    def check_price_alert(self, stock: Dict, thresholds: Dict) -> List[Dict]:
        """
        检查价格预警
        
        Args:
            stock: 股票数据
            thresholds: {'upper': 11.0, 'lower': 9.5}
        """
        alerts = []
        price = stock.get('price', 0)
        code = stock.get('code', '')
        name = stock.get('name', '')
        
        upper = thresholds.get('upper')
        lower = thresholds.get('lower')
        
        if upper and price >= upper:
            alerts.append({
                'type': 'price_upper',
                'level': 'info',
                'code': code,
                'name': name,
                'message': f'{name}价格达到{price}，超过目标价{upper}',
                'timestamp': datetime.now().isoformat()
            })
        
        if lower and price <= lower:
            alerts.append({
                'type': 'price_lower',
                'level': 'warning',
                'code': code,
                'name': name,
                'message': f'{name}价格跌至{price}，跌破止损价{lower}',
                'timestamp': datetime.now().isoformat()
            })
        
        return alerts
    
    def check_signal_alert(self, stock: Dict, signal: Dict) -> List[Dict]:
        """检查信号预警"""
        alerts = []
        
        signal_type = signal.get('signal', '')
        score = signal.get('score', 0)
        
        # Strong Buy信号
        if signal_type == 'Strong Buy' and score >= 75:
            alerts.append({
                'type': 'strong_buy_signal',
                'level': 'opportunity',
                'code': stock.get('code'),
                'name': stock.get('name'),
                'message': f"强烈买入信号：{stock.get('name')}评分{score}",
                'timestamp': datetime.now().isoformat()
            })
        
        # Risk信号
        if signal_type == 'Risk':
            alerts.append({
                'type': 'risk_signal',
                'level': 'danger',
                'code': stock.get('code'),
                'name': stock.get('name'),
                'message': f"风险提示：{stock.get('name')}出现风险信号",
                'timestamp': datetime.now().isoformat()
            })
        
        return alerts
    
    def check_portfolio_alert(self, portfolio_analysis: Dict) -> List[Dict]:
        """检查组合预警"""
        alerts = []
        
        risk_level = portfolio_analysis.get('risk_level', 'low')
        
        if risk_level == 'high':
            alerts.append({
                'type': 'portfolio_risk',
                'level': 'warning',
                'message': '组合风险过高，建议减仓或分散投资',
                'details': portfolio_analysis.get('warnings', []),
                'timestamp': datetime.now().isoformat()
            })
        
        return alerts
    
    def get_active_alerts(self, hours: int = 24) -> List[Dict]:
        """获取活跃预警"""
        cutoff = datetime.now() - timedelta(hours=hours)
        
        active = []
        for alert in self.alerts:
            alert_time = datetime.fromisoformat(alert['timestamp'])
            if alert_time > cutoff:
                active.append(alert)
        
        return active


class AdvancedVisualization:
    """高级可视化辅助"""
    
    @staticmethod
    def generate_factor_radar_chart(factor_scores: Dict) -> str:
        """生成因子雷达图（使用Chart.js）"""
        
        factors = list(factor_scores.keys())
        scores = [factor_scores[f]['score'] for f in factors]
        
        # 转换为Chart.js配置
        chart_config = {
            'type': 'radar',
            'data': {
                'labels': factors,
                'datasets': [{
                    'label': 'Factor Scores',
                    'data': scores,
                    'backgroundColor': 'rgba(0, 212, 255, 0.2)',
                    'borderColor': 'rgba(0, 212, 255, 1)',
                    'borderWidth': 2
                }]
            },
            'options': {
                'scales': {
                    'r': {
                        'beginAtZero': True,
                        'max': 100
                    }
                }
            }
        }
        
        return json.dumps(chart_config)
    
    @staticmethod
    def generate_trend_chart(historical_data: List[Dict]) -> str:
        """生成趋势图配置"""
        dates = [d['date'] for d in historical_data]
        values = [d['value'] for d in historical_data]
        
        chart_config = {
            'type': 'line',
            'data': {
                'labels': dates,
                'datasets': [{
                    'label': 'Portfolio Value',
                    'data': values,
                    'borderColor': '#00d4ff',
                    'backgroundColor': 'rgba(0, 212, 255, 0.1)',
                    'fill': True,
                    'tension': 0.4
                }]
            },
            'options': {
                'responsive': True,
                'plugins': {
                    'legend': {'display': True}
                }
            }
        }
        
        return json.dumps(chart_config)


def main():
    """测试P3模块"""
    print("=" * 60)
    print("P3 Enhancement Test")
    print("=" * 60)
    
    # 测试新闻情感分析
    print("\n1. News Sentiment Analysis")
    analyzer = NewsSentimentAnalyzer()
    
    test_news = [
        {'title': '某股涨停，业绩大幅增长', 'content': '公司发布利好公告'},
        {'title': '市场回调，注意风险', 'content': '大盘下跌，谨慎操作'},
        {'title': '公司获得大额订单', 'content': '中标重大项目'},
    ]
    
    for news in test_news:
        result = analyzer.analyze(news['title'])
        print(f"  {news['title'][:20]}... -> {result['sentiment']} ({result['score']})")
    
    # 批量分析
    batch_result = analyzer.analyze_batch(test_news)
    print(f"\n  Overall: {batch_result['overall_sentiment']}")
    print(f"  Hot Keywords: {batch_result['hot_keywords']}")
    
    # 测试智能预警
    print("\n2. Smart Alert System")
    alert_system = SmartAlertSystem()
    
    test_stock = {'code': '000001', 'name': 'Test', 'price': 10.5}
    test_signal = {'signal': 'Strong Buy', 'score': 80}
    
    alerts = alert_system.check_signal_alert(test_stock, test_signal)
    for alert in alerts:
        print(f"  Alert: {alert['message']}")
    
    # 测试高级可视化
    print("\n3. Advanced Visualization")
    viz = AdvancedVisualization()
    
    factor_scores = {
        'volume_price': {'score': 75},
        'rank_trend': {'score': 60},
        'technical': {'score': 70}
    }
    
    chart_config = viz.generate_factor_radar_chart(factor_scores)
    print(f"  Generated chart config: {len(chart_config)} chars")
    
    print("\n" + "=" * 60)
    print("P3 Test Complete")
    print("=" * 60)


if __name__ == '__main__':
    main()

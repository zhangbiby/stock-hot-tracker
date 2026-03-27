# -*- coding: utf-8 -*-
"""
新闻分析师智能体
News Analyst Agent
"""

import json
import os
from typing import Dict, Any, List, Optional
from .base_agent import BaseAgent


class NewsAnalyst(BaseAgent):
    """
    新闻分析师
    分析相关新闻的情绪和影响
    """
    
    def __init__(self, news_file: str = "output/news_latest.json"):
        super().__init__(
            name="NewsAnalyst",
            role="新闻分析专家"
        )
        self.news_file = news_file
        
        # 关键词库
        self.positive_keywords = [
            '上涨', '增长', '利好', '突破', '创新', '合作', '融资',
            '收购', '重组', '扩张', '盈利', '业绩', '超预期', '强势'
        ]
        
        self.negative_keywords = [
            '下跌', '下降', '利空', '风险', '亏损', '破产', '退市',
            '调查', '处罚', '违规', '诉讼', '减持', '暴跌', '弱势'
        ]
    
    def analyze(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行新闻分析
        
        Args:
            context: 包含以下字段的上下文
                - stock_code: 股票代码 (必需)
                - stock_name: 股票名称 (可选)
                
        Returns:
            新闻分析结果
        """
        if not self._validate_context(context, ['stock_code']):
            return self._create_result('neutral', 0, '缺少必要的股票信息')
        
        try:
            stock_code = context['stock_code']
            stock_name = context.get('stock_name', '')
            
            # 读取最新新闻
            news_list = self._load_news()
            
            # 过滤相关新闻
            relevant_news = self._filter_relevant_news(
                news_list,
                stock_code,
                stock_name
            )
            
            if not relevant_news:
                return self._create_result(
                    'neutral',
                    0,
                    '暂无相关新闻',
                    news_count=0,
                    relevant_news=[]
                )
            
            # 分析新闻情绪
            sentiment_scores = []
            news_details = []
            
            for news in relevant_news:
                sentiment = self._analyze_news_sentiment(news)
                sentiment_scores.append(sentiment['score'])
                news_details.append({
                    'title': news.get('title', ''),
                    'source': news.get('source', ''),
                    'sentiment': sentiment['sentiment'],
                    'score': sentiment['score'],
                    'keywords': sentiment['keywords']
                })
            
            # 综合新闻信号
            avg_sentiment = sum(sentiment_scores) / len(sentiment_scores)
            signal = self._score_to_signal(avg_sentiment)
            confidence = min(0.8, len(relevant_news) * 0.2)  # 新闻越多，置信度越高
            
            # 生成报告
            report = self._generate_report(relevant_news, news_details, avg_sentiment)
            
            self.log(f"新闻分析完成: {signal}, 相关新闻数: {len(relevant_news)}")
            
            return self._create_result(
                signal=signal,
                confidence=confidence,
                report=report,
                news_sentiment_score=avg_sentiment,
                news_count=len(relevant_news),
                relevant_news=news_details
            )
            
        except Exception as e:
            self.log(f"新闻分析出错: {e}", "ERROR")
            return self._create_result('neutral', 0, f'分析出错: {str(e)}')
    
    def _load_news(self) -> List[Dict[str, Any]]:
        """
        加载最新新闻
        
        Returns:
            新闻列表
        """
        try:
            if not os.path.exists(self.news_file):
                self.log(f"新闻文件不存在: {self.news_file}", "WARNING")
                return []
            
            with open(self.news_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 支持两种格式
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and 'news' in data:
                return data['news']
            else:
                return []
                
        except Exception as e:
            self.log(f"加载新闻失败: {e}", "ERROR")
            return []
    
    def _filter_relevant_news(
        self,
        news_list: List[Dict[str, Any]],
        stock_code: str,
        stock_name: str
    ) -> List[Dict[str, Any]]:
        """
        过滤与股票相关的新闻
        
        Args:
            news_list: 新闻列表
            stock_code: 股票代码
            stock_name: 股票名称
            
        Returns:
            相关新闻列表
        """
        relevant = []
        
        for news in news_list:
            title = news.get('title', '').lower()
            content = news.get('content', '').lower()
            
            # 检查是否包含股票代码或名称
            if stock_code.lower() in title or stock_code.lower() in content:
                relevant.append(news)
            elif stock_name and stock_name.lower() in title:
                relevant.append(news)
        
        return relevant
    
    def _analyze_news_sentiment(self, news: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析单条新闻的情绪
        
        Args:
            news: 新闻数据
            
        Returns:
            情绪分析结果
        """
        title = news.get('title', '')
        content = news.get('content', '')
        text = f"{title} {content}".lower()
        
        # 计算正面和负面关键词数量
        positive_count = sum(1 for kw in self.positive_keywords if kw in text)
        negative_count = sum(1 for kw in self.negative_keywords if kw in text)
        
        # 计算情绪评分
        if positive_count + negative_count == 0:
            score = 0
            sentiment = 'neutral'
        else:
            score = (positive_count - negative_count) / (positive_count + negative_count)
            if score > 0.3:
                sentiment = 'positive'
            elif score < -0.3:
                sentiment = 'negative'
            else:
                sentiment = 'neutral'
        
        # 提取关键词
        found_keywords = []
        for kw in self.positive_keywords:
            if kw in text:
                found_keywords.append(('positive', kw))
        for kw in self.negative_keywords:
            if kw in text:
                found_keywords.append(('negative', kw))
        
        return {
            'score': score,
            'sentiment': sentiment,
            'keywords': found_keywords,
            'positive_count': positive_count,
            'negative_count': negative_count
        }
    
    def _score_to_signal(self, score: float) -> str:
        """
        将新闻情绪评分转换为信号
        
        Args:
            score: 情绪评分
            
        Returns:
            信号 (bullish/bearish/neutral)
        """
        if score > 0.2:
            return 'bullish'
        elif score < -0.2:
            return 'bearish'
        else:
            return 'neutral'
    
    def _generate_report(
        self,
        news_list: List[Dict[str, Any]],
        news_details: List[Dict[str, Any]],
        avg_sentiment: float
    ) -> str:
        """
        生成新闻分析报告
        
        Returns:
            报告文本
        """
        report_lines = [
            "=== 新闻分析报告 ===",
            "",
            f"相关新闻数量: {len(news_list)}",
            f"综合情绪评分: {avg_sentiment:.2f}",
            "",
            "新闻详情:",
        ]
        
        for i, detail in enumerate(news_details[:5], 1):  # 只显示前5条
            report_lines.append(f"  {i}. {detail['title']}")
            report_lines.append(f"     情绪: {detail['sentiment']} (评分: {detail['score']:.2f})")
            if detail['keywords']:
                keywords_str = ', '.join([f"{kw[1]}({kw[0]})" for kw in detail['keywords'][:3]])
                report_lines.append(f"     关键词: {keywords_str}")
        
        if len(news_list) > 5:
            report_lines.append(f"  ... 还有 {len(news_list) - 5} 条新闻")
        
        return "\n".join(report_lines)

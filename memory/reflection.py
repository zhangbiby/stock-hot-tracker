# -*- coding: utf-8 -*-
"""
反思系统
Reflection System
"""

import json
import os
from typing import Dict, List, Any
from datetime import datetime
import logging


class ReflectionSystem:
    """
    反思系统
    分析历史决策，提取经验教训，改进决策模型
    """
    
    def __init__(self, storage_dir: str = "memory/reflections"):
        """
        初始化反思系统
        
        Args:
            storage_dir: 存储目录
        """
        self.storage_dir = storage_dir
        self.logger = logging.getLogger("ReflectionSystem")
        
        # 确保目录存在
        os.makedirs(storage_dir, exist_ok=True)
    
    def analyze_decision_outcome(
        self,
        stock_code: str,
        decision: Dict[str, Any],
        outcome: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        分析决策结果
        
        Args:
            stock_code: 股票代码
            decision: 原始决策
            outcome: 决策结果
            
        Returns:
            分析结果
        """
        analysis = {
            'stock_code': stock_code,
            'decision_time': decision.get('timestamp'),
            'outcome_time': outcome.get('timestamp'),
            'signal': decision.get('signal'),
            'action': decision.get('action'),
            'target_price': decision.get('target_price'),
            'actual_price': outcome.get('actual_price'),
            'result': 'unknown'
        }
        
        # 判断决策是否成功
        if decision.get('action') == 'buy':
            if outcome.get('actual_price', 0) > decision.get('target_price', 0):
                analysis['result'] = 'success'
            else:
                analysis['result'] = 'failure'
        elif decision.get('action') == 'sell':
            if outcome.get('actual_price', 0) < decision.get('target_price', 0):
                analysis['result'] = 'success'
            else:
                analysis['result'] = 'failure'
        
        # 计算收益
        if decision.get('entry_price', 0) > 0:
            if decision.get('action') == 'buy':
                analysis['return'] = (outcome.get('actual_price', 0) - decision.get('entry_price', 0)) / decision.get('entry_price', 0)
            else:
                analysis['return'] = (decision.get('entry_price', 0) - outcome.get('actual_price', 0)) / decision.get('entry_price', 0)
        
        return analysis
    
    def extract_lessons(
        self,
        analyses: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        从多个决策分析中提取经验教训
        
        Args:
            analyses: 决策分析列表
            
        Returns:
            经验教训
        """
        if not analyses:
            return {}
        
        lessons = {
            'total_decisions': len(analyses),
            'successful_decisions': 0,
            'failed_decisions': 0,
            'success_rate': 0,
            'avg_return': 0,
            'best_return': 0,
            'worst_return': 0,
            'insights': []
        }
        
        returns = []
        
        for analysis in analyses:
            if analysis.get('result') == 'success':
                lessons['successful_decisions'] += 1
            elif analysis.get('result') == 'failure':
                lessons['failed_decisions'] += 1
            
            if 'return' in analysis:
                returns.append(analysis['return'])
        
        # 计算统计指标
        if lessons['total_decisions'] > 0:
            lessons['success_rate'] = lessons['successful_decisions'] / lessons['total_decisions']
        
        if returns:
            lessons['avg_return'] = sum(returns) / len(returns)
            lessons['best_return'] = max(returns)
            lessons['worst_return'] = min(returns)
        
        # 提取洞察
        lessons['insights'] = self._generate_insights(lessons, analyses)
        
        return lessons
    
    def _generate_insights(
        self,
        lessons: Dict[str, Any],
        analyses: List[Dict[str, Any]]
    ) -> List[str]:
        """
        生成洞察
        
        Args:
            lessons: 经验教训
            analyses: 决策分析列表
            
        Returns:
            洞察列表
        """
        insights = []
        
        # 成功率洞察
        if lessons['success_rate'] > 0.7:
            insights.append("决策成功率较高，当前策略有效")
        elif lessons['success_rate'] < 0.3:
            insights.append("决策成功率较低，需要改进策略")
        
        # 收益洞察
        if lessons['avg_return'] > 0.05:
            insights.append("平均收益率为正，策略盈利能力良好")
        elif lessons['avg_return'] < -0.05:
            insights.append("平均收益率为负，需要优化风险管理")
        
        # 信号分析
        bullish_analyses = [a for a in analyses if a.get('signal') == 'bullish']
        bearish_analyses = [a for a in analyses if a.get('signal') == 'bearish']
        
        if bullish_analyses:
            bullish_success = sum(1 for a in bullish_analyses if a.get('result') == 'success')
            bullish_rate = bullish_success / len(bullish_analyses)
            if bullish_rate > 0.6:
                insights.append("看涨信号准确度较高")
            elif bullish_rate < 0.4:
                insights.append("看涨信号准确度较低，需要改进")
        
        if bearish_analyses:
            bearish_success = sum(1 for a in bearish_analyses if a.get('result') == 'success')
            bearish_rate = bearish_success / len(bearish_analyses)
            if bearish_rate > 0.6:
                insights.append("看跌信号准确度较高")
            elif bearish_rate < 0.4:
                insights.append("看跌信号准确度较低，需要改进")
        
        return insights
    
    def save_reflection(
        self,
        stock_code: str,
        reflection: Dict[str, Any]
    ) -> bool:
        """
        保存反思记录
        
        Args:
            stock_code: 股票代码
            reflection: 反思数据
            
        Returns:
            是否保存成功
        """
        try:
            file_path = os.path.join(self.storage_dir, f"{stock_code}_reflections.json")
            
            # 读取现有反思
            reflections = []
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    reflections = json.load(f)
            
            # 添加时间戳
            if 'timestamp' not in reflection:
                reflection['timestamp'] = datetime.now().isoformat()
            
            # 追加新反思
            reflections.append(reflection)
            
            # 只保留最近100条
            if len(reflections) > 100:
                reflections = reflections[-100:]
            
            # 保存
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(reflections, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"反思记录已保存: {stock_code}")
            return True
            
        except Exception as e:
            self.logger.error(f"保存反思失败: {stock_code}, 错误: {e}")
            return False
    
    def get_reflections(
        self,
        stock_code: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        获取反思历史
        
        Args:
            stock_code: 股票代码
            limit: 返回数量限制
            
        Returns:
            反思列表
        """
        try:
            file_path = os.path.join(self.storage_dir, f"{stock_code}_reflections.json")
            
            if not os.path.exists(file_path):
                return []
            
            with open(file_path, 'r', encoding='utf-8') as f:
                reflections = json.load(f)
            
            # 返回最近的N条
            return reflections[-limit:] if reflections else []
            
        except Exception as e:
            self.logger.error(f"读取反思历史失败: {stock_code}, 错误: {e}")
            return []

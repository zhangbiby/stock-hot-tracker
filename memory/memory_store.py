# -*- coding: utf-8 -*-
"""
记忆存储模块
Memory Store Module
"""

import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging


class MemoryStore:
    """
    记忆存储
    使用文件存储（JSON格式），支持存储决策记录和检索相似历史案例
    """
    
    def __init__(self, storage_dir: str = "memory/storage"):
        """
        初始化记忆存储
        
        Args:
            storage_dir: 存储目录
        """
        self.storage_dir = storage_dir
        self.logger = logging.getLogger("MemoryStore")
        
        # 确保目录存在
        os.makedirs(storage_dir, exist_ok=True)
        
        # 内存缓存
        self._cache: Dict[str, List[Dict]] = {}
    
    def save_decision(
        self,
        stock_code: str,
        decision: Dict[str, Any]
    ) -> bool:
        """
        保存决策记录
        
        Args:
            stock_code: 股票代码
            decision: 决策数据
            
        Returns:
            是否保存成功
        """
        try:
            file_path = self._get_decision_file(stock_code)
            
            # 读取现有决策
            decisions = []
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    decisions = json.load(f)
            
            # 添加时间戳
            if 'timestamp' not in decision:
                decision['timestamp'] = datetime.now().isoformat()
            
            # 追加新决策
            decisions.append(decision)
            
            # 只保留最近1000条记录
            if len(decisions) > 1000:
                decisions = decisions[-1000:]
            
            # 保存
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(decisions, f, ensure_ascii=False, indent=2)
            
            # 更新缓存
            self._cache[stock_code] = decisions
            
            self.logger.info(f"决策记录已保存: {stock_code}")
            return True
            
        except Exception as e:
            self.logger.error(f"保存决策失败: {stock_code}, 错误: {e}")
            return False
    
    def get_decisions(
        self,
        stock_code: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        获取决策历史
        
        Args:
            stock_code: 股票代码
            limit: 返回数量限制
            
        Returns:
            决策列表
        """
        try:
            # 尝试从缓存读取
            if stock_code in self._cache:
                decisions = self._cache[stock_code]
            else:
                file_path = self._get_decision_file(stock_code)
                if not os.path.exists(file_path):
                    return []
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    decisions = json.load(f)
                    self._cache[stock_code] = decisions
            
            # 返回最近的N条
            return decisions[-limit:] if decisions else []
            
        except Exception as e:
            self.logger.error(f"读取决策历史失败: {stock_code}, 错误: {e}")
            return []
    
    def find_similar_cases(
        self,
        stock_code: str,
        current_signal: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        查找相似的历史案例
        
        Args:
            stock_code: 股票代码
            current_signal: 当前信号
            limit: 返回数量限制
            
        Returns:
            相似案例列表
        """
        decisions = self.get_decisions(stock_code, limit=100)
        
        if not decisions:
            return []
        
        # 过滤相同信号的决策
        similar = [d for d in decisions if d.get('signal') == current_signal]
        
        # 按时间倒序排列
        similar.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return similar[:limit]
    
    def calculate_success_rate(
        self,
        stock_code: str,
        signal: str = None
    ) -> float:
        """
        计算成功率
        
        Args:
            stock_code: 股票代码
            signal: 信号类型（可选）
            
        Returns:
            成功率 (0-1)
        """
        decisions = self.get_decisions(stock_code, limit=100)
        
        if not decisions:
            return 0.5  # 默认50%
        
        # 过滤信号
        if signal:
            decisions = [d for d in decisions if d.get('signal') == signal]
        
        if not decisions:
            return 0.5
        
        # 计算成功数
        successful = sum(1 for d in decisions if d.get('result') == 'success')
        
        return successful / len(decisions)
    
    def _get_decision_file(self, stock_code: str) -> str:
        """获取决策文件路径"""
        return os.path.join(self.storage_dir, f"{stock_code}_decisions.json")
    
    def export_decisions(
        self,
        stock_code: str,
        output_file: str
    ) -> bool:
        """
        导出决策记录
        
        Args:
            stock_code: 股票代码
            output_file: 输出文件路径
            
            Returns:
            是否导出成功
        """
        try:
            decisions = self.get_decisions(stock_code, limit=1000)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(decisions, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"决策记录已导出: {output_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"导出决策失败: {e}")
            return False
    
    def get_ranking_changes(self, stock_code: str, days: int = 5) -> List[int]:
        """
        获取排名变化历史
        
        Args:
            stock_code: 股票代码
            days: 天数
            
        Returns:
            排名变化列表
        """
        try:
            decisions = self.get_decisions(stock_code, limit=days)
            changes = [d.get('rank_change', 0) for d in decisions]
            return changes if changes else [0] * days
        except:
            return [0] * days
    
    def get_history(self, stock_code: str, limit: int = 100) -> List[Dict]:
        """
        获取历史记录（get_decisions的别名）
        
        Args:
            stock_code: 股票代码
            limit: 返回数量限制
            
        Returns:
            决策历史列表
        """
        return self.get_decisions(stock_code, limit)

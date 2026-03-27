# -*- coding: utf-8 -*-
"""
基类智能体
Base Agent Class
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any
from datetime import datetime


class BaseAgent(ABC):
    """
    所有智能体的基类
    定义统一接口和通用功能
    """
    
    def __init__(self, name: str, role: str):
        """
        初始化智能体
        
        Args:
            name: 智能体名称
            role: 智能体角色描述
        """
        self.name = name
        self.role = role
        self.logger = self._setup_logger()
        
    def _setup_logger(self) -> logging.Logger:
        """配置日志记录器"""
        logger = logging.getLogger(f"Agent.{self.name}")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                f'[%(asctime)s] [{self.name}] %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    def log(self, message: str, level: str = "INFO"):
        """
        记录日志
        
        Args:
            message: 日志消息
            level: 日志级别 (INFO, WARNING, ERROR, DEBUG)
        """
        log_func = getattr(self.logger, level.lower(), self.logger.info)
        log_func(message)
    
    @abstractmethod
    def analyze(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行分析（抽象方法，由子类实现）
        
        Args:
            context: 分析上下文，包含股票数据、市场信息等
            
        Returns:
            分析结果字典，必须包含:
            - agent_name: 智能体名称
            - signal: 信号 (bullish/bearish/neutral)
            - confidence: 置信度 (0-1)
            - report: 分析报告文本
            - timestamp: 时间戳
        """
        pass
    
    def _create_result(
        self, 
        signal: str, 
        confidence: float, 
        report: str,
        **extra_fields
    ) -> Dict[str, Any]:
        """
        创建标准化的分析结果
        
        Args:
            signal: 信号类型
            confidence: 置信度
            report: 分析报告
            **extra_fields: 额外字段
            
        Returns:
            标准化的结果字典
        """
        result = {
            'agent_name': self.name,
            'role': self.role,
            'signal': signal,
            'confidence': round(confidence, 3),
            'report': report,
            'timestamp': datetime.now().isoformat(),
        }
        result.update(extra_fields)
        return result
    
    def _validate_context(self, context: Dict[str, Any], required_keys: list) -> bool:
        """
        验证上下文是否包含必要的键
        
        Args:
            context: 上下文字典
            required_keys: 必需的键列表
            
        Returns:
            是否验证通过
        """
        missing_keys = [key for key in required_keys if key not in context]
        if missing_keys:
            self.log(f"缺少必要的上下文键: {missing_keys}", "WARNING")
            return False
        return True
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name='{self.name}', role='{self.role}')>"

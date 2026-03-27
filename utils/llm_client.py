# -*- coding: utf-8 -*-
"""
LLM客户端
LLM Client for API calls
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List


class LLMClient:
    """
    LLM客户端
    封装OpenAI/DeepSeek等API，提供统一接口
    支持本地回退（规则模式）
    """
    
    def __init__(
        self,
        api_provider: str = 'local',
        api_key: Optional[str] = None,
        model: str = 'gpt-3.5-turbo'
    ):
        """
        初始化LLM客户端
        
        Args:
            api_provider: API提供商 ('openai', 'deepseek', 'local')
            api_key: API密钥
            model: 模型名称
        """
        self.api_provider = api_provider
        self.api_key = api_key or os.getenv('OPENAI_API_KEY', '')
        self.model = model
        self.logger = logging.getLogger("LLMClient")
        
        # 尝试导入相关库
        self.openai_available = False
        if api_provider in ['openai', 'deepseek']:
            try:
                import openai
                self.openai = openai
                self.openai_available = True
                self.logger.info(f"OpenAI库可用，使用{api_provider}")
            except ImportError:
                self.logger.warning("OpenAI库不可用，将使用本地规则模式")
    
    def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 500,
        **kwargs
    ) -> str:
        """
        生成文本
        
        Args:
            prompt: 提示词
            temperature: 温度参数
            max_tokens: 最大令牌数
            **kwargs: 其他参数
            
        Returns:
            生成的文本
        """
        if self.api_provider == 'local' or not self.openai_available:
            return self._generate_local(prompt, **kwargs)
        
        try:
            if self.api_provider == 'openai':
                return self._generate_openai(prompt, temperature, max_tokens)
            elif self.api_provider == 'deepseek':
                return self._generate_deepseek(prompt, temperature, max_tokens)
        except Exception as e:
            self.logger.warning(f"API调用失败: {e}，回退到本地模式")
            return self._generate_local(prompt, **kwargs)
    
    def _generate_openai(
        self,
        prompt: str,
        temperature: float,
        max_tokens: int
    ) -> str:
        """
        使用OpenAI API生成文本
        
        Args:
            prompt: 提示词
            temperature: 温度参数
            max_tokens: 最大令牌数
            
        Returns:
            生成的文本
        """
        try:
            response = self.openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个专业的股票分析师。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=self.api_key
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            self.logger.error(f"OpenAI API调用失败: {e}")
            raise
    
    def _generate_deepseek(
        self,
        prompt: str,
        temperature: float,
        max_tokens: int
    ) -> str:
        """
        使用DeepSeek API生成文本
        
        Args:
            prompt: 提示词
            temperature: 温度参数
            max_tokens: 最大令牌数
            
        Returns:
            生成的文本
        """
        # DeepSeek API调用逻辑
        # 这里是示例实现
        try:
            response = self.openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个专业的股票分析师。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=self.api_key,
                api_base="https://api.deepseek.com/v1"  # DeepSeek API端点
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            self.logger.error(f"DeepSeek API调用失败: {e}")
            raise
    
    def _generate_local(self, prompt: str, **kwargs) -> str:
        """
        本地规则模式生成文本
        
        Args:
            prompt: 提示词
            **kwargs: 其他参数
            
        Returns:
            生成的文本
        """
        # 简单的规则模式实现
        # 实际应用中可以使用更复杂的规则或本地模型
        
        if '看涨' in prompt or 'bullish' in prompt.lower():
            return "基于技术面和基本面分析，该股票呈现看涨趋势。建议关注上方阻力位，逢低布局。"
        elif '看跌' in prompt or 'bearish' in prompt.lower():
            return "基于多项指标分析，该股票呈现看跌趋势。建议谨慎操作，关注下方支撑位。"
        else:
            return "市场信号不明确，建议保持观望，等待更清晰的交易信号。"
    
    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """
        分析文本情绪
        
        Args:
            text: 文本内容
            
        Returns:
            情绪分析结果
        """
        prompt = f"""
        请分析以下文本的情绪，返回JSON格式的结果：
        {{
            "sentiment": "positive/negative/neutral",
            "score": -1到1之间的数字,
            "keywords": ["关键词1", "关键词2"]
        }}
        
        文本: {text}
        """
        
        try:
            response = self.generate(prompt, max_tokens=200)
            
            # 尝试解析JSON
            import json
            result = json.loads(response)
            return result
            
        except Exception as e:
            self.logger.warning(f"情绪分析失败: {e}")
            return {
                'sentiment': 'neutral',
                'score': 0,
                'keywords': []
            }
    
    def summarize(self, text: str, max_length: int = 200) -> str:
        """
        总结文本
        
        Args:
            text: 文本内容
            max_length: 最大长度
            
        Returns:
            总结文本
        """
        prompt = f"请用{max_length}字以内总结以下文本：\n{text}"
        
        try:
            return self.generate(prompt, max_tokens=max_length // 4)
        except Exception as e:
            self.logger.warning(f"文本总结失败: {e}")
            return text[:max_length]

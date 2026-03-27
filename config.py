# -*- coding: utf-8 -*-
"""
项目配置文件
Project Configuration
"""

# 系统配置
SYSTEM_CONFIG = {
    'name': '多智能体股票分析系统',
    'version': '1.0.0',
    'description': '基于TradingAgents-CN设计思想的多智能体协作股票分析系统',
    'author': 'Stock Analysis Team'
}

# 智能体配置
AGENT_CONFIG = {
    'technical_analyst': {
        'enabled': True,
        'rsi_overbought': 70,
        'rsi_oversold': 30,
        'ma_periods': [5, 10, 20, 60]
    },
    'sentiment_analyst': {
        'enabled': True,
        'history_days': 7,
        'turnover_threshold': 5.0
    },
    'news_analyst': {
        'enabled': True,
        'news_file': 'output/news_latest.json',
        'max_news_count': 10
    },
    'fundamental_analyst': {
        'enabled': True,
        'pe_undervalued': 15,
        'pe_overvalued': 35,
        'pb_undervalued': 1.5,
        'pb_overvalued': 5.0
    },
    'bull_researcher': {
        'enabled': True
    },
    'bear_researcher': {
        'enabled': True
    },
    'research_manager': {
        'enabled': True
    },
    'trader': {
        'enabled': True,
        'min_quantity': 1
    },
    'risk_manager': {
        'enabled': True,
        'max_single_position': 0.15,
        'max_portfolio_risk': 0.05,
        'max_drawdown': 0.20
    }
}

# LLM配置
LLM_CONFIG = {
    'provider': 'local',  # 'openai', 'deepseek', 'local'
    'model': 'gpt-3.5-turbo',
    'temperature': 0.7,
    'max_tokens': 500,
    'api_key': None  # 从环境变量读取
}

# 存储配置
STORAGE_CONFIG = {
    'memory_dir': 'memory/storage',
    'reflection_dir': 'memory/reflections',
    'history_dir': 'data/history',
    'output_dir': 'output'
}

# 日志配置
LOGGING_CONFIG = {
    'level': 'INFO',
    'format': '[%(asctime)s] [%(name)s] %(message)s',
    'date_format': '%Y-%m-%d %H:%M:%S',
    'file': 'logs/system.log'
}

# 分析参数
ANALYSIS_CONFIG = {
    'parallel_analysts': True,
    'max_workers': 4,
    'timeout': 30,  # 秒
    'retry_count': 3
}

# 交易参数
TRADING_CONFIG = {
    'position_sizes': {
        'small': 0.05,
        'medium': 0.10,
        'large': 0.20
    },
    'time_horizons': {
        'short_term': 1,      # 天
        'medium_term': 5,
        'long_term': 20
    }
}

# 风险参数
RISK_CONFIG = {
    'max_single_position': 0.15,
    'max_portfolio_risk': 0.05,
    'max_drawdown': 0.20,
    'stop_loss_distance': 0.05,  # 5%
    'take_profit_distance': 0.15  # 15%
}

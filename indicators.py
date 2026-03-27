#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
技术指标计算模块
基于历史价格序列计算 RSI、MACD、布林带、均线偏离等指标
"""

from typing import Optional


def calc_rsi(prices: list, period: int = 14) -> Optional[float]:
    """计算 RSI（相对强弱指数）"""
    if len(prices) < period + 1:
        return None
    
    gains, losses = [], []
    for i in range(1, len(prices)):
        diff = prices[i] - prices[i - 1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    
    # 初始平均
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    
    # Wilder 平滑
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - 100 / (1 + rs), 2)


def calc_ema(prices: list, period: int) -> list:
    """计算 EMA 序列"""
    if len(prices) < period:
        return []
    k = 2 / (period + 1)
    ema = [sum(prices[:period]) / period]
    for p in prices[period:]:
        ema.append(p * k + ema[-1] * (1 - k))
    return ema


def calc_macd(prices: list, fast: int = 12, slow: int = 26, signal: int = 9) -> Optional[float]:
    """计算 MACD 值（DIF - DEA）"""
    if len(prices) < slow + signal:
        return None
    
    ema_fast = calc_ema(prices, fast)
    ema_slow = calc_ema(prices, slow)
    
    # 对齐长度
    min_len = min(len(ema_fast), len(ema_slow))
    if min_len < signal:
        return None
    
    ema_fast = ema_fast[-min_len:]
    ema_slow = ema_slow[-min_len:]
    
    dif = [f - s for f, s in zip(ema_fast, ema_slow)]
    
    if len(dif) < signal:
        return None
    
    dea = calc_ema(dif, signal)
    if not dea:
        return None
    
    macd_val = (dif[-1] - dea[-1]) * 2
    return round(macd_val, 4)


def calc_bollinger_position(prices: list, period: int = 20, std_mult: float = 2.0) -> Optional[float]:
    """
    计算布林带位置
    返回 (price - lower) / (upper - lower)，范围约 [0, 1]
    """
    if len(prices) < period:
        return None
    
    window = prices[-period:]
    ma = sum(window) / period
    std = (sum((p - ma) ** 2 for p in window) / period) ** 0.5
    
    if std == 0:
        return 0.5
    
    upper = ma + std_mult * std
    lower = ma - std_mult * std
    
    if upper == lower:
        return 0.5
    
    pos = (prices[-1] - lower) / (upper - lower)
    return round(max(0.0, min(1.0, pos)), 4)


def calc_ma_diff(prices: list, period: int) -> Optional[float]:
    """计算当前价与N日均线的偏离百分比"""
    if len(prices) < period:
        return None
    
    ma = sum(prices[-period:]) / period
    if ma == 0:
        return None
    
    diff = (prices[-1] - ma) / ma * 100
    return round(diff, 2)


def add_technical_indicators(stock: dict, price_history: list) -> dict:
    """
    为股票添加技术指标
    
    Args:
        stock: 股票数据字典
        price_history: 历史收盘价列表（从旧到新）
    
    Returns:
        添加了技术指标的股票字典
    """
    prices = [float(p) for p in price_history if p is not None and float(p) > 0]
    
    stock['rsi']          = calc_rsi(prices, 14)
    stock['macd']         = calc_macd(prices, 12, 26, 9)
    stock['bb_position']  = calc_bollinger_position(prices, 20)
    stock['ma5_diff']     = calc_ma_diff(prices, 5)
    stock['ma20_diff']    = calc_ma_diff(prices, 20)
    stock['price_count']  = len(prices)   # 记录用了多少历史价格
    
    return stock


def get_indicator_features(stock: dict) -> dict:
    """提取用于模型训练的指标特征（缺失值填 None）"""
    return {
        'rsi':          stock.get('rsi'),
        'macd':         stock.get('macd'),
        'bb_position':  stock.get('bb_position'),
        'ma5_diff':     stock.get('ma5_diff'),
        'ma20_diff':    stock.get('ma20_diff'),
        'change_pct':   float(stock.get('change_pct', 0) or 0),
        'turnover_rate':float(stock.get('turnover_rate', 0) or 0),
        'volume_ratio': float(stock.get('volume_ratio', 1) or 1),
        'rank':         int(stock.get('rank', 100) or 100),
    }

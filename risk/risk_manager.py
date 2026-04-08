# -*- coding: utf-8 -*-
"""
Smart Risk Management System
智能风控系统

特性:
- 实时风险监控
- 动态仓位调整
- 黑天鹅事件检测
- 相关性风险分析
- VaR/CVaR计算
- 凯利公式仓位管理
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
from pathlib import Path


class RiskLevel(Enum):
    """风险等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    BLACK_SWAN = "black_swan"


@dataclass
class RiskMetrics:
    """风险指标"""
    # VaR指标
    var_95: float = 0.0           # 95%置信度VaR
    var_99: float = 0.0           # 99%置信度VaR
    cvar_95: float = 0.0          # 条件VaR
    cvar_99: float = 0.0          # 条件VaR
    
    # 市场风险
    portfolio_beta: float = 1.0   # 组合Beta
    correlation_risk: float = 0.0 # 相关性风险 (平均相关系数)
    concentration_risk: float = 0.0 # 集中度风险 (HHI指数)
    
    # 流动性风险
    liquidity_risk: float = 0.0   # 流动性风险得分
    avg_days_to_liquidate: float = 0  # 平均变现天数
    
    # 杠杆风险
    leverage_ratio: float = 0.0   # 杠杆比率
    margin_level: float = 1.0     # 保证金水平
    
    # 情绪风险
    fear_greed_index: float = 50.0 # 恐慌贪婪指数
    market_breadth: float = 0.5    # 市场广度
    
    def to_dict(self) -> dict:
        return {
            'var_95': f"{self.var_95:.2%}",
            'var_99': f"{self.var_99:.2%}",
            'cvar_95': f"{self.cvar_95:.2%}",
            'cvar_99': f"{self.cvar_99:.2%}",
            'portfolio_beta': round(self.portfolio_beta, 3),
            'correlation_risk': f"{self.correlation_risk:.2%}",
            'concentration_risk': f"{self.concentration_risk:.2%}",
            'liquidity_risk': f"{self.liquidity_risk:.2%}",
            'leverage_ratio': round(self.leverage_ratio, 3)
        }


@dataclass
class RiskAlert:
    """风险告警"""
    alert_id: str
    timestamp: datetime
    level: RiskLevel
    alert_type: str              # 'var_breach', 'concentration', 'liquidity', 'black_swan', ...
    title: str
    message: str
    affected_stocks: List[str] = field(default_factory=list)
    recommended_action: str = ""
    suggested_reduction: float = 0.0  # 建议减仓比例
    
    def to_dict(self) -> dict:
        return {
            'alert_id': self.alert_id,
            'timestamp': self.timestamp.isoformat(),
            'level': self.level.value,
            'type': self.alert_type,
            'title': self.title,
            'message': self.message,
            'affected_stocks': self.affected_stocks,
            'recommended_action': self.recommended_action,
            'suggested_reduction': f"{self.suggested_reduction:.2%}" if self.suggested_reduction else None
        }


@dataclass
class Position:
    """持仓信息"""
    stock_code: str
    stock_name: str
    quantity: int
    avg_cost: float
    current_price: float
    entry_date: datetime
    sector: str = ""              # 所属行业
    
    @property
    def market_value(self) -> float:
        return self.quantity * self.current_price
    
    @property
    def unrealized_pnl(self) -> float:
        return (self.current_price - self.avg_cost) * self.quantity
    
    @property
    def return_pct(self) -> float:
        if self.avg_cost == 0:
            return 0
        return (self.current_price - self.avg_cost) / self.avg_cost


class BlackSwanDetector:
    """
    黑天鹅事件检测器
    
    检测条件:
    1. 大盘单日跌幅 > 5%
    2. VIX指数飙升 > 30
    3. 多只股票同时跌停 (>50只)
    4. 北向资金大幅流出 > 100亿
    5. 成交额大幅萎缩
    """
    
    def __init__(self):
        self.trigger_history: List[Dict] = []
        self.alert_callbacks: List[Callable] = []
    
    def check(
        self,
        index_change: float,
        vix: float,
        limit_down_count: int,
        northbound_flow: float,
        volume_change: float,
        fear_greed: float
    ) -> Tuple[bool, List[str], float]:
        """
        检测黑天鹅事件
        
        Args:
            index_change: 大盘涨跌幅
            vix: VIX指数
            limit_down_count: 跌停股票数量
            northbound_flow: 北向资金净流入 (亿元)
            volume_change: 成交量变化率
            fear_greed: 恐慌贪婪指数
            
        Returns:
            (is_black_swan, triggers, severity)
        """
        triggers = []
        severity = 0.0
        
        # 1. 大盘暴跌
        if index_change < -0.05:
            triggers.append(f"大盘暴跌 {index_change:.2%}")
            severity += 0.3
        elif index_change < -0.03:
            triggers.append(f"大盘大跌 {index_change:.2%}")
            severity += 0.15
        
        # 2. VIX飙升
        if vix > 40:
            triggers.append(f"VIX飙升 {vix:.1f}")
            severity += 0.3
        elif vix > 30:
            triggers.append(f"VIX偏高 {vix:.1f}")
            severity += 0.15
        
        # 3. 大面积跌停
        if limit_down_count > 100:
            triggers.append(f"大面积跌停 {limit_down_count}只")
            severity += 0.3
        elif limit_down_count > 50:
            triggers.append(f"跌停增加 {limit_down_count}只")
            severity += 0.15
        
        # 4. 北向资金大幅流出
        if northbound_flow < -50:
            triggers.append(f"北向资金大幅流出 {-northbound_flow:.0f}亿")
            severity += 0.2
        elif northbound_flow < -20:
            triggers.append(f"北向资金流出 {-northbound_flow:.0f}亿")
            severity += 0.1
        
        # 5. 成交量萎缩
        if volume_change < -0.5:
            triggers.append(f"成交萎缩 {volume_change:.2%}")
            severity += 0.15
        
        # 6. 极度恐慌
        if fear_greed < 20:
            triggers.append(f"市场极度恐慌 {fear_greed:.0f}")
            severity += 0.2
        
        is_black_swan = severity >= 0.6 or len(triggers) >= 3
        
        if is_black_swan:
            self._record_event(triggers, severity)
        
        return is_black_swan, triggers, severity
    
    def _record_event(self, triggers: List[str], severity: float):
        """记录黑天鹅事件"""
        event = {
            'timestamp': datetime.now().isoformat(),
            'triggers': triggers,
            'severity': severity
        }
        self.trigger_history.append(event)
        
        # 触发回调
        for callback in self.alert_callbacks:
            callback(event)
    
    def add_callback(self, callback: Callable):
        """添加事件回调"""
        self.alert_callbacks.append(callback)
    
    def get_history(self) -> List[Dict]:
        """获取历史事件"""
        return self.trigger_history


class PositionSizer:
    """
    智能仓位计算器
    
    支持:
    - 凯利公式
    - 风险平价
    - 固定比例
    - 波动率调整
    """
    
    def __init__(
        self,
        method: str = 'kelly',
        max_position: float = 0.15,
        min_position: float = 0.01
    ):
        """
        Args:
            method: 仓位计算方法 ('kelly', 'risk_parity', 'fixed')
            max_position: 最大单只仓位
            min_position: 最小单只仓位
        """
        self.method = method
        self.max_position = max_position
        self.min_position = min_position
    
    def calculate(
        self,
        signal_strength: float,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        volatility: float,
        portfolio_value: float,
        market_volatility: float = 0.02
    ) -> float:
        """
        计算最优仓位
        
        Args:
            signal_strength: 信号强度 [0, 1]
            win_rate: 胜率 [0, 1]
            avg_win: 平均盈利比例
            avg_loss: 平均亏损比例
            volatility: 股票波动率
            portfolio_value: 组合总价值
            market_volatility: 市场波动率
            
        Returns:
            建议仓位比例
        """
        if self.method == 'kelly':
            return self._kelly_formula(win_rate, avg_win, avg_loss, volatility)
        elif self.method == 'risk_parity':
            return self._risk_parity(volatility, market_volatility)
        elif self.method == 'fixed':
            return self._fixed_fraction(signal_strength)
        else:
            return self._kelly_formula(win_rate, avg_win, avg_loss, volatility)
    
    def _kelly_formula(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        volatility: float
    ) -> float:
        """
        凯利公式
        
        f* = (p*b - q) / b
        f*: 最佳仓位比例
        p: 胜率
        b: 盈亏比
        q: 败率 (1-p)
        """
        if avg_loss == 0:
            return self.max_position
        
        # 盈亏比
        win_loss_ratio = abs(avg_win / avg_loss)
        
        # 凯利比例
        kelly = (win_rate * win_loss_ratio - (1 - win_rate)) / win_loss_ratio
        
        # 半凯利 (保守)
        kelly = kelly / 2
        
        # 波动率调整
        vol_adjustment = 0.02 / max(volatility, 0.01)
        kelly = kelly * min(vol_adjustment, 2.0)
        
        # 限制范围
        kelly = max(self.min_position, min(self.max_position, kelly))
        
        return kelly
    
    def _risk_parity(self, volatility: float, market_volatility: float) -> float:
        """
        风险平价
        
        目标: 各资产对组合风险的贡献相等
        """
        if market_volatility == 0:
            return self.max_position / 2
        
        # 风险平价仓位
        beta = volatility / market_volatility
        position = (self.max_position / 2) / beta
        
        return max(self.min_position, min(self.max_position, position))
    
    def _fixed_fraction(self, signal_strength: float) -> float:
        """
        固定比例
        
        根据信号强度调整仓位
        """
        base_position = self.max_position / 2
        position = base_position * (0.5 + signal_strength * 0.5)
        
        return max(self.min_position, min(self.max_position, position))


class SmartRiskManager:
    """
    智能风险管理系统
    
    特性:
    - 实时风险监控
    - 动态仓位调整
    - 黑天鹅事件检测
    - 相关性风险分析
    - VaR/CVaR计算
    """
    
    def __init__(
        self,
        # 仓位限制
        max_single_position: float = 0.15,
        max_sector_exposure: float = 0.30,
        max_correlation: float = 0.70,
        max_total_position: float = 0.85,
        
        # 风险限制
        var_limit: float = 0.02,
        max_drawdown_limit: float = 0.15,
        max_leverage: float = 1.0,
        
        # 流动性限制
        min_daily_volume: float = 50000000,  # 5000万
        max_liquidity_risk: float = 0.10
    ):
        """
        Args:
            max_single_position: 单只股票最大仓位
            max_sector_exposure: 单一行业最大暴露
            max_correlation: 最大相关系数
            max_total_position: 最大总仓位
            var_limit: VaR限制
            max_drawdown_limit: 最大回撤限制
            max_leverage: 最大杠杆
            min_daily_volume: 最小日成交量
            max_liquidity_risk: 最大流动性风险
        """
        # 仓位限制
        self.max_single_position = max_single_position
        self.max_sector_exposure = max_sector_exposure
        self.max_correlation = max_correlation
        self.max_total_position = max_total_position
        
        # 风险限制
        self.var_limit = var_limit
        self.max_drawdown_limit = max_drawdown_limit
        self.max_leverage = max_leverage
        
        # 流动性限制
        self.min_daily_volume = min_daily_volume
        self.max_liquidity_risk = max_liquidity_risk
        
        # 子系统
        self.black_swan_detector = BlackSwanDetector()
        self.position_sizer = PositionSizer(max_position=max_single_position)
        
        # 状态
        self.current_positions: Dict[str, Position] = {}
        self.portfolio_value: float = 0
        self.cash: float = 0
        self.equity_curve: List[float] = []
        
        # 历史
        self.alert_history: List[RiskAlert] = []
        self.risk_metrics_history: List[RiskMetrics] = []
        
        # 回调
        self.alert_callbacks: List[Callable] = []
    
    def update_positions(self, positions: Dict[str, Position], portfolio_value: float, cash: float):
        """更新持仓信息"""
        self.current_positions = positions
        self.portfolio_value = portfolio_value
        self.cash = cash
        
        if portfolio_value > 0:
            self.equity_curve.append(portfolio_value)
    
    def analyze_risk(
        self,
        market_data: Dict[str, Dict]
    ) -> Tuple[RiskMetrics, List[RiskAlert]]:
        """
        分析投资组合风险
        
        Args:
            market_data: 市场数据
                {
                    'stock_code': {
                        'price': float,
                        'volume': float,
                        'volatility': float,
                        'sector': str,
                        ...
                    }
                }
            
        Returns:
            (RiskMetrics, List[RiskAlert])
        """
        # 计算各项风险指标
        metrics = self._calculate_metrics(market_data)
        
        # 检查风险限制
        alerts = self._check_risk_limits(metrics, market_data)
        
        # 检测黑天鹅
        black_swan_alerts = self._check_black_swan(market_data)
        alerts.extend(black_swan_alerts)
        
        # 记录历史
        self.risk_metrics_history.append(metrics)
        self.alert_history.extend(alerts)
        
        return metrics, alerts
    
    def _calculate_metrics(self, market_data: Dict) -> RiskMetrics:
        """计算风险指标"""
        metrics = RiskMetrics()
        
        if not self.current_positions:
            return metrics
        
        # 基本信息
        total_value = self.portfolio_value
        positions = list(self.current_positions.values())
        
        # ==================== VaR计算 ====================
        returns = []
        for pos in positions:
            stock_data = market_data.get(pos.stock_code, {})
            volatility = stock_data.get('volatility', 0.02)
            returns.append((pos.market_value / total_value) * volatility)
        
        portfolio_vol = np.sqrt(sum(r**2 for r in returns)) if returns else 0
        
        # 简化VaR计算 (假设正态分布)
        z_95 = 1.645
        z_99 = 2.326
        
        metrics.var_95 = portfolio_vol * z_95
        metrics.var_99 = portfolio_vol * z_99
        metrics.cvar_95 = portfolio_vol * (z_95 + 0.4)
        metrics.cvar_99 = portfolio_vol * (z_99 + 0.4)
        
        # ==================== 集中度风险 ====================
        weights = [pos.market_value / total_value for pos in positions]
        metrics.concentration_risk = sum(w**2 for w in weights)  # HHI指数
        
        # ==================== 流动性风险 ====================
        liquidity_scores = []
        for pos in positions:
            stock_data = market_data.get(pos.stock_code, {})
            daily_volume = stock_data.get('volume', 0)
            
            if daily_volume > 0:
                position_ratio = pos.market_value / daily_volume
                # 计算变现天数 (假设每天最多变现10%成交量)
                days_to_liquidate = position_ratio / 0.1
                liquidity_scores.append(min(days_to_liquidate / 10, 1.0))  # 归一化
            else:
                liquidity_scores.append(1.0)
        
        metrics.liquidity_risk = np.mean(liquidity_scores)
        metrics.avg_days_to_liquidate = np.mean([
            s * 10 for s in liquidity_scores
        ])
        
        # ==================== Beta ====================
        betas = []
        for pos in positions:
            stock_data = market_data.get(pos.stock_code, {})
            beta = stock_data.get('beta', 1.0)
            betas.append(beta * (pos.market_value / total_value))
        
        metrics.portfolio_beta = sum(betas) if betas else 1.0
        
        # ==================== 相关性风险 ====================
        # 简化: 使用HHI作为相关性风险的代理
        metrics.correlation_risk = metrics.concentration_risk
        
        return metrics
    
    def _check_risk_limits(
        self,
        metrics: RiskMetrics,
        market_data: Dict
    ) -> List[RiskAlert]:
        """检查风险限制"""
        alerts = []
        alert_counter = 0
        
        # VaR检查
        if metrics.var_95 > self.var_limit:
            alert_counter += 1
            alerts.append(RiskAlert(
                alert_id=f"VAR_{datetime.now().strftime('%Y%m%d%H%M%S')}_{alert_counter}",
                timestamp=datetime.now(),
                level=RiskLevel.HIGH,
                alert_type='var_breach',
                title='VaR超过限制',
                message=f'日VaR ({metrics.var_95:.2%}) 超过限制 ({self.var_limit:.2%})',
                recommended_action='reduce_position',
                suggested_reduction=0.2
            ))
        
        # 集中度检查
        if metrics.concentration_risk > 0.25:
            alert_counter += 1
            alerts.append(RiskAlert(
                alert_id=f"CONC_{datetime.now().strftime('%Y%m%d%H%M%S')}_{alert_counter}",
                timestamp=datetime.now(),
                level=RiskLevel.MEDIUM,
                alert_type='concentration',
                title='持仓集中度过高',
                message=f'持仓集中度 (HHI: {metrics.concentration_risk:.2%}) 偏高',
                recommended_action='diversify',
                suggested_reduction=0.15
            ))
        
        # 流动性检查
        if metrics.liquidity_risk > self.max_liquidity_risk:
            alert_counter += 1
            alerts.append(RiskAlert(
                alert_id=f"LIQ_{datetime.now().strftime('%Y%m%d%H%M%S')}_{alert_counter}",
                timestamp=datetime.now(),
                level=RiskLevel.MEDIUM,
                alert_type='liquidity',
                title='流动性风险上升',
                message=f'平均变现天数: {metrics.avg_days_to_liquidate:.1f}天',
                recommended_action='reduce_illiquid_positions',
                suggested_reduction=0.10
            ))
        
        # 最大回撤检查
        if len(self.equity_curve) > 20:
            drawdown = self._calculate_current_drawdown()
            if drawdown < -self.max_drawdown_limit:
                alert_counter += 1
                alerts.append(RiskAlert(
                    alert_id=f"DD_{datetime.now().strftime('%Y%m%d%H%M%S')}_{alert_counter}",
                    timestamp=datetime.now(),
                    level=RiskLevel.CRITICAL,
                    alert_type='drawdown',
                    title='回撤超过限制',
                    message=f'当前回撤 ({drawdown:.2%}) 超过限制 ({self.max_drawdown_limit:.2%})',
                    recommended_action='immediate_liquidation',
                    suggested_reduction=0.50
                ))
        
        return alerts
    
    def _check_black_swan(self, market_data: Dict) -> List[RiskAlert]:
        """检测黑天鹅事件"""
        # 提取市场级别数据
        index_change = market_data.get('__INDEX__', {}).get('change_pct', 0)
        vix = market_data.get('__VIX__', {}).get('value', 20)
        limit_down_count = market_data.get('__MARKET__', {}).get('limit_down_count', 0)
        northbound_flow = market_data.get('__NORTHBOUND__', {}).get('net_flow', 0) / 1e8  # 转为亿
        volume_change = market_data.get('__VOLUME__', {}).get('change_pct', 0)
        fear_greed = market_data.get('__FEAR__', {}).get('value', 50)
        
        is_black_swan, triggers, severity = self.black_swan_detector.check(
            index_change, vix, limit_down_count, northbound_flow, volume_change, fear_greed
        )
        
        if is_black_swan:
            level = RiskLevel.BLACK_SWAN if severity >= 0.8 else RiskLevel.CRITICAL
            
            return [RiskAlert(
                alert_id=f"BS_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                timestamp=datetime.now(),
                level=level,
                alert_type='black_swan',
                title='黑天鹅事件预警',
                message=f"检测到黑天鹅事件: {'; '.join(triggers)}",
                recommended_action='emergency_liquidation',
                suggested_reduction=0.70
            )]
        
        return []
    
    def _calculate_current_drawdown(self) -> float:
        """计算当前回撤"""
        if len(self.equity_curve) < 2:
            return 0
        
        current = self.equity_curve[-1]
        peak = max(self.equity_curve)
        
        if peak == 0:
            return 0
        
        return (current - peak) / peak
    
    def get_position_size(
        self,
        signal_strength: float,
        stock_volatility: float,
        available_capital: float
    ) -> Tuple[float, str]:
        """
        计算仓位大小
        
        Args:
            signal_strength: 信号强度 [0, 1]
            stock_volatility: 股票波动率
            available_capital: 可用资金
            
        Returns:
            (position_value, reason)
        """
        # 检查总仓位限制
        total_position_value = self.portfolio_value - self.cash
        total_position_ratio = total_position_value / self.portfolio_value
        
        if total_position_ratio >= self.max_total_position:
            return 0, "已达到最大总仓位"
        
        # 计算仓位
        position = self.position_sizer.calculate(
            signal_strength=signal_strength,
            win_rate=signal_strength,  # 简化
            avg_win=0.05,
            avg_loss=0.03,
            volatility=stock_volatility,
            portfolio_value=self.portfolio_value
        )
        
        # 应用限制
        max_single_value = self.portfolio_value * self.max_single_position
        max_total_value = self.portfolio_value * self.max_total_position - total_position_value
        
        position_value = min(
            position * self.portfolio_value,
            max_single_value,
            max_total_value,
            available_capital
        )
        
        if position_value < 1000:  # 最小买入金额
            return 0, "资金不足或仓位过小"
        
        return position_value, "正常"
    
    def should_sell(
        self,
        stock_code: str,
        current_return: float,
        holding_days: int
    ) -> Tuple[bool, str]:
        """
        判断是否应该卖出
        
        Returns:
            (should_sell, reason)
        """
        if stock_code not in self.current_positions:
            return False, "无持仓"
        
        pos = self.current_positions[stock_code]
        
        # 止损检查
        stop_loss = -0.07
        if current_return <= stop_loss:
            return True, f"触发止损 ({current_return:.2%})"
        
        # 止盈检查
        take_profit = 0.15
        if current_return >= take_profit:
            return True, f"达到止盈目标 ({current_return:.2%})"
        
        # 持仓时间检查 (最长30天)
        if holding_days > 30:
            return True, f"持仓时间过长 ({holding_days}天)"
        
        # 亏损超过20%
        if current_return < -0.20:
            return True, f"亏损过大 ({current_return:.2%})"
        
        return False, "继续持有"
    
    def add_alert_callback(self, callback: Callable):
        """添加告警回调"""
        self.alert_callbacks.append(callback)
    
    def get_risk_summary(self) -> Dict:
        """获取风险摘要"""
        current_metrics = self.risk_metrics_history[-1] if self.risk_metrics_history else RiskMetrics()
        current_drawdown = self._calculate_current_drawdown()
        
        return {
            'portfolio_value': self.portfolio_value,
            'cash': self.cash,
            'total_position_ratio': (self.portfolio_value - self.cash) / self.portfolio_value if self.portfolio_value > 0 else 0,
            'num_positions': len(self.current_positions),
            'current_drawdown': current_drawdown,
            'var_95': current_metrics.var_95,
            'liquidity_risk': current_metrics.liquidity_risk,
            'concentration_risk': current_metrics.concentration_risk,
            'alerts_today': len([a for a in self.alert_history if a.timestamp.date() == datetime.now().date()])
        }
    
    def export_report(self, output_dir: str = 'output') -> str:
        """导出风险报告"""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        report = {
            'generated_at': datetime.now().isoformat(),
            'summary': self.get_risk_summary(),
            'positions': {
                code: {
                    'stock_name': pos.stock_name,
                    'quantity': pos.quantity,
                    'avg_cost': pos.avg_cost,
                    'current_price': pos.current_price,
                    'market_value': pos.market_value,
                    'unrealized_pnl': pos.unrealized_pnl,
                    'return_pct': pos.return_pct,
                    'sector': pos.sector
                }
                for code, pos in self.current_positions.items()
            },
            'recent_alerts': [a.to_dict() for a in self.alert_history[-20:]]
        }
        
        report_path = output_dir / f"risk_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        return str(report_path)


def create_sample_market_data() -> Dict:
    """创建示例市场数据"""
    np.random.seed(42)
    
    stocks = {
        '000001': {'price': 12.5, 'volume': 50000000, 'volatility': 0.025, 'beta': 1.2, 'sector': '金融'},
        '000002': {'price': 25.8, 'volume': 80000000, 'volatility': 0.022, 'beta': 1.1, 'sector': '地产'},
        '000004': {'price': 18.2, 'volume': 20000000, 'volatility': 0.035, 'beta': 1.5, 'sector': '科技'},
        '000005': {'price': 3.8, 'volume': 30000000, 'volatility': 0.028, 'beta': 0.9, 'sector': '制造'},
        '000006': {'price': 8.5, 'volume': 40000000, 'volatility': 0.020, 'beta': 1.0, 'sector': '基建'},
    }
    
    # 添加市场级别数据
    stocks['__INDEX__'] = {'change_pct': -0.015}
    stocks['__VIX__'] = {'value': 22}
    stocks['__MARKET__'] = {'limit_down_count': 10}
    stocks['__NORTHBOUND__'] = {'net_flow': 2e8}
    stocks['__FEAR__'] = {'value': 55}
    
    return stocks


if __name__ == '__main__':
    print("=" * 60)
    print("Smart Risk Manager Test")
    print("=" * 60)
    
    # 创建风控系统
    risk_manager = SmartRiskManager(
        max_single_position=0.15,
        max_total_position=0.85,
        max_drawdown_limit=0.15
    )
    
    # 创建示例持仓
    positions = {
        '000001': Position(
            stock_code='000001',
            stock_name='平安银行',
            quantity=10000,
            avg_cost=12.0,
            current_price=12.5,
            entry_date=datetime.now() - timedelta(days=5),
            sector='金融'
        ),
        '000002': Position(
            stock_code='000002',
            stock_name='万科A',
            quantity=5000,
            avg_cost=26.0,
            current_price=25.8,
            entry_date=datetime.now() - timedelta(days=3),
            sector='地产'
        ),
        '000004': Position(
            stock_code='000004',
            stock_name='国华网安',
            quantity=8000,
            avg_cost=18.0,
            current_price=18.2,
            entry_date=datetime.now() - timedelta(days=2),
            sector='科技'
        )
    }
    
    # 更新持仓
    portfolio_value = 1000000
    cash = 200000
    risk_manager.update_positions(positions, portfolio_value, cash)
    
    # 创建市场数据
    market_data = create_sample_market_data()
    
    # 分析风险
    print("\n[Risk Analysis]")
    metrics, alerts = risk_manager.analyze_risk(market_data)
    
    print(f"\nRisk Metrics:")
    print(f"  VaR (95%):    {metrics.var_95:.2%}")
    print(f"  VaR (99%):    {metrics.var_99:.2%}")
    print(f"  Concentration: {metrics.concentration_risk:.2%}")
    print(f"  Liquidity:    {metrics.liquidity_risk:.2%}")
    print(f"  Beta:         {metrics.portfolio_beta:.3f}")
    
    print(f"\nAlerts ({len(alerts)}):")
    for alert in alerts:
        print(f"  [{alert.level.value.upper()}] {alert.title}")
        print(f"    {alert.message}")
        if alert.suggested_reduction:
            print(f"    建议减仓: {alert.suggested_reduction:.0%}")
    
    # 测试仓位计算
    print("\n[Position Sizing]")
    position_value, reason = risk_manager.get_position_size(
        signal_strength=0.7,
        stock_volatility=0.025,
        available_capital=cash
    )
    print(f"  Recommended position: {position_value:,.2f}")
    print(f"  Reason: {reason}")
    
    # 测试卖出判断
    print("\n[Should Sell Test]")
    should_sell, sell_reason = risk_manager.should_sell('000001', 0.04, 3)
    print(f"  000001 (return: 4%): should_sell={should_sell}, reason={sell_reason}")
    
    should_sell, sell_reason = risk_manager.should_sell('000002', -0.08, 3)
    print(f"  000002 (return: -8%): should_sell={should_sell}, reason={sell_reason}")
    
    # 风险摘要
    print("\n[Risk Summary]")
    summary = risk_manager.get_risk_summary()
    for key, value in summary.items():
        if isinstance(value, float) and abs(value) < 10:
            print(f"  {key}: {value:.4f}")
        else:
            print(f"  {key}: {value}")
    
    print("\n[Smart Risk Manager] Test completed!")

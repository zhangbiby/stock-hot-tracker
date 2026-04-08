# -*- coding: utf-8 -*-
"""
Professional Backtest Engine
专业回测引擎

特性:
- 支持滑点和手续费模拟
- 支持多种订单类型
- 详细的交易记录
- 完整的风险评估指标
- 支持信号生成器集成
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Callable, Optional, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
import json
import warnings

# 尝试导入绘图库
try:
    import matplotlib.pyplot as plt
    PLOT_AVAILABLE = True
except ImportError:
    PLOT_AVAILABLE = False
    plt = None


@dataclass
class Position:
    """持仓信息"""
    stock_code: str
    quantity: int               # 持股数 (100的倍数)
    avg_cost: float             # 平均成本
    entry_date: datetime        # 买入日期
    entry_price: float           # 买入价格
    
    @property
    def market_value(self, current_price: float) -> float:
        return self.quantity * current_price
    
    @property
    def unrealized_pnl(self, current_price: float) -> float:
        return (current_price - self.avg_cost) * self.quantity
    
    @property
    def return_pct(self, current_price: float) -> float:
        if self.avg_cost == 0:
            return 0
        return (current_price - self.avg_cost) / self.avg_cost


@dataclass
class Trade:
    """交易记录"""
    trade_id: int
    timestamp: datetime
    stock_code: str
    action: str                 # 'buy' or 'sell'
    price: float                # 成交价格
    quantity: int               # 成交数量
    commission: float           # 手续费
    stamp_duty: float           # 印花税 (仅卖出)
    capital_before: float       # 交易前资金
    capital_after: float        # 交易后资金
    signal: str = ''             # 触发信号
    notes: str = ''
    
    @property
    def total_cost(self) -> float:
        """总成本"""
        if self.action == 'buy':
            return self.price * self.quantity + self.commission
        else:
            return self.commission + self.stamp_duty
    
    @property
    def net_amount(self) -> float:
        """净成交金额"""
        if self.action == 'buy':
            return self.price * self.quantity
        else:
            return self.price * self.quantity - self.commission - self.stamp_duty


@dataclass
class BacktestConfig:
    """回测配置"""
    # 资金设置
    initial_capital: float = 1000000.0     # 初始资金
    max_position_pct: float = 0.15          # 最大单只仓位比例
    max_total_position: float = 0.85        # 最大总仓位
    
    # 交易成本
    commission_rate: float = 0.0003          # 佣金费率 (万3)
    stamp_duty_rate: float = 0.001           # 印花税率 (千1, 仅卖出)
    min_commission: float = 5.0              # 最低佣金
    slippage_rate: float = 0.001            # 滑点 (千1)
    
    # 风控参数
    stop_loss_pct: float = 0.07             # 止损线 7%
    take_profit_pct: float = 0.15            # 止盈线 15%
    max_drawdown_limit: float = 0.20        # 最大回撤限制 20%
    
    # 回测设置
    rebalance_frequency: str = 'daily'       # 调仓频率: 'daily', 'weekly'
    signal_threshold: float = 0.6            # 买入信号阈值
    sell_signal_threshold: float = 0.4       # 卖出信号阈值
    
    def validate(self) -> bool:
        """验证配置"""
        errors = []
        
        if self.initial_capital <= 0:
            errors.append("initial_capital must be positive")
        if not 0 < self.max_position_pct <= 1:
            errors.append("max_position_pct must be between 0 and 1")
        if self.commission_rate < 0 or self.stamp_duty_rate < 0:
            errors.append("Commission and stamp duty rates must be non-negative")
        if self.stop_loss_pct <= 0 or self.take_profit_pct <= 0:
            errors.append("Stop loss and take profit must be positive")
        
        if errors:
            warnings.warn("BacktestConfig validation errors: " + ", ".join(errors))
            return False
        return True


@dataclass
class BacktestResult:
    """回测结果"""
    # 收益指标
    total_return: float                  # 总收益率
    annualized_return: float             # 年化收益率
    benchmark_return: float = 0          # 基准收益率
    
    # 风险指标
    volatility: float                    # 波动率
    sharpe_ratio: float                  # 夏普比率
    max_drawdown: float                  # 最大回撤
    max_drawdown_duration: int = 0       # 最大回撤持续天数
    calmar_ratio: float = 0              # 卡玛比率
    
    # 交易统计
    num_trades: int = 0                  # 交易次数
    win_rate: float = 0                  # 胜率
    avg_win: float = 0                   # 平均盈利
    avg_loss: float = 0                  # 平均亏损
    profit_factor: float = 0             # 盈亏比
    
    # 持仓统计
    avg_holding_days: float = 0          # 平均持仓天数
    max_holding_days: int = 0            # 最长持仓天数
    
    # 时间序列
    equity_curve: pd.DataFrame = None    # 权益曲线
    trades: List[Trade] = field(default_factory=list)  # 交易记录
    monthly_returns: pd.Series = None    # 月度收益
    daily_returns: pd.Series = None      # 日度收益
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'total_return': f"{self.total_return:.2%}",
            'annualized_return': f"{self.annualized_return:.2%}",
            'volatility': f"{self.volatility:.2%}",
            'sharpe_ratio': f"{self.sharpe_ratio:.3f}",
            'max_drawdown': f"{self.max_drawdown:.2%}",
            'win_rate': f"{self.win_rate:.2%}",
            'profit_factor': f"{self.profit_factor:.2f}",
            'num_trades': self.num_trades,
        }
    
    def summary(self) -> str:
        """生成摘要报告"""
        lines = [
            "=" * 60,
            "Backtest Result Summary",
            "=" * 60,
            f"\n【收益指标】",
            f"  总收益率:      {self.total_return:.2%}",
            f"  年化收益率:    {self.annualized_return:.2%}",
            f"  基准收益率:    {self.benchmark_return:.2%}",
            f"  超额收益:      {self.total_return - self.benchmark_return:.2%}",
            f"\n【风险指标】",
            f"  波动率:        {self.volatility:.2%}",
            f"  夏普比率:      {self.sharpe_ratio:.3f}",
            f"  最大回撤:      {self.max_drawdown:.2%}",
            f"  卡玛比率:      {self.calmar_ratio:.3f}" if self.calmar_ratio > 0 else "",
            f"\n【交易统计】",
            f"  总交易次数:    {self.num_trades}",
            f"  胜率:          {self.win_rate:.2%}",
            f"  平均盈利:      {self.avg_win:.2%}",
            f"  平均亏损:      {self.avg_loss:.2%}",
            f"  盈亏比:        {self.profit_factor:.2f}",
            f"\n【持仓统计】",
            f"  平均持仓天数:  {self.avg_holding_days:.1f}",
            f"  最长持仓天数:  {self.max_holding_days}",
            "=" * 60,
        ]
        return "\n".join(filter(None, lines))


class BacktestEngine:
    """
    专业回测引擎
    
    支持:
    - 完整的交易成本模拟 (佣金、印花税、滑点)
    - T+1交易规则
    - 止损止盈
    - 多空双向
    - 灵活的信号生成器接口
    """
    
    def __init__(self, config: BacktestConfig = None):
        """
        Args:
            config: 回测配置
        """
        self.config = config or BacktestConfig()
        self.config.validate()
        
        # 状态变量
        self.reset()
    
    def reset(self):
        """重置回测状态"""
        self.capital = self.config.initial_capital
        self.positions: Dict[str, Position] = {}  # {stock_code: Position}
        self.trades: List[Trade] = []
        self.equity_curve: List[Dict] = []
        self.trade_id_counter = 0
        self.current_date = None
        
        # 统计数据
        self.sell_trades = []  # 仅用于统计的卖出记录
        self.daily_returns = []
    
    def run(
        self,
        data: pd.DataFrame,
        signal_generator: Callable[[pd.DataFrame, Dict], List[Dict]],
        start_date: datetime = None,
        end_date: datetime = None,
        benchmark_data: pd.DataFrame = None
    ) -> BacktestResult:
        """
        运行回测
        
        Args:
            data: 历史数据 DataFrame
                   必须包含: date, stock_code, open, high, low, close, volume
            signal_generator: 信号生成函数
                    signature: (current_data, positions) -> List[Signal]
                    Signal格式: {'stock_code': str, 'action': 'buy'|'sell'|'hold',
                                 'signal_strength': float, 'price': float}
            start_date: 回测开始日期
            end_date: 回测结束日期
            benchmark_data: 基准数据 (用于计算超额收益)
            
        Returns:
            BacktestResult: 回测结果
        """
        print("\n" + "=" * 60)
        print("Starting Backtest")
        print("=" * 60)
        
        self.reset()
        
        # 预处理数据
        data = self._prepare_data(data, start_date, end_date)
        dates = sorted(data['date'].unique())
        
        print(f"Backtest period: {dates[0]} to {dates[-1]}")
        print(f"Trading days: {len(dates)}")
        print(f"Initial capital: {self.config.initial_capital:,.2f}")
        
        # 预处理基准数据
        if benchmark_data is not None:
            benchmark_returns = self._prepare_benchmark(benchmark_data, dates)
        else:
            benchmark_returns = None
        
        # 主回测循环
        for i, date in enumerate(dates):
            self.current_date = date
            
            # 获取当日数据
            daily_data = data[data['date'] == date]
            
            # 更新持仓状态 (T+1检查)
            self._update_positions(daily_data)
            
            # 检查止损止盈
            self._check_stop_loss_take_profit(daily_data)
            
            # 生成信号并执行交易
            signals = signal_generator(daily_data, self._get_positions_info())
            self._execute_signals(signals, daily_data)
            
            # 记录权益
            self._record_equity(daily_data)
            
            # 打印进度
            if (i + 1) % 20 == 0 or i == len(dates) - 1:
                print(f"Progress: {i+1}/{len(dates)} | "
                      f"Capital: {self.capital:,.2f} | "
                      f"Positions: {len(self.positions)}")
        
        # 平仓 (最后一天)
        self._close_all_positions(data[data['date'] == dates[-1]])
        
        # 计算结果
        result = self._calculate_results(benchmark_returns)
        
        # 打印结果
        print(result.summary())
        
        return result
    
    def _prepare_data(
        self, 
        data: pd.DataFrame, 
        start_date, 
        end_date
    ) -> pd.DataFrame:
        """预处理数据"""
        df = data.copy()
        
        # 确保date列是datetime类型
        if not pd.api.types.is_datetime64_any_dtype(df['date']):
            df['date'] = pd.to_datetime(df['date'])
        
        # 过滤日期范围
        if start_date:
            df = df[df['date'] >= pd.to_datetime(start_date)]
        if end_date:
            df = df[df['date'] <= pd.to_datetime(end_date)]
        
        # 排序
        df = df.sort_values(['date', 'stock_code']).reset_index(drop=True)
        
        # 检查必要列
        required_cols = ['date', 'stock_code', 'open', 'high', 'low', 'close', 'volume']
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
        
        return df
    
    def _prepare_benchmark(
        self, 
        benchmark_data: pd.DataFrame, 
        dates: List[datetime]
    ) -> pd.Series:
        """预处理基准数据"""
        if 'date' not in benchmark_data.columns:
            raise ValueError("Benchmark data must have 'date' column")
        
        if not pd.api.types.is_datetime64_any_dtype(benchmark_data['date']):
            benchmark_data['date'] = pd.to_datetime(benchmark_data['date'])
        
        benchmark_data = benchmark_data.set_index('date').sort_index()
        
        # 计算日收益率
        if 'close' in benchmark_data.columns:
            benchmark_returns = benchmark_data['close'].pct_change()
        else:
            raise ValueError("Benchmark data must have 'close' column")
        
        # 只保留回测期间的收益率
        start_date = min(dates)
        end_date = max(dates)
        benchmark_returns = benchmark_returns.loc[
            (benchmark_returns.index >= start_date) & 
            (benchmark_returns.index <= end_date)
        ]
        
        return benchmark_returns
    
    def _get_positions_info(self) -> Dict:
        """获取持仓信息摘要"""
        info = {}
        for stock_code, pos in self.positions.items():
            info[stock_code] = {
                'quantity': pos.quantity,
                'avg_cost': pos.avg_cost,
                'holding_days': (self.current_date - pos.entry_date).days if pos.entry_date else 0
            }
        return info
    
    def _update_positions(self, daily_data: pd.DataFrame):
        """更新持仓状态"""
        for stock_code in list(self.positions.keys()):
            pos = self.positions[stock_code]
            
            # 检查是否T+1可卖
            if pos.entry_date:
                days_held = (self.current_date - pos.entry_date).days
                pos.can_sell = days_held >= 1  # T+1规则
    
    def _check_stop_loss_take_profit(self, daily_data: pd.DataFrame):
        """检查止损止盈"""
        trades_to_execute = []
        
        for stock_code, pos in self.positions.items():
            stock_data = daily_data[daily_data['stock_code'] == stock_code]
            if stock_data.empty:
                continue
            
            current_price = stock_data['close'].iloc[0]
            return_pct = (current_price - pos.avg_cost) / pos.avg_cost
            
            # 止损检查
            if return_pct <= -self.config.stop_loss_pct:
                trades_to_execute.append({
                    'stock_code': stock_code,
                    'action': 'sell',
                    'reason': 'stop_loss',
                    'price': current_price,
                    'quantity': pos.quantity
                })
            
            # 止盈检查
            elif return_pct >= self.config.take_profit_pct:
                trades_to_execute.append({
                    'stock_code': stock_code,
                    'action': 'sell',
                    'reason': 'take_profit',
                    'price': current_price,
                    'quantity': pos.quantity
                })
        
        # 执行强制交易
        for trade_info in trades_to_execute:
            self._execute_sell(
                trade_info['stock_code'],
                trade_info['price'],
                trade_info['quantity'],
                f"{trade_info['reason']}"
            )
    
    def _execute_signals(self, signals: List[Dict], daily_data: pd.DataFrame):
        """执行交易信号"""
        for signal in signals:
            action = signal.get('action', 'hold')
            stock_code = signal['stock_code']
            price = signal.get('price')
            strength = signal.get('signal_strength', 0.5)
            
            if action == 'buy':
                # 买入信号
                stock_data = daily_data[daily_data['stock_code'] == stock_code]
                if not stock_data.empty and price is None:
                    price = stock_data['close'].iloc[0]
                
                if price and strength >= self.config.signal_threshold:
                    self._execute_buy(stock_code, price, strength, signal)
                    
            elif action == 'sell':
                # 卖出信号
                if stock_code in self.positions:
                    pos = self.positions[stock_code]
                    
                    # T+1检查
                    if hasattr(pos, 'can_sell') and not pos.can_sell:
                        continue
                    
                    if strength <= self.config.sell_signal_threshold:
                        self._execute_sell(stock_code, price, pos.quantity, 'signal')
    
    def _execute_buy(
        self, 
        stock_code: str, 
        price: float, 
        signal_strength: float,
        signal_info: Dict = None
    ):
        """执行买入"""
        # 计算可用资金
        available_capital = self.capital * self.config.max_total_position
        if available_capital <= 0:
            return
        
        # 计算买入数量 (100股整数)
        max_shares = int(available_capital / (price * (1 + self.config.slippage_rate)) / 100) * 100
        
        # 检查单只仓位限制
        max_position_value = self.config.initial_capital * self.config.max_position_pct
        position_value = price * max_shares
        if position_value > max_position_value:
            max_shares = int(max_position_value / price / 100) * 100
        
        if max_shares < 100:
            return
        
        # 应用滑点 (向上滑)
        executed_price = price * (1 + self.config.slippage_rate)
        
        # 计算手续费
        commission = max(position_value * self.config.commission_rate, self.config.min_commission)
        total_cost = position_value + commission
        
        if total_cost > self.capital:
            # 资金不足，调整数量
            max_shares = int((self.capital - commission) / executed_price / 100) * 100
            if max_shares < 100:
                return
            position_value = max_shares * executed_price
            commission = max(position_value * self.config.commission_rate, self.config.min_commission)
            total_cost = position_value + commission
        
        # 执行买入
        self.capital -= total_cost
        
        if stock_code in self.positions:
            # 加仓
            pos = self.positions[stock_code]
            total_quantity = pos.quantity + max_shares
            avg_cost = (pos.quantity * pos.avg_cost + max_shares * executed_price) / total_quantity
            pos.quantity = total_quantity
            pos.avg_cost = avg_cost
        else:
            # 新建持仓
            self.positions[stock_code] = Position(
                stock_code=stock_code,
                quantity=max_shares,
                avg_cost=executed_price,
                entry_date=self.current_date,
                entry_price=executed_price
            )
            if hasattr(self.positions[stock_code], 'can_sell'):
                self.positions[stock_code].can_sell = False
        
        # 记录交易
        self.trade_id_counter += 1
        trade = Trade(
            trade_id=self.trade_id_counter,
            timestamp=self.current_date,
            stock_code=stock_code,
            action='buy',
            price=executed_price,
            quantity=max_shares,
            commission=commission,
            stamp_duty=0,
            capital_before=self.capital + total_cost,
            capital_after=self.capital,
            signal=f"signal_{signal_strength:.2f}",
            notes=signal_info.get('notes', '') if signal_info else ''
        )
        self.trades.append(trade)
    
    def _execute_sell(
        self, 
        stock_code: str, 
        price: float, 
        quantity: int = None,
        reason: str = ''
    ):
        """执行卖出"""
        if stock_code not in self.positions:
            return
        
        pos = self.positions[stock_code]
        
        # 确定卖出数量
        if quantity is None:
            quantity = pos.quantity
        
        quantity = min(quantity, pos.quantity)
        if quantity <= 0:
            return
        
        # 应用滑点 (向下滑)
        executed_price = price * (1 - self.config.slippage_rate)
        
        # 计算费用
        revenue = executed_price * quantity
        commission = max(revenue * self.config.commission_rate, self.config.min_commission)
        stamp_duty = revenue * self.config.stamp_duty_rate
        total_cost = commission + stamp_duty
        
        # 执行卖出
        net_revenue = revenue - total_cost
        self.capital += net_revenue
        
        # 更新持仓
        if quantity == pos.quantity:
            del self.positions[stock_code]
        else:
            pos.quantity -= quantity
        
        # 记录交易
        self.trade_id_counter += 1
        cost_basis = quantity * pos.avg_cost
        profit = revenue - cost_basis - total_cost
        
        trade = Trade(
            trade_id=self.trade_id_counter,
            timestamp=self.current_date,
            stock_code=stock_code,
            action='sell',
            price=executed_price,
            quantity=quantity,
            commission=commission,
            stamp_duty=stamp_duty,
            capital_before=self.capital - net_revenue,
            capital_after=self.capital,
            signal=reason,
            notes=f"profit: {profit:.2f}, return: {profit/cost_basis:.2%}"
        )
        self.trades.append(trade)
        self.sell_trades.append(trade)
    
    def _close_all_positions(self, daily_data: pd.DataFrame):
        """最后一天平仓"""
        for stock_code in list(self.positions.keys()):
            stock_data = daily_data[daily_data['stock_code'] == stock_code]
            if not stock_data.empty:
                price = stock_data['close'].iloc[0]
                self._execute_sell(stock_code, price, reason='backtest_end')
    
    def _record_equity(self, daily_data: pd.DataFrame):
        """记录权益"""
        position_value = 0
        
        for stock_code, pos in self.positions.items():
            stock_data = daily_data[daily_data['stock_code'] == stock_code]
            if not stock_data.empty:
                price = stock_data['close'].iloc[0]
                position_value += pos.quantity * price
        
        total_equity = self.capital + position_value
        
        self.equity_curve.append({
            'date': self.current_date,
            'cash': self.capital,
            'position_value': position_value,
            'total_equity': total_equity,
            'num_positions': len(self.positions)
        })
        
        # 计算日收益率
        if len(self.equity_curve) > 1:
            prev_equity = self.equity_curve[-2]['total_equity']
            daily_return = (total_equity - prev_equity) / prev_equity
            self.daily_returns.append(daily_return)
    
    def _calculate_results(self, benchmark_returns: pd.Series = None) -> BacktestResult:
        """计算回测结果"""
        equity_df = pd.DataFrame(self.equity_curve)
        
        if equity_df.empty:
            return BacktestResult(total_return=0, annualized_return=0)
        
        # 基础收益率
        total_return = (equity_df['total_equity'].iloc[-1] / self.config.initial_capital) - 1
        
        # 年化收益率
        days = len(equity_df)
        years = days / 252
        if years > 0:
            annualized_return = (1 + total_return) ** (1 / years) - 1
        else:
            annualized_return = 0
        
        # 基准收益率
        benchmark_return = 0
        if benchmark_returns is not None and len(benchmark_returns) > 0:
            benchmark_return = benchmark_returns.iloc[-1] if len(benchmark_returns) > 0 else 0
        
        # 波动率
        if self.daily_returns:
            volatility = np.std(self.daily_returns) * np.sqrt(252)
            daily_returns_series = pd.Series(self.daily_returns)
        else:
            volatility = 0
            daily_returns_series = pd.Series()
        
        # 夏普比率
        if volatility > 0:
            sharpe_ratio = (annualized_return - 0.02) / volatility  # 假设无风险利率2%
        else:
            sharpe_ratio = 0
        
        # 最大回撤
        cumulative = (1 + pd.Series(self.daily_returns)).cumprod()
        peak = cumulative.expanding().max()
        drawdown = (cumulative - peak) / peak
        max_drawdown = drawdown.min()
        
        # 最大回撤持续时间
        max_dd_duration = 0
        is_in_drawdown = False
        dd_start = 0
        for i, dd in enumerate(drawdown):
            if dd < 0 and not is_in_drawdown:
                is_in_drawdown = True
                dd_start = i
            elif dd >= 0 and is_in_drawdown:
                is_in_drawdown = False
                max_dd_duration = max(max_dd_duration, i - dd_start)
        
        # 卡玛比率
        calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0
        
        # 交易统计
        sell_trades_df = pd.DataFrame([{
            'profit': t.price * t.quantity - t.quantity * (self.positions.get(t.stock_code, None) or Position('', 0, 0, None, 0)).avg_cost - t.commission - t.stamp_duty,
            'cost': t.quantity * (self.positions.get(t.stock_code, None) or Position('', 0, 0, None, 0)).avg_cost
        } for t in self.sell_trades])
        
        if sell_trades_df.empty:
            sell_trades_df = pd.DataFrame(columns=['profit', 'cost'])
        
        wins = sell_trades_df[sell_trades_df['profit'] > 0]
        losses = sell_trades_df[sell_trades_df['profit'] <= 0]
        
        win_rate = len(wins) / len(sell_trades_df) if len(sell_trades_df) > 0 else 0
        avg_win = wins['profit'].mean() / wins['cost'].mean() if len(wins) > 0 else 0
        avg_loss = abs(losses['profit'].mean() / losses['cost'].mean()) if len(losses) > 0 else 0
        profit_factor = (wins['profit'].sum() / abs(losses['profit'].sum())) if len(losses) > 0 and losses['profit'].sum() != 0 else float('inf')
        
        # 持仓统计
        holding_days = []
        for trade in self.sell_trades:
            # 估算持仓天数
            days = (trade.timestamp - self.current_date).days if hasattr(self, 'current_date') else 5
            holding_days.append(max(1, days))
        
        avg_holding_days = np.mean(holding_days) if holding_days else 0
        max_holding_days = max(holding_days) if holding_days else 0
        
        # 月度收益
        if len(equity_df) > 0:
            equity_df['date'] = pd.to_datetime(equity_df['date'])
            equity_df['month'] = equity_df['date'].dt.to_period('M')
            monthly_returns = equity_df.groupby('month')['total_equity'].apply(
                lambda x: (x.iloc[-1] / x.iloc[0]) - 1 if len(x) > 1 else 0
            )
        else:
            monthly_returns = pd.Series()
        
        return BacktestResult(
            total_return=total_return,
            annualized_return=annualized_return,
            benchmark_return=benchmark_return,
            volatility=volatility,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            max_drawdown_duration=max_dd_duration,
            calmar_ratio=calmar_ratio,
            num_trades=len(self.trades),
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            avg_holding_days=avg_holding_days,
            max_holding_days=max_holding_days,
            equity_curve=equity_df,
            trades=self.trades,
            monthly_returns=monthly_returns,
            daily_returns=daily_returns_series
        )
    
    def plot_results(self, result: BacktestResult, save_path: str = None):
        """绘制回测结果图表"""
        if not PLOT_AVAILABLE:
            print("[BacktestEngine] matplotlib not available. Skipping plot.")
            return
        
        if result.equity_curve is None or result.equity_curve.empty:
            print("[BacktestEngine] No equity curve data to plot.")
            return
        
        fig, axes = plt.subplots(3, 1, figsize=(12, 10))
        
        # 1. 权益曲线
        ax1 = axes[0]
        equity_df = result.equity_curve
        ax1.plot(equity_df['date'], equity_df['total_equity'], label='Portfolio', linewidth=1.5)
        ax1.fill_between(equity_df['date'], equity_df['cash'], equity_df['total_equity'], 
                         alpha=0.3, label='Position Value')
        ax1.set_title('Equity Curve', fontsize=12)
        ax1.set_ylabel('Capital')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 2. 回撤曲线
        ax2 = axes[1]
        cumulative = (1 + pd.Series(result.daily_returns)).cumprod()
        peak = cumulative.expanding().max()
        drawdown = (cumulative - peak) / peak * 100
        ax2.fill_between(range(len(drawdown)), drawdown, 0, alpha=0.3, color='red')
        ax2.plot(drawdown, color='red', linewidth=1)
        ax2.set_title(f'Drawdown (Max: {result.max_drawdown:.2%})', fontsize=12)
        ax2.set_ylabel('Drawdown (%)')
        ax2.grid(True, alpha=0.3)
        
        # 3. 月度收益
        ax3 = axes[2]
        if result.monthly_returns is not None and len(result.monthly_returns) > 0:
            monthly = result.monthly_returns * 100
            colors = ['green' if x >= 0 else 'red' for x in monthly]
            ax3.bar(range(len(monthly)), monthly, color=colors, alpha=0.7)
            ax3.set_title('Monthly Returns', fontsize=12)
            ax3.set_ylabel('Return (%)')
            ax3.set_xticks(range(len(monthly)))
            ax3.set_xticklabels([str(m) for m in monthly.index], rotation=45)
            ax3.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"[BacktestEngine] Plot saved to {save_path}")
        
        plt.show()
    
    def export_results(self, result: BacktestResult, output_dir: str = 'output'):
        """导出回测结果"""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 导出权益曲线
        if result.equity_curve is not None:
            equity_path = output_dir / 'equity_curve.csv'
            result.equity_curve.to_csv(equity_path, index=False)
        
        # 导出交易记录
        trades_path = output_dir / 'trades.csv'
        trades_data = [{
            'trade_id': t.trade_id,
            'date': t.timestamp,
            'stock_code': t.stock_code,
            'action': t.action,
            'price': t.price,
            'quantity': t.quantity,
            'commission': t.commission,
            'capital_after': t.capital_after
        } for t in result.trades]
        pd.DataFrame(trades_data).to_csv(trades_path, index=False)
        
        # 导出统计报告
        report_path = output_dir / 'backtest_report.json'
        report = result.to_dict()
        report['trades_count'] = len(result.trades)
        report['win_trades'] = len([t for t in result.trades if t.action == 'sell' and float(t.notes.split(': ')[1].split(',')[0]) > 0]) if result.trades else 0
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"[BacktestEngine] Results exported to {output_dir}")


def create_sample_signal_generator(threshold_buy: float = 0.7, threshold_sell: float = 0.4):
    """
    创建示例信号生成器
    
    简化策略:
    - 随机生成买入/卖出信号
    """
    np.random.seed(42)
    
    def signal_generator(current_data: pd.DataFrame, positions: Dict) -> List[Dict]:
        signals = []
        
        for _, row in current_data.iterrows():
            stock_code = row['stock_code']
            
            # 模拟信号强度
            signal_strength = np.random.random()
            
            if stock_code in positions:
                # 持仓股票
                if signal_strength < threshold_sell:
                    signals.append({
                        'stock_code': stock_code,
                        'action': 'sell',
                        'signal_strength': signal_strength,
                        'price': row['close']
                    })
            else:
                # 非持仓股票
                if signal_strength > threshold_buy:
                    signals.append({
                        'stock_code': stock_code,
                        'action': 'buy',
                        'signal_strength': signal_strength,
                        'price': row['close']
                    })
        
        return signals
    
    return signal_generator


if __name__ == '__main__':
    print("=" * 60)
    print("Backtest Engine Test")
    print("=" * 60)
    
    # 创建示例数据
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', '2024-03-31', freq='B')  # 工作日
    
    stock_codes = ['000001', '000002', '000004', '000005', '000006']
    
    data = []
    for date in dates:
        for stock in stock_codes:
            base_price = 10 + np.random.rand() * 10
            change = np.random.randn() * 0.02
            close = base_price * (1 + change)
            
            data.append({
                'date': date,
                'stock_code': stock,
                'open': close * (1 - np.random.rand() * 0.01),
                'high': close * (1 + np.random.rand() * 0.02),
                'low': close * (1 - np.random.rand() * 0.02),
                'close': close,
                'volume': np.random.randint(1000000, 10000000)
            })
    
    df = pd.DataFrame(data)
    
    print(f"\nGenerated sample data:")
    print(f"  Date range: {df['date'].min()} to {df['date'].max()}")
    print(f"  Total records: {len(df)}")
    
    # 创建回测引擎
    config = BacktestConfig(
        initial_capital=1000000,
        commission_rate=0.0003,
        stop_loss_pct=0.05,
        take_profit_pct=0.10
    )
    
    engine = BacktestEngine(config)
    
    # 创建信号生成器
    signal_gen = create_sample_signal_generator(threshold_buy=0.8, threshold_sell=0.3)
    
    # 运行回测
    result = engine.run(df, signal_gen)
    
    # 绘制结果
    engine.plot_results(result)
    
    # 导出结果
    engine.export_results(result)
    
    print("\n[Backtest Engine] Test completed!")

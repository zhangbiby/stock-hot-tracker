#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
回测引擎 - 完整实现
使用历史数据验证策略有效性
"""

import sqlite3
import json
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass

BASE_DIR = Path(__file__).parent
DB_FILE = BASE_DIR / "output" / "stock_tracker.db"

@dataclass
class Trade:
    """交易记录"""
    timestamp: str
    code: str
    name: str
    action: str  # 'buy' or 'sell'
    price: float
    quantity: int
    amount: float
    fee: float
    profit: float = 0
    profit_pct: float = 0
    reason: str = ""

@dataclass
class BacktestResult:
    """回测结果"""
    strategy_name: str
    start_date: str
    end_date: str
    initial_capital: float
    final_capital: float
    total_return: float
    total_return_pct: float
    win_rate: float
    profit_factor: float
    max_drawdown: float
    max_drawdown_pct: float
    sharpe_ratio: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_profit: float
    avg_loss: float
    avg_hold_days: float
    trades: List[Trade]

class BacktestEngine:
    """回测引擎"""
    
    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.positions = {}  # 当前持仓
        self.trades = []     # 交易记录
        self.daily_values = []  # 每日资产价值
        
    def run(self, start_date: str, end_date: str, strategy_config: dict) -> BacktestResult:
        """
        运行回测
        
        Args:
            start_date: '2026-03-01'
            end_date: '2026-03-27'
            strategy_config: {
                'signal_threshold': 50,
                'stop_loss': 0.03,
                'take_profit': 0.05,
                'max_holding_days': 3,
                'max_positions': 5,
                'position_size': 0.2
            }
        """
        print(f"[Backtest] 开始回测: {start_date} ~ {end_date}")
        print(f"[Backtest] 初始资金: {self.initial_capital:,.2f}")
        
        # 加载历史信号数据
        signals = self._load_historical_signals(start_date, end_date)
        print(f"[Backtest] 加载 {len(signals)} 条历史信号")
        
        # 按日期分组
        signals_by_date = self._group_signals_by_date(signals)
        
        # 遍历每个交易日
        for date in sorted(signals_by_date.keys()):
            daily_signals = signals_by_date[date]
            
            # 检查止盈止损
            self._check_stop_loss_take_profit(date, strategy_config)
            
            # 检查持仓天数
            self._check_holding_period(date, strategy_config)
            
            # 执行买入信号
            for signal in daily_signals:
                if signal['score'] >= strategy_config.get('signal_threshold', 50):
                    self._execute_buy(signal, date, strategy_config)
            
            # 记录每日资产价值
            self._record_daily_value(date)
        
        # 计算回测结果
        result = self._calculate_result(start_date, end_date, strategy_config)
        
        print(f"[Backtest] 回测完成")
        print(f"[Backtest] 最终资金: {result.final_capital:,.2f}")
        print(f"[Backtest] 总收益率: {result.total_return_pct:.2f}%")
        print(f"[Backtest] 胜率: {result.win_rate:.2f}%")
        
        return result
    
    def _load_historical_signals(self, start_date: str, end_date: str) -> List[Dict]:
        """加载历史信号"""
        try:
            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM signals 
                WHERE timestamp >= ? AND timestamp <= ?
                ORDER BY timestamp ASC
            ''', (start_date, end_date + ' 23:59:59'))
            
            signals = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return signals
        except:
            # 如果数据库不可用，从JSON加载
            return self._load_signals_from_json(start_date, end_date)
    
    def _load_signals_from_json(self, start_date: str, end_date: str) -> List[Dict]:
        """从JSON文件加载信号（兼容旧代码）"""
        signals_file = BASE_DIR / "output" / "signals_latest.json"
        if not signals_file.exists():
            return []
        
        with open(signals_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        signals = data.get('signals', [])
        # 过滤日期范围
        filtered = []
        for s in signals:
            signal_date = s.get('timestamp', '')[:10]
            if start_date <= signal_date <= end_date:
                filtered.append(s)
        return filtered
    
    def _group_signals_by_date(self, signals: List[Dict]) -> Dict[str, List[Dict]]:
        """按日期分组信号"""
        grouped = {}
        for signal in signals:
            date = signal.get('timestamp', '')[:10]
            if date not in grouped:
                grouped[date] = []
            grouped[date].append(signal)
        return grouped
    
    def _execute_buy(self, signal: Dict, date: str, config: dict):
        """执行买入"""
        code = signal['code']
        
        # 检查是否已持仓
        if code in self.positions:
            return
        
        # 检查最大持仓数量
        max_positions = config.get('max_positions', 5)
        if len(self.positions) >= max_positions:
            return
        
        # 计算买入金额
        position_size = config.get('position_size', 0.2)
        invest_amount = self.capital * position_size
        
        # 获取价格
        price = signal.get('price', 0)
        if price <= 0:
            return
        
        # 计算数量（100股整数）
        quantity = int(invest_amount / price / 100) * 100
        if quantity < 100:
            return
        
        amount = price * quantity
        fee = amount * 0.00025  # 手续费0.025%
        total_cost = amount + fee
        
        if total_cost > self.capital:
            return
        
        # 扣除资金
        self.capital -= total_cost
        
        # 记录持仓
        self.positions[code] = {
            'code': code,
            'name': signal.get('name', code),
            'buy_price': price,
            'quantity': quantity,
            'buy_date': date,
            'amount': amount,
            'fee': fee,
            'highest_price': price  # 用于跟踪止盈
        }
        
        # 记录交易
        trade = Trade(
            timestamp=f"{date} 09:30:00",
            code=code,
            name=signal.get('name', code),
            action='buy',
            price=price,
            quantity=quantity,
            amount=amount,
            fee=fee,
            reason=f"信号评分: {signal.get('score', 0)}"
        )
        self.trades.append(trade)
        
        print(f"[Backtest] {date} 买入 {code} {quantity}股 @ {price:.2f}")
    
    def _check_stop_loss_take_profit(self, date: str, config: dict):
        """检查止盈止损"""
        stop_loss = config.get('stop_loss', 0.03)
        take_profit = config.get('take_profit', 0.05)
        
        to_sell = []
        for code, pos in self.positions.items():
            # 获取当前价格（从当日信号或快照）
            current_price = self._get_current_price(code, date)
            if current_price <= 0:
                continue
            
            buy_price = pos['buy_price']
            profit_pct = (current_price - buy_price) / buy_price
            
            # 更新最高价（用于移动止盈）
            if current_price > pos['highest_price']:
                pos['highest_price'] = current_price
            
            # 检查止损
            if profit_pct <= -stop_loss:
                to_sell.append((code, current_price, '止损'))
            # 检查止盈
            elif profit_pct >= take_profit:
                to_sell.append((code, current_price, '止盈'))
            # 移动止盈：从最高点回撤3%
            elif current_price < pos['highest_price'] * 0.97 and profit_pct > 0:
                to_sell.append((code, current_price, '移动止盈'))
        
        # 执行卖出
        for code, price, reason in to_sell:
            self._execute_sell(code, price, date, reason)
    
    def _check_holding_period(self, date: str, config: dict):
        """检查持仓天数"""
        max_days = config.get('max_holding_days', 3)
        
        to_sell = []
        for code, pos in self.positions.items():
            buy_date = datetime.strptime(pos['buy_date'], '%Y-%m-%d')
            current_date = datetime.strptime(date, '%Y-%m-%d')
            hold_days = (current_date - buy_date).days
            
            if hold_days >= max_days:
                # 获取当前价格
                current_price = self._get_current_price(code, date)
                if current_price > 0:
                    to_sell.append((code, current_price, f'持仓{hold_days}天'))
        
        # 执行卖出
        for code, price, reason in to_sell:
            self._execute_sell(code, price, date, reason)
    
    def _execute_sell(self, code: str, price: float, date: str, reason: str):
        """执行卖出"""
        if code not in self.positions:
            return
        
        pos = self.positions[code]
        quantity = pos['quantity']
        amount = price * quantity
        
        # 计算费用
        fee = amount * 0.00025  # 手续费
        tax = amount * 0.0005   # 印花税（卖出时）
        total_fee = fee + tax
        
        # 计算盈亏
        cost = pos['amount'] + pos['fee']
        revenue = amount - total_fee
        profit = revenue - cost
        profit_pct = profit / cost * 100
        
        # 增加资金
        self.capital += revenue
        
        # 记录交易
        trade = Trade(
            timestamp=f"{date} 15:00:00",
            code=code,
            name=pos['name'],
            action='sell',
            price=price,
            quantity=quantity,
            amount=amount,
            fee=total_fee,
            profit=profit,
            profit_pct=profit_pct,
            reason=reason
        )
        self.trades.append(trade)
        
        # 移除持仓
        del self.positions[code]
        
        print(f"[Backtest] {date} 卖出 {code} {quantity}股 @ {price:.2f} 盈亏: {profit:,.2f} ({profit_pct:+.2f}%) [{reason}]")
    
    def _get_current_price(self, code: str, date: str) -> float:
        """获取指定日期的价格"""
        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT price FROM snapshots 
                WHERE code = ? AND timestamp LIKE ?
                ORDER BY timestamp DESC LIMIT 1
            ''', (code, f'{date}%'))
            row = cursor.fetchone()
            conn.close()
            return row[0] if row else 0
        except:
            return 0
    
    def _record_daily_value(self, date: str):
        """记录每日资产价值"""
        # 计算持仓市值
        position_value = 0
        for code, pos in self.positions.items():
            current_price = self._get_current_price(code, date)
            if current_price > 0:
                position_value += current_price * pos['quantity']
        
        total_value = self.capital + position_value
        self.daily_values.append({
            'date': date,
            'cash': self.capital,
            'position_value': position_value,
            'total_value': total_value
        })
    
    def _calculate_result(self, start_date: str, end_date: str, config: dict) -> BacktestResult:
        """计算回测结果"""
        # 计算最终资产价值（包含未平仓持仓）
        final_value = self.capital
        for code, pos in self.positions.items():
            # 使用买入价格计算（保守估计）
            final_value += pos['amount']
        
        # 总收益
        total_return = final_value - self.initial_capital
        total_return_pct = (total_return / self.initial_capital) * 100
        
        # 统计交易
        total_trades = len([t for t in self.trades if t.action == 'sell'])
        winning_trades = len([t for t in self.trades if t.action == 'sell' and t.profit > 0])
        losing_trades = total_trades - winning_trades
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        # 盈亏比
        avg_profit = sum(t.profit for t in self.trades if t.action == 'sell' and t.profit > 0) / winning_trades if winning_trades > 0 else 0
        avg_loss = sum(t.profit for t in self.trades if t.action == 'sell' and t.profit < 0) / losing_trades if losing_trades > 0 else 0
        profit_factor = abs(avg_profit / avg_loss) if avg_loss != 0 else float('inf')
        
        # 最大回撤
        max_drawdown = 0
        max_drawdown_pct = 0
        peak = self.initial_capital
        for dv in self.daily_values:
            if dv['total_value'] > peak:
                peak = dv['total_value']
            drawdown = peak - dv['total_value']
            drawdown_pct = (drawdown / peak) * 100
            if drawdown > max_drawdown:
                max_drawdown = drawdown
                max_drawdown_pct = drawdown_pct
        
        # 夏普比率（简化计算，假设无风险利率为3%）
        if len(self.daily_values) > 1:
            returns = []
            for i in range(1, len(self.daily_values)):
                daily_return = (self.daily_values[i]['total_value'] - self.daily_values[i-1]['total_value']) / self.daily_values[i-1]['total_value']
                returns.append(daily_return)
            
            avg_return = sum(returns) / len(returns)
            variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
            std_dev = variance ** 0.5
            
            # 年化夏普比率
            sharpe_ratio = ((avg_return * 252 - 0.03) / (std_dev * (252 ** 0.5))) if std_dev > 0 else 0
        else:
            sharpe_ratio = 0
        
        # 平均持仓天数
        hold_days = []
        buy_times = {}
        for t in self.trades:
            if t.action == 'buy':
                buy_times[t.code] = datetime.strptime(t.timestamp[:10], '%Y-%m-%d')
            elif t.action == 'sell' and t.code in buy_times:
                sell_date = datetime.strptime(t.timestamp[:10], '%Y-%m-%d')
                hold_days.append((sell_date - buy_times[t.code]).days)
        avg_hold_days = sum(hold_days) / len(hold_days) if hold_days else 0
        
        return BacktestResult(
            strategy_name=config.get('name', '默认策略'),
            start_date=start_date,
            end_date=end_date,
            initial_capital=self.initial_capital,
            final_capital=final_value,
            total_return=total_return,
            total_return_pct=total_return_pct,
            win_rate=win_rate,
            profit_factor=profit_factor,
            max_drawdown=max_drawdown,
            max_drawdown_pct=max_drawdown_pct,
            sharpe_ratio=sharpe_ratio,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            avg_profit=avg_profit,
            avg_loss=avg_loss,
            avg_hold_days=avg_hold_days,
            trades=self.trades
        )
    
    def generate_report(self, result: BacktestResult, output_file: str = None):
        """生成回测报告HTML"""
        if output_file is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = BASE_DIR / "output" / f"backtest_report_{timestamp}.html"
        
        html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>回测报告 - {result.strategy_name}</title>
    <style>
        body {{ font-family: 'Microsoft YaHei', sans-serif; background: #0f1419; color: #e0e0e0; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ text-align: center; padding: 30px; border-bottom: 2px solid #1a2332; margin-bottom: 30px; }}
        .header h1 {{ color: #00d4ff; }}
        .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .metric-card {{ background: rgba(0,212,255,0.1); padding: 20px; border-radius: 10px; text-align: center; }}
        .metric-value {{ font-size: 2rem; font-weight: bold; color: #00d4ff; }}
        .metric-label {{ color: #7a8fa6; margin-top: 5px; }}
        .positive {{ color: #2ed573; }}
        .negative {{ color: #ff4757; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th {{ background: rgba(0,212,255,0.2); padding: 12px; text-align: left; }}
        td {{ padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.1); }}
        tr:hover {{ background: rgba(255,255,255,0.05); }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 回测报告</h1>
            <p>{result.strategy_name} | {result.start_date} ~ {result.end_date}</p>
        </div>
        
        <div class="metrics">
            <div class="metric-card">
                <div class="metric-value {'positive' if result.total_return_pct > 0 else 'negative'}">{result.total_return_pct:+.2f}%</div>
                <div class="metric-label">总收益率</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{result.win_rate:.1f}%</div>
                <div class="metric-label">胜率</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{result.profit_factor:.2f}</div>
                <div class="metric-label">盈亏比</div>
            </div>
            <div class="metric-card">
                <div class="metric-value negative">{result.max_drawdown_pct:.2f}%</div>
                <div class="metric-label">最大回撤</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{result.sharpe_ratio:.2f}</div>
                <div class="metric-label">夏普比率</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{result.total_trades}</div>
                <div class="metric-label">交易次数</div>
            </div>
        </div>
        
        <h2 style="color: #00d4ff; margin-top: 30px;">交易明细</h2>
        <table>
            <thead>
                <tr>
                    <th>时间</th>
                    <th>代码</th>
                    <th>操作</th>
                    <th>价格</th>
                    <th>数量</th>
                    <th>盈亏</th>
                    <th>原因</th>
                </tr>
            </thead>
            <tbody>
'''
        
        for trade in result.trades:
            profit_class = 'positive' if trade.profit > 0 else 'negative' if trade.profit < 0 else ''
            profit_str = f'{trade.profit:+.2f}' if trade.action == 'sell' else '-'
            html += f'''
                <tr>
                    <td>{trade.timestamp}</td>
                    <td>{trade.code}</td>
                    <td>{'买入' if trade.action == 'buy' else '卖出'}</td>
                    <td>{trade.price:.2f}</td>
                    <td>{trade.quantity}</td>
                    <td class="{profit_class}">{profit_str}</td>
                    <td>{trade.reason}</td>
                </tr>
'''
        
        html += '''
            </tbody>
        </table>
    </div>
</body>
</html>'''
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"[Backtest] 报告已生成: {output_file}")
        return output_file


def main():
    """测试回测引擎"""
    print("=" * 60)
    print("回测引擎测试")
    print("=" * 60)
    
    # 创建回测引擎
    engine = BacktestEngine(initial_capital=100000)
    
    # 配置策略
    strategy_config = {
        'name': '短线3日策略',
        'signal_threshold': 50,
        'stop_loss': 0.03,
        'take_profit': 0.05,
        'max_holding_days': 3,
        'max_positions': 5,
        'position_size': 0.2
    }
    
    # 运行回测
    result = engine.run(
        start_date='2026-03-01',
        end_date='2026-03-27',
        strategy_config=strategy_config
    )
    
    # 生成报告
    report_path = engine.generate_report(result)
    
    print("\n" + "=" * 60)
    print("回测完成!")
    print(f"报告路径: {report_path}")
    print("=" * 60)


if __name__ == '__main__':
    main()

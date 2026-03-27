#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票持仓管理模块
支持买入标记、T+1卖出规则、持仓盈亏计算
使用数据库存储（兼容旧JSON接口）
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# 尝试导入数据库管理器
try:
    from db_manager import db_manager
    USE_DATABASE = True
except ImportError:
    USE_DATABASE = False


class Portfolio:
    """持仓管理类"""
    
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = Path(__file__).parent / "output"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.holdings_file = self.data_dir / "holdings.json"
        self.history_file = self.data_dir / "trade_history.json"
    
    def _load_holdings(self) -> dict:
        """加载持仓数据（兼容旧接口）"""
        if USE_DATABASE:
            # 从数据库加载
            holdings = db_manager.get_holdings()
            return {
                "holdings": holdings,
                "cash": 100000.0  # 默认资金
            }
        
        # 从JSON加载（兼容旧代码）
        if self.holdings_file.exists():
            try:
                with open(self.holdings_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {"holdings": [], "cash": 100000.0}
    
    def _save_holdings(self, data: dict):
        """保存持仓数据（兼容旧接口）"""
        if USE_DATABASE:
            # 数据库实时更新，无需批量保存
            pass
        else:
            # 保存到JSON（兼容旧代码）
            with open(self.holdings_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _load_history(self) -> list:
        """加载交易历史（兼容旧接口）"""
        if USE_DATABASE:
            return db_manager.get_trades()
        
        # 从JSON加载（兼容旧代码）
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return []
    
    def _save_history(self, history: list):
        """保存交易历史（兼容旧接口）"""
        if not USE_DATABASE:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
    
    def is_trading_day(self, date: datetime = None) -> bool:
        """检查是否为交易日"""
        if date is None:
            date = datetime.now()
        # 周末不是交易日
        if date.weekday() >= 5:
            return False
        return True
    
    def get_next_trading_day(self, from_date: datetime = None) -> datetime:
        """获取下一个交易日"""
        if from_date is None:
            from_date = datetime.now()
        
        next_day = from_date + timedelta(days=1)
        while not self.is_trading_day(next_day):
            next_day += timedelta(days=1)
        return next_day
    
    def can_sell(self, buy_date: str) -> tuple[bool, str]:
        """
        检查是否可以卖出（T+1规则）
        返回: (是否可以卖出, 原因)
        """
        buy_dt = datetime.strptime(buy_date, "%Y-%m-%d")
        
        # 今天的日期
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # 计算可卖出日期（买入后下一个交易日）
        sellable_date = self.get_next_trading_day(buy_dt)
        sellable_date = sellable_date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        if today >= sellable_date:
            return True, "可卖出"
        else:
            # 计算还需要等待多少天
            days_wait = (sellable_date - today).days
            if days_wait == 1:
                return False, f"明天({sellable_date.strftime('%m-%d')})可卖出"
            return False, f"{days_wait}天后({sellable_date.strftime('%m-%d')})可卖出"
    
    def buy_stock(self, code: str, name: str, price: float, quantity: int, signal_time: str = None) -> dict:
        """
        买入股票
        """
        if signal_time is None:
            signal_time = datetime.now().strftime("%Y-%m-%d")
        
        data = self._load_holdings()
        
        # 检查是否已持仓
        for h in data["holdings"]:
            if h["code"] == code:
                return {"success": False, "message": f"已在持仓中，无需重复买入"}
        
        # 计算买入金额
        cost = price * quantity
        if cost > data["cash"]:
            return {"success": False, "message": f"资金不足，需要{cost:.2f}元，当前可用{data['cash']:.2f}元"}
        
        # 添加持仓
        holding = {
            "code": code,
            "name": name,
            "buy_price": price,
            "quantity": quantity,
            "buy_date": signal_time,
            "sellable_date": self.get_next_trading_day(datetime.now()).strftime("%Y-%m-%d"),
            "buy_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        data["holdings"].append(holding)
        
        # 扣除资金
        data["cash"] -= cost
        
        self._save_holdings(data)
        
        # 同时保存到数据库
        if USE_DATABASE:
            can_sell = self.get_next_trading_day(datetime.now()) <= datetime.now()
            db_manager.add_holding(code, name, price, quantity, signal_time, can_sell)
            db_manager.record_trade(code, name, "buy", price, quantity, cost * 0.00025)  # 手续费0.025%
        
        # 记录历史
        history = self._load_history()
        history.append({
            "action": "BUY",
            "code": code,
            "name": name,
            "price": price,
            "quantity": quantity,
            "amount": cost,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
        self._save_history(history)
        
        return {
            "success": True,
            "message": f"买入成功 {name} {quantity}股 @{price}",
            "holding": holding
        }
    
    def add_custom_holding(self, code: str, name: str, price: float, quantity: int, buy_date: str = None) -> dict:
        """
        添加自定义持仓（不检查资金，不记录交易历史）
        用于跟踪持仓，非实际交易
        """
        if buy_date is None:
            buy_date = datetime.now().strftime("%Y-%m-%d")
        
        data = self._load_holdings()
        
        # 检查是否已持仓
        for h in data["holdings"]:
            if h["code"] == code:
                # 更新现有持仓
                h["buy_price"] = price
                h["quantity"] = quantity
                h["buy_date"] = buy_date
                h["custom"] = True  # 标记为自定义持仓
                self._save_holdings(data)
                return {
                    "success": True, 
                    "message": f"已更新自定义持仓 {name} {quantity}股 @{price}",
                    "holding": h
                }
        
        # 添加新持仓
        holding = {
            "code": code,
            "name": name,
            "buy_price": price,
            "quantity": quantity,
            "buy_date": buy_date,
            "sellable_date": self.get_next_trading_day(datetime.now()).strftime("%Y-%m-%d"),
            "buy_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "custom": True  # 标记为自定义持仓
        }
        data["holdings"].append(holding)
        
        # 不扣除资金（自定义持仓不占用模拟资金）
        
        self._save_holdings(data)
        
        # 同时保存到数据库
        if USE_DATABASE:
            can_sell = self.get_next_trading_day(datetime.strptime(buy_date, "%Y-%m-%d")) <= datetime.now()
            db_manager.add_holding(code, name, price, quantity, buy_date, can_sell)
        
        # 不记录交易历史（自定义持仓）
        
        return {
            "success": True,
            "message": f"已添加自定义持仓 {name} {quantity}股 @{price}",
            "holding": holding
        }
    
    def sell_stock(self, code: str, price: float, quantity: int = None) -> dict:
        """
        卖出股票
        """
        data = self._load_holdings()
        
        # 找到持仓
        holding = None
        holding_idx = None
        for i, h in enumerate(data["holdings"]):
            if h["code"] == code:
                holding = h
                holding_idx = i
                break
        
        if holding is None:
            return {"success": False, "message": f"未持仓 {code}"}
        
        # 检查是否可以卖出
        can_sell, reason = self.can_sell(holding["buy_date"])
        if not can_sell:
            return {"success": False, "message": f"T+1规则: {reason}"}
        
        # 确定卖出数量
        sell_qty = quantity if quantity else holding["quantity"]
        if sell_qty > holding["quantity"]:
            return {"success": False, "message": f"持仓不足，仅剩{holding['quantity']}股"}
        
        # 计算卖出金额
        revenue = price * sell_qty
        profit = (price - holding["buy_price"]) * sell_qty
        profit_pct = (price - holding["buy_price"]) / holding["buy_price"] * 100
        
        # 更新持仓或删除
        if sell_qty == holding["quantity"]:
            data["holdings"].pop(holding_idx)
            # 从数据库删除
            if USE_DATABASE:
                db_manager.delete_holding(code)
        else:
            data["holdings"][holding_idx]["quantity"] -= sell_qty
            # 更新数据库
            if USE_DATABASE:
                db_manager.update_holding(code, quantity=holding["quantity"] - sell_qty)
        
        # 增加资金
        data["cash"] += revenue
        
        self._save_holdings(data)
        
        # 记录交易
        if USE_DATABASE:
            fee = revenue * 0.00025  # 手续费
            tax = revenue * 0.0005 if sell_qty == holding["quantity"] else 0  # 印花税（卖出时）
            db_manager.record_trade(code, holding["name"], "sell", price, sell_qty, 
                                   fee + tax, profit, profit_pct)
        
        # 记录历史
        history = self._load_history()
        history.append({
            "action": "SELL",
            "code": code,
            "name": holding["name"],
            "price": price,
            "quantity": sell_qty,
            "amount": revenue,
            "profit": profit,
            "profit_pct": profit_pct,
            "buy_price": holding["buy_price"],
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
        self._save_history(history)
        
        return {
            "success": True,
            "message": f"卖出成功 {holding['name']} {sell_qty}股 @{price}",
            "profit": profit,
            "profit_pct": profit_pct
        }
    
    def get_holdings(self) -> list:
        """获取当前持仓"""
        data = self._load_holdings()
        return data["holdings"]
    
    def get_holdings_with_status(self) -> list:
        """获取持仓及状态（含T+1信息）"""
        data = self._load_holdings()
        holdings = []
        
        for h in data["holdings"]:
            can_sell, reason = self.can_sell(h["buy_date"])
            holdings.append({
                **h,
                "can_sell": can_sell,
                "sell_status": reason,
            })
        
        return holdings
    
    def get_history(self, limit: int = 50) -> list:
        """获取交易历史"""
        history = self._load_history()
        return history[-limit:]
    
    def get_portfolio_value(self, current_prices: dict) -> dict:
        """计算持仓市值和盈亏"""
        data = self._load_holdings()
        
        total_cost = 0
        total_value = 0
        holdings_detail = []
        
        for h in data["holdings"]:
            code = h["code"]
            cost = h["buy_price"] * h["quantity"]
            current_price = current_prices.get(code, h["buy_price"])
            value = current_price * h["quantity"]
            profit = (current_price - h["buy_price"]) * h["quantity"]
            profit_pct = (current_price - h["buy_price"]) / h["buy_price"] * 100
            
            can_sell, reason = self.can_sell(h["buy_date"])
            
            holdings_detail.append({
                **h,
                "current_price": current_price,
                "cost": cost,
                "value": value,
                "profit": profit,
                "profit_pct": profit_pct,
                "can_sell": can_sell,
                "sell_status": reason,
            })
            
            total_cost += cost
            total_value += value
        
        return {
            "cash": data["cash"],
            "total_cost": total_cost,
            "total_value": total_value,
            "total_assets": data["cash"] + total_value,
            "total_profit": total_value - total_cost,
            "profit_rate": (total_value - total_cost) / total_cost * 100 if total_cost > 0 else 0,
            "holdings": holdings_detail,
        }


def main():
    """测试"""
    portfolio = Portfolio()
    
    print("=== 持仓管理测试 ===\n")
    
    # 模拟买入
    print("1. 买入测试:")
    result = portfolio.buy_stock("601016", "节能风电", 5.40, 1000)
    print(f"   {result}")
    
    # 查看持仓
    print("\n2. 当前持仓:")
    holdings = portfolio.get_holdings_with_status()
    for h in holdings:
        print(f"   {h['name']} ({h['code']}): 买入价={h['buy_price']}, 数量={h['quantity']}, 可卖出: {h['sell_status']}")
    
    # 查看可交易账户
    print(f"\n3. 账户资金: {portfolio._load_holdings()['cash']:.2f}元")


if __name__ == "__main__":
    main()

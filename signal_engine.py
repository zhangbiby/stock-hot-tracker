#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票信号计算引擎 v3.0
多因子规则模型 + 机器学习辅助 + 多智能体系统集成
"""

import json
from datetime import datetime
from pathlib import Path
from history_store import (
    get_prev_rank, get_stock_history,
    get_industry_stocks, save_snapshot,
    get_latest_snapshot, init_storage,
    get_price_history
)
from portfolio import Portfolio
from indicators import add_technical_indicators, get_indicator_features

# 多智能体系统集成（可选）
try:
    from agents import Orchestrator
    from memory import MemoryStore
    MULTI_AGENT_AVAILABLE = True
except ImportError:
    MULTI_AGENT_AVAILABLE = False
    print("[SignalEngine] 多智能体模块未找到，使用传统引擎")

BASE_DIR   = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"


class MLModel:
    """机器学习模型封装（可选，不存在时静默跳过）"""
    
    def __init__(self):
        self.model   = None
        self.scaler  = None
        self.feature_cols = []
        self.accuracy = 0.0
        self._load()
    
    def _load(self):
        """尝试加载模型，失败则静默跳过"""
        model_file = OUTPUT_DIR / "stock_model.pkl"
        if not model_file.exists():
            return
        
        try:
            import joblib
            data = joblib.load(model_file)
            self.model        = data['model']
            self.scaler       = data['scaler']
            self.feature_cols = data['feature_cols']
            self.accuracy     = data.get('accuracy', 0.0)
            print(f"ML model loaded (accuracy={self.accuracy:.4f})")
        except Exception as e:
            print(f"ML model load failed (skipping): {e}")
    
    @property
    def available(self) -> bool:
        return self.model is not None and self.scaler is not None
    
    def predict_proba(self, stock: dict) -> float | None:
        """
        预测上涨概率
        Returns: float [0,1] 或 None（模型不可用）
        """
        if not self.available:
            return None
        
        try:
            features = get_indicator_features(stock)
            
            # 构建特征向量（缺失值填均值/中性值）
            defaults = {
                'rsi': 50, 'macd': 0, 'bb_position': 0.5,
                'ma5_diff': 0, 'ma20_diff': 0,
                'change_pct': 0, 'turnover_rate': 0,
                'volume_ratio': 1, 'rank': 100, 'amplitude': 0
            }
            
            row = []
            for col in self.feature_cols:
                val = features.get(col)
                if val is None:
                    val = defaults.get(col, 0)
                row.append(float(val))
            
            import numpy as np
            X = np.array([row])
            X_scaled = self.scaler.transform(X)
            proba = self.model.predict_proba(X_scaled)[0]
            
            # 返回上涨概率（class=1）
            classes = list(self.model.classes_)
            if 1 in classes:
                return float(proba[classes.index(1)])
            return float(proba[-1])
            
        except Exception as e:
            return None


# 全局模型实例（懒加载）
_ml_model: MLModel | None = None

def get_ml_model() -> MLModel:
    global _ml_model
    if _ml_model is None:
        _ml_model = MLModel()
    return _ml_model


class SignalEngine:
    """信号计算引擎 v2.0"""
    
    SIGNAL_THRESHOLDS = {
        'strong_buy': 60,
        'buy': 40,
        'hold': 20,
    }
    
    # 模型得分权重（初期低权重，数据充足后可调高）
    ML_WEIGHT = 0.15   # 15%
    
    def __init__(self):
        self.ml = get_ml_model()
    
    # ── 规则因子 ──────────────────────────────────────────────────────────
    
    def calculate_rank_trend(self, code: str, current_rank: int) -> tuple[int, list]:
        score, reasons = 0, []
        
        prev_5m = get_prev_rank(code, minutes_ago=5)
        if prev_5m:
            delta = prev_5m - current_rank
            if delta >= 10:
                score += 12; reasons.append(f"5分钟上升{delta}位")
            elif delta >= 5:
                score += 6;  reasons.append(f"5分钟上升{delta}位")
            elif delta <= -10:
                score -= 15; reasons.append(f"5分钟下降{abs(delta)}位")
        
        prev_1h = get_prev_rank(code, minutes_ago=60)
        if prev_1h:
            delta = prev_1h - current_rank
            if delta >= 10:
                score += 10; reasons.append(f"1小时上升{delta}位")
            elif delta <= -10:
                score -= 10; reasons.append(f"1小时下降{abs(delta)}位")
        
        return score, reasons
    
    def calculate_volume_price(self, stock: dict) -> tuple[int, str]:
        change_pct   = float(stock.get('change_pct', 0) or 0)
        volume_ratio = float(stock.get('volume_ratio', 1) or 1)
        
        if change_pct > 5 and volume_ratio > 1.5:
            return 30, f"涨幅{change_pct:.1f}%+量比{volume_ratio:.1f}，强势启动"
        elif change_pct > 3 and volume_ratio > 1.2:
            return 20, "量价配合良好"
        elif change_pct > 0 and volume_ratio > 1:
            return 10, "放量上涨"
        elif change_pct < -3 and volume_ratio > 1.5:
            return -15, "放量下跌，注意风险"
        return 0, "量价正常"
    
    def calculate_turnover_risk(self, stock: dict) -> tuple[int, str]:
        tr = float(stock.get('turnover_rate', 0) or 0)
        if tr > 20:   return -15, f"换手率{tr:.1f}%，极度活跃"
        if tr > 15:   return -10, f"换手率{tr:.1f}%，活跃度高"
        return 0, f"换手率{tr:.1f}%，正常"
    
    def calculate_bias(self, stock: dict) -> tuple[int, str]:
        change_pct = float(stock.get('change_pct', 0) or 0)
        if change_pct > 9.5:  return -10, "接近涨停，追高风险"
        if change_pct > 7:    return -5,  "涨幅较大"
        if change_pct < -7:   return 15,  "可能超跌反弹"
        if change_pct < -3:   return 5,   "回调中"
        return 0, "正常区间"
    
    def calculate_industry_effect(self, stock: dict) -> tuple[int, list]:
        code     = stock.get('code', '')
        industry = stock.get('industry', '')
        if not industry:
            return 0, []
        
        same = get_industry_stocks(code, hours=1)
        cnt  = len(same) + 1
        
        if cnt >= 5:  return 15, [f"{industry}板块{cnt}只股上榜"]
        if cnt >= 3:  return 10, [f"{industry}板块{cnt}只股上榜"]
        if cnt >= 2:  return 5,  [f"{industry}板块{cnt}只股上榜"]
        return 0, []
    
    def calculate_pe_risk(self, stock: dict) -> tuple[int, str]:
        pe_ratio = stock.get('pe_ratio')
        if pe_ratio is None or pe_ratio == 0:
            return 0, ""
        try:
            pe = float(pe_ratio)
        except:
            return 0, ""
        
        if pe < 0:    return -15, f"PE为负，亏损"
        if pe > 100:  return -10, f"PE={pe:.0f}，估值过高"
        if pe > 50:   return -5,  f"PE={pe:.0f}，估值偏高"
        return 0, f"PE={pe:.0f}，合理"
    
    def calculate_technical_score(self, stock: dict) -> tuple[int, list]:
        """基于技术指标的规则得分"""
        score, reasons = 0, []
        
        rsi = stock.get('rsi')
        if rsi is not None:
            if rsi < 30:
                score += 10; reasons.append(f"RSI={rsi:.0f}，超卖区间")
            elif rsi > 70:
                score -= 8;  reasons.append(f"RSI={rsi:.0f}，超买区间")
        
        bb_pos = stock.get('bb_position')
        if bb_pos is not None:
            if bb_pos < 0.2:
                score += 8;  reasons.append(f"布林带下轨附近，支撑位")
            elif bb_pos > 0.8:
                score -= 6;  reasons.append(f"布林带上轨附近，压力位")
        
        macd = stock.get('macd')
        if macd is not None:
            if macd > 0:
                score += 5;  reasons.append("MACD金叉区域")
            elif macd < 0:
                score -= 3;  reasons.append("MACD死叉区域")
        
        ma5_diff = stock.get('ma5_diff')
        if ma5_diff is not None:
            if -2 < ma5_diff < 2:
                score += 3;  reasons.append("价格在5日均线附近")
        
        return score, reasons
    
    # ── 模型得分 ──────────────────────────────────────────────────────────
    
    def calculate_model_score(self, stock: dict) -> tuple[int, str, float | None]:
        """
        计算模型预测得分
        Returns: (score, reason, up_proba)
        """
        if not self.ml.available:
            return 0, "", None
        
        up_proba = self.ml.predict_proba(stock)
        if up_proba is None:
            return 0, "", None
        
        # 将概率映射为得分 [-10, 20]
        # 0.5 → 0分，1.0 → 20分，0.0 → -10分
        if up_proba >= 0.5:
            raw_score = (up_proba - 0.5) * 40   # [0, 20]
        else:
            raw_score = (up_proba - 0.5) * 20   # [-10, 0]
        
        # 乘以权重
        weighted_score = int(raw_score * self.ML_WEIGHT)
        reason = f"模型预测上涨概率{up_proba*100:.0f}%"
        
        return weighted_score, reason, up_proba
    
    # ── 卖出信号评分体系 ──────────────────────────────────────────────────

    def calculate_sell_signal(self, stock: dict, holding: dict, cur_price: float) -> dict:
        """
        独立卖出信号评分体系
        
        卖出得分越高 → 越应该卖出
        
        Returns:
            {
                sell_signal:  "强力卖出" | "建议卖出" | "考虑减仓" | "持有观察" | "继续持有",
                sell_strength: 1-5,
                sell_score:   int,
                sell_reasons: list,
                sell_risks:   list,
            }
        """
        sell_score   = 0
        sell_reasons = []
        sell_risks   = []

        buy_price  = holding.get('buy_price', 0)
        quantity   = holding.get('quantity', 0)
        can_sell   = holding.get('can_sell', False)
        sell_status = holding.get('sell_status', '')

        if buy_price <= 0:
            return self._sell_result(0, [], [], can_sell, sell_status)

        profit_pct = (cur_price - buy_price) / buy_price * 100

        # ── 1. 止盈因子 ──────────────────────────────────────────────────
        if profit_pct >= 20:
            sell_score += 40
            sell_reasons.append(f"盈利{profit_pct:.1f}%，已达强止盈线(20%)")
        elif profit_pct >= 10:
            sell_score += 25
            sell_reasons.append(f"盈利{profit_pct:.1f}%，达到止盈线(10%)")
        elif profit_pct >= 5:
            sell_score += 10
            sell_reasons.append(f"盈利{profit_pct:.1f}%，可考虑部分止盈")

        # ── 2. 止损因子 ──────────────────────────────────────────────────
        if profit_pct <= -10:
            sell_score += 45
            sell_risks.append(f"亏损{abs(profit_pct):.1f}%，已触发强止损线(-10%)")
        elif profit_pct <= -5:
            sell_score += 30
            sell_risks.append(f"亏损{abs(profit_pct):.1f}%，触发止损线(-5%)")
        elif profit_pct <= -3:
            sell_score += 15
            sell_risks.append(f"亏损{abs(profit_pct):.1f}%，接近止损线")

        # ── 3. 人气衰退因子 ──────────────────────────────────────────────
        rank = stock.get('rank', 100)
        prev_rank_5m = get_prev_rank(stock.get('code', ''), minutes_ago=5)
        prev_rank_1h = get_prev_rank(stock.get('code', ''), minutes_ago=60)

        if prev_rank_5m:
            rank_drop = rank - prev_rank_5m   # 正数=排名下降（人气减退）
            if rank_drop >= 15:
                sell_score += 20
                sell_reasons.append(f"5分钟人气下降{rank_drop}位，关注度快速衰退")
            elif rank_drop >= 8:
                sell_score += 10
                sell_reasons.append(f"5分钟人气下降{rank_drop}位")

        if prev_rank_1h:
            rank_drop_1h = rank - prev_rank_1h
            if rank_drop_1h >= 20:
                sell_score += 15
                sell_reasons.append(f"1小时人气下降{rank_drop_1h}位，持续衰退")

        # ── 4. 技术面卖出信号 ────────────────────────────────────────────
        rsi = stock.get('rsi')
        if rsi is not None:
            if rsi > 80:
                sell_score += 20
                sell_reasons.append(f"RSI={rsi:.0f}，严重超买")
            elif rsi > 70:
                sell_score += 10
                sell_reasons.append(f"RSI={rsi:.0f}，超买区间")

        bb_pos = stock.get('bb_position')
        if bb_pos is not None:
            if bb_pos > 0.9:
                sell_score += 15
                sell_reasons.append("价格触及布林带上轨，压力位")
            elif bb_pos > 0.8:
                sell_score += 8
                sell_reasons.append("价格接近布林带上轨")

        macd = stock.get('macd')
        if macd is not None and macd < -0.05:
            sell_score += 8
            sell_reasons.append("MACD死叉，趋势转弱")

        # ── 5. 量价背离因子 ──────────────────────────────────────────────
        change_pct   = float(stock.get('change_pct', 0) or 0)
        volume_ratio = float(stock.get('volume_ratio', 1) or 1)

        if change_pct < 0 and volume_ratio > 1.5:
            sell_score += 20
            sell_reasons.append(f"放量下跌(量比{volume_ratio:.1f})，主力出货信号")
        elif change_pct < -3 and volume_ratio > 1.2:
            sell_score += 12
            sell_reasons.append("量价背离，下跌加速")

        # ── 6. 换手率异常 ────────────────────────────────────────────────
        turnover = float(stock.get('turnover_rate', 0) or 0)
        if turnover > 20 and profit_pct > 0:
            sell_score += 15
            sell_reasons.append(f"换手率{turnover:.1f}%极高，筹码松动")
        elif turnover > 15 and profit_pct > 5:
            sell_score += 8
            sell_reasons.append(f"换手率{turnover:.1f}%偏高，注意出货")

        # ── 7. 涨停板次日风险 ────────────────────────────────────────────
        if change_pct > 9.5:
            sell_score += 10
            sell_risks.append("接近涨停，次日高开低走风险")

        # ── 8. T+1 状态 ──────────────────────────────────────────────────
        if not can_sell:
            # T+1 未到，不能卖出，降低卖出得分
            sell_score = max(0, sell_score - 5)
            sell_risks.append(f"T+1限制: {sell_status}")

        return self._sell_result(sell_score, sell_reasons, sell_risks, can_sell, sell_status)

    def _sell_result(self, score: int, reasons: list, risks: list,
                     can_sell: bool, sell_status: str) -> dict:
        """根据卖出得分生成卖出信号"""
        if score >= 60:
            sell_signal, sell_strength = "强力卖出", 5
        elif score >= 40:
            sell_signal, sell_strength = "建议卖出", 4
        elif score >= 20:
            sell_signal, sell_strength = "考虑减仓", 3
        elif score >= 5:
            sell_signal, sell_strength = "持有观察", 2
        else:
            sell_signal, sell_strength = "继续持有", 1

        return {
            'sell_signal':   sell_signal,
            'sell_strength': sell_strength,
            'sell_score':    score,
            'sell_reasons':  reasons[:4],
            'sell_risks':    risks[:3],
            'can_sell':      can_sell,
            'sell_status':   sell_status,
        }
    
    def calculate_signal(self, stock: dict) -> dict:
        code       = stock.get('code', '')
        name       = stock.get('name', '')
        rank       = stock.get('rank', 0)
        change_pct = float(stock.get('change_pct', 0) or 0)
        
        total_score = 0
        reasons     = []
        risks       = []
        factors     = []  # 新增：因子详情
        
        # 1. 人气趋势
        s, r = self.calculate_rank_trend(code, rank)
        total_score += s; reasons.extend([f"人气: {x}" for x in r])
        factors.append({'name': '人气趋势', 'score': s, 'reason': r[0] if r else '排名稳定'})
        
        # 2. 量价配合
        s, r = self.calculate_volume_price(stock)
        total_score += s
        if r != "量价正常": reasons.append(f"量价: {r}")
        factors.append({'name': '量价配合', 'score': s, 'reason': r})
        
        # 3. 换手率风险
        s, r = self.calculate_turnover_risk(stock)
        total_score += s
        if s < 0: risks.append(r)
        factors.append({'name': '换手率风险', 'score': s, 'reason': r})
        
        # 4. 乖离率
        s, r = self.calculate_bias(stock)
        total_score += s
        if r != "正常区间": reasons.append(f"乖离: {r}")
        factors.append({'name': '乖离率', 'score': s, 'reason': r})
        
        # 5. 板块效应
        s, r = self.calculate_industry_effect(stock)
        total_score += s; reasons.extend(r)
        factors.append({'name': '板块效应', 'score': s, 'reason': r[0] if r else '板块正常'})
        
        # 6. 估值风险
        s, r = self.calculate_pe_risk(stock)
        total_score += s
        if s < 0 and r: risks.append(r)
        factors.append({'name': '估值风险', 'score': s, 'reason': r if r else '估值正常'})
        
        # 7. 技术指标（规则）
        s, r = self.calculate_technical_score(stock)
        total_score += s; reasons.extend(r)
        factors.append({'name': '技术指标', 'score': s, 'reason': r[0] if r else '技术中性'})
        
        # 8. 机器学习模型得分（辅助，低权重）
        ml_score, ml_reason, up_proba = self.calculate_model_score(stock)
        total_score += ml_score
        if ml_reason: reasons.append(ml_reason)
        factors.append({'name': 'ML模型', 'score': ml_score, 'reason': ml_reason if ml_reason else '无预测'})
        
        # 通用风险
        if change_pct > 7:
            risks.append("短期涨幅较大，注意追高风险")
        
        # 确定信号
        if total_score >= self.SIGNAL_THRESHOLDS['strong_buy']:
            signal, strength = "Strong Buy", 5
        elif total_score >= self.SIGNAL_THRESHOLDS['buy']:
            signal, strength = "Buy", 4
        elif total_score >= self.SIGNAL_THRESHOLDS['hold']:
            signal, strength = "Hold", 3
        elif total_score >= 0:
            signal, strength = "Caution", 2
        else:
            signal, strength = "Risk", 1
        
        result = {
            'code':       code,
            'name':       name,
            'rank':       rank,
            'signal':     signal,
            'strength':   strength,
            'score':      total_score,
            'reasons':    reasons[:5],
            'risks':      risks[:3],
            'factors':    factors,  # 新增
            'price':      stock.get('price'),
            'change_pct': change_pct,
            'signal_time':datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'up_proba':   round(up_proba, 4) if up_proba is not None else None,
            'ml_score':   ml_score,
            'has_ml':     up_proba is not None,
            'suggestion': self._generate_suggestion(signal, total_score, up_proba),
        }
        return result
    
    def _generate_suggestion(self, signal: str, score: int, up_proba: float) -> str:
        """生成交易建议"""
        suggestions = {
            'Strong Buy': '强烈建议买入，多因子共振，上涨概率高',
            'Buy': '建议买入，信号积极，可适度建仓',
            'Hold': '建议持有观望，信号中性，等待更明确方向',
            'Caution': '建议谨慎，信号偏弱，注意风险控制',
            'Risk': '建议回避，风险信号明显，不宜参与',
        }
        return suggestions.get(signal, '建议观望')
    
    def process_all(self, stocks: list[dict]) -> list[dict]:
        """处理所有股票，先计算技术指标再计算信号"""
        print("\n[SignalEngine] 计算技术指标...")
        
        # 为每只股票添加技术指标
        for stock in stocks:
            code = stock.get('code', '')
            if code:
                price_history = get_price_history(code, days=60)
                # 提取价格列表（如果是字典列表）
                if price_history and isinstance(price_history[0], dict):
                    prices = [p.get('price', 0) for p in price_history]
                else:
                    prices = price_history
                add_technical_indicators(stock, prices)
        
        print(f"[SignalEngine] 计算买卖信号 (ML={'enabled' if self.ml.available else 'disabled'})...")
        
        signals = []
        portfolio    = Portfolio()
        holdings     = portfolio.get_holdings_with_status()
        holding_codes = {h['code']: h for h in holdings}
        
        for stock in stocks:
            signal = self.calculate_signal(stock)
            code   = signal['code']
            
            if code in holding_codes:
                h = holding_codes[code]
                cur_price = float(signal.get('price') or 0)
                profit     = (cur_price - h['buy_price']) * h['quantity']
                profit_pct = ((cur_price - h['buy_price']) / h['buy_price'] * 100) if h['buy_price'] > 0 else 0

                # 计算独立卖出信号
                sell_info = self.calculate_sell_signal(stock, h, cur_price)

                signal['in_portfolio'] = True
                signal['holding_info'] = {
                    'buy_price':     h['buy_price'],
                    'quantity':      h['quantity'],
                    'profit':        profit,
                    'profit_pct':    profit_pct,
                    'can_sell':      h['can_sell'],
                    'sell_status':   h['sell_status'],
                    # 卖出信号
                    'sell_signal':   sell_info['sell_signal'],
                    'sell_strength': sell_info['sell_strength'],
                    'sell_score':    sell_info['sell_score'],
                    'sell_reasons':  sell_info['sell_reasons'],
                    'sell_risks':    sell_info['sell_risks'],
                }
                signal['sell_signal']   = sell_info['sell_signal']
                signal['sell_strength'] = sell_info['sell_strength']
                signal['sell_score']    = sell_info['sell_score']
                signal['sell_alert']    = sell_info['sell_strength'] >= 3  # 考虑减仓及以上才提示
            else:
                signal['in_portfolio'] = False
                signal['holding_info'] = None
                signal['sell_alert']   = False
            
            signals.append(signal)
        
        signals.sort(key=lambda x: (x['strength'], x['score']), reverse=True)
        return signals


def save_signals_to_json(signals: list[dict]):
    """保存信号到 JSON 文件"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    filepath = OUTPUT_DIR / "signals_latest.json"
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump({
            "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "signals": signals
        }, f, ensure_ascii=False, indent=2)
    
    return filepath


def load_signals_from_json() -> list[dict]:
    filepath = OUTPUT_DIR / "signals_latest.json"
    if filepath.exists():
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f).get("signals", [])
        except:
            pass
    return []


def calculate_signal_with_multi_agent(stock: dict, orchestrator) -> dict:
    """
    使用多智能体系统计算信号
    
    Args:
        stock: 股票数据
        orchestrator: 多智能体协调器实例
        
    Returns:
        信号字典（与传统格式兼容）
    """
    try:
        # 构建分析上下文
        code = stock.get('code', '')
        name = stock.get('name', '')
        price = float(stock.get('price', 0) or 0)
        change_pct = float(stock.get('change_pct', 0) or 0)
        
        # 获取价格历史
        price_history = get_price_history(code, days=30)
        prices = [p['close'] for p in price_history] if price_history else [price]
        high_prices = [p['high'] for p in price_history] if price_history else [price]
        low_prices = [p['low'] for p in price_history] if price_history else [price]
        
        context = {
            'stock_code': code,
            'stock_name': name,
            'current_price': price,
            'prices': prices,
            'high_prices': high_prices,
            'low_prices': low_prices,
            'rank': int(stock.get('rank', 100) or 100),
            'turnover_rate': float(stock.get('turnover_rate', 0) or 0),
            'volume_ratio': float(stock.get('volume_ratio', 1) or 1),
            'price_change': change_pct,
            'pe_ratio': float(stock.get('pe_ratio', 0) or 0),
            'pb_ratio': float(stock.get('pb_ratio', 0) or 0),
            'roe': float(stock.get('roe', 0) or 0),
            'industry_pe': float(stock.get('industry_pe', 0) or 0),
            'industry_pb': float(stock.get('industry_pb', 0) or 0),
            'portfolio_info': {
                'total_value': 100000,
                'available_capital': 20000
            },
            'market_volatility': 0.025
        }
        
        # 执行多智能体分析
        result = orchestrator.execute_analysis_pipeline(context)
        
        # 转换为传统信号格式
        final_signal = result.get('final_signal', 'neutral')
        confidence = result.get('final_confidence', 0)
        
        # 映射信号类型
        signal_map = {
            'bullish': 'Strong Buy' if confidence > 0.6 else 'Buy',
            'bearish': 'Risk' if confidence > 0.6 else 'Caution',
            'neutral': 'Hold'
        }
        signal = signal_map.get(final_signal, 'Hold')
        
        # 计算分数和强度
        score = int(confidence * 100)
        strength = min(5, max(1, int(confidence * 5)))
        
        # 获取分析师报告
        analyst_reports = result.get('analyst_reports', [])
        reasons = []
        if isinstance(analyst_reports, list):
            for report in analyst_reports:
                if isinstance(report, dict) and report.get('signal') != 'neutral':
                    agent_name = report.get('agent_name', report.get('name', 'Unknown'))
                    reasons.append(f"{agent_name}: {report.get('signal')} ({report.get('confidence', 0)*100:.0f}%)")
        elif isinstance(analyst_reports, dict):
            for agent_name, report in analyst_reports.items():
                if isinstance(report, dict) and report.get('signal') != 'neutral':
                    reasons.append(f"{agent_name}: {report.get('signal')} ({report.get('confidence', 0)*100:.0f}%)")
        
        return {
            'code': code,
            'name': name,
            'price': price,
            'change_pct': change_pct,
            'rank': context['rank'],
            'signal': signal,
            'score': score,
            'strength': strength,
            'reasons': reasons,
            'up_proba': confidence,
            'multi_agent': True,
            'agent_details': result
        }
        
    except Exception as e:
        print(f"[MultiAgent] 分析失败 {stock.get('code')}: {e}")
        return None


def main(use_multi_agent: bool = False):
    """
    主函数
    
    Args:
        use_multi_agent: 是否使用多智能体系统（默认False使用传统引擎）
    """
    init_storage()
    stocks = get_latest_snapshot()
    
    if not stocks:
        print("No data. Run fetch_hot_stocks.py first.")
        return
    
    # 选择引擎
    if use_multi_agent and MULTI_AGENT_AVAILABLE:
        print("🤖 使用多智能体系统分析...")
        orchestrator = Orchestrator(MemoryStore())
        engine = SignalEngine()
        
        # 先用传统引擎添加技术指标
        for stock in stocks:
            code = stock.get('code', '')
            if code:
                price_history = get_price_history(code, days=60)
                add_technical_indicators(stock, price_history)
        
        signals = []
        for stock in stocks:
            # 尝试多智能体分析
            ma_signal = calculate_signal_with_multi_agent(stock, orchestrator)
            if ma_signal:
                # 合并传统引擎的持仓信息
                portfolio = Portfolio()
                holdings = portfolio.get_holdings_with_status()
                holding_codes = {h['code']: h for h in holdings}
                code = ma_signal['code']
                
                if code in holding_codes:
                    h = holding_codes[code]
                    cur_price = float(ma_signal.get('price') or 0)
                    profit = (cur_price - h['buy_price']) * h['quantity']
                    profit_pct = ((cur_price - h['buy_price']) / h['buy_price'] * 100) if h['buy_price'] > 0 else 0
                    
                    ma_signal['in_portfolio'] = True
                    ma_signal['holding_info'] = {
                        'buy_price': h['buy_price'],
                        'quantity': h['quantity'],
                        'profit': profit,
                        'profit_pct': profit_pct,
                        'can_sell': h['can_sell'],
                        'sell_status': h['sell_status'],
                    }
                else:
                    ma_signal['in_portfolio'] = False
                    ma_signal['holding_info'] = None
                
                signals.append(ma_signal)
            else:
                # 回退到传统引擎
                sig = engine.calculate_signal(stock)
                signals.append(sig)
        
        signals.sort(key=lambda x: (x['strength'], x['score']), reverse=True)
    else:
        # 使用传统引擎
        print("[SignalEngine] 使用传统信号引擎...")
        engine = SignalEngine()
        signals = engine.process_all(stocks)
    
    filepath = save_signals_to_json(signals)
    print(f"Signals saved: {filepath}")
    
    print("\n" + "=" * 70)
    for s in signals[:10]:
        ml_str = f" [ML:{s['up_proba']*100:.0f}%]" if s.get('up_proba') is not None else ""
        ma_str = " [MA]" if s.get('multi_agent') else ""
        reason = s['reasons'][0] if s['reasons'] else "-"
        stars  = "★" * s['strength'] + "☆" * (5 - s['strength'])
        print(f"{s['rank']:>4} {s['code']} {s['name']:<8} {s['signal']:<12} {stars} {s['score']:>4}{ml_str}{ma_str}  {reason[:25]}")


if __name__ == "__main__":
    import sys
    # 支持 --multi-agent 参数启用多智能体
    use_ma = '--multi-agent' in sys.argv or '-m' in sys.argv
    main(use_multi_agent=use_ma)

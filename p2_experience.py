#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P2 体验提升模块
- 组合风险控制
- 60分钟K线支持
- 移动端适配辅助
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"


class PortfolioRiskManager:
    """组合风险管理器"""
    
    def __init__(self, max_sector_weight: float = 0.20, max_single_stock_weight: float = 0.25):
        self.max_sector_weight = max_sector_weight
        self.max_single_stock_weight = max_single_stock_weight
        
        # 行业关键词映射
        self.sector_keywords = {
            '电力': ['电', '能源', '风电', '水电', '火电', '核电', '电网'],
            '银行': ['银行', '证券', '保险', '金融'],
            '医药': ['药', '医', '生物', '疗'],
            '科技': ['科技', '电子', '芯片', '软件', '通信', '半导体'],
            '煤炭': ['煤', '炭', '能源'],
            '房地产': ['地产', '房', '建筑'],
            '消费': ['食品', '饮料', '白酒', '家电', '消费'],
            '汽车': ['汽车', '车', '新能源'],
            '军工': ['军工', '航空', '航天', '船舶'],
            '有色': ['有色', '金属', '稀土', '锂'],
        }
    
    def analyze_portfolio_risk(self, holdings: List[Dict], total_value: float) -> Dict:
        """
        分析组合风险
        
        Args:
            holdings: 持仓列表
            total_value: 总资产
            
        Returns:
            {
                'risk_level': 'low' | 'medium' | 'high',
                'sector_concentration': {
                    '电力': 0.35,
                    '银行': 0.15
                },
                'single_stock_risk': [
                    {'code': '000001', 'weight': 0.30, 'risk': 'high'}
                ],
                'warnings': [...],
                'suggestions': [...]
            }
        """
        if not holdings:
            return {
                'risk_level': 'low',
                'sector_concentration': {},
                'single_stock_risk': [],
                'warnings': [],
                'suggestions': ['当前空仓，建议关注市场机会']
            }
        
        # 分析行业集中度
        sector_weights = self._calculate_sector_weights(holdings, total_value)
        
        # 分析个股集中度
        single_stock_risks = []
        for h in holdings:
            weight = (h.get('buy_price', 0) * h.get('quantity', 0)) / total_value if total_value > 0 else 0
            
            if weight > self.max_single_stock_weight:
                single_stock_risks.append({
                    'code': h.get('code'),
                    'name': h.get('name'),
                    'weight': weight,
                    'risk': 'high'
                })
        
        # 生成警告和建议
        warnings = []
        suggestions = []
        
        # 检查行业集中度
        for sector, weight in sector_weights.items():
            if weight > self.max_sector_weight:
                warnings.append(f"{sector}板块占比{weight:.1%}，超过{self.max_sector_weight:.0%}限制")
                suggestions.append(f"建议减仓{sector}板块，分散投资")
        
        # 检查个股集中度
        for risk in single_stock_risks:
            warnings.append(f"{risk['name']}占比{risk['weight']:.1%}，仓位过重")
            suggestions.append(f"建议减仓{risk['name']}，控制单一股票风险")
        
        # 确定风险等级
        if len(warnings) >= 2:
            risk_level = 'high'
        elif len(warnings) == 1:
            risk_level = 'medium'
        else:
            risk_level = 'low'
            suggestions.append('组合风险分散良好，可继续持有')
        
        return {
            'risk_level': risk_level,
            'sector_concentration': sector_weights,
            'single_stock_risk': single_stock_risks,
            'warnings': warnings,
            'suggestions': suggestions
        }
    
    def _calculate_sector_weights(self, holdings: List[Dict], total_value: float) -> Dict[str, float]:
        """计算各行业权重"""
        sector_values = {}
        
        for h in holdings:
            name = h.get('name', '')
            value = h.get('buy_price', 0) * h.get('quantity', 0)
            
            # 识别行业
            sector = self._detect_sector(name)
            
            if sector not in sector_values:
                sector_values[sector] = 0
            sector_values[sector] += value
        
        # 计算权重
        if total_value > 0:
            return {k: v / total_value for k, v in sector_values.items()}
        return {}
    
    def _detect_sector(self, stock_name: str) -> str:
        """识别股票所属行业"""
        for sector, keywords in self.sector_keywords.items():
            if any(kw in stock_name for kw in keywords):
                return sector
        return '其他'
    
    def can_add_position(self, new_stock: Dict, holdings: List[Dict], 
                        total_value: float, new_position_value: float) -> Tuple[bool, str]:
        """
        检查是否可以添加新仓位
        
        Returns:
            (是否可以添加, 原因)
        """
        new_name = new_stock.get('name', '')
        new_sector = self._detect_sector(new_name)
        
        # 检查行业集中度
        sector_values = {}
        for h in holdings:
            name = h.get('name', '')
            value = h.get('buy_price', 0) * h.get('quantity', 0)
            sector = self._detect_sector(name)
            sector_values[sector] = sector_values.get(sector, 0) + value
        
        # 加上新仓位后的行业权重
        current_sector_value = sector_values.get(new_sector, 0)
        new_sector_weight = (current_sector_value + new_position_value) / (total_value + new_position_value)
        
        if new_sector_weight > self.max_sector_weight:
            return False, f"{new_sector}板块占比将达{new_sector_weight:.1%}，超过{self.max_sector_weight:.0%}限制"
        
        # 检查个股集中度
        new_single_weight = new_position_value / (total_value + new_position_value)
        if new_single_weight > self.max_single_stock_weight:
            return False, f"单只股票占比将达{new_single_weight:.1%}，超过{self.max_single_stock_weight:.0%}限制"
        
        return True, "可以添加"


class HourlyKlineManager:
    """60分钟K线管理器"""
    
    def __init__(self):
        self.data_dir = OUTPUT_DIR / "hourly_kline"
        self.data_dir.mkdir(exist_ok=True)
    
    def save_hourly_data(self, code: str, data: List[Dict]):
        """保存60分钟K线数据"""
        file_path = self.data_dir / f"{code}.json"
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load_hourly_data(self, code: str, days: int = 5) -> List[Dict]:
        """加载60分钟K线数据"""
        file_path = self.data_dir / f"{code}.json"
        
        if not file_path.exists():
            return []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 返回最近N天数据（每天4小时，每小时1条 = 4条/天）
        return data[-(days * 4):]
    
    def calculate_hourly_indicators(self, code: str) -> Dict:
        """计算60分钟技术指标"""
        data = self.load_hourly_data(code, days=3)
        
        if len(data) < 10:
            return {}
        
        closes = [d['close'] for d in data]
        
        # 计算60分钟MACD
        macd = self._calculate_macd(closes)
        
        # 计算60分钟RSI
        rsi = self._calculate_rsi(closes)
        
        return {
            'macd': macd,
            'rsi': rsi,
            'data_points': len(closes)
        }
    
    def _calculate_macd(self, prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> float:
        """计算MACD（简化版）"""
        if len(prices) < slow:
            return 0
        
        # 计算EMA
        ema_fast = self._calculate_ema(prices, fast)
        ema_slow = self._calculate_ema(prices, slow)
        
        # MACD线
        macd_line = ema_fast - ema_slow
        
        return round(macd_line, 4)
    
    def _calculate_ema(self, prices: List[float], period: int) -> float:
        """计算EMA"""
        if len(prices) < period:
            return prices[-1] if prices else 0
        
        multiplier = 2 / (period + 1)
        ema = sum(prices[:period]) / period  # 初始SMA
        
        for price in prices[period:]:
            ema = (price - ema) * multiplier + ema
        
        return ema
    
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """计算RSI"""
        if len(prices) < period + 1:
            return 50
        
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        if len(gains) < period:
            return 50
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return round(rsi, 2)


class MobileOptimizer:
    """移动端优化辅助"""
    
    @staticmethod
    def generate_mobile_css() -> str:
        """生成移动端适配CSS"""
        return """
        /* 移动端适配 */
        @media (max-width: 768px) {
            .container { padding: 10px; }
            .header h1 { font-size: 1.5rem; }
            .metrics { grid-template-columns: repeat(2, 1fr); }
            .stock-table { display: none; }
            .stock-cards { display: block; }
            .stock-card {
                background: rgba(255,255,255,0.05);
                border-radius: 10px;
                padding: 15px;
                margin-bottom: 10px;
                border-left: 3px solid #00d4ff;
            }
            .stock-card-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 10px;
            }
            .stock-card-body {
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 10px;
                font-size: 0.9rem;
            }
            .btn { padding: 8px 12px; font-size: 0.85rem; }
            .modal-content { width: 95%; margin: 10px auto; }
        }
        
        /* 卡片布局（默认隐藏，移动端显示） */
        .stock-cards { display: none; }
        
        @media (max-width: 768px) {
            .stock-cards { display: block; }
        }
        """
    
    @staticmethod
    def generate_stock_card(stock: Dict, signal: Dict) -> str:
        """生成股票卡片HTML"""
        signal_class = {
            'Strong Buy': 'strong-buy',
            'Buy': 'buy',
            'Hold': 'hold',
            'Caution': 'caution',
            'Risk': 'risk'
        }.get(signal.get('signal', ''), 'hold')
        
        return f"""
        <div class="stock-card {signal_class}">
            <div class="stock-card-header">
                <div>
                    <strong>{stock.get('name')}</strong>
                    <span class="stock-code">{stock.get('code')}</span>
                </div>
                <span class="signal-badge {signal_class}">{signal.get('signal')}</span>
            </div>
            <div class="stock-card-body">
                <div>价格: {stock.get('price')}</div>
                <div>涨跌: {stock.get('change_pct'):+.2f}%</div>
                <div>排名: {stock.get('rank')}</div>
                <div>评分: {signal.get('score')}</div>
            </div>
            <div class="stock-card-actions">
                <button onclick="showSignalDetail('{stock.get('code')}')">详情</button>
                <button onclick="generateStockReport('{stock.get('code')}', '{stock.get('name')}')">报告</button>
            </div>
        </div>
        """


def main():
    """测试"""
    print("=" * 60)
    print("P2 Experience Enhancement Test")
    print("=" * 60)
    
    # 测试组合风险管理
    print("\n1. Portfolio Risk Manager")
    risk_manager = PortfolioRiskManager()
    
    test_holdings = [
        {'code': '600396', 'name': '华电辽能', 'buy_price': 9.17, 'quantity': 1000},
        {'code': '601016', 'name': '节能风电', 'buy_price': 5.63, 'quantity': 2000},
        {'code': '000001', 'name': '平安银行', 'buy_price': 10.5, 'quantity': 500},
    ]
    
    total_value = sum(h['buy_price'] * h['quantity'] for h in test_holdings)
    risk_analysis = risk_manager.analyze_portfolio_risk(test_holdings, total_value)
    
    print(f"Risk Level: {risk_analysis['risk_level']}")
    print(f"Sector Concentration: {risk_analysis['sector_concentration']}")
    print(f"Warnings: {risk_analysis['warnings']}")
    
    # 测试60分钟K线
    print("\n2. Hourly Kline Manager")
    kline_manager = HourlyKlineManager()
    print("OK: HourlyKlineManager initialized")
    
    # 测试移动端优化
    print("\n3. Mobile Optimizer")
    mobile_css = MobileOptimizer.generate_mobile_css()
    print(f"OK: Generated {len(mobile_css)} chars CSS")
    
    print("\n" + "=" * 60)
    print("P2 Test Complete")
    print("=" * 60)


if __name__ == '__main__':
    main()

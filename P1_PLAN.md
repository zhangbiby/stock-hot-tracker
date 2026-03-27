# P1 优化实施计划

## 实施时间：2026-03-27 开始

---

## P1.1 增加资金流数据源

### 1.1.1 北向资金数据
**新文件**: `fetch_northbound.py`

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""北向资金数据采集"""

import urllib.request
import json
from datetime import datetime

def fetch_northbound_flow():
    """获取北向资金净流入"""
    # 东方财富API
    url = 'https://push2.eastmoney.com/api/qt/stock/get'
    params = {
        'secid': '1.000001',  # 上证指数
        'fields': 'f184',  # 北向资金净流入
    }
    # 实现采集逻辑
    pass

def fetch_northbound_top10():
    """获取北向资金买入/卖出前10"""
    pass
```

### 1.1.2 龙虎榜数据
**新文件**: `fetch_dragon_tiger.py`

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""龙虎榜数据采集"""

def fetch_daily_dragon_tiger(date=None):
    """获取每日龙虎榜"""
    # 东方财富龙虎榜API
    pass

def analyze_seats(stock_code):
    """分析游资席位"""
    # 识别知名游资：章盟主、赵老哥等
    pass
```

### 1.1.3 行业资金流
**新文件**: `fetch_industry_flow.py`

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""行业资金流数据采集"""

def fetch_industry_capital_flow():
    """获取行业资金净流入排名"""
    pass

def get_industry_strength(industry_code):
    """计算行业强度"""
    pass
```

---

## P1.2 因子权重动态调整

### 1.2.1 市场状态检测器
**新文件**: `market_state.py`

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""市场状态检测"""

class MarketStateDetector:
    """检测当前市场状态"""
    
    def detect(self):
        """
        返回: 'strong_bull', 'bull', 'neutral', 'bear', 'strong_bear'
        """
        # 基于以下指标：
        # 1. 大盘指数20日均线趋势
        # 2. 市场波动率 (VIX风格)
        # 3. 涨跌家数比
        # 4. 成交量变化
        pass
    
    def get_factor_weights(self, state):
        """根据市场状态返回权重配置"""
        weights_map = {
            'strong_bull': {
                'volume_price': 0.30,
                'rank_trend': 0.25,
                'technical': 0.20,
                'capital_flow': 0.15,
                'sentiment': 0.10,
                'risk': 0.00
            },
            'bull': {
                'volume_price': 0.25,
                'rank_trend': 0.25,
                'technical': 0.20,
                'capital_flow': 0.15,
                'sentiment': 0.10,
                'risk': 0.05
            },
            'neutral': {
                'volume_price': 0.20,
                'rank_trend': 0.20,
                'technical': 0.20,
                'capital_flow': 0.15,
                'sentiment': 0.15,
                'risk': 0.10
            },
            'bear': {
                'volume_price': 0.15,
                'rank_trend': 0.15,
                'technical': 0.20,
                'capital_flow': 0.10,
                'sentiment': 0.10,
                'risk': 0.30
            },
            'strong_bear': {
                'volume_price': 0.10,
                'rank_trend': 0.10,
                'technical': 0.15,
                'capital_flow': 0.05,
                'sentiment': 0.10,
                'risk': 0.50
            }
        }
        return weights_map.get(state, weights_map['neutral'])
```

### 1.2.2 动态信号引擎
**修改**: `signal_engine.py`

```python
class DynamicSignalEngine(SignalEngine):
    """动态权重信号引擎"""
    
    def __init__(self):
        super().__init__()
        from market_state import MarketStateDetector
        self.state_detector = MarketStateDetector()
    
    def calculate_signal(self, stock):
        # 检测市场状态
        market_state = self.state_detector.detect()
        weights = self.state_detector.get_factor_weights(market_state)
        
        # 使用动态权重计算
        score = 0
        score += self.volume_price_score(stock) * weights['volume_price']
        score += self.rank_trend_score(stock) * weights['rank_trend']
        score += self.technical_score(stock) * weights['technical']
        score += self.capital_flow_score(stock) * weights['capital_flow']
        score += self.sentiment_score(stock) * weights['sentiment']
        score -= self.risk_score(stock) * weights['risk']
        
        return score
```

---

## P1.3 决策过程透明化

### 1.3.1 后端API
**修改**: `server.py`

```python
def get_signal_detail(self, params):
    """获取信号详细分析"""
    code = params.get('code')
    
    # 查询最新信号
    signal = db_manager.get_signals(code, limit=1)
    
    # 查询各因子得分
    factors = {
        'volume_price': self.calculate_volume_price_factor(code),
        'rank_trend': self.calculate_rank_factor(code),
        'technical': self.calculate_technical_factor(code),
        'capital_flow': self.calculate_capital_flow_factor(code),
        'sentiment': self.calculate_sentiment_factor(code),
        'risk': self.calculate_risk_factor(code)
    }
    
    # 查询技术指标
    indicators = db_manager.get_latest_snapshot(code)
    
    return {
        'success': True,
        'signal': signal,
        'factors': factors,
        'indicators': indicators,
        'reasons': self.generate_reasons(factors),
        'risks': self.generate_risk_warnings(factors)
    }
```

### 1.3.2 前端详情弹窗
**修改**: `generate_page.py`

```javascript
function showSignalDetail(code, name) {
    fetch(`/get_signal_detail?code=${code}`)
        .then(r => r.json())
        .then(data => {
            // 弹出模态框
            const modal = document.createElement('div');
            modal.className = 'signal-detail-modal';
            modal.innerHTML = `
                <div class="modal-content">
                    <h2>${name} (${code}) 信号详情</h2>
                    
                    <!-- 因子得分雷达图 -->
                    <div class="factor-radar">
                        <canvas id="radarChart"></canvas>
                    </div>
                    
                    <!-- 各因子得分 -->
                    <div class="factor-scores">
                        ${Object.entries(data.factors).map(([k, v]) => `
                            <div class="factor-item">
                                <span>${k}</span>
                                <div class="score-bar">
                                    <div style="width: ${v}%"></div>
                                </div>
                                <span>${v.toFixed(1)}</span>
                            </div>
                        `).join('')}
                    </div>
                    
                    <!-- 技术指标 -->
                    <div class="indicators">
                        <h3>技术指标</h3>
                        <p>RSI: ${data.indicators.rsi?.toFixed(2) || 'N/A'}</p>
                        <p>MACD: ${data.indicators.macd?.toFixed(4) || 'N/A'}</p>
                        <p>布林带位置: ${(data.indicators.bb_position * 100)?.toFixed(1) || 'N/A'}%</p>
                    </div>
                    
                    <!-- 风险提示 -->
                    <div class="risk-warnings">
                        <h3>风险提示</h3>
                        ${data.risks.map(r => `<p>⚠️ ${r}</p>`).join('')}
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
        });
}
```

---

## 实施时间表

### Week 1 (3/27-4/2)
- [ ] Day 1-2: 北向资金数据采集
- [ ] Day 3-4: 龙虎榜数据采集
- [ ] Day 5-7: 行业资金流数据采集

### Week 2 (4/3-4/9)
- [ ] Day 8-10: 市场状态检测器
- [ ] Day 11-12: 动态权重信号引擎
- [ ] Day 13-14: 决策透明化后端API

### Week 3 (4/10-4/16)
- [ ] Day 15-17: 前端详情弹窗
- [ ] Day 18-19: 雷达图可视化
- [ ] Day 20-21: 集成测试

---

## 预期效果

| 指标 | 优化前 | 优化后 | 提升 |
|------|--------|--------|------|
| 数据维度 | 2维 | 6维 | +200% |
| 市场适应性 | 固定权重 | 动态调整 | 显著 |
| 决策透明度 | 黑盒 | 白盒 | 完全 |
| 信号准确率 | ~55% | ~65% | +10% |

---

## 下一步行动

1. **立即开始**: 实施北向资金数据采集
2. **并行开发**: 市场状态检测器
3. **持续测试**: 每完成一个模块立即测试

**开始P1实施！**
# Stock Hot Tracker - 系统优化路线图

基于用户反馈的完整优化方案

---

## 📊 优化优先级总览

| 优先级 | 类别 | 优化点 | 预期收益 |
|--------|------|--------|----------|
| **P0** | 稳定性 | 统一数据库存储、修复采集调度 | 系统稳定性 |
| **P0** | 验证 | 增加回测模块 | 验证策略有效性 |
| **P1** | 数据 | 增加资金流数据源（北向、龙虎榜） | 提升信号质量 |
| **P1** | 模型 | 因子权重动态调整 | 适应市场变化 |
| **P1** | 体验 | 决策过程透明化（详情弹窗） | 用户信任度 |
| **P2** | 数据 | 60分钟K线支持 | 捕捉日内动能 |
| **P2** | 风控 | 组合风险控制 | 降低回撤 |
| **P2** | 体验 | 移动端适配 | 用户体验 |
| **P3** | 数据 | 新闻情感分析 | 辅助判断 |

---

## 🔴 P0 - 必须立即实施

### 1. 统一数据库存储

**现状**: history_store.py 使用文件存储，Web服务和采集可能冲突

**方案**:
```python
# 修改 history_store.py 使用 SQLite
# 已有 database.py，需要整合

# 新架构:
database.py (统一数据库接口)
    ├── 历史快照表 (snapshots)
    ├── 信号记录表 (signals)
    ├── 持仓表 (holdings)
    ├── 交易记录表 (trades)
    └── 回测记录表 (backtests)
```

**实施步骤**:
1. 扩展 database.py 添加缺失的表结构
2. 修改 history_store.py 使用数据库
3. 修改 signal_engine.py 写入数据库
4. 修改 portfolio.py 使用数据库
5. 保留旧接口兼容现有代码

### 2. 修复采集调度

**现状**: smart_collector.py 只执行一次

**方案**:
```python
# 修改为常驻进程
class DataCollector:
    def run(self):
        while True:
            if is_trading_time():
                self.collect()      # 3分钟间隔
                time.sleep(180)
            else:
                self.collect()      # 30分钟间隔
                time.sleep(1800)
    
    def collect(self):
        # 异常重试机制
        for attempt in range(3):
            try:
                self._do_collect()
                break
            except Exception as e:
                logger.error(f"采集失败(尝试{attempt+1}): {e}")
                time.sleep(60)
```

### 3. 增加回测模块

**新文件**: `backtest.py`

**功能**:
```python
class BacktestEngine:
    """回测引擎"""
    
    def run(self, start_date, end_date, strategy):
        """
        运行回测
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            strategy: 策略配置
            
        Returns:
            回测报告: {
                'total_return': 总收益率,
                'win_rate': 胜率,
                'profit_factor': 盈亏比,
                'max_drawdown': 最大回撤,
                'sharpe_ratio': 夏普比率,
                'trades': 交易记录列表
            }
        """
```

**回测逻辑**:
1. 遍历历史快照
2. 按信号买入，记录成本
3. 按卖出信号/止盈止损卖出
4. 计算手续费、印花税
5. 生成回测报告

---

## 🟡 P1 - 重要优化

### 4. 增加资金流数据源

**新数据源**:
- 北向资金（沪深港通）
- 龙虎榜数据
- 行业资金流

**新文件**: `fetch_capital_flow.py`

```python
def fetch_northbound_capital():
    """获取北向资金数据"""
    # 东方财富API
    pass

def fetch_dragon_tiger_list():
    """获取龙虎榜数据"""
    # 东方财富龙虎榜
    pass

def fetch_industry_capital():
    """获取行业资金流"""
    # 同花顺/东方财富
    pass
```

**信号引擎集成**:
```python
# signal_engine.py 新增因子
def calculate_capital_flow_score(stock):
    """资金流因子得分"""
    score = 0
    # 北向资金流入 +10
    # 龙虎榜游资买入 +15
    # 行业资金净流入 +8
    return score
```

### 5. 因子权重动态调整

**市场状态检测**:
```python
class MarketStateDetector:
    """市场状态检测器"""
    
    def detect(self):
        """
        检测当前市场状态
        
        Returns:
            'strong_bull', 'bull', 'neutral', 'bear', 'strong_bear'
        """
        # 基于大盘指数趋势、波动率、成交量
        pass
    
    def get_factor_weights(self, state):
        """根据市场状态返回因子权重"""
        weights = {
            'strong_bull': {
                'volume_price': 0.30,    # 量价因子权重提高
                'rank_trend': 0.25,
                'technical': 0.20,
                'capital_flow': 0.15,
                'risk': 0.10
            },
            'bear': {
                'volume_price': 0.15,
                'rank_trend': 0.15,
                'technical': 0.20,
                'capital_flow': 0.10,
                'risk': 0.40             # 熊市提高风险因子权重
            }
        }
        return weights.get(state, default_weights)
```

### 6. 决策过程透明化

**前端改进**:
```javascript
// 股票行增加"详情"按钮
function showSignalDetail(code) {
    fetch(`/api/signal_detail?code=${code}`)
        .then(r => r.json())
        .then(data => {
            // 弹出对话框展示:
            // - 各因子得分明细
            // - 技术指标数值
            // - 风险点提示
            // - 买入/卖出理由
        });
}
```

**后端API**:
```python
# server.py 新增端点
def get_signal_detail(self, params):
    """获取信号详细分析"""
    code = params.get('code')
    # 返回各因子得分、技术指标、风险点
```

---

## 🟢 P2 - 增强功能

### 7. 60分钟K线支持

**数据存储**:
```python
# database.py 新增表
CREATE TABLE hourly_kline (
    code TEXT,
    datetime TEXT,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume INTEGER,
    PRIMARY KEY (code, datetime)
);
```

**指标计算**:
```python
# indicators.py 新增
class HourlyIndicators:
    @staticmethod
    def calculate_hourly_macd(prices):
        pass
    
    @staticmethod
    def calculate_hourly_rsi(prices):
        pass
```

### 8. 组合风险控制

**新模块**: `portfolio_risk.py`

```python
class PortfolioRiskManager:
    """组合风险管理"""
    
    def check_concentration_risk(self, holdings, new_stock):
        """检查集中度风险"""
        # 计算同板块持仓占比
        sector = self.get_sector(new_stock)
        sector_weight = sum(h['value'] for h in holdings if h['sector'] == sector) / total_value
        
        if sector_weight > 0.20:  # 超过20%
            return {
                'allowed': False,
                'reason': f'{sector}板块持仓已达{sector_weight:.1%}，超过20%限制'
            }
        return {'allowed': True}
    
    def calculate_portfolio_risk_metrics(self, holdings):
        """计算组合风险指标"""
        # Beta系数
        # 波动率
        # 最大回撤
        pass
```

### 9. 移动端适配

**响应式设计**:
```css
/* generate_page.py 样式 */
@media (max-width: 768px) {
    .stock-card {
        display: grid;
        grid-template-columns: 1fr 1fr;
        /* 卡片式布局 */
    }
    .desktop-table { display: none; }
    .mobile-cards { display: block; }
}
```

---

## 🔵 P3 - 可选增强

### 10. 新闻情感分析

**方案**:
```python
# news_analyst.py 增强
class NewsSentimentAnalyzer:
    def analyze(self, news_list):
        """
        分析新闻情感
        
        简单规则:
        - 正面词: +1 (涨停、利好、突破、增长)
        - 负面词: -1 (跌停、利空、下跌、亏损)
        - 计算总体情感得分
        """
        pass
```

---

## 📅 实施计划

### 第1周：P0 - 基础稳定
- [ ] Day 1-2: 统一数据库存储
- [ ] Day 3-4: 修复采集调度
- [ ] Day 5-7: 增加回测模块

### 第2周：P1 - 核心优化
- [ ] Day 8-10: 增加资金流数据源
- [ ] Day 11-12: 因子权重动态调整
- [ ] Day 13-14: 决策过程透明化

### 第3周：P2 - 体验提升
- [ ] Day 15-17: 60分钟K线支持
- [ ] Day 18-19: 组合风险控制
- [ ] Day 20-21: 移动端适配

### 第4周：P3 - 锦上添花
- [ ] Day 22-28: 新闻情感分析、测试优化

---

## 📊 预期效果

| 指标 | 当前 | 优化后 | 提升 |
|------|------|--------|------|
| 信号准确率 | ~55% | ~65% | +10% |
| 系统稳定性 | 中 | 高 | 显著 |
| 数据维度 | 2维 | 6维 | +200% |
| 用户体验 | 6分 | 9分 | +50% |
| 风险控制 | 基础 | 完善 | 显著 |

---

## 💡 关键成功因素

1. **数据质量**: 多数据源交叉验证
2. **模型迭代**: 基于回测持续优化
3. **用户反馈**: 收集信号准确性反馈
4. **风险控制**: 永远把风险控制放在第一位

---

**开始实施**: 建议从P0开始，逐步推进
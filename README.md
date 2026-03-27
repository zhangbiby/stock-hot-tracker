# Stock Hot Tracker - 系统文档

## 📊 系统功能概览

### 核心功能
1. **实时数据采集**
   - 东方财富人气榜TOP100
   - 开盘时间：每3分钟采集一次
   - 非交易时间：每1小时采集一次

2. **多智能体AI分析**
   - 11个专业分析师并行工作
   - 技术/情绪/新闻/基本面四维分析
   - 多空辩论机制
   - 记忆反思系统

3. **智能信号系统**
   - Strong Buy (≥70分) - 强烈买入
   - Buy (50-69分) - 买入
   - Hold (30-49分) - 持有
   - Caution (20-29分) - 谨慎
   - Risk (<20分) - 风险

4. **报告生成**
   - 日报：市场整体分析
   - 个股报告：多空辩论详情
   - 实时更新

5. **持仓管理**
   - 自定义持仓
   - T+1交易规则
   - 盈亏实时计算

---

## 🤖 多智能体架构

```
Orchestrator (协调器)
    ├── TechnicalAnalyst (技术分析师)
    │   └── RSI, MACD, 布林带, 均线
    ├── SentimentAnalyst (情绪分析师)
    │   └── 排名变化, 换手率, 量比
    ├── NewsAnalyst (新闻分析师)
    │   └── 新闻情绪, 事件驱动
    ├── FundamentalAnalyst (基本面分析师)
    │   └── PE/PB估值, ROE
    ├── BullResearcher (看涨研究员)
    ├── BearResearcher (看跌研究员)
    ├── ResearchManager (研究经理)
    ├── Trader (交易员)
    └── RiskManager (风险经理)
```

---

## 💰 买入卖出模型

### 买入条件 (满足3项以上)
- 信号评分 ≥ 50分
- 人气排名上升
- 量价配合良好 (涨幅>3%, 量比>1.2)
- RSI < 70 (非超买)
- MACD金叉区域
- 同板块多只股票上榜
- PE < 100 (估值合理)

**建议仓位**: 20%

### 卖出条件 (满足1项即触发)
- 盈利 ≥ 10%
- 亏损 ≥ 3% (止损)
- 信号变为 Caution/Risk
- 换手率 > 20% (异常)
- T+1后可卖出

**止损设置**: 买入价 × 0.97

---

## 📈 信号计算因子

| 因子 | 权重 | 说明 |
|------|------|------|
| 排名趋势 | 25% | 5分钟/1小时排名变化 |
| 量价配合 | 20% | 涨幅 + 量比 |
| 技术指标 | 20% | RSI + MACD + 布林带 |
| 换手率 | 15% | 活跃度指标 |
| 板块效应 | 10% | 同板块上榜数量 |
| 估值 | 10% | PE/PB合理性 |

---

## 🚀 快速开始

```bash
# 1. 启动服务器
python server.py

# 2. 访问 http://localhost:8080

# 3. 查看实时数据
# 4. 点击 📊 生成个股报告
# 5. 点击 📄 生成日报
```

---

## 📁 文件结构

```
stock-hot-tracker/
├── server.py              # Web服务器
├── signal_engine.py       # 信号引擎
├── generate_page.py       # 页面生成
├── fetch_hot_stocks.py    # 数据采集
├── quick_fetch.py         # 快速采集
├── agents/                # 多智能体系统
│   ├── orchestrator.py
│   ├── technical_analyst.py
│   ├── sentiment_analyst.py
│   ├── news_analyst.py
│   ├── fundamental_analyst.py
│   ├── bull_researcher.py
│   ├── bear_researcher.py
│   ├── research_manager.py
│   ├── trader.py
│   └── risk_manager.py
├── memory/                # 记忆系统
├── output/                # 输出目录
│   ├── index.html         # 主页面
│   ├── hot_stocks.json    # 股票数据
│   ├── signals_latest.json # 信号数据
│   └── system_docs.html   # 系统文档
└── portfolio.py           # 持仓管理
```

---

## 📊 大盘指数

- 上证指数 (sh000001)
- 深证成指 (sz399001) ← 新增
- 创业板指 (sz399006)
- 科创50 (sh000688)

---

**访问系统**: http://localhost:8080  
**系统文档**: http://localhost:8080/output/system_docs.html
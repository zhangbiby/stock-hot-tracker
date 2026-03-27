# 🚀 Stock Hot Tracker - 完整使用指南

> **多智能体股票分析系统**
> 结合人气榜数据、技术分析、情绪分析、新闻分析的智能投资决策系统

---

## 📋 目录

1. [系统概述](#系统概述)
2. [快速开始](#快速开始)
3. [核心功能](#核心功能)
4. [多智能体架构](#多智能体架构)
5. [命令参考](#命令参考)
6. [配置说明](#配置说明)
7. [常见问题](#常见问题)

---

## 系统概述

### 🎯 系统特点

- **实时人气榜数据**：采集东方财富股吧人气榜TOP100股票
- **多智能体分析**：技术分析师、情绪分析师、新闻分析师、基本面分析师
- **辩论机制**：看涨研究员 vs 看跌研究员
- **记忆反思**：记录历史决策，优化未来判断
- **风险控制**：自动风险评估和仓位建议
- **可视化界面**：实时行情、信号统计、图表分析

### 📊 数据流程

```
东方财富人气榜 → 数据采集 → 多智能体分析 → 信号输出 → 可视化展示
     ↓              ↓              ↓            ↓            ↓
  实时TOP100    多因子计算     辩论决策     买卖信号     Web界面
```

### 🏗️ 系统架构

```
stock-hot-tracker/
├── agents/              # 多智能体系统
│   ├── technical_analyst.py    # 技术分析师
│   ├── sentiment_analyst.py    # 情绪分析师
│   ├── news_analyst.py         # 新闻分析师
│   ├── fundamental_analyst.py  # 基本面分析师
│   ├── bull_researcher.py      # 看涨研究员
│   ├── bear_researcher.py      # 看跌研究员
│   ├── research_manager.py     # 研究经理
│   ├── trader.py               # 交易员
│   ├── risk_manager.py         # 风险经理
│   └── orchestrator.py         # 协调器
│
├── memory/              # 记忆系统
│   ├── memory_store.py         # 决策记录存储
│   └── reflection.py           # 反思系统
│
├── utils/               # 工具模块
│   └── llm_client.py           # LLM调用封装
│
├── output/              # 输出目录
│   ├── hot_stocks.json         # 热门股票数据
│   ├── signals_latest.json     # 最新信号
│   ├── index.html              # 可视化页面
│   └── daily_report_*.html     # 日报文件
│
├── server.py            # Web服务器
├── signal_engine.py     # 信号引擎（传统）
├── history_store.py     # 历史数据存储
├── indicators.py        # 技术指标计算
└── portfolio.py         # 持仓管理
```

---

## 快速开始

### ⚡ 5分钟快速启动

```powershell
# 1. 进入项目目录
cd F:\qclaw\workspace\stock-hot-tracker

# 2. 启动服务器（自动采集数据）
python server.py

# 3. 打开浏览器
# 访问 http://localhost:8080
```

**首次启动会自动**：
- ✅ 采集人气榜TOP100股票数据
- ✅ 计算技术指标和买卖信号
- ✅ 生成可视化页面
- ✅ 启动Web服务器

### 🔧 完整启动流程

```powershell
# 步骤1: 数据采集（可选，server.py会自动采集）
python fetch_hot_stocks.py

# 步骤2: 信号计算（可选，server.py会自动计算）
python signal_engine.py

# 步骤3: 生成页面（可选，server.py会自动生成）
python generate_page.py

# 步骤4: 启动服务器
python server.py

# 现在访问 http://localhost:8080 查看实时数据
```

---

## 核心功能

### 📈 实时监控

**功能**：
- 人气榜TOP100股票实时追踪
- 大盘指数实时显示（上证/创业板/科创50）
- 每5-10分钟自动更新（交易时间）

**操作**：
1. 打开 `http://localhost:8080`
2. 页面左上角显示大盘指数
3. 中间显示信号统计
4. 下方显示股票列表

### 🤖 多智能体分析

**分析流程**：

```
┌─────────────────────────────────────────────────────┐
│              第一阶段：并行分析                        │
├─────────────┬─────────────┬─────────────┬───────────┤
│ 技术分析师   │ 情绪分析师   │ 新闻分析师   │基本面分析师│
│ RSI/MACD    │ 排名变化     │ 新闻情绪     │ PE/PB     │
│ 布林带      │ 换手率/量比  │             │ ROE       │
└──────┬──────┴──────┬──────┴──────┬──────┴─────┬─────┘
       │             │             │            │
       └─────────────┴─────────────┴────────────┘
                            │
                 ┌──────────▼──────────┐
                 │   第二阶段：辩论      │
                 ├──────────┬──────────┤
                 │ 看涨研究员│看跌研究员 │
                 │ 生成论据  │生成论据   │
                 └──────┬───┴─────┬────┘
                        │         │
                 ┌──────▼─────────▼───┐
                 │  第三阶段：综合决策  │
                 │     研究经理        │
                 │  生成投资计划       │
                 └──────────┬──────────┘
                           │
                 ┌─────────▼──────────┐
                 │  第四阶段：执行     │
                 ├──────────┬─────────┤
                 │  交易员  │风险经理  │
                 │ 生成指令 │风险评估  │
                 └──────────┴─────────┘
                           │
                    ┌──────▼──────┐
                    │  最终决策    │
                    │ 买卖信号     │
                    │ 置信度       │
                    └─────────────┘
```

**使用方法**：

```python
from agents import Orchestrator
from memory import MemoryStore

# 初始化
orchestrator = Orchestrator(MemoryStore())

# 准备数据
context = {
    'stock_code': '000001',
    'stock_name': '平安银行',
    'current_price': 10.5,
    'prices': [10.0, 10.1, 10.2, ...],  # 历史价格
    'rank': 15,  # 人气排名
    'turnover_rate': 3.5,  # 换手率
    'volume_ratio': 1.8,   # 量比
    'pe_ratio': 8.5,       # PE
    'pb_ratio': 0.9,       # PB
    # ... 更多数据
}

# 执行分析
result = orchestrator.execute_analysis_pipeline(context)

# 查看结果
print(f"信号: {result['final_signal']}")        # bullish/bearish/neutral
print(f"置信度: {result['final_confidence']:.0%}")
print(f"交易指令: {result['trade_order']['action']}")
```

### 📊 个股报告生成

**功能**：
- 专业的投资分析报告
- 多空辩论框架
- 技术分析 + 基本面分析
- 具体操作建议

**使用方法**：

1. **Web界面**：
   - 打开 `http://localhost:8080`
   - 点击股票列表中的 "📊" 按钮
   - 自动生成并打开报告

2. **命令行**：
```powershell
# 确保服务器运行中
python server.py

# 在另一个终端，访问报告API
# POST http://localhost:8080/generate_stock_report
# Body: {"code": "000001", "name": "平安银行"}
```

**报告内容**：
- 标题：动态生成（根据涨停/信号类型）
- 多空辩论：看涨者 vs 看跌者观点
- 技术分析：RSI、MACD、布林带等
- 基本面分析：PE、PB、ROE等
- 投资建议：止损位、目标价位、仓位建议
- 风险提示：四维风险评估

### 📄 日报生成

**功能**：
- 微信公众号友好的HTML格式
- 板块热点分析
- 涨停榜/跌幅榜
- 高换手率预警

**使用方法**：

1. **Web界面**：
   - 打开 `http://localhost:8080`
   - 点击右上角 "📄 生成日报" 按钮
   - 自动生成并打开报告

2. **命令行**：
```powershell
# 确保服务器运行中
python server.py

# 在另一个终端
curl -X POST http://localhost:8080/generate_report
```

**报告保存位置**：
```
output/daily_report_YYYYMMDD.html
```

### 💼 持仓管理

**功能**：
- 自定义持仓添加
- T+1交易规则
- 盈亏计算
- 持仓持久化

**使用方法**：

1. **Web界面**：
   - 打开 `http://localhost:8080`
   - 页面右侧 "持仓管理" 区域
   - 输入股票代码、成本价、数量、买入日期
   - 点击 "添加持仓"

2. **数据存储**：
```
output/holdings.json  # 持仓数据（JSON格式）
```

---

## 多智能体架构

### 🤖 智能体列表

| 智能体 | 角色 | 输入 | 输出 |
|--------|------|------|------|
| **TechnicalAnalyst** | 技术分析师 | 价格历史、成交量 | RSI、MACD、布林带信号 |
| **SentimentAnalyst** | 情绪分析师 | 人气排名、换手率、量比 | 情绪评分(-1到1) |
| **NewsAnalyst** | 新闻分析师 | 新闻数据 | 新闻情绪信号 |
| **FundamentalAnalyst** | 基本面分析师 | PE、PB、ROE | 估值信号 |
| **BullResearcher** | 看涨研究员 | 所有分析师报告 | 看涨置信度、论据列表 |
| **BearResearcher** | 看跌研究员 | 所有分析师报告 | 看跌置信度、论据列表 |
| **ResearchManager** | 研究经理 | 看涨/看跌观点 | 投资计划、目标价格 |
| **Trader** | 交易员 | 投资计划、历史记忆 | 交易指令、仓位大小 |
| **RiskManager** | 风险经理 | 交易指令、市场波动 | 风险等级、止损位 |
| **Orchestrator** | 协调器 | - | 调度所有智能体 |

### 🔄 工作流程

```python
# 1. 初始化协调器
from agents import Orchestrator
from memory import MemoryStore

orchestrator = Orchestrator(MemoryStore())

# 2. 准备分析上下文
context = {
    'stock_code': '000001',
    'current_price': 10.5,
    'prices': [...],
    # ... 更多数据
}

# 3. 执行分析流程（自动调度）
result = orchestrator.execute_analysis_pipeline(context)

# 4. 获取结果
print(result['final_signal'])      # 最终信号
print(result['final_confidence'])  # 置信度
print(result['trade_order'])       # 交易指令
print(result['risk_assessment'])   # 风险评估
```

### 💾 记忆系统

**功能**：
- 自动保存每次决策记录
- 检索相似历史案例
- 计算历史成功率
- 支持决策反思和优化

**使用方法**：

```python
from memory import MemoryStore, ReflectionSystem

# 初始化
memory_store = MemoryStore()
reflection_system = ReflectionSystem()

# 保存决策
decision = {
    'stock_code': '000001',
    'signal': 'bullish',
    'confidence': 0.75,
    'action': 'buy',
    'timestamp': '2026-03-27T10:00:00'
}
memory_store.save_decision('000001', decision)

# 查询历史
history = memory_store.get_decisions('000001', limit=20)

# 查找相似案例
similar = memory_store.find_similar_cases('000001', 'bullish')

# 计算成功率
success_rate = memory_store.calculate_success_rate('000001')
```

### 🧠 LLM增强（可选）

**支持的语言模型**：
- OpenAI (GPT-3.5/GPT-4)
- DeepSeek
- 阿里百炼

**配置方法**：

```python
# utils/llm_client.py

class LLMClient:
    def __init__(self, provider='deepseek', api_key=None):
        self.provider = provider
        self.api_key = api_key or os.getenv('DEEPSEEK_API_KEY')
        
    def generate(self, prompt):
        """生成自然语言报告"""
        # 调用API
        ...
```

**使用示例**：

```python
from utils.llm_client import LLMClient

# 初始化
llm = LLMClient(provider='deepseek')

# 生成报告
prompt = "基于以下分析数据，生成投资建议..."
report = llm.generate(prompt)
```

---

## 命令参考

### 📦 数据采集

```powershell
# 采集人气榜TOP100
python fetch_hot_stocks.py

# 采集新闻数据
python fetch_news.py

# 采集所有股票名称映射
python fetch_all_stocks.py
```

### 🔧 信号计算

```powershell
# 计算买卖信号（传统单引擎）
python signal_engine.py

# 计算技术指标
python indicators.py
```

### 🖥️ Web服务

```powershell
# 启动服务器（推荐）
python server.py

# 端口: 8080
# 访问: http://localhost:8080
```

### 📊 页面生成

```powershell
# 生成可视化页面
python generate_page.py

# 输出: output/index.html
```

### 🧪 测试

```powershell
# 测试多智能体系统
python example_usage.py

# 输出: 完整分析流程示例
```

---

## 配置说明

### ⚙️ 端口配置

```python
# server.py

PORT = 8080  # 默认端口
```

### ⏱️ 采集频率

```python
# server.py

# 交易时间：每5-10分钟
# 非交易时间：每60分钟
```

### 📁 数据存储

```
output/
├── hot_stocks.json         # 热门股票数据
├── signals_latest.json     # 最新信号
├── holdings.json           # 持仓数据
├── stock_name_map.json     # 股票名称映射
├── news_latest.json        # 最新新闻
├── index.html              # 可视化页面
└── daily_report_*.html     # 日报文件

memory/storage/
└── *_decisions.json        # 决策记录
```

### 🔑 API配置（可选）

```python
# utils/llm_client.py

# 环境变量
export DEEPSEEK_API_KEY="your_api_key"
export OPENAI_API_KEY="your_api_key"
export ALIBABA_API_KEY="your_api_key"
```

---

## 常见问题

### ❓ Q1: 服务器启动后无法访问？

**解决方案**：
```powershell
# 检查端口占用
netstat -ano | findstr ":8080"

# 如果端口被占用，修改端口
# 编辑 server.py，修改 PORT = 9999
```

### ❓ Q2: 数据没有更新？

**解决方案**：
```powershell
# 手动采集数据
python fetch_hot_stocks.py

# 重启服务器
python server.py
```

### ❓ Q3: 持仓数据丢失？

**解决方案**：
```powershell
# 检查文件
dir output\holdings.json

# 如果文件存在，数据应该还在
# 如果清空了浏览器缓存，数据会丢失
# 建议：运行服务器时访问 http://localhost:8080
```

### ❓ Q4: 个股报告生成失败？

**解决方案**：
```powershell
# 确保服务器运行中
python server.py

# 检查数据文件
dir output\hot_stocks.json
dir output\signals_latest.json

# 刷新页面后重试
# 访问 http://localhost:8080 并按 Ctrl+F5 刷新
```

### ❓ Q5: 图表不显示？

**解决方案**：
```powershell
# 刷新页面
# 按 Ctrl+F5 强制刷新

# 检查网络连接
# 图表需要从CDN加载ECharts库
```

---

## 🎯 使用建议

### 📅 日常使用流程

**早上 (9:00-9:30)**：
```powershell
1. 启动服务器: python server.py
2. 打开浏览器: http://localhost:8080
3. 查看昨日信号统计
4. 查看今日开盘情况
```

**中午 (12:00-13:00)**：
```powershell
1. 刷新页面查看最新数据
2. 检查持仓盈亏
3. 查看是否有新的交易信号
```

**收盘后 (15:30-16:30)**：
```powershell
1. 生成日报
2. 分析今日决策
3. 规划明日操作
```

### 🔍 分析建议

**信号解读**：
- **Strong Buy**: 强烈买入信号（评分≥70）
- **Buy**: 买入信号（评分50-69）
- **Hold**: 持有观望（评分30-49）
- **Caution**: 谨慎（评分20-29）
- **Risk**: 风险信号（评分<20）

**置信度**：
- **≥60%**: 高置信度，可考虑执行
- **40-60%**: 中等置信度，需结合其他因素
- **<40%**: 低置信度，建议观望

**风险等级**：
- **very_low**: 可考虑加仓
- **low**: 正常交易
- **medium**: 轻仓尝试
- **high**: 谨慎操作
- **very_high**: 建议观望

---

## 📞 技术支持

- **项目路径**: `F:\qclaw\workspace\stock-hot-tracker`
- **文档位置**: `README.md`
- **配置文件**: `config.py`
- **日志文件**: 控制台输出

---

## 🎉 总结

**系统已完全就绪！**

✅ **核心功能**：
- 实时人气榜追踪
- 多智能体分析
- 个股报告生成
- 日报生成
- 持仓管理

✅ **使用流程**：
1. `python server.py` 启动服务器
2. 访问 `http://localhost:8080` 查看数据
3. 点击按钮生成报告
4. 查看信号执行交易

✅ **特色亮点**：
- 多智能体协作
- 辩论机制
- 记忆反思
- 风险控制
- 专业报告

**开始使用吧！** 🚀
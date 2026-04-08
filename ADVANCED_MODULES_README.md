# Advanced Trading System Modules

## 概述

本目录包含A股股票交易系统的五个核心高级模块:

1. **MLSC多标签股票分类器** (`models/`)
2. **强化学习动态权重调整** (`rl/`)
3. **专业回测框架** (`backtest/`)
4. **WebSocket实时数据推送** (`realtime/`)
5. **智能风控系统** (`risk/`)

所有模块已集成到 `advanced_features.py` 中。

---

## 模块详情

### 1. MLSC多标签股票分类器 (`models/`)

#### 核心文件
- `mlsc_model.py` - MLSC模型定义
- `mlsc_trainer.py` - 模型训练器

#### 主要功能
- 同时预测1天、3天、5天的股票趋势
- CNN + Multi-Head Attention + Bi-GRU混合架构
- 多任务学习框架
- 趋势持续性预测

#### 使用示例

```python
from models import MLSCPredictor

# 初始化预测器
predictor = MLSCPredictor('output/mlsc_model.pth')

# 准备历史数据
history = [...]  # 最近20-25天的股票数据

# 预测
predictions = predictor.predict(history)
consensus = predictor.get_consensus_signal(predictions)

print(f"信号: {consensus['consensus_signal']}")
print(f"置信度: {consensus['confidence']:.2%}")
print(f"持续性: {consensus['trend_sustainability']}")
```

#### 训练模型

```python
from models import MLSCTrainer

trainer = MLSCTrainer()
X, y = trainer.prepare_data_from_csv('training_data.csv')
train_loader, val_loader, test_loader = trainer.split_data(X, y)
results = trainer.train(train_loader, val_loader, epochs=100)
```

---

### 2. 强化学习动态权重调整 (`rl/`)

#### 核心文件
- `weight_optimizer.py` - RL权重优化器

#### 主要功能
- PPO算法动态调整因子权重
- 根据市场状态自适应优化
- 快速推理模式 (无需完整RL模型)

#### 使用示例

```python
from rl import RLWeightAdapter, MarketState

# 初始化
adapter = RLWeightAdapter('output/rl_weight_model.zip')

# 快速模式 (不需要RL模型)
weights = adapter.get_adaptive_weights(
    index_change=0.02,      # 大盘涨跌
    volatility=0.025,       # 波动率
    volume_ratio=1.5,       # 量比
    fear_greed=70           # 恐慌贪婪指数
)

print(f"优化后权重: {weights}")
```

---

### 3. 专业回测框架 (`backtest/`)

#### 核心文件
- `backtest_engine.py` - 回测引擎

#### 主要功能
- 完整的交易成本模拟 (佣金、印花税、滑点)
- T+1交易规则支持
- 止损止盈
- 详细的绩效统计

#### 使用示例

```python
from backtest import BacktestEngine, BacktestConfig

config = BacktestConfig(
    initial_capital=1000000,
    commission_rate=0.0003,
    stop_loss_pct=0.05,
    take_profit_pct=0.10
)

engine = BacktestEngine(config)

# 定义信号生成器
def my_signal_generator(data, positions):
    signals = []
    for _, row in data.iterrows():
        # 根据策略生成信号
        signals.append({
            'stock_code': row['stock_code'],
            'action': 'buy' if row['volume'] > 10000000 else 'hold',
            'price': row['close']
        })
    return signals

# 运行回测
result = engine.run(your_data, my_signal_generator)

# 查看结果
print(result.summary())
engine.plot_results(result)
```

---

### 4. WebSocket实时数据推送 (`realtime/`)

#### 核心文件
- `websocket_server.py` - WebSocket服务器
- `client_example.py` - 客户端示例

#### 主要功能
- 多客户端并发连接
- 股票订阅/取消订阅
- 实时信号推送
- 市场状态广播
- 心跳检测

#### 服务端使用

```python
from realtime import StockDataServer, StockSignal
from datetime import datetime

server = StockDataServer(host='0.0.0.0', port=8765)

# 设置回调
server.on_client_connect = lambda c: print(f"Client: {c.client_id}")

# 推送信号
signal = StockSignal(
    stock_code='000001',
    stock_name='平安银行',
    signal_type='buy',
    signal_strength=0.75,
    confidence=0.82,
    price=12.5,
    change_pct=2.5,
    timestamp=datetime.now()
)

asyncio.run(server.broadcast_signal('000001', signal.to_dict()))
```

#### 客户端使用

```python
from realtime import WebSocketClientExample
import asyncio

async def on_signal(stock_code, data):
    print(f"收到信号: {stock_code} - {data['signal_type']}")

client = WebSocketClientExample(
    uri='ws://localhost:8765',
    on_signal=on_signal
)

await client.connect()
await client.subscribe(['000001', '000002'])
await client.listen()
```

---

### 5. 智能风控系统 (`risk/`)

#### 核心文件
- `risk_manager.py` - 风控管理器

#### 主要功能
- VaR/CVaR风险指标计算
- 黑天鹅事件检测
- 智能仓位管理 (凯利公式)
- 实时风险监控
- 告警系统

#### 使用示例

```python
from risk import SmartRiskManager, RiskMetrics, Position
from datetime import datetime

# 初始化
risk_manager = SmartRiskManager(
    max_single_position=0.15,
    max_total_position=0.85,
    max_drawdown=0.15
)

# 更新持仓
positions = {
    '000001': Position(
        stock_code='000001',
        stock_name='平安银行',
        quantity=10000,
        avg_cost=12.0,
        current_price=12.5,
        entry_date=datetime.now()
    )
}

risk_manager.update_positions(positions, portfolio_value=1000000, cash=200000)

# 分析风险
market_data = {
    '000001': {'price': 12.5, 'volume': 50000000, 'volatility': 0.025}
}

metrics, alerts = risk_manager.analyze_risk(market_data)

print(f"VaR (95%): {metrics.var_95:.2%}")
print(f"告警数量: {len(alerts)}")

# 计算仓位
position_value, reason = risk_manager.get_position_size(
    signal_strength=0.7,
    stock_volatility=0.025,
    available_capital=200000
)
print(f"建议仓位: {position_value:,.2f}")
```

---

## 集成使用

```python
from advanced_features import AdvancedTradingSystem

# 初始化完整系统
system = AdvancedTradingSystem()
system.initialize()

# 综合分析
result = system.analyze_stock(
    stock_code='000001',
    history=stock_history,
    market_context={
        'index_change': 0.01,
        'volatility': 0.02,
        'volume_ratio': 1.2,
        'fear_greed': 60
    }
)

print(f"交易建议: {result['recommendation']['action']}")
print(f"信号: {result['recommendation']['signal']}")
print(f"置信度: {result['recommendation']['confidence']:.2%}")
```

---

## 依赖安装

```bash
# 核心依赖
pip install torch numpy pandas

# MLSC模型
pip install scikit-learn

# RL模块
pip install stable-baselines3

# WebSocket服务器
pip install websockets

# 回测图表
pip install matplotlib

# 完整安装
pip install torch numpy pandas scikit-learn stable-baselines3 websockets matplotlib
```

---

## 配置文件

配置文件位于 `config/advanced_config.json`:

```json
{
    "mlsc": {
        "model_path": "output/mlsc_model.pth",
        "enabled": true
    },
    "rl": {
        "model_path": "output/rl_weight_model.zip",
        "enabled": true
    },
    "backtest": {
        "initial_capital": 1000000,
        "commission_rate": 0.0003
    },
    "risk": {
        "max_single_position": 0.15,
        "max_drawdown": 0.15
    },
    "realtime": {
        "host": "0.0.0.0",
        "port": 8765
    }
}
```

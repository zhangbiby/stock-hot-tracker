# 高级模块集成指南

本文档说明如何将 MLSC、RL、回测、风控、WebSocket 等高级模块集成到现有系统中。

---

## 目录

1. [快速集成（推荐）](#1-快速集成推荐)
2. [模块化集成](#2-模块化集成)
3. [与现有 signal_engine.py 集成](#3-与现有-signal_enginepy-集成)
4. [与服务器 server.py 集成](#4-与服务器-serverpy-集成)
5. [API 参考](#5-api-参考)

---

## 1. 快速集成（推荐）

### 一步启动完整系统

```python
from advanced_features import AdvancedTradingSystem

# 创建系统
system = AdvancedTradingSystem()

# 初始化所有模块
system.initialize()

# 启动（包含WebSocket服务器）
system.start()

# 获取股票信号
signal = system.get_signal("000001", stock_data)

# 停止系统
system.stop()
```

---

## 2. 模块化集成

### 2.1 仅使用 MLSC 预测器

```python
from models import MLSCPredictor

# 创建预测器
predictor = MLSCPredictor(model_path='output/mlsc_model.pth')

# 预测信号
stock_history = [
    {'close': 10.5, 'volume': 1000000, 'high': 10.8, 'low': 10.2, ...},
    # ... 更多历史数据
]
prediction = predictor.predict("000001", stock_history)

print(f"1天信号: {prediction.signals[1].signal}")  # 'bullish', 'bearish', 'neutral'
print(f"3天信号: {prediction.signals[3].signal}")
print(f"5天信号: {prediction.signals[5].signal}")
print(f"综合置信度: {prediction.consensus_confidence:.2%}")
```

### 2.2 仅使用 RL 权重适配器

```python
from rl import RLWeightAdapter, MarketState

# 创建适配器
adapter = RLWeightAdapter()

# 获取市场状态
market_state = MarketState(
    index_change=0.5,      # 指数涨跌幅
    volatility=0.15,       # 波动率
    volume_ratio=1.2,      # 量比
    fear_greed_index=65,   # 恐慌贪婪指数
    up_count=1500,         # 上涨家数
    down_count=800         # 下跌家数
)

# 获取自适应权重
weights = adapter.get_adaptive_weights(market_state)

print(f"趋势权重: {weights['trend_weight']:.3f}")
print(f"动量权重: {weights['momentum_weight']:.3f}")
print(f"情绪权重: {weights['sentiment_weight']:.3f}")
```

### 2.3 仅使用回测引擎

```python
from backtest import BacktestEngine, BacktestConfig, BacktestSignal

# 创建引擎
config = BacktestConfig(
    initial_capital=1000000,
    commission_rate=0.0003,
    slippage_rate=0.001
)
engine = BacktestEngine(config)

# 定义信号生成器
def my_signal_generator(data: pd.DataFrame) -> List[BacktestSignal]:
    signals = []
    for i, row in data.iterrows():
        # 简单示例：MA金叉买入，死叉卖出
        if row['ma5'] > row['ma20'] and row['ma5_prev'] <= row['ma20_prev']:
            signals.append(BacktestSignal(
                date=data.index[i],
                stock_code='000001',
                action='buy',
                price=row['close'],
                quantity=100
            ))
        elif row['ma5'] < row['ma20']:
            signals.append(BacktestSignal(
                date=data.index[i],
                stock_code='000001',
                action='sell',
                price=row['close'],
                quantity=100
            ))
    return signals

# 运行回测
result = engine.run(data, my_signal_generator)

print(f"总收益率: {result.total_return:.2%}")
print(f"夏普比率: {result.sharpe_ratio:.2f}")
print(f"最大回撤: {result.max_drawdown:.2%}")
```

### 2.4 仅使用风控系统

```python
from risk import SmartRiskManager, Position

# 创建风控管理器
risk_mgr = SmartRiskManager(
    max_single_position=0.15,    # 单股最大仓位15%
    max_total_position=0.85,      # 总仓位不超过85%
    max_drawdown_limit=0.15      # 最大回撤15%
)

# 当前持仓
positions = [
    Position(stock_code='000001', quantity=1000, avg_price=10.5, current_price=11.0),
    Position(stock_code='000002', quantity=2000, avg_price=20.0, current_price=19.5),
]

# 市场数据
market_data = {
    '000001': {'price': 11.0, 'volume': 5000000, 'beta': 1.1},
    '000002': {'price': 19.5, 'volume': 3000000, 'beta': 0.9},
    'index': {'price': 3000, 'change': 0.5}
}

# 分析组合风险
metrics = risk_mgr.analyze_portfolio(positions, market_data)

print(f"VaR(95%): {metrics.var_95:.2%}")
print(f"CVaR(95%): {metrics.cvar_95:.2%}")
print(f"Beta: {metrics.beta:.2f}")
print(f"集中度风险: {metrics.concentration_risk:.2%}")

# 计算建议仓位
size = risk_mgr.calculate_position_size(
    signal_strength=0.8,      # 信号强度 0-1
    stock_risk=0.12,           # 股票风险
    portfolio_value=1000000    # 组合价值
)
print(f"建议仓位: {size:.2%}")

# 检测黑天鹅
if risk_mgr.detect_black_swan(market_data):
    print("⚠️ 警告：检测到黑天鹅事件！")
```

### 2.5 仅使用 WebSocket 推送

```python
from realtime import RealtimeSignalPusher, StockSignal

# 创建推送器
pusher = RealtimeSignalPusher(host='0.0.0.0', port=8765)

# 启动服务器
pusher.start()

# 推送信号
signal = StockSignal(
    stock_code='000001',
    signal='bullish',
    confidence=0.85,
    horizons={1: 0.8, 3: 0.75, 5: 0.7},
    timestamp=datetime.now()
)
pusher.push_signal('000001', signal)

# 推送市场状态
pusher.push_market_status(
    index='沪深300',
    change=0.5,
    volume_ratio=1.2,
    hot_stocks=['000001', '000002']
)

# 停止
pusher.stop()
```

---

## 3. 与现有 signal_engine.py 集成

### 3.1 扩展现有信号引擎

```python
# 在 signal_engine.py 中添加以下代码

# 导入高级模块
try:
    from models import MLSCPredictor
    from rl import RLWeightAdapter, MarketState
    MLSC_AVAILABLE = True
except ImportError:
    MLSC_AVAILABLE = False
    print("[SignalEngine] 高级模块未安装，跳过MLSC集成")

class EnhancedSignalEngine:
    """增强版信号引擎"""
    
    def __init__(self):
        self.mlsc_predictor = None
        self.rl_adapter = None
        
        # 初始化高级模块
        if MLSC_AVAILABLE:
            self._init_advanced_modules()
    
    def _init_advanced_modules(self):
        """初始化高级模块"""
        try:
            self.mlsc_predictor = MLSCPredictor()
            self.rl_adapter = RLWeightAdapter()
            print("[SignalEngine] 高级模块初始化成功")
        except Exception as e:
            print(f"[SignalEngine] 高级模块初始化失败: {e}")
    
    def calculate_signal(self, stock: dict) -> dict:
        """计算综合信号"""
        # 1. 基础信号（原有逻辑）
        base_signal = self._calculate_base_signal(stock)
        
        # 2. MLSC 多周期预测
        if self.mlsc_predictor:
            history = get_price_history(stock['code'])
            mlsc_pred = self.mlsc_predictor.predict(stock['code'], history)
            base_signal['mlsc'] = {
                '1d': mlsc_pred.signals[1].signal,
                '3d': mlsc_pred.signals[3].signal,
                '5d': mlsc_pred.signals[5].signal,
                'confidence': mlsc_pred.consensus_confidence
            }
        
        # 3. RL 权重调整
        if self.rl_adapter:
            market_state = MarketState(
                index_change=stock.get('index_change', 0),
                volatility=stock.get('volatility', 0.02),
                volume_ratio=stock.get('volume_ratio', 1),
                fear_greed_index=stock.get('fear_greed', 50),
                up_count=stock.get('up_count', 1000),
                down_count=stock.get('down_count', 1000)
            )
            weights = self.rl_adapter.get_adaptive_weights(market_state)
            base_signal['weights'] = weights
        
        # 4. 综合评分
        base_signal['final_score'] = self._calculate_final_score(base_signal)
        
        return base_signal
    
    def _calculate_final_score(self, signal: dict) -> float:
        """计算最终评分"""
        score = signal.get('base_score', 0.5)
        
        # MLSC 加权
        if 'mlsc' in signal:
            mlsc = signal['mlsc']
            if mlsc['confidence'] > 0.7:
                if mlsc['1d'] == 'bullish':
                    score += 0.1 * mlsc['confidence']
                elif mlsc['1d'] == 'bearish':
                    score -= 0.1 * mlsc['confidence']
        
        return max(0, min(1, score))
```

### 3.2 在交易策略中使用

```python
# 在现有策略中添加MLSC信号

def should_buy(stock: dict) -> bool:
    """判断是否应该买入"""
    # 原有买入条件
    base_condition = (
        stock['change_pct'] > 2 and
        stock['volume_ratio'] > 1.5 and
        stock['rsi'] < 70
    )
    
    # MLSC 确认
    if MLSC_AVAILABLE and stock.get('mlsc'):
        mlsc = stock['mlsc']
        mlsc_confirm = (
            mlsc['1d'] == 'bullish' and
            mlsc['confidence'] > 0.6
        )
        return base_condition and mlsc_confirm
    
    return base_condition
```

---

## 4. 与服务器 server.py 集成

### 4.1 添加 WebSocket 端点

```python
# 在 server.py 中添加

from realtime import RealtimeSignalPusher, StockSignal

class EnhancedServer:
    def __init__(self):
        self.signal_pusher = None
        
    def _init_realtime(self):
        """初始化实时推送"""
        self.signal_pusher = RealtimeSignalPusher(
            host='0.0.0.0',
            port=8765
        )
        self.signal_pusher.start()
    
    async def handle_signal_update(self, stock_code: str, signal: dict):
        """处理信号更新并推送"""
        # 原有逻辑...
        
        # 推送WebSocket信号
        if self.signal_pusher:
            ws_signal = StockSignal(
                stock_code=stock_code,
                signal=signal.get('final_signal', 'neutral'),
                confidence=signal.get('confidence', 0.5),
                horizons={
                    1: signal.get('mlsc_1d', 0.5),
                    3: signal.get('mlsc_3d', 0.5),
                    5: signal.get('mlsc_5d', 0.5)
                },
                timestamp=datetime.now()
            )
            self.signal_pusher.push_signal(stock_code, ws_signal)
```

### 4.2 添加回测API

```python
# 添加回测API端点

from backtest import BacktestEngine, BacktestConfig
from advanced_features import signal_generator_from_history

@app.route('/api/backtest', methods=['POST'])
def backtest_strategy():
    """回测策略"""
    data = request.json
    
    # 解析参数
    stock_codes = data.get('stocks', [])
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    
    # 获取历史数据
    history_data = {}
    for code in stock_codes:
        history_data[code] = get_price_history(code, start_date, end_date)
    
    # 运行回测
    config = BacktestConfig(
        initial_capital=data.get('capital', 1000000),
        commission_rate=data.get('commission', 0.0003)
    )
    engine = BacktestEngine(config)
    
    # 使用系统信号生成器
    def gen_signals(df):
        return signal_generator_from_history(df, strategy='mlsc')
    
    result = engine.run(pd.DataFrame(history_data), gen_signals)
    
    return jsonify({
        'total_return': result.total_return,
        'annualized_return': result.annualized_return,
        'sharpe_ratio': result.sharpe_ratio,
        'max_drawdown': result.max_drawdown,
        'win_rate': result.win_rate,
        'trades': len(result.trades)
    })
```

---

## 5. API 参考

### MLSCPredictor

| 方法 | 说明 | 参数 |
|------|------|------|
| `predict(stock_code, history)` | 预测信号 | 股票代码, 历史数据 |
| `get_consensus_signal(predictions)` | 获取共识信号 | 预测结果列表 |
| `is_loaded` | 模型是否加载 | 只读属性 |

### RLWeightAdapter

| 方法 | 说明 | 参数 |
|------|------|------|
| `get_adaptive_weights(market_state)` | 获取自适应权重 | MarketState对象 |
| `update_performance(weights, return_val)` | 更新性能反馈 | 权重, 收益率 |

### BacktestEngine

| 方法 | 说明 | 参数 |
|------|------|------|
| `run(data, signal_generator)` | 运行回测 | 数据, 信号生成器 |
| `get_trades()` | 获取交易记录 | - |
| `get_equity_curve()` | 获取资金曲线 | - |

### SmartRiskManager

| 方法 | 说明 | 参数 |
|------|------|------|
| `analyze_portfolio(positions, market_data)` | 分析组合风险 | 持仓, 市场数据 |
| `calculate_position_size(signal, risk, value)` | 计算仓位 | 信号强度, 风险, 价值 |
| `detect_black_swan(market_data)` | 检测黑天鹅 | 市场数据 |

### RealtimeSignalPusher

| 方法 | 说明 | 参数 |
|------|------|------|
| `start()` | 启动服务器 | - |
| `stop()` | 停止服务器 | - |
| `push_signal(code, signal)` | 推送信号 | 股票代码, 信号 |
| `push_market_status(...)` | 推送市场状态 | 多个市场指标 |

---

## 常见问题

### Q: 导入失败怎么办？

```bash
# 确保在正确目录
cd f:/QClaw/workspace/stock-hot-tracker/stock-hot-tracker/stock-hot-tracker

# 检查模块是否存在
ls models/
ls rl/
ls backtest/
ls risk/
ls realtime/
```

### Q: 如何训练MLSC模型？

```python
from models import MLSCPredictor, MLSCTrainer

# 准备数据
trainer = MLSCTrainer()
trainer.prepare_data(your_dataframe)

# 训练
trainer.train(epochs=50, batch_size=32)

# 保存
trainer.save('output/mlsc_model.pth')
```

### Q: 如何调整回测参数？

编辑 `config/advanced_config.json`:

```json
{
    "backtest": {
        "initial_capital": 1000000,
        "commission_rate": 0.0003,
        "slippage_rate": 0.001
    }
}
```

---

## 下一步

- 查看 [ADVANCED_MODULES_README.md](./ADVANCED_MODULES_README.md) 了解更多细节
- 查看各模块的源代码获取完整API
- 运行示例代码测试各模块功能

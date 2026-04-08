# 网页集成指南

本文档说明如何将高级交易模块集成到现有网页前端。

---

## 方案概览

```
┌─────────────────────────────────────────────────────────┐
│                    前端网页 (HTML/JS)                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
│  │  MLSC信号   │  │  风控面板   │  │  实时推送   │      │
│  │   展示      │  │   展示      │  │   接收      │      │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘      │
│         │                │                │              │
│         └────────────────┼────────────────┘              │
│                          │                               │
│                   JavaScript SDK                         │
│              (realtime_client.js)                        │
└──────────────────────────┼───────────────────────────────┘
                           │ WebSocket / HTTP
┌──────────────────────────┼───────────────────────────────┐
│                   Python 后端                             │
│         ┌────────────────┼────────────────┐             │
│         │                │                │              │
│  ┌──────┴──────┐  ┌──────┴──────┐  ┌──────┴──────┐      │
│  │  WebSocket  │  │    API      │  │  高级模块   │      │
│  │   服务器    │  │   端点      │  │  MLSC/RL    │      │
│  └─────────────┘  └─────────────┘  └─────────────┘      │
└─────────────────────────────────────────────────────────┘
```

---

## 快速开始

### 1. 启动增强服务器

```bash
cd f:/QClaw/workspace/stock-hot-tracker/stock-hot-tracker/stock-hot-tracker

# 启动增强服务器（包含WebSocket支持）
python enhanced_server.py
```

### 2. 在HTML中引入SDK

```html
<script src="/static/realtime_client.js"></script>
```

### 3. 使用示例

```javascript
// 连接服务器
const client = new AdvancedTradingClient('ws://localhost:8765');

// 连接成功
client.onConnect = () => {
    console.log('已连接到高级交易服务器');
};

// 接收实时信号
client.onSignal = (signal) => {
    console.log('收到信号:', signal);
    // signal.stock_code  - 股票代码
    // signal.signal      - 信号类型: bullish/bearish/neutral
    // signal.confidence  - 置信度 0-1
    // signal.horizons    - {1: 0.8, 3: 0.75, 5: 0.7} 各周期预测
};

// 接收风控警告
client.onRiskAlert = (alert) => {
    console.log('风控警告:', alert);
    // alert.level       - 警告级别: warning/critical
    // alert.message     - 警告信息
};

// 订阅股票
client.subscribe('000001');
client.subscribe('000002');
```

---

## WebSocket 消息格式

### 客户端 → 服务器

```javascript
// 订阅股票
{ "type": "subscribe", "stock_code": "000001" }

// 取消订阅
{ "type": "unsubscribe", "stock_code": "000001" }

// 请求信号
{ "type": "get_signal", "stock_code": "000001" }

// 请求风控分析
{ "type": "risk_analysis" }
```

### 服务器 → 客户端

```javascript
// 实时信号推送
{
    "type": "signal",
    "stock_code": "000001",
    "signal": "bullish",
    "confidence": 0.85,
    "horizons": { "1d": "bullish", "3d": "bullish", "5d": "neutral" },
    "timestamp": "2026-04-08T21:30:00"
}

// 风控警告
{
    "type": "risk_alert",
    "level": "warning",
    "message": "检测到黑天鹅事件",
    "metrics": { "var_95": 0.05, "cvar_95": 0.08 }
}

// 市场状态
{
    "type": "market_status",
    "index": "沪深300",
    "change": 0.5,
    "volume_ratio": 1.2,
    "hot_stocks": ["000001", "000002"]
}
```

---

## HTTP API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/mlsc/{stock_code}` | GET | 获取MLSC预测 |
| `/api/risk/analysis` | GET | 获取风控指标 |
| `/api/weights` | GET | 获取自适应权重 |
| `/api/backtest` | POST | 运行回测 |

### 示例响应

**GET /api/mlsc/000001**
```json
{
    "stock_code": "000001",
    "signals": {
        "1d": { "signal": "bullish", "confidence": 0.82 },
        "3d": { "signal": "bullish", "confidence": 0.75 },
        "5d": { "signal": "neutral", "confidence": 0.60 }
    },
    "consensus_signal": "bullish",
    "consensus_confidence": 0.72
}
```

---

## 前端组件示例

### MLSC 信号卡片

```html
<div class="mlsc-signal-card" id="card_000001">
    <h3>000001 平安银行</h3>
    <div class="signal-badge" id="badge_000001">--</div>
    <div class="horizons">
        <span>1天: <b id="h1d_000001">--</b></span>
        <span>3天: <b id="h3d_000001">--</b></span>
        <span>5天: <b id="h5d_000001">--</b></span>
    </div>
    <div class="confidence-bar">
        <div class="bar" id="bar_000001"></div>
    </div>
</div>
```

```javascript
// 更新信号显示
function updateSignal(signal) {
    const code = signal.stock_code;
    document.getElementById(`badge_${code}`).textContent = signal.signal;
    document.getElementById(`badge_${code}`).className = `signal-badge ${signal.signal}`;
    document.getElementById(`h1d_${code}`).textContent = signal.horizons['1d'];
    document.getElementById(`h3d_${code}`).textContent = signal.horizons['3d'];
    document.getElementById(`h5d_${code}`).textContent = signal.horizons['5d'];
    document.getElementById(`bar_${code}`).style.width = (signal.confidence * 100) + '%';
}

client.onSignal = updateSignal;
```

### 样式

```css
.signal-badge { padding: 4px 12px; border-radius: 4px; font-weight: bold; }
.signal-badge.bullish { background: #4caf50; color: white; }
.signal-badge.bearish { background: #f44336; color: white; }
.signal-badge.neutral { background: #9e9e9e; color: white; }
.confidence-bar { height: 8px; background: #eee; border-radius: 4px; }
.confidence-bar .bar { height: 100%; background: #4caf50; }
```

---

## 完整示例

查看 `web_integration_example.html` 获取完整示例。

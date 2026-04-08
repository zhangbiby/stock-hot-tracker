/**
 * Advanced Trading WebSocket Client SDK
 * 前端实时交易信号接收SDK
 */

class AdvancedTradingClient {
    constructor(wsUrl) {
        this.wsUrl = wsUrl;
        this.ws = null;
        this.connected = false;
        this.subscribedStocks = new Set();
        
        // 回调函数
        this.onConnect = null;
        this.onDisconnect = null;
        this.onSignal = null;
        this.onRiskAlert = null;
        this.onMarketStatus = null;
        this.onError = null;
        
        // 重连配置
        this.reconnectInterval = 3000;
        this.maxReconnectAttempts = 10;
        this.reconnectAttempts = 0;
        
        // 连接
        this.connect();
    }
    
    connect() {
        try {
            this.ws = new WebSocket(this.wsUrl);
            
            this.ws.onopen = () => {
                this.connected = true;
                this.reconnectAttempts = 0;
                console.log('[TradingClient] 已连接');
                
                // 重新订阅之前订阅的股票
                for (const code of this.subscribedStocks) {
                    this.send({ type: 'subscribe', stock_code: code });
                }
                
                if (this.onConnect) this.onConnect();
            };
            
            this.ws.onclose = () => {
                this.connected = false;
                console.log('[TradingClient] 连接断开');
                if (this.onDisconnect) this.onDisconnect();
                
                // 自动重连
                if (this.reconnectAttempts < this.maxReconnectAttempts) {
                    this.reconnectAttempts++;
                    console.log(`[TradingClient] ${this.reconnectInterval/1000}秒后重连...`);
                    setTimeout(() => this.connect(), this.reconnectInterval);
                }
            };
            
            this.ws.onerror = (error) => {
                console.error('[TradingClient] WebSocket错误:', error);
                if (this.onError) this.onError(error);
            };
            
            this.ws.onmessage = (event) => {
                this.handleMessage(JSON.parse(event.data));
            };
            
        } catch (error) {
            console.error('[TradingClient] 连接失败:', error);
            if (this.onError) this.onError(error);
        }
    }
    
    handleMessage(data) {
        switch (data.type) {
            case 'signal':
                if (this.onSignal) this.onSignal(data);
                break;
            case 'risk_alert':
                if (this.onRiskAlert) this.onRiskAlert(data);
                break;
            case 'market_status':
                if (this.onMarketStatus) this.onMarketStatus(data);
                break;
            case 'error':
                console.error('[TradingClient] 服务器错误:', data.message);
                break;
            default:
                console.log('[TradingClient] 未知消息类型:', data.type);
        }
    }
    
    send(message) {
        if (this.ws && this.connected) {
            this.ws.send(JSON.stringify(message));
        }
    }
    
    // 订阅股票信号
    subscribe(stockCode) {
        this.subscribedStocks.add(stockCode);
        this.send({ type: 'subscribe', stock_code: stockCode });
    }
    
    // 取消订阅
    unsubscribe(stockCode) {
        this.subscribedStocks.delete(stockCode);
        this.send({ type: 'unsubscribe', stock_code: stockCode });
    }
    
    // 请求信号
    getSignal(stockCode) {
        this.send({ type: 'get_signal', stock_code: stockCode });
    }
    
    // 请求风控分析
    getRiskAnalysis() {
        this.send({ type: 'risk_analysis' });
    }
    
    // 断开连接
    disconnect() {
        this.maxReconnectAttempts = 0;  // 防止自动重连
        if (this.ws) {
            this.ws.close();
        }
    }
}

// ============================================

/**
 * 简化的HTTP API客户端（用于不支持WebSocket的情况）
 */
class TradingAPIClient {
    constructor(baseUrl = '') {
        this.baseUrl = baseUrl;
    }
    
    async getMLSCSignal(stockCode) {
        const response = await fetch(`${this.baseUrl}/api/mlsc/${stockCode}`);
        return response.json();
    }
    
    async getRiskAnalysis() {
        const response = await fetch(`${this.baseUrl}/api/risk/analysis`);
        return response.json();
    }
    
    async getWeights() {
        const response = await fetch(`${this.baseUrl}/api/weights`);
        return response.json();
    }
    
    async runBacktest(params) {
        const response = await fetch(`${this.baseUrl}/api/backtest`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params)
        });
        return response.json();
    }
}

// 导出
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { AdvancedTradingClient, TradingAPIClient };
}

# -*- coding: utf-8 -*-
"""
WebSocket Client Example
WebSocket客户端示例代码
"""

import asyncio
import json
from typing import Set, Callable, Optional
from datetime import datetime

try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False


class WebSocketClientExample:
    """
    WebSocket客户端示例
    
    用法:
        client = WebSocketClientExample('ws://localhost:8765')
        client.subscribe(['000001', '000002'])
        client.connect()
    """
    
    def __init__(
        self,
        uri: str = 'ws://localhost:8765',
        on_signal: Optional[Callable] = None,
        on_market_status: Optional[Callable] = None,
        on_alert: Optional[Callable] = None
    ):
        """
        Args:
            uri: WebSocket服务器地址
            on_signal: 信号回调函数
            on_market_status: 市场状态回调函数
            on_alert: 告警回调函数
        """
        self.uri = uri
        self.websocket = None
        self.running = False
        
        # 回调函数
        self.on_signal = on_signal
        self.on_market_status = on_market_status
        self.on_alert = on_alert
        
        # 状态
        self.subscriptions: Set[str] = set()
        self.message_count = 0
        self.last_message_time = None
    
    async def connect(self):
        """连接到WebSocket服务器"""
        if not WEBSOCKETS_AVAILABLE:
            print("[WebSocketClient] websockets library not available")
            return False
        
        try:
            self.websocket = await websockets.connect(self.uri)
            self.running = True
            print(f"[WebSocketClient] Connected to {self.uri}")
            return True
        except Exception as e:
            print(f"[WebSocketClient] Connection failed: {e}")
            return False
    
    async def disconnect(self):
        """断开连接"""
        self.running = False
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
        print("[WebSocketClient] Disconnected")
    
    async def subscribe(self, stocks: list):
        """
        订阅股票
        
        Args:
            stocks: 股票代码列表
        """
        if not self.websocket:
            print("[WebSocketClient] Not connected")
            return
        
        message = {
            'type': 'subscribe',
            'stocks': stocks
        }
        
        await self.websocket.send(json.dumps(message))
        self.subscriptions.update(stocks)
        print(f"[WebSocketClient] Subscribed to: {stocks}")
    
    async def unsubscribe(self, stocks: list):
        """取消订阅"""
        if not self.websocket:
            print("[WebSocketClient] Not connected")
            return
        
        message = {
            'type': 'unsubscribe',
            'stocks': stocks
        }
        
        await self.websocket.send(json.dumps(message))
        self.subscriptions.difference_update(stocks)
        print(f"[WebSocketClient] Unsubscribed from: {stocks}")
    
    async def send_ping(self):
        """发送心跳"""
        if not self.websocket:
            return
        
        message = {
            'type': 'ping',
            'timestamp': datetime.now().isoformat()
        }
        
        await self.websocket.send(json.dumps(message))
    
    async def listen(self):
        """监听消息"""
        if not self.websocket:
            print("[WebSocketClient] Not connected")
            return
        
        print("[WebSocketClient] Listening for messages...")
        
        try:
            while self.running:
                message = await self.websocket.recv()
                self.message_count += 1
                self.last_message_time = datetime.now()
                
                await self._handle_message(message)
                
        except websockets.exceptions.ConnectionClosed:
            print("[WebSocketClient] Connection closed")
            self.running = False
    
    async def _handle_message(self, message: str):
        """处理接收到的消息"""
        try:
            data = json.loads(message)
            msg_type = data.get('type')
            
            if msg_type == 'signal_update':
                await self._handle_signal_update(data)
                
            elif msg_type == 'market_status':
                await self._handle_market_status(data)
                
            elif msg_type == 'alert':
                await self._handle_alert(data)
                
            elif msg_type == 'pong':
                pass  # 心跳响应
                
            elif msg_type == 'error':
                print(f"[WebSocketClient] Server error: {data.get('message')}")
                
            else:
                print(f"[WebSocketClient] Unknown message type: {msg_type}")
                
        except json.JSONDecodeError:
            print(f"[WebSocketClient] Invalid JSON: {message}")
    
    async def _handle_signal_update(self, data: dict):
        """处理信号更新"""
        signal_data = data.get('data', {})
        stock_code = data.get('stock_code')
        
        print(f"\n[Signal] {stock_code}:")
        print(f"  Signal: {signal_data.get('signal_type')}")
        print(f"  Strength: {signal_data.get('signal_strength'):.2%}")
        print(f"  Price: {signal_data.get('price'):.2f}")
        print(f"  Change: {signal_data.get('change_pct'):.2f}%")
        
        # 调用回调
        if self.on_signal:
            self.on_signal(stock_code, signal_data)
    
    async def _handle_market_status(self, data: dict):
        """处理市场状态"""
        status = data.get('data', {})
        
        print(f"\n[Market] {status.get('index_name')}:")
        print(f"  Value: {status.get('index_value'):.2f}")
        print(f"  Change: {status.get('change_pct'):.2f}%")
        print(f"  Mode: {status.get('market_mode')}")
        
        if self.on_market_status:
            self.on_market_status(status)
    
    async def _handle_alert(self, data: dict):
        """处理告警"""
        alert = data.get('data', {})
        
        print(f"\n[ALERT] {alert.get('title', 'Warning')}:")
        print(f"  {alert.get('message')}")
        
        if self.on_alert:
            self.on_alert(alert)
    
    def get_stats(self) -> dict:
        """获取连接统计"""
        return {
            'connected': self.websocket is not None,
            'subscriptions': list(self.subscriptions),
            'message_count': self.message_count,
            'last_message': self.last_message_time.isoformat() if self.last_message_time else None
        }


async def example_usage():
    """示例用法"""
    
    def on_signal(stock_code, data):
        """信号回调"""
        if data.get('signal_strength', 0) > 0.7:
            print(f"  -> Strong buy signal!")
    
    # 创建客户端
    client = WebSocketClientExample(
        uri='ws://localhost:8765',
        on_signal=on_signal
    )
    
    # 连接
    if not await client.connect():
        return
    
    # 订阅股票
    await client.subscribe(['000001', '000002', '000004'])
    
    # 监听消息 (会一直运行)
    # await client.listen()
    
    # 或者只监听N条消息
    for _ in range(10):
        try:
            message = await asyncio.wait_for(client.websocket.recv(), timeout=10)
            await client._handle_message(message)
        except asyncio.TimeoutError:
            await client.send_ping()
            print("[.] Still connected...")
    
    # 断开连接
    await client.disconnect()


if __name__ == '__main__':
    if WEBSOCKETS_AVAILABLE:
        asyncio.run(example_usage())
    else:
        print("websockets library not installed")

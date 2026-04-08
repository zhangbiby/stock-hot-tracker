# -*- coding: utf-8 -*-
"""
WebSocket Real-time Data Push Server
WebSocket实时数据推送服务器

特性:
- 支持多客户端并发连接
- 实时推送股票信号更新
- 心跳检测保持连接
- 订阅/取消订阅机制
"""

import asyncio
import json
import logging
from typing import Set, Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from enum import Enum

# 尝试导入websockets库
try:
    import websockets
    from websockets.server import WebSocketServerProtocol
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    WebSocketServerProtocol = Any
    print("[WebSocketServer] websockets library not installed. Real-time features disabled.")
    print("[WebSocketServer] Install with: pip install websockets")


# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MessageType(Enum):
    """消息类型枚举"""
    # 客户端 -> 服务器
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    PING = "ping"
    
    # 服务器 -> 客户端
    SUBSCRIBED = "subscribed"
    UNSUBSCRIBED = "unsubscribed"
    PONG = "pong"
    
    # 数据推送
    SIGNAL_UPDATE = "signal_update"
    MARKET_STATUS = "market_status"
    ALERT = "alert"
    ERROR = "error"


@dataclass
class Client:
    """客户端连接"""
    websocket: WebSocketServerProtocol
    client_id: str
    subscriptions: Set[str] = field(default_factory=set)  # 订阅的股票代码
    ip_address: str = ""
    user_agent: str = ""
    connected_at: datetime = field(default_factory=datetime.now)
    last_ping: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        return {
            'client_id': self.client_id,
            'subscriptions': list(self.subscriptions),
            'ip_address': self.ip_address,
            'connected_at': self.connected_at.isoformat(),
            'is_alive': self.is_alive()
        }
    
    def is_alive(self) -> bool:
        """检查连接是否活跃 (5分钟内有心跳)"""
        return (datetime.now() - self.last_ping).seconds < 300


@dataclass
class StockSignal:
    """股票信号数据"""
    stock_code: str
    stock_name: str
    signal_type: str                    # 'buy', 'sell', 'hold'
    signal_strength: float              # 0-1
    confidence: float                  # 置信度 0-1
    price: float
    change_pct: float
    timestamp: datetime
    
    # 详细分析
    technical_score: float = 0
    sentiment_score: float = 0
    capital_flow_score: float = 0
    industry_score: float = 0
    
    # 预测
    prediction_1d: Dict = field(default_factory=dict)
    prediction_3d: Dict = field(default_factory=dict)
    prediction_5d: Dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            'stock_code': self.stock_code,
            'stock_name': self.stock_name,
            'signal_type': self.signal_type,
            'signal_strength': round(self.signal_strength, 4),
            'confidence': round(self.confidence, 4),
            'price': self.price,
            'change_pct': round(self.change_pct, 2),
            'timestamp': self.timestamp.isoformat(),
            'analysis': {
                'technical': round(self.technical_score, 4),
                'sentiment': round(self.sentiment_score, 4),
                'capital_flow': round(self.capital_flow_score, 4),
                'industry': round(self.industry_score, 4)
            },
            'predictions': {
                '1d': self.prediction_1d,
                '3d': self.prediction_3d,
                '5d': self.prediction_5d
            }
        }


@dataclass
class MarketStatus:
    """市场状态"""
    index_name: str
    index_value: float
    change_pct: float
    volume: float
    market_mode: str                   # 'bull', 'bear', 'sideways'
    fear_greed_index: float = 50
    northbound_flow: float = 0
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        return {
            'index_name': self.index_name,
            'index_value': round(self.index_value, 2),
            'change_pct': round(self.change_pct, 2),
            'volume': self.volume,
            'market_mode': self.market_mode,
            'fear_greed_index': round(self.fear_greed_index, 2),
            'northbound_flow': self.northbound_flow,
            'timestamp': self.timestamp.isoformat()
        }


class StockDataServer:
    """
    WebSocket实时数据推送服务器
    
    支持功能:
    - 多客户端并发连接
    - 股票订阅/取消订阅
    - 信号实时推送
    - 市场状态广播
    - 告警推送
    - 心跳检测
    """
    
    def __init__(
        self,
        host: str = '0.0.0.0',
        port: int = 8765,
        ping_interval: int = 30,
        ping_timeout: int = 10
    ):
        """
        Args:
            host: 服务器地址
            port: 服务器端口
            ping_interval: 心跳间隔(秒)
            ping_timeout: 心跳超时(秒)
        """
        self.host = host
        self.port = port
        self.ping_interval = ping_interval
        self.ping_timeout = ping_timeout
        
        self.clients: Dict[str, Client] = {}
        self.subscriptions: Dict[str, Set[str]] = {}  # {stock_code: {client_ids}}
        
        self.running = False
        self.server = None
        self.push_queue: asyncio.Queue = asyncio.Queue()
        
        # 回调函数
        self.on_client_connect: Optional[Callable] = None
        self.on_client_disconnect: Optional[Callable] = None
        self.on_subscribe: Optional[Callable] = None
        
        # 统计
        self.stats = {
            'total_messages_sent': 0,
            'total_connections': 0,
            'start_time': datetime.now().isoformat()
        }
        
        logger.info(f"[WebSocketServer] Initialized on {host}:{port}")
    
    async def start(self):
        """启动服务器"""
        if not WEBSOCKETS_AVAILABLE:
            logger.error("[WebSocketServer] Cannot start: websockets library not available")
            return
        
        self.running = True
        
        # 启动消息处理协程
        asyncio.create_task(self._process_push_queue())
        asyncio.create_task(self._cleanup_inactive_clients())
        
        # 启动WebSocket服务器
        async with websockets.serve(
            self._handle_client,
            self.host,
            self.port,
            ping_interval=self.ping_interval,
            ping_timeout=self.ping_timeout
        ):
            logger.info(f"[WebSocketServer] Started on ws://{self.host}:{self.port}")
            
            # 保持运行
            while self.running:
                await asyncio.sleep(1)
    
    async def stop(self):
        """停止服务器"""
        self.running = False
        
        # 关闭所有客户端连接
        for client_id, client in list(self.clients.items()):
            try:
                await client.websocket.close()
            except:
                pass
        
        self.clients.clear()
        self.subscriptions.clear()
        
        logger.info("[WebSocketServer] Stopped")
    
    async def _handle_client(self, websocket: WebSocketServerProtocol, path: str):
        """处理客户端连接"""
        # 获取客户端信息
        client_id = f"{websocket.remote_address[0]}_{datetime.now().timestamp()}"
        
        try:
            # 获取WebSocket headers
            headers = dict(websocket.request_headers) if hasattr(websocket, 'request_headers') else {}
            
            client = Client(
                websocket=websocket,
                client_id=client_id,
                ip_address=websocket.remote_address[0] if websocket.remote_address else "unknown",
                user_agent=headers.get('User-Agent', 'Unknown')
            )
            
            self.clients[client_id] = client
            self.stats['total_connections'] += 1
            
            logger.info(f"[WebSocketServer] Client connected: {client_id} from {client.ip_address}")
            
            # 调用回调
            if self.on_client_connect:
                self.on_client_connect(client)
            
            # 处理消息
            async for message in websocket:
                await self._handle_message(client, message)
                
        except websockets.exceptions.ConnectionClosed as e:
            logger.info(f"[WebSocketServer] Client disconnected: {client_id}, reason: {e.reason}")
        except Exception as e:
            logger.error(f"[WebSocketServer] Error handling client {client_id}: {e}")
        finally:
            # 清理
            if client_id in self.clients:
                await self._remove_client(client_id)
    
    async def _handle_message(self, client: Client, message: str):
        """处理客户端消息"""
        try:
            data = json.loads(message)
            msg_type = data.get('type')
            
            if msg_type == MessageType.SUBSCRIBE.value:
                await self._handle_subscribe(client, data)
                
            elif msg_type == MessageType.UNSUBSCRIBE.value:
                await self._handle_unsubscribe(client, data)
                
            elif msg_type == MessageType.PING.value:
                client.last_ping = datetime.now()
                await self._send_message(client, {
                    'type': MessageType.PONG.value,
                    'timestamp': datetime.now().isoformat()
                })
                
            else:
                await self._send_error(client, f"Unknown message type: {msg_type}")
                
        except json.JSONDecodeError:
            await self._send_error(client, "Invalid JSON format")
        except Exception as e:
            logger.error(f"[WebSocketServer] Error handling message: {e}")
            await self._send_error(client, str(e))
    
    async def _handle_subscribe(self, client: Client, data: dict):
        """处理订阅请求"""
        stocks = data.get('stocks', [])
        if not stocks:
            await self._send_error(client, "No stocks specified")
            return
        
        # 添加订阅
        for stock_code in stocks:
            if stock_code not in self.subscriptions:
                self.subscriptions[stock_code] = set()
            self.subscriptions[stock_code].add(client.client_id)
            client.subscriptions.add(stock_code)
        
        # 确认订阅
        await self._send_message(client, {
            'type': MessageType.SUBSCRIBED.value,
            'stocks': stocks,
            'timestamp': datetime.now().isoformat()
        })
        
        logger.info(f"[WebSocketServer] Client {client.client_id} subscribed to {stocks}")
        
        # 调用回调
        if self.on_subscribe:
            self.on_subscribe(client, stocks)
    
    async def _handle_unsubscribe(self, client: Client, data: dict):
        """处理取消订阅请求"""
        stocks = data.get('stocks', [])
        
        for stock_code in stocks:
            self.subscriptions.get(stock_code, set()).discard(client.client_id)
            client.subscriptions.discard(stock_code)
        
        await self._send_message(client, {
            'type': MessageType.UNSUBSCRIBED.value,
            'stocks': stocks,
            'timestamp': datetime.now().isoformat()
        })
    
    async def _remove_client(self, client_id: str):
        """移除客户端"""
        if client_id not in self.clients:
            return
        
        client = self.clients[client_id]
        
        # 清理订阅
        for stock_code in client.subscriptions:
            if stock_code in self.subscriptions:
                self.subscriptions[stock_code].discard(client_id)
        
        del self.clients[client_id]
        
        # 调用回调
        if self.on_client_disconnect:
            self.on_client_disconnect(client)
        
        logger.info(f"[WebSocketServer] Client {client_id} removed")
    
    async def _send_message(self, client: Client, data: dict):
        """发送消息到客户端"""
        try:
            await client.websocket.send(json.dumps(data, ensure_ascii=False))
            self.stats['total_messages_sent'] += 1
        except websockets.exceptions.ConnectionClosed:
            await self._remove_client(client.client_id)
        except Exception as e:
            logger.error(f"[WebSocketServer] Error sending message: {e}")
    
    async def _send_error(self, client: Client, error_message: str):
        """发送错误消息"""
        await self._send_message(client, {
            'type': MessageType.ERROR.value,
            'message': error_message,
            'timestamp': datetime.now().isoformat()
        })
    
    async def _process_push_queue(self):
        """处理推送队列"""
        while True:
            try:
                item = await asyncio.wait_for(self.push_queue.get(), timeout=1.0)
                
                push_type = item.get('type')
                
                if push_type == 'signal':
                    await self.broadcast_signal(item['stock_code'], item['data'])
                elif push_type == 'market':
                    await self.broadcast_market_status(item['data'])
                elif push_type == 'alert':
                    await self.broadcast_alert(item['data'])
                elif push_type == 'custom':
                    await self.broadcast_custom(item['data'], item.get('target_clients'))
                    
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"[WebSocketServer] Error processing push queue: {e}")
    
    async def _cleanup_inactive_clients(self):
        """清理不活跃的客户端"""
        while True:
            await asyncio.sleep(60)  # 每分钟检查一次
            
            inactive = [
                client_id for client_id, client in self.clients.items()
                if not client.is_alive()
            ]
            
            for client_id in inactive:
                try:
                    client = self.clients.get(client_id)
                    if client:
                        await client.websocket.close()
                except:
                    pass
    
    # ==================== 公共推送方法 ====================
    
    def push_signal(self, stock_code: str, signal: StockSignal):
        """添加信号到推送队列 (线程安全)"""
        asyncio.create_task(self.push_queue.put({
            'type': 'signal',
            'stock_code': stock_code,
            'data': signal.to_dict()
        }))
    
    def push_market_status(self, status: MarketStatus):
        """推送市场状态"""
        asyncio.create_task(self.push_queue.put({
            'type': 'market',
            'data': status.to_dict()
        }))
    
    def push_alert(self, alert: Dict):
        """推送告警"""
        asyncio.create_task(self.push_queue.put({
            'type': 'alert',
            'data': alert
        }))
    
    async def broadcast_signal(self, stock_code: str, signal_data: dict):
        """广播信号到订阅的客户端"""
        if stock_code not in self.subscriptions:
            return
        
        message = json.dumps({
            'type': MessageType.SIGNAL_UPDATE.value,
            'stock_code': stock_code,
            'timestamp': datetime.now().isoformat(),
            'data': signal_data
        }, ensure_ascii=False)
        
        # 发送给订阅的客户端
        clients = list(self.subscriptions[stock_code])
        
        for client_id in clients:
            client = self.clients.get(client_id)
            if client:
                try:
                    await client.websocket.send(message)
                    self.stats['total_messages_sent'] += 1
                except websockets.exceptions.ConnectionClosed:
                    await self._remove_client(client_id)
    
    async def broadcast_market_status(self, status_data: dict):
        """广播市场状态到所有客户端"""
        message = json.dumps({
            'type': MessageType.MARKET_STATUS.value,
            'timestamp': datetime.now().isoformat(),
            'data': status_data
        }, ensure_ascii=False)
        
        for client in list(self.clients.values()):
            try:
                await client.websocket.send(message)
                self.stats['total_messages_sent'] += 1
            except websockets.exceptions.ConnectionClosed:
                await self._remove_client(client.client_id)
    
    async def broadcast_alert(self, alert_data: dict):
        """广播告警到指定客户端或所有客户端"""
        target_clients = alert_data.pop('target_clients', None)
        
        message = json.dumps({
            'type': MessageType.ALERT.value,
            'timestamp': datetime.now().isoformat(),
            'data': alert_data
        }, ensure_ascii=False)
        
        clients = list(self.clients.values())
        
        # 如果指定了目标客户端，过滤
        if target_clients:
            clients = [c for c in clients if c.client_id in target_clients]
        
        for client in clients:
            try:
                await client.websocket.send(message)
                self.stats['total_messages_sent'] += 1
            except websockets.exceptions.ConnectionClosed:
                await self._remove_client(client.client_id)
    
    async def broadcast_custom(self, data: dict, client_ids: List[str] = None):
        """广播自定义消息"""
        message = json.dumps(data, ensure_ascii=False)
        
        clients = list(self.clients.values())
        if client_ids:
            clients = [c for c in clients if c.client_id in client_ids]
        
        for client in clients:
            try:
                await client.websocket.send(message)
            except websockets.exceptions.ConnectionClosed:
                await self._remove_client(client.client_id)
    
    def get_stats(self) -> dict:
        """获取服务器统计"""
        return {
            **self.stats,
            'active_clients': len(self.clients),
            'total_subscriptions': sum(len(s) for s in self.subscriptions.values()),
            'subscribed_stocks': len(self.subscriptions)
        }


class RealtimeSignalPusher:
    """
    实时信号推送器
    
    集成到现有的信号引擎中，自动推送信号更新
    """
    
    def __init__(
        self,
        ws_host: str = '0.0.0.0',
        ws_port: int = 8765
    ):
        """
        Args:
            ws_host: WebSocket服务器地址
            ws_port: WebSocket服务器端口
        """
        self.ws_host = ws_host
        self.ws_port = ws_port
        
        self.server = StockDataServer(ws_host, ws_port)
        self.push_queue: asyncio.Queue = asyncio.Queue()
        
        # 缓存最近的信号
        self.signal_cache: Dict[str, StockSignal] = {}
        
        # 是否正在运行
        self.is_running = False
    
    async def start(self):
        """启动推送服务"""
        self.is_running = True
        
        # 启动WebSocket服务器
        asyncio.create_task(self.server.start())
        
        # 启动推送处理器
        asyncio.create_task(self._process_push_queue())
        
        print(f"[RealtimePusher] Started WebSocket server on ws://{self.ws_host}:{self.ws_port}")
    
    async def stop(self):
        """停止推送服务"""
        self.is_running = False
        await self.server.stop()
    
    async def _process_push_queue(self):
        """处理推送队列"""
        while self.is_running:
            try:
                item = await asyncio.wait_for(self.push_queue.get(), timeout=1.0)
                
                push_type = item.get('type')
                
                if push_type == 'signal':
                    signal = item['signal']
                    self.signal_cache[signal.stock_code] = signal
                    self.server.push_signal(signal.stock_code, signal)
                    
                elif push_type == 'batch_signals':
                    # 批量推送
                    for signal in item['signals']:
                        self.signal_cache[signal.stock_code] = signal
                    self.server.push_signal(item['stock_code'], item['signals'][0])
                    
                elif push_type == 'market':
                    self.server.push_market_status(item['status'])
                    
                elif push_type == 'alert':
                    self.server.push_alert(item['alert'])
                    
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"[RealtimePusher] Error processing push: {e}")
    
    def push_signal(self, signal: StockSignal):
        """推送单个信号"""
        if self.is_running:
            asyncio.create_task(self.push_queue.put({
                'type': 'signal',
                'signal': signal
            }))
    
    def push_batch_signals(self, signals: List[StockSignal], top_stock: str):
        """批量推送信号 (推送top1)"""
        if self.is_running and signals:
            asyncio.create_task(self.push_queue.put({
                'type': 'batch_signals',
                'signals': [s.to_dict() for s in signals],
                'stock_code': top_stock
            }))
    
    def push_market_status(self, status: MarketStatus):
        """推送市场状态"""
        if self.is_running:
            asyncio.create_task(self.push_queue.put({
                'type': 'market',
                'status': status
            }))
    
    def push_alert(self, alert: Dict):
        """推送告警"""
        if self.is_running:
            asyncio.create_task(self.push_queue.put({
                'type': 'alert',
                'alert': alert
            }))
    
    def create_signal_from_dict(self, data: dict) -> StockSignal:
        """从字典创建信号"""
        return StockSignal(
            stock_code=data['stock_code'],
            stock_name=data.get('stock_name', ''),
            signal_type=data.get('signal_type', 'hold'),
            signal_strength=data.get('signal_strength', 0),
            confidence=data.get('confidence', 0),
            price=data.get('price', 0),
            change_pct=data.get('change_pct', 0),
            timestamp=datetime.now(),
            technical_score=data.get('technical_score', 0),
            sentiment_score=data.get('sentiment_score', 0),
            capital_flow_score=data.get('capital_flow_score', 0),
            industry_score=data.get('industry_score', 0),
            prediction_1d=data.get('prediction_1d', {}),
            prediction_3d=data.get('prediction_3d', {}),
            prediction_5d=data.get('prediction_5d', {})
        )


# 便捷函数
async def run_server():
    """运行WebSocket服务器"""
    server = StockDataServer()
    await server.start()


if __name__ == '__main__':
    if not WEBSOCKETS_AVAILABLE:
        print("\n[ERROR] websockets library not installed")
        print("Please install with: pip install websockets")
        exit(1)
    
    print("=" * 60)
    print("WebSocket Server Test")
    print("=" * 60)
    
    # 测试服务器
    server = StockDataServer()
    
    # 设置回调
    server.on_client_connect = lambda c: print(f"Client connected: {c.client_id}")
    server.on_client_disconnect = lambda c: print(f"Client disconnected: {c.client_id}")
    
    # 运行服务器
    asyncio.run(server.start())

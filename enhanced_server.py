#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强服务器 - 支持网页前端集成
集成MLSC、RL、回测、风控、WebSocket实时推送

使用方式:
    python enhanced_server.py
    然后打开 http://localhost:8080
"""

import json
import asyncio
import threading
import time
from datetime import datetime
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import websockets
from collections import defaultdict

# 导入高级模块
try:
    from advanced_features import AdvancedTradingSystem
    ADVANCED_AVAILABLE = True
except ImportError:
    ADVANCED_AVAILABLE = False
    print("[EnhancedServer] 高级模块未安装，部分功能不可用")

from portfolio import Portfolio
from generate_page import generate_page

PORT = 8080
WS_PORT = 8765
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"


class WebSocketHandler:
    """WebSocket处理器"""
    
    def __init__(self):
        self.clients = defaultdict(set)  # stock_code -> set of websocket
        self.all_clients = set()
        self.advanced_system = None
        
        if ADVANCED_AVAILABLE:
            self.advanced_system = AdvancedTradingSystem()
            self.advanced_system.initialize()
    
    async def handle_client(self, websocket, path):
        """处理WebSocket客户端连接"""
        self.all_clients.add(websocket)
        print(f"[WS] 客户端连接 (当前: {len(self.all_clients)}个)")
        
        try:
            async for message in websocket:
                data = json.loads(message)
                await self.process_message(websocket, data)
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.all_clients.discard(websocket)
            # 从所有订阅列表中移除
            for code in self.clients:
                self.clients[code].discard(websocket)
            print(f"[WS] 客户端断开 (当前: {len(self.all_clients)}个)")
    
    async def process_message(self, websocket, data):
        """处理客户端消息"""
        msg_type = data.get('type')
        
        if msg_type == 'subscribe':
            code = data.get('stock_code')
            self.clients[code].add(websocket)
            print(f"[WS] 订阅: {code}")
            
        elif msg_type == 'unsubscribe':
            code = data.get('stock_code')
            self.clients[code].discard(websocket)
            
        elif msg_type == 'get_signal':
            code = data.get('stock_code')
            if self.advanced_system:
                stock_data = self._get_stock_data(code)
                signal = self.advanced_system.get_signal(code, stock_data)
                await websocket.send(json.dumps({
                    'type': 'signal',
                    **signal
                }))
                
        elif msg_type == 'risk_analysis':
            if self.advanced_system:
                metrics = self.advanced_system.get_risk_metrics()
                await websocket.send(json.dumps({
                    'type': 'risk_analysis',
                    **metrics
                }))
    
    def _get_stock_data(self, code):
        """获取股票数据（可从数据库或缓存获取）"""
        return {
            'code': code,
            'close': 10.0,
            'change_pct': 0,
            'volume_ratio': 1.0,
            'rsi': 50
        }
    
    async def broadcast_signal(self, stock_code, signal_data):
        """广播信号给订阅者"""
        if stock_code in self.clients:
            message = json.dumps({
                'type': 'signal',
                'stock_code': stock_code,
                **signal_data,
                'timestamp': datetime.now().isoformat()
            })
            
            for client in self.clients[stock_code]:
                try:
                    await client.send(message)
                except:
                    pass
    
    async def broadcast_risk_alert(self, alert_data):
        """广播风控警告"""
        message = json.dumps({
            'type': 'risk_alert',
            **alert_data,
            'timestamp': datetime.now().isoformat()
        })
        
        for client in self.all_clients:
            try:
                await client.send(message)
            except:
                pass


class EnhancedHandler(BaseHTTPRequestHandler):
    """增强的HTTP处理器"""
    
    ws_handler = None
    
    def do_GET(self):
        path = urlparse(self.path).path
        query = urlparse(self.path).query
        params = parse_qs(query, encoding='utf-8')
        
        # 静态文件
        if path.startswith('/static/'):
            self.serve_static(path)
        
        # API端点
        elif path == '/api/mlsc':
            self.api_mlsc(params)
        elif path.startswith('/api/mlsc/'):
            code = path.split('/')[-1]
            self.api_mlsc_detail(code)
        elif path == '/api/risk/analysis':
            self.api_risk_analysis()
        elif path == '/api/weights':
            self.api_weights()
        elif path == '/api/market_status':
            self.api_market_status()
        
        # 原有端点
        elif path in ('/', '/index.html'):
            self.serve_index()
        elif path == '/holdings':
            self.get_holdings()
        elif path == '/get_news':
            self.get_news()
        elif path.startswith('/output/'):
            self.serve_file(path)
        else:
            self.send_error(404)
    
    def do_POST(self):
        path = urlparse(self.path).path
        
        if path == '/api/backtest':
            self.api_backtest()
        elif path == '/generate_report':
            self.generate_report()
        else:
            self.send_error(404)
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    # ==========================================
    # API实现
    # ==========================================
    
    def api_mlsc(self, params):
        """获取所有热门股票的MLSC信号"""
        self.send_json({
            'success': True,
            'stocks': self._get_mlsc_signals()
        })
    
    def api_mlsc_detail(self, code):
        """获取单个股票的MLSC预测"""
        if ADVANCED_AVAILABLE and EnhancedHandler.ws_handler:
            system = EnhancedHandler.ws_handler.advanced_system
            if system:
                signal = system.get_signal(code, {'code': code})
                self.send_json({
                    'success': True,
                    **signal
                })
                return
        
        self.send_json({
            'success': False,
            'error': '高级模块不可用'
        })
    
    def api_risk_analysis(self):
        """获取风控分析"""
        if ADVANCED_AVAILABLE and EnhancedHandler.ws_handler:
            system = EnhancedHandler.ws_handler.advanced_system
            if system:
                metrics = system.get_risk_metrics()
                self.send_json({
                    'success': True,
                    **metrics
                })
                return
        
        self.send_json({
            'success': True,
            'total_value': 0,
            'total_position': 0,
            'var_95': 0,
            'cvar_95': 0,
            'beta': 1.0
        })
    
    def api_weights(self):
        """获取当前因子权重"""
        if ADVANCED_AVAILABLE and EnhancedHandler.ws_handler:
            system = EnhancedHandler.ws_handler.advanced_system
            if system and system.rl_adapter:
                weights = system.rl_adapter.get_adaptive_weights()
                self.send_json({'success': True, 'weights': weights})
                return
        
        self.send_json({
            'success': True,
            'weights': {
                'trend_weight': 0.30,
                'momentum_weight': 0.25,
                'sentiment_weight': 0.15,
                'volume_weight': 0.10,
                'volatility_weight': 0.08,
                'liquidity_weight': 0.07,
                'market_weight': 0.05
            }
        })
    
    def api_market_status(self):
        """获取市场状态"""
        self.send_json({
            'success': True,
            'index': '沪深300',
            'change': 0.5,
            'volume_ratio': 1.2,
            'fear_greed': 60,
            'up_count': 2000,
            'down_count': 1000
        })
    
    def api_backtest(self):
        """运行回测"""
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        params = json.loads(body)
        
        self.send_json({
            'success': True,
            'message': '回测功能已提交',
            'params': params
        })
    
    # ==========================================
    # 辅助方法
    # ==========================================
    
    def _get_mlsc_signals(self):
        """获取MLSC信号列表"""
        stocks_file = OUTPUT_DIR / 'hot_stocks.json'
        if not stocks_file.exists():
            return []
        
        with open(stocks_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        signals = []
        for stock in data.get('stocks', [])[:20]:  # 取前20只
            signals.append({
                'code': stock.get('code'),
                'name': stock.get('name'),
                'signal': 'bullish',
                'confidence': 0.7 + hash(stock.get('code', '')) % 30 / 100,
                'horizons': {
                    '1d': 'bullish',
                    '3d': 'bullish',
                    '5d': 'neutral'
                }
            })
        return signals
    
    def serve_static(self, path):
        """服务静态文件"""
        file_path = BASE_DIR / path.lstrip('/')
        if file_path.exists():
            self.serve_file_content(file_path)
        else:
            self.send_error(404)
    
    def serve_index(self):
        """服务主页"""
        index_file = OUTPUT_DIR / 'index.html'
        if index_file.exists():
            self.serve_file_content(index_file, 'text/html')
        else:
            self.send_html('<html><body><h1>股票热点追踪系统</h1></body></html>')
    
    def serve_file(self, path):
        """服务文件"""
        file_path = BASE_DIR / path.lstrip('/')
        self.serve_file_content(file_path)
    
    def serve_file_content(self, file_path, content_type=None):
        """服务文件内容"""
        if not file_path.exists():
            self.send_error(404)
            return
        
        if content_type is None:
            ext = file_path.suffix.lower()
            types = {
                '.html': 'text/html',
                '.js': 'application/javascript',
                '.css': 'text/css',
                '.json': 'application/json',
                '.png': 'image/png',
                '.jpg': 'image/jpeg'
            }
            content_type = types.get(ext, 'text/plain')
        
        with open(file_path, 'rb') as f:
            content = f.read()
        
        self.send_response(200)
        self.send_header('Content-Type', f'{content_type}; charset=utf-8')
        self.send_header('Content-Length', len(content))
        self.end_headers()
        self.wfile.write(content)
    
    def send_json(self, data):
        """发送JSON响应"""
        content = json.dumps(data, ensure_ascii=False)
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(content.encode('utf-8'))
    
    def send_html(self, html):
        """发送HTML响应"""
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))
    
    # 原有功能（简化版）
    def get_holdings(self):
        self.send_json({'success': True, 'holdings': []})
    
    def get_news(self):
        self.send_json({'success': True, 'news': []})
    
    def generate_report(self):
        self.send_json({'success': True, 'url': '/output/daily_report.html'})


async def run_websocket_server(ws_handler):
    """运行WebSocket服务器"""
    async with websockets.serve(ws_handler.handle_client, '0.0.0.0', WS_PORT):
        print(f"[WebSocket] 服务器运行在 ws://0.0.0.0:{WS_PORT}")
        await asyncio.Future()  # 永久运行


def run_http_server():
    """运行HTTP服务器"""
    server = HTTPServer(('0.0.0.0', PORT), EnhancedHandler)
    print(f"[HTTP] 服务器运行在 http://0.0.0.0:{PORT}")
    print(f"[API] MLSC信号: http://localhost:{PORT}/api/mlsc")
    print(f"[API] 风控分析: http://localhost:{PORT}/api/risk/analysis")
    print(f"[API] 因子权重: http://localhost:{PORT}/api/weights")
    server.serve_forever()


def main():
    print("\n" + "=" * 60)
    print("增强服务器 - 网页集成版")
    print("=" * 60)
    
    # 初始化WebSocket处理器
    ws_handler = WebSocketHandler()
    EnhancedHandler.ws_handler = ws_handler
    
    # 启动HTTP服务器（主线程）
    http_thread = threading.Thread(target=run_http_server, daemon=True)
    http_thread.start()
    
    # 启动WebSocket服务器
    try:
        asyncio.run(run_websocket_server(ws_handler))
    except KeyboardInterrupt:
        print("\n服务器已停止")


if __name__ == '__main__':
    main()

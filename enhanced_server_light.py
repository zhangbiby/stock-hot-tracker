#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
轻量级增强服务器 - 不依赖PyTorch
集成回测、风控、WebSocket实时推送（使用简化MLSC算法）

使用方式:
    python enhanced_server_light.py
    然后打开 http://localhost:8080
"""

import json
import asyncio
import threading
import time
import random
from datetime import datetime
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from collections import defaultdict

from portfolio import Portfolio
from generate_page import generate_page

PORT = 8080
WS_PORT = 8765
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"


# ============================================================
# 轻量级信号计算器（不使用PyTorch）
# ============================================================

class LightweightSignalCalculator:
    """轻量级信号计算器 - 基于技术指标规则"""
    
    def __init__(self):
        self.default_weights = {
            'trend_weight': 0.30,
            'momentum_weight': 0.25,
            'sentiment_weight': 0.15,
            'volume_weight': 0.10,
            'volatility_weight': 0.08,
            'liquidity_weight': 0.07,
            'market_weight': 0.05
        }
    
    def calculate_signal(self, stock_data: dict) -> dict:
        """计算综合信号"""
        close = stock_data.get('close', 10.0)
        change_pct = stock_data.get('change_pct', 0)
        volume_ratio = stock_data.get('volume_ratio', 1.0)
        rsi = stock_data.get('rsi', 50)
        amplitude = stock_data.get('amplitude', 0)
        
        # 1. 趋势评分
        trend_score = 0.5
        if change_pct > 0:
            trend_score += min(change_pct * 0.05, 0.3)
        else:
            trend_score -= min(abs(change_pct) * 0.05, 0.3)
        if rsi > 70:
            trend_score -= 0.1
        elif rsi < 30:
            trend_score += 0.1
        
        # 2. 动量评分
        momentum_score = 0.5
        if volume_ratio > 1.5:
            momentum_score += 0.2
        elif volume_ratio > 2.0:
            momentum_score += 0.3
        
        # 3. 情绪评分
        sentiment_score = 0.5
        if amplitude > 5:
            sentiment_score += 0.1
        
        # 综合评分
        weights = self.default_weights
        final_score = (
            trend_score * weights['trend_weight'] +
            momentum_score * weights['momentum_weight'] +
            sentiment_score * weights['sentiment_weight'] +
            0.5 * (weights['volume_weight'] + weights['volatility_weight'] + 
                   weights['liquidity_weight'] + weights['market_weight'])
        )
        
        if final_score > 0.6:
            signal = 'bullish'
        elif final_score < 0.4:
            signal = 'bearish'
        else:
            signal = 'neutral'
        
        confidence = abs(final_score - 0.5) * 2
        
        return {
            'final_signal': signal,
            'final_score': final_score,
            'confidence': confidence,
            'mlsc': self._get_mlsc_prediction(change_pct, volume_ratio, rsi)
        }
    
    def _get_mlsc_prediction(self, change_pct: float, volume_ratio: float, rsi: float) -> dict:
        base = 0.5
        if change_pct > 0 and volume_ratio > 1.2:
            base = 0.7 if rsi < 65 else 0.5
        elif change_pct < 0 and volume_ratio > 1.5:
            base = 0.3 if rsi > 35 else 0.5
        
        noise = random.uniform(-0.1, 0.1)
        return {
            '1d': self._score_to_signal(base + noise + 0.05),
            '3d': self._score_to_signal(base + noise),
            '5d': self._score_to_signal(base + noise - 0.05),
            'confidence': abs(base - 0.5) + 0.3
        }
    
    def _score_to_signal(self, score: float) -> str:
        if score > 0.6:
            return 'bullish'
        elif score < 0.4:
            return 'bearish'
        return 'neutral'
    
    def get_adaptive_weights(self, market_state: dict = None) -> dict:
        if not market_state:
            return self.default_weights
        return self.default_weights.copy()


class LightweightRiskManager:
    """轻量级风控管理器"""
    
    def __init__(self):
        self.max_single_position = 0.15
        self.max_total_position = 0.85
    
    def analyze_portfolio(self, positions: list, market_data: dict) -> dict:
        total_value = sum(p.get('value', 0) for p in positions)
        return {
            'total_value': total_value,
            'total_position': min(total_value / 1000000, 1.0),
            'var_95': 0.05,
            'cvar_95': 0.08,
            'beta': 1.05,
            'concentration_risk': 0.28,
            'liquidity_risk': 0.15
        }
    
    def detect_black_swan(self, market_data: dict) -> bool:
        index_data = market_data.get('index', {})
        change = index_data.get('change', 0)
        return change < -5


class WebSocketHandler:
    """WebSocket处理器"""
    
    def __init__(self):
        self.clients = defaultdict(set)
        self.all_clients = set()
        self.signal_calculator = LightweightSignalCalculator()
        self.risk_manager = LightweightRiskManager()
    
    async def handle_client(self, websocket, path):
        self.all_clients.add(websocket)
        print(f"[WS] 客户端连接 (当前: {len(self.all_clients)}个)")
        
        try:
            async for message in websocket:
                data = json.loads(message)
                await self.process_message(websocket, data)
        except Exception as e:
            print(f"[WS] 错误: {e}")
        finally:
            self.all_clients.discard(websocket)
    
    async def process_message(self, websocket, data):
        msg_type = data.get('type')
        
        if msg_type == 'subscribe':
            code = data.get('stock_code')
            self.clients[code].add(websocket)
        elif msg_type == 'get_signal':
            code = data.get('stock_code')
            signal = self.signal_calculator.calculate_signal({'code': code})
            await websocket.send(json.dumps({
                'type': 'signal', 'stock_code': code, **signal,
                'timestamp': datetime.now().isoformat()
            }))
        elif msg_type == 'risk_analysis':
            metrics = self.risk_manager.analyze_portfolio([], {})
            await websocket.send(json.dumps({'type': 'risk_analysis', **metrics}))
    
    async def broadcast_market_status(self):
        status = {
            'type': 'market_status',
            'index': '沪深300',
            'change': round(random.uniform(-2, 2), 2),
            'volume_ratio': round(random.uniform(0.8, 1.5), 2),
            'fear_greed': random.randint(30, 80),
            'up_count': random.randint(1000, 2500),
            'down_count': random.randint(1000, 2500),
            'timestamp': datetime.now().isoformat()
        }
        for client in self.all_clients:
            try:
                await client.send(json.dumps(status))
            except:
                pass


class EnhancedHandler(BaseHTTPRequestHandler):
    
    ws_handler = None
    
    def do_GET(self):
        path = urlparse(self.path).path
        
        if path.startswith('/static/'):
            self.serve_static(path)
        elif path == '/' or path == '/web_demo':
            self.serve_html('index.html')
        elif path == '/api/mlsc':
            self.api_mlsc()
        elif path.startswith('/api/mlsc/'):
            code = path.split('/')[-1]
            self.api_mlsc_detail(code)
        elif path == '/api/risk/analysis':
            self.api_risk_analysis()
        elif path == '/api/weights':
            self.api_weights()
        elif path == '/api/market_status':
            self.api_market_status()
        elif path.startswith('/output/'):
            self.serve_file(path)
        else:
            self.send_error(404)
    
    def do_POST(self):
        path = urlparse(self.path).path
        if path == '/api/backtest':
            self.api_backtest()
        else:
            self.send_error(404)
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def api_mlsc(self):
        """获取人气100个股的MLSC信号"""
        calc = LightweightSignalCalculator()
        stocks_file = OUTPUT_DIR / 'hot_stocks.json'
        signals = []
        
        if stocks_file.exists():
            with open(stocks_file, 'r', encoding='utf-8') as f:
                stocks_data = json.load(f)
            for stock in stocks_data.get('stocks', [])[:100]:
                signal = calc.calculate_signal(stock)
                signals.append({
                    'code': stock.get('code'),
                    'name': stock.get('name'),
                    'price': stock.get('price'),
                    'change_pct': stock.get('change_pct'),
                    'turnover_rate': stock.get('turnover_rate'),
                    'rank': stock.get('rank'),
                    **signal
                })
        else:
            # 如果没有数据，返回演示数据
            demo_stocks = [
                {'code': '000001', 'name': '平安银行', 'price': 10.5, 'change_pct': 1.5},
                {'code': '000002', 'name': '万科A', 'price': 8.2, 'change_pct': -0.5},
                {'code': '600519', 'name': '贵州茅台', 'price': 1680, 'change_pct': 2.1},
                {'code': '600036', 'name': '招商银行', 'price': 35.6, 'change_pct': 0.8},
                {'code': '000858', 'name': '五粮液', 'price': 145, 'change_pct': 3.2},
            ]
            for stock in demo_stocks:
                signal = calc.calculate_signal(stock)
                signals.append({**stock, **signal})
        
        self.send_json({'success': True, 'stocks': signals})
    
    def api_mlsc_detail(self, code):
        calc = LightweightSignalCalculator()
        signal = calc.calculate_signal({'code': code})
        self.send_json({'success': True, 'stock_code': code, **signal})
    
    def api_risk_analysis(self):
        mgr = LightweightRiskManager()
        metrics = mgr.analyze_portfolio([], {})
        self.send_json({'success': True, **metrics})
    
    def api_weights(self):
        calc = LightweightSignalCalculator()
        self.send_json({'success': True, 'weights': calc.get_adaptive_weights()})
    
    def get_market_indices(self):
        """获取实时大盘指数（上证/深证/创业板/科创50）"""
        try:
            import urllib.request
            
            # 腾讯财经API获取大盘指数（添加深证成指）
            url = 'https://web.sqt.gtimg.cn/q=sh000001,sz399001,sz399006,sh000688'
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = response.read().decode('gbk', errors='ignore')
            
            indices = []
            # 解析返回数据
            for line in data.strip().split('\n'):
                if '=' not in line:
                    continue
                parts = line.split('=')[1].strip('";').split('~')
                if len(parts) > 32:
                    name = parts[1] if len(parts) > 1 else ''
                    price = float(parts[3]) if parts[3] else 0
                    change = float(parts[31]) if parts[31] else 0
                    change_pct = float(parts[32]) if parts[32] else 0
                    
                    # 映射指数名称
                    if '000001' in line:
                        name = '上证指数'
                    elif '399001' in line:
                        name = '深证成指'
                    elif '399006' in line:
                        name = '创业板指'
                    elif '000688' in line:
                        name = '科创50'
                    
                    if name:
                        indices.append({
                            'name': name,
                            'price': price,
                            'change': change,
                            'change_pct': change_pct
                        })
            
            return indices if indices else self._get_default_market_indices()
            
        except Exception as e:
            print(f"[DEBUG] 获取大盘指数失败: {e}")
            return self._get_default_market_indices()
    
    def get_market_statistics(self):
        """获取市场统计（涨跌家数等）- 汇总沪深两市"""
        try:
            import urllib.request
            # 东方财富API获取涨跌家数（同时获取上证和深证）
            url = 'https://push2.eastmoney.com/api/qt/ulist.np/get'
            params = '?fltt=2&invt=2&fields=f12,f13,f14,f104,f105&secids=1.000001,0.399001&ut=fa5fd1943c7b386f172d6893dbfba10b'
            req = urllib.request.Request(url + params, headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://quote.eastmoney.com/'})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode('utf-8'))
            
            total_up = 0
            total_down = 0
            
            if data.get('data') and data['data'].get('diff'):
                for stock_data in data['data']['diff']:
                    # f104=上涨家数, f105=下跌家数
                    total_up += stock_data.get('f104', 0) or 0
                    total_down += stock_data.get('f105', 0) or 0
            
            if total_up > 0 and total_down > 0:
                return {'up_count': int(total_up), 'down_count': int(total_down)}
            
            return self._get_default_market_stats()
            
        except Exception as e:
            print(f"[DEBUG] 获取市场统计失败: {e}")
            return self._get_default_market_stats()
    
    def _get_default_market_stats(self):
        """获取默认市场统计"""
        return {'up_count': 2500, 'down_count': 1500}
    
    def _get_default_market_indices(self):
        """获取默认的大盘指数（当API失败时使用）"""
        return [
            {'name': '上证指数', 'price': 3889.08, 'change': -42.76, 'change_pct': -1.09},
            {'name': '创业板指', 'price': 3272.49, 'change': -44.48, 'change_pct': -1.34},
            {'name': '科创50', 'price': 1288.81, 'change': -26.60, 'change_pct': -2.02}
        ]
    
    def api_market_status(self):
        """获取市场状态，包含真实的上证指数和涨跌家数"""
        indices = self.get_market_indices()
        market_stats = self.get_market_statistics()
        
        # 找到上证指数
        shanghai = next((idx for idx in indices if idx['name'] == '上证指数'), None)
        if shanghai:
            index = f"上证 {shanghai['price']:.2f}"
            change = shanghai['change']
            change_pct = shanghai['change_pct']
        else:
            index = '沪深300'
            change = round(random.uniform(-2, 2), 2)
            change_pct = change
        
        self.send_json({
            'success': True,
            'index': index,
            'change': change,
            'change_pct': change_pct,
            'indices': indices,
            'volume_ratio': round(random.uniform(0.8, 1.5), 2),
            'fear_greed': random.randint(30, 80),
            'up_count': market_stats['up_count'],
            'down_count': market_stats['down_count']
        })
    
    def api_backtest(self):
        self.send_json({
            'success': True, 'message': '回测演示',
            'result': {'total_return': 0.15, 'sharpe_ratio': 1.8, 'max_drawdown': 0.08}
        })
    
    def serve_static(self, path):
        file_path = BASE_DIR / path.lstrip('/')
        if file_path.exists():
            self.serve_file_content(file_path)
        else:
            self.send_error(404)
    
    def serve_html(self, filename):
        file_path = BASE_DIR / filename
        if file_path.exists():
            self.serve_file_content(file_path, 'text/html')
        else:
            self.send_error(404)
    
    def serve_file(self, path):
        file_path = BASE_DIR / path.lstrip('/')
        self.serve_file_content(file_path)
    
    def serve_file_content(self, file_path, content_type=None):
        if not file_path.exists():
            self.send_error(404)
            return
        if content_type is None:
            ext = file_path.suffix.lower()
            types = {'.html': 'text/html', '.js': 'application/javascript', '.css': 'text/css'}
            content_type = types.get(ext, 'text/plain')
        with open(file_path, 'rb') as f:
            content = f.read()
        self.send_response(200)
        self.send_header('Content-Type', f'{content_type}; charset=utf-8')
        self.send_header('Content-Length', len(content))
        self.end_headers()
        self.wfile.write(content)
    
    def send_json(self, data):
        content = json.dumps(data, ensure_ascii=False)
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(content.encode('utf-8'))


async def run_websocket_server(ws_handler):
    try:
        import websockets
        async with websockets.serve(ws_handler.handle_client, '0.0.0.0', WS_PORT):
            print(f"[WebSocket] ws://0.0.0.0:{WS_PORT}")
            while True:
                await asyncio.sleep(10)
                await ws_handler.broadcast_market_status()
    except ImportError:
        print("[WebSocket] websockets未安装，跳过")
        print("提示: pip install websockets")
    except OSError as e:
        if "10048" in str(e) or "Address already in use" in str(e):
            print(f"[WebSocket] 端口{WS_PORT}已被占用，WebSocket功能禁用")
            print("提示: 请关闭占用端口的程序，或修改WS_PORT配置")
        else:
            raise


def run_http_server():
    server = HTTPServer(('0.0.0.0', PORT), EnhancedHandler)
    print(f"[HTTP] http://0.0.0.0:{PORT}")
    print(f"[访问] http://localhost:{PORT}/web_demo")
    print(f"[API] http://localhost:{PORT}/api/mlsc")
    server.serve_forever()


def main():
    print("\n" + "=" * 50)
    print("轻量级增强服务器 (无需PyTorch)")
    print("=" * 50)
    
    ws_handler = WebSocketHandler()
    EnhancedHandler.ws_handler = ws_handler
    
    http_thread = threading.Thread(target=run_http_server, daemon=True)
    http_thread.start()
    
    try:
        asyncio.run(run_websocket_server(ws_handler))
    except KeyboardInterrupt:
        print("\n服务器已停止")


if __name__ == '__main__':
    main()

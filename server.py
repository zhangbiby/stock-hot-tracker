#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple HTTP server for portfolio management
Usage: python server.py
Then open http://localhost:8080
"""

import json
import os
import sys
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Fix stdout encoding on Windows
if sys.platform == 'win32':
    try:
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    except:
        pass

# Import our modules
from portfolio import Portfolio
from generate_page import generate_page

PORT = 8080
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"


class Handler(BaseHTTPRequestHandler):

    def do_GET(self):
        path   = urlparse(self.path).path
        query  = urlparse(self.path).query
        params = parse_qs(query, encoding='utf-8')

        if path in ('/', '/index.html'):
            self.serve_index()
        elif path == '/add_holding':
            self.add_holding(params)
        elif path == '/delete_holding':
            self.delete_holding(params)
        elif path == '/sell_holding':
            self.sell_holding(params)
        elif path == '/get_stock_name':
            self.get_stock_name(params)
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
        if path == '/generate_report':
            self.generate_report()
        elif path == '/generate_stock_report':
            self.generate_stock_report()
        else:
            self.send_error(404)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    # ── 报告生成 ──────────────────────────────────────────────────────────

    def generate_report(self):
        """生成微信公众号友好的日报 HTML"""
        try:
            stocks_file  = OUTPUT_DIR / 'hot_stocks.json'
            signals_file = OUTPUT_DIR / 'signals_latest.json'

            if not stocks_file.exists():
                self.json_response({'success': False, 'error': 'hot_stocks.json 不存在，请先运行采集'})
                return

            with open(stocks_file, 'r', encoding='utf-8') as f:
                stocks_data = json.load(f)
            stocks = stocks_data.get('stocks', [])

            signals = []
            if signals_file.exists():
                with open(signals_file, 'r', encoding='utf-8') as f:
                    sig_data = json.load(f)
                signals = sig_data.get('signals', [])

            html = _build_report_html(stocks, signals)

            today = datetime.now().strftime('%Y%m%d')
            report_file = OUTPUT_DIR / f'daily_report_{today}.html'
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(html)

            self.json_response({'success': True, 'url': f'/output/daily_report_{today}.html'})

        except Exception as e:
            import traceback
            self.json_response({'success': False, 'error': str(e), 'trace': traceback.format_exc()})

    # ── 个股报告生成 ──────────────────────────────────────────────────────────

    def generate_stock_report(self):
        """生成单只股票的专业分析报告"""
        try:
            # 读取请求体
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            params = parse_qs(body, encoding='utf-8')
            
            code = params.get('code', [''])[0].strip()
            name = params.get('name', [''])[0].strip()
            
            if not code:
                self.json_response({'success': False, 'error': '缺少股票代码'})
                return
            
            # 获取股票数据
            stocks_file = OUTPUT_DIR / 'hot_stocks.json'
            signals_file = OUTPUT_DIR / 'signals_latest.json'
            
            if not stocks_file.exists():
                self.json_response({'success': False, 'error': 'hot_stocks.json 不存在'})
                return
            
            with open(stocks_file, 'r', encoding='utf-8') as f:
                stocks_data = json.load(f)
            stocks = stocks_data.get('stocks', [])
            
            # 查找目标股票
            target_stock = None
            for s in stocks:
                if s.get('code') == code:
                    target_stock = s
                    break
            
            if not target_stock:
                self.json_response({'success': False, 'error': f'未找到股票 {code}'})
                return
            
            # 如果没有提供名称，使用股票数据中的名称
            if not name:
                name = target_stock.get('name', code)
            
            # 获取信号数据
            target_signal = {}
            if signals_file.exists():
                with open(signals_file, 'r', encoding='utf-8') as f:
                    sig_data = json.load(f)
                signals = sig_data.get('signals', [])
                for s in signals:
                    if s.get('code') == code:
                        target_signal = s
                        break
            
            # 获取大盘指数
            market_indices = self.get_market_indices()
            
            # 获取板块信息
            sector_info = self.get_sector_info(stocks, code)
            
            # 生成个股分析报告HTML
            html = _build_stock_report_html(target_stock, target_signal, market_indices, sector_info)
            
            today = datetime.now().strftime('%Y%m%d')
            report_file = OUTPUT_DIR / f'stock_report_{code}_{today}.html'
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(html)
            
            self.json_response({'success': True, 'url': f'/output/stock_report_{code}_{today}.html', 'name': name})
            
        except Exception as e:
            import traceback
            self.json_response({'success': False, 'error': str(e), 'trace': traceback.format_exc()})
    
    def get_market_indices(self):
        """获取实时大盘指数（上证/创业板/科创50）"""
        try:
            import urllib.request
            
            # 腾讯财经API获取大盘指数
            url = 'https://web.sqt.gtimg.cn/q=sh000001,sz399006,sh000688'
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
    
    def _get_default_market_indices(self):
        """获取默认的大盘指数（当API失败时使用）"""
        return [
            {'name': '上证指数', 'price': 3889.08, 'change': -42.76, 'change_pct': -1.09},
            {'name': '创业板指', 'price': 3272.49, 'change': -44.48, 'change_pct': -1.34},
            {'name': '科创50', 'price': 1288.81, 'change': -26.60, 'change_pct': -2.02}
        ]
    
    def get_sector_info(self, stocks, target_code):
        """获取目标股票所属板块信息"""
        # 查找目标股票
        target_stock = None
        for stock in stocks:
            if stock.get('code') == target_code:
                target_stock = stock
                break
        
        if not target_stock:
            return {'sector': '未知板块', 'stocks_in_sector': 0, 'avg_change': 0}
        
        # 简单行业关键词匹配
        stock_name = target_stock.get('name', '')
        
        sectors = {
            '电力': ['电力', '风电', '水电', '火电', '核电', '电网', '能源'],
            '科技': ['电子', '软件', '通信', '半导体', '芯片', '科技'],
            '金融': ['银行', '证券', '保险', '信托', '金融'],
            '医药': ['医药', '生物', '医疗', '中药', '疫苗'],
            '消费': ['食品', '饮料', '白酒', '家电', '纺织', '服装'],
            '工业': ['机械', '化工', '钢铁', '有色', '建材', '汽车'],
            '新能源': ['锂', '电池', '光伏', '储能', '氢能', '电动车'],
            '军工': ['军工', '航空', '航天', '船舶', '国防'],
            '地产': ['地产', '房地产', '建筑', '园林'],
            '传媒': ['传媒', '文化', '影视', '游戏', '教育']
        }
        
        detected_sector = '综合'
        for sector, keywords in sectors.items():
            for kw in keywords:
                if kw in stock_name:
                    detected_sector = sector
                    break
        
        # 统计同板块股票数量和平均涨跌幅
        sector_stocks = []
        for s in stocks:
            sname = s.get('name', '')
            for kw in sectors.get(detected_sector, []):
                if kw in sname:
                    sector_stocks.append(s)
                    break
        
        avg_change = 0
        if sector_stocks:
            changes = [float(s.get('change_pct', 0) or 0) for s in sector_stocks]
            avg_change = sum(changes) / len(changes)
        
        return {
            'sector': detected_sector,
            'stocks_in_sector': len(sector_stocks),
            'avg_change': avg_change,
            'sector_stocks': sector_stocks[:5]  # 取前5只展示
        }

    def get_news(self):
        """返回最新财经新闻"""
        try:
            news_file = OUTPUT_DIR / 'news_latest.json'
            if news_file.exists():
                with open(news_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.json_response({'success': True, 'news': data.get('news', []), 'update_time': data.get('update_time', '')})
            else:
                # 文件不存在，尝试立即采集一次
                try:
                    from fetch_news import fetch_all_news
                    news = fetch_all_news()
                    self.json_response({'success': True, 'news': news, 'update_time': datetime.now().strftime('%H:%M')})
                except Exception as e2:
                    self.json_response({'success': False, 'news': [], 'error': str(e2)})
        except Exception as e:
            self.json_response({'success': False, 'news': [], 'error': str(e)})

    # ── 原有接口 ──────────────────────────────────────────────────────────

    def serve_index(self):
        """Serve index.html - same as /output/index.html"""
        try:
            index_file = OUTPUT_DIR / 'index.html'
            
            # If file doesn't exist or is older than 5 minutes, regenerate
            if not index_file.exists():
                signals_file = OUTPUT_DIR / 'signals_latest.json'
                stocks_file  = OUTPUT_DIR / 'hot_stocks.json'
                if signals_file.exists() and stocks_file.exists():
                    generate_page(signals_file, stocks_file, index_file)
            
            if index_file.exists():
                with open(index_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                self.send_header('Pragma', 'no-cache')
                self.send_header('Expires', '0')
                self.end_headers()
                self.wfile.write(content.encode('utf-8'))
            else:
                self.send_error(404, 'Page not generated yet')
        except Exception as e:
            self.send_error(500, str(e))

    def add_holding(self, params):
        try:
            code  = params.get('code',  [''])[0].strip()
            name  = params.get('name',  [''])[0].strip() or code
            price = float(params.get('price', [0])[0])
            qty   = int(params.get('qty',   [0])[0])
            date  = params.get('date',  [''])[0]
            if not code or not price or not qty:
                self.json_response({'success': False, 'message': 'Missing parameters'})
                return
            portfolio = Portfolio()
            result = portfolio.add_custom_holding(code, name, price, qty, date)
            if result.get('success'):
                self.json_response({'success': True, 'message': result['message'], 'holding': result.get('holding')})
            else:
                self.json_response({'success': False, 'message': result.get('message', 'Failed')})
        except Exception as e:
            self.json_response({'success': False, 'message': str(e)})

    def delete_holding(self, params):
        try:
            code = params.get('code', [''])[0].strip()
            if not code:
                self.json_response({'success': False, 'message': 'Missing code'})
                return
            portfolio = Portfolio()
            data = portfolio._load_holdings()
            before = len(data['holdings'])
            data['holdings'] = [h for h in data['holdings'] if h['code'] != code]
            if len(data['holdings']) < before:
                portfolio._save_holdings(data)
                self.json_response({'success': True, 'message': f'已删除 {code}'})
            else:
                self.json_response({'success': False, 'message': '持仓不存在'})
        except Exception as e:
            self.json_response({'success': False, 'message': str(e)})

    def sell_holding(self, params):
        """卖出持仓（模拟）"""
        try:
            code = params.get('code', [''])[0].strip()
            quantity = int(params.get('quantity', ['0'])[0])
            price = float(params.get('price', ['0'])[0])
            
            if not code:
                self.json_response({'success': False, 'message': 'Missing code'})
                return
            
            portfolio = Portfolio()
            result = portfolio.sell_stock(code, price, quantity)
            
            if result.get('success'):
                self.json_response({
                    'success': True, 
                    'message': result['message'],
                    'trade': result.get('trade', {})
                })
            else:
                self.json_response({
                    'success': False, 
                    'message': result.get('message', '卖出失败')
                })
        except Exception as e:
            self.json_response({'success': False, 'message': str(e)})

    def get_stock_name(self, params):
        try:
            code = params.get('code', [''])[0].strip()
            if not code or len(code) != 6:
                self.json_response({'success': False, 'message': 'Invalid code'})
                return
            name_map_file = OUTPUT_DIR / 'stock_name_map.json'
            if name_map_file.exists():
                with open(name_map_file, 'r', encoding='utf-8') as f:
                    name_map = json.load(f)
                if code in name_map:
                    self.json_response({'success': True, 'name': name_map[code]})
                    return
            stocks_file = OUTPUT_DIR / 'hot_stocks.json'
            if stocks_file.exists():
                with open(stocks_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for stock in data.get('stocks', []):
                    if stock.get('code') == code:
                        self.json_response({'success': True, 'name': stock.get('name', '')})
                        return
            self.json_response({'success': False, 'message': 'Stock not found'})
        except Exception as e:
            self.json_response({'success': False, 'message': str(e)})

    def get_holdings(self):
        try:
            portfolio = Portfolio()
            holdings  = portfolio.get_holdings_with_status()
            self.json_response({'success': True, 'holdings': holdings})
        except Exception as e:
            self.json_response({'success': False, 'message': str(e)})

    def serve_file(self, path):
        file_path = BASE_DIR / path[1:]
        if file_path.exists() and file_path.is_file():
            ext = file_path.suffix.lower()
            content_types = {
                '.html': 'text/html; charset=utf-8',
                '.json': 'application/json',
                '.js':   'application/javascript',
                '.css':  'text/css',
            }
            with open(file_path, 'rb') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', content_types.get(ext, 'text/plain'))
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')
            self.end_headers()
            self.wfile.write(content)
        else:
            self.send_error(404)

    def json_response(self, data):
        content = json.dumps(data, ensure_ascii=False)
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(content.encode('utf-8'))

    def log_message(self, format, *args):
        pass


# ── 报告 HTML 生成函数 ────────────────────────────────────────────────────

def _build_report_html(stocks: list, signals: list) -> str:
    """生成微信公众号友好的日报 HTML（文章格式，兼容 WechatSync）"""

    today_str = datetime.now().strftime('%Y年%m月%d日')
    now_str   = datetime.now().strftime('%Y-%m-%d %H:%M')
    date_str  = datetime.now().strftime('%Y-%m-%d')

    def flt(v):
        return float(v or 0)

    up_stocks = [s for s in stocks if flt(s.get('change_pct')) > 0]
    zt_stocks = [s for s in stocks if flt(s.get('change_pct')) >= 9.5]
    dn_stocks = [s for s in stocks if flt(s.get('change_pct')) < 0]
    top_dn    = sorted(stocks, key=lambda x: flt(x.get('change_pct')))[:5]

    # ── 主题板块 ──
    THEMES = {
        '化工/材料':   ['海科新源','石大胜华','渤海化学','西部材料','金牛化工','厦门钨业','天赐材料','多氟多'],
        '光通信/光纤': ['长飞光纤','天孚通信','亨通光电','光迅科技','杭电股份','铭普光磁'],
        '锂电/储能':   ['宁德时代','比亚迪','赣锋锂业','融捷股份','圣阳股份','天际股份'],
        '光伏/新能源': ['协鑫集成','协鑫能科','隆基绿能','阳光电源','东方新能'],
        '电力/能源':   ['华电辽能','节能风电','中闽能源','粤电力Ａ','宝新能源','金开新能',
                       '闽东电力','华电能源','晋控电力','韶能股份','新能泰山','辽宁能源',
                       '浙江新能','华电新能','宁波能源','华银电力','通宝能源','甘肃能源',
                       '豫能控股','中国电建','中国能建'],
        '半导体/芯片': ['兆易创新','佰维存储','三安光电','英唐智控'],
        '军工/航天':   ['长城军工','航天发展','电光科技'],
        '通信/网络':   ['再升科技','通鼎互联','信维通信','二六三','真视通','瑞斯康达',
                       '天玑科技','特发信息','中国长城'],
        '科技/AI':     ['华工科技','东方财富','光环新网','罗博特科','美利云','大位科技'],
    }

    stock_map = {s['name']: s for s in stocks}
    theme_stats = []
    for theme, names in THEMES.items():
        matched = [stock_map[n] for n in names if n in stock_map]
        if not matched:
            continue
        avg = sum(flt(s.get('change_pct')) for s in matched) / len(matched)
        up  = sum(1 for s in matched if flt(s.get('change_pct')) > 0)
        theme_stats.append({'name': theme, 'count': len(matched), 'avg': avg,
                            'up': up, 'dn': len(matched) - up, 'stocks': matched})
    theme_stats.sort(key=lambda x: x['avg'], reverse=True)

    best_theme  = theme_stats[0]  if theme_stats else None
    worst_theme = theme_stats[-1] if theme_stats else None

    # ── 生成标题 ──
    best_theme_name = best_theme['name'] if best_theme else '多板块'
    best_theme_avg = best_theme['avg'] if best_theme else 0
    main_title = f"【人气榜100日报】{len(zt_stocks)}股涨停，{best_theme_name}板块{'全线飘红' if best_theme_avg > 5 else '表现强势'} ({date_str})"
    sub_title = f"基于东方财富股吧实时人气数据，今日前100只热门股中，{len(up_stocks)}只上涨，{len(zt_stocks)}只涨停，{best_theme_name}平均涨幅{best_theme_avg:+.2f}%，成为最强热点。"

    # ── 辅助函数 ──
    def chg_color(v):
        return '#e03131' if v > 0 else ('#2f9e44' if v < 0 else '#868e96')

    def tr_color(v):
        return '#e03131' if v > 20 else ('#f08c00' if v > 10 else '#2f9e44')

    def theme_row(t):
        color     = '#e03131' if t['avg'] > 0 else '#2f9e44'
        bar_w     = min(abs(t['avg']) / 15 * 100, 100)
        bar_color = '#ffcdd2' if t['avg'] > 0 else '#c8e6c9'
        bar_fill  = '#e03131' if t['avg'] > 0 else '#2f9e44'
        names_str = '、'.join(
            s['name'] for s in sorted(t['stocks'], key=lambda x: flt(x.get('change_pct')), reverse=True)[:4]
        )
        return (
            f'<tr>'
            f'<td style="padding:10px 12px;font-weight:600;color:#212529;">{t["name"]}</td>'
            f'<td style="padding:10px 12px;text-align:center;color:#495057;">{t["count"]}只</td>'
            f'<td style="padding:10px 12px;text-align:center;"><span style="color:{color};font-weight:700;">{t["avg"]:+.2f}%</span></td>'
            f'<td style="padding:10px 12px;">'
            f'<div style="background:{bar_color};border-radius:4px;height:8px;width:100%;overflow:hidden;">'
            f'<div style="background:{bar_fill};height:8px;width:{bar_w:.0f}%;border-radius:4px;"></div>'
            f'</div></td>'
            f'<td style="padding:10px 12px;font-size:12px;color:#868e96;">{names_str}</td>'
            f'</tr>'
        )

    def zt_row(i, s):
        chg = flt(s.get('change_pct'))
        tr  = flt(s.get('turnover_rate'))
        bg  = ['#e03131', '#f03e3e', '#fa5252'][min(i, 2)] if i < 3 else '#868e96'
        return (
            f'<tr style="border-bottom:1px solid #f1f3f5;">'
            f'<td style="padding:10px 12px;text-align:center;">'
            f'<span style="background:{bg};color:#fff;border-radius:50%;width:22px;height:22px;'
            f'display:inline-flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;">{i+1}</span>'
            f'</td>'
            f'<td style="padding:10px 12px;font-weight:600;">{s["name"]}</td>'
            f'<td style="padding:10px 12px;font-family:monospace;color:#495057;">{s.get("code","")}</td>'
            f'<td style="padding:10px 12px;font-family:monospace;font-weight:700;color:{chg_color(chg)};">{chg:+.2f}%</td>'
            f'<td style="padding:10px 12px;font-family:monospace;color:{tr_color(tr)};">{tr:.1f}%</td>'
            f'<td style="padding:10px 12px;font-family:monospace;color:#495057;">{flt(s.get("price")):.2f}</td>'
            f'</tr>'
        )

    def dn_row(s):
        chg = flt(s.get('change_pct'))
        tr  = flt(s.get('turnover_rate'))
        return (
            f'<tr style="border-bottom:1px solid #f1f3f5;">'
            f'<td style="padding:10px 12px;font-weight:600;">{s["name"]}</td>'
            f'<td style="padding:10px 12px;font-family:monospace;color:#495057;">{s.get("code","")}</td>'
            f'<td style="padding:10px 12px;font-family:monospace;font-weight:700;color:{chg_color(chg)};">{chg:+.2f}%</td>'
            f'<td style="padding:10px 12px;font-family:monospace;color:{tr_color(tr)};">{tr:.1f}%</td>'
            f'<td style="padding:10px 12px;font-family:monospace;color:#495057;">{flt(s.get("price")):.2f}</td>'
            f'</tr>'
        )

    def build_theme_detail(theme_name, theme_obj):
        """生成单个板块的深度解读"""
        stocks_list = sorted(theme_obj['stocks'], key=lambda x: flt(x.get('change_pct')), reverse=True)
        top3 = stocks_list[:3]
        bottom3 = stocks_list[-3:] if len(stocks_list) > 3 else []
        top3_str = '、'.join(f"{s['name']}({flt(s.get('change_pct')):+.2f}%)" for s in top3)
        bottom3_str = '、'.join(f"{s['name']}({flt(s.get('change_pct')):+.2f}%)" for s in bottom3)
        
        if theme_name == '化工/材料':
            return f"化工板块{theme_obj['count']}只个股{'全线飘红' if theme_obj['dn'] == 0 else '整体偏强'}，平均涨幅{theme_obj['avg']:+.2f}%。强势股：{top3_str}。化工品价格上涨预期叠加资金集中炒作，板块合力明显。"
        elif theme_name == '光通信/光纤':
            return f"光通信板块{theme_obj['count']}只个股{'全部上涨' if theme_obj['dn'] == 0 else '整体向好'}，平均{theme_obj['avg']:+.2f}%。龙头股：{top3_str}。AI大模型训练对光通信基础设施需求持续旺盛，该板块中长期逻辑清晰。"
        elif theme_name == '锂电/储能':
            return f"锂电板块{theme_obj['count']}只个股{theme_obj['up']}涨{theme_obj['dn']}跌，平均{theme_obj['avg']:+.2f}%。龙头稳健：{top3_str}。宁德时代等龙头地位稳固，锂价企稳预期下估值修复。"
        elif theme_name == '电力/能源':
            return f"能源板块{theme_obj['count']}只个股内部严重分化，{theme_obj['up']}涨{theme_obj['dn']}跌，平均{theme_obj['avg']:+.2f}%。强势：{top3_str}。弱势：{bottom3_str}。需谨慎甄别，已涨停个股次日高开低走风险较大。"
        else:
            return f"{theme_name}板块{theme_obj['count']}只个股{theme_obj['up']}涨{theme_obj['dn']}跌，平均{theme_obj['avg']:+.2f}%。代表股：{top3_str}。"

    best_detail = build_theme_detail(best_theme['name'], best_theme) if best_theme else ""
    worst_detail = build_theme_detail(worst_theme['name'], worst_theme) if worst_theme else ""

    # ── 高换手率 TOP6 ──
    top_tr = sorted(stocks, key=lambda x: flt(x.get('turnover_rate')), reverse=True)[:6]
    tr_warnings_html = ''
    for i, s in enumerate(top_tr, 1):
        chg = flt(s.get('change_pct'))
        tr  = flt(s.get('turnover_rate'))
        chg_color_val = '#e03131' if chg > 0 else '#2f9e44'
        warning = '极度活跃，筹码松动' if tr > 30 else ('高度活跃，需关注' if tr > 20 else '活跃度高')
        tr_warnings_html += f'''
        <tr style="border-bottom:1px solid #f1f3f5;">
          <td style="padding:10px 12px;text-align:center;font-weight:700;color:#868e96;">{i}</td>
          <td style="padding:10px 12px;font-weight:600;">{s['name']}</td>
          <td style="padding:10px 12px;font-family:monospace;color:#495057;">{s.get('code','')}</td>
          <td style="padding:10px 12px;font-family:monospace;font-weight:700;color:{chg_color_val};">{chg:+.2f}%</td>
          <td style="padding:10px 12px;font-family:monospace;font-weight:700;color:#e03131;">{tr:.1f}%</td>
          <td style="padding:10px 12px;font-size:12px;color:#666;">{warning}</td>
        </tr>'''

    # ── 操作建议 ──
    strong_themes = [t for t in theme_stats if t['avg'] >= 3]
    weak_themes   = [t for t in theme_stats if t['avg'] <= -3]
    advice_buy    = '、'.join(t['name'] for t in strong_themes[:3]) or '暂无明显强势板块'
    advice_sell   = '、'.join(t['name'] for t in weak_themes[:3])   or '暂无明显弱势板块'

    # ── 生成表格 HTML ──
    theme_rows_html = ''.join(theme_row(t) for t in theme_stats)
    zt_rows_html    = ''.join(zt_row(i, s) for i, s in enumerate(zt_stocks))
    dn_rows_html    = ''.join(dn_row(s) for s in top_dn)

    # ── 返回完整 HTML ──
    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{main_title}</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif; background:#f7f7f7; color:#212529; font-size:15px; line-height:1.8; }}
  table {{ border-collapse:collapse; width:100%; }}
</style>
</head>
<body>
<div id="js_content" style="max-width:680px;margin:0 auto;background:#fff;padding-bottom:40px;">

  <!-- 标题区 -->
  <div style="padding:20px;border-bottom:2px solid #f0f0f0;">
    <h1 style="font-size:18px;font-weight:700;color:#1a1a1a;line-height:1.5;margin-bottom:12px;">{main_title}</h1>
    <p style="font-size:13px;color:#666;line-height:1.8;margin:0;">{sub_title}</p>
  </div>

  <!-- 数据看板 -->
  <div style="background:linear-gradient(135deg,#0f2027,#203a43,#2c5364);padding:28px 20px;margin:0;">
    <div style="display:flex;justify-content:space-around;gap:8px;">
      <div style="flex:1;text-align:center;padding:12px;background:rgba(255,255,255,.05);border-radius:10px;">
        <div style="font-size:20px;font-weight:700;color:#ff6b6b;">{len(up_stocks)}</div>
        <div style="font-size:11px;color:rgba(255,255,255,.6);margin-top:4px;">上涨只数</div>
      </div>
      <div style="flex:1;text-align:center;padding:12px;background:rgba(255,255,255,.05);border-radius:10px;">
        <div style="font-size:20px;font-weight:700;color:#ffd700;">{len(zt_stocks)}</div>
        <div style="font-size:11px;color:rgba(255,255,255,.6);margin-top:4px;">涨停只数</div>
      </div>
      <div style="flex:1;text-align:center;padding:12px;background:rgba(255,255,255,.05);border-radius:10px;">
        <div style="font-size:20px;font-weight:700;color:#51cf66;">{len(dn_stocks)}</div>
        <div style="font-size:11px;color:rgba(255,255,255,.6);margin-top:4px;">下跌只数</div>
      </div>
      <div style="flex:1;text-align:center;padding:12px;background:rgba(255,255,255,.05);border-radius:10px;">
        <div style="font-size:20px;font-weight:700;color:#a0a0a0;">100</div>
        <div style="font-size:11px;color:rgba(255,255,255,.6);margin-top:4px;">监控总数</div>
      </div>
    </div>
  </div>

  <div style="padding:0 20px;">

    <!-- 板块全景 -->
    <div style="margin:28px 0;">
      <div style="display:flex;align-items:center;gap:8px;font-size:17px;font-weight:700;color:#1a1a1a;margin-bottom:14px;padding-bottom:10px;border-bottom:2px solid #f0f0f0;">
        <span style="background:#fff1f0;width:28px;height:28px;border-radius:8px;display:inline-flex;align-items:center;justify-content:center;font-size:14px;">🔥</span>
        板块全景扫描
      </div>
      <div style="overflow-x:auto;">
        <table style="font-size:13px;min-width:500px;">
          <thead>
            <tr style="background:#fafafa;border-bottom:1px solid #f0f0f0;">
              <th style="padding:10px 12px;text-align:left;color:#666;font-weight:600;font-size:12px;">板块</th>
              <th style="padding:10px 12px;text-align:center;color:#666;font-weight:600;font-size:12px;">只数</th>
              <th style="padding:10px 12px;text-align:center;color:#666;font-weight:600;font-size:12px;">平均涨跌</th>
              <th style="padding:10px 12px;color:#666;font-weight:600;font-size:12px;">强度</th>
              <th style="padding:10px 12px;color:#666;font-weight:600;font-size:12px;">代表股</th>
            </tr>
          </thead>
          <tbody>{theme_rows_html}</tbody>
        </table>
      </div>
    </div>

    <!-- 重点板块深度解读 -->
    <div style="margin:28px 0;">
      <div style="display:flex;align-items:center;gap:8px;font-size:17px;font-weight:700;color:#1a1a1a;margin-bottom:14px;padding-bottom:10px;border-bottom:2px solid #f0f0f0;">
        <span style="background:#fff1f0;width:28px;height:28px;border-radius:8px;display:inline-flex;align-items:center;justify-content:center;font-size:14px;">🔬</span>
        重点板块深度解读
      </div>
      <div style="background:#f8f9fa;border-radius:10px;padding:14px 16px;margin-bottom:12px;border-left:3px solid #e03131;">
        <div style="font-size:13px;font-weight:700;color:#e03131;margin-bottom:8px;">🏆 最强板块：{best_theme['name'] if best_theme else '暂无'}</div>
        <p style="font-size:13px;color:#555;line-height:1.8;">{best_detail}</p>
      </div>
      <div style="background:#f8f9fa;border-radius:10px;padding:14px 16px;border-left:3px solid #2f9e44;">
        <div style="font-size:13px;font-weight:700;color:#2f9e44;margin-bottom:8px;">📉 弱势板块：{worst_theme['name'] if worst_theme else '暂无'}</div>
        <p style="font-size:13px;color:#555;line-height:1.8;">{worst_detail}</p>
      </div>
    </div>

    <!-- 涨停榜 -->
    <div style="margin:28px 0;">
      <div style="display:flex;align-items:center;gap:8px;font-size:17px;font-weight:700;color:#1a1a1a;margin-bottom:14px;padding-bottom:10px;border-bottom:2px solid #f0f0f0;">
        <span style="background:#fff1f0;width:28px;height:28px;border-radius:8px;display:inline-flex;align-items:center;justify-content:center;font-size:14px;">🚀</span>
        今日涨停榜 · {len(zt_stocks)}只
      </div>
      <div style="overflow-x:auto;">
        <table style="font-size:13px;">
          <thead>
            <tr style="background:#fafafa;border-bottom:1px solid #f0f0f0;">
              <th style="padding:10px 12px;text-align:center;color:#666;font-weight:600;font-size:12px;">#</th>
              <th style="padding:10px 12px;color:#666;font-weight:600;font-size:12px;">股票</th>
              <th style="padding:10px 12px;color:#666;font-weight:600;font-size:12px;">代码</th>
              <th style="padding:10px 12px;color:#666;font-weight:600;font-size:12px;">涨幅</th>
              <th style="padding:10px 12px;color:#666;font-weight:600;font-size:12px;">换手率</th>
              <th style="padding:10px 12px;color:#666;font-weight:600;font-size:12px;">价格</th>
            </tr>
          </thead>
          <tbody>{zt_rows_html}</tbody>
        </table>
      </div>
    </div>

    <!-- 跌幅榜 -->
    <div style="margin:28px 0;">
      <div style="display:flex;align-items:center;gap:8px;font-size:17px;font-weight:700;color:#1a1a1a;margin-bottom:14px;padding-bottom:10px;border-bottom:2px solid #f0f0f0;">
        <span style="background:#f6ffed;width:28px;height:28px;border-radius:8px;display:inline-flex;align-items:center;justify-content:center;font-size:14px;">📉</span>
        跌幅榜 · 风险预警
      </div>
      <div style="overflow-x:auto;">
        <table style="font-size:13px;">
          <thead>
            <tr style="background:#fafafa;border-bottom:1px solid #f0f0f0;">
              <th style="padding:10px 12px;color:#666;font-weight:600;font-size:12px;">股票</th>
              <th style="padding:10px 12px;color:#666;font-weight:600;font-size:12px;">代码</th>
              <th style="padding:10px 12px;color:#666;font-weight:600;font-size:12px;">跌幅</th>
              <th style="padding:10px 12px;color:#666;font-weight:600;font-size:12px;">换手率</th>
              <th style="padding:10px 12px;color:#666;font-weight:600;font-size:12px;">价格</th>
            </tr>
          </thead>
          <tbody>{dn_rows_html}</tbody>
        </table>
      </div>
    </div>

    <!-- 高换手率预警 -->
    <div style="margin:28px 0;">
      <div style="display:flex;align-items:center;gap:8px;font-size:17px;font-weight:700;color:#1a1a1a;margin-bottom:14px;padding-bottom:10px;border-bottom:2px solid #f0f0f0;">
        <span style="background:#fff9db;width:28px;height:28px;border-radius:8px;display:inline-flex;align-items:center;justify-content:center;font-size:14px;">⚡</span>
        高换手率预警 · 资金异动监控
      </div>
      <div style="background:#fff9db;border-radius:10px;padding:12px 14px;margin-bottom:12px;font-size:12px;color:#5c4a00;line-height:1.7;">
        换手率超过20%通常意味着筹码高度活跃，可能是主力建仓或出货信号，需结合涨跌方向综合判断。
      </div>
      <div style="overflow-x:auto;">
        <table style="font-size:13px;">
          <thead>
            <tr style="background:#fafafa;border-bottom:1px solid #f0f0f0;">
              <th style="padding:10px 12px;text-align:center;color:#666;font-weight:600;font-size:12px;">#</th>
              <th style="padding:10px 12px;color:#666;font-weight:600;font-size:12px;">股票</th>
              <th style="padding:10px 12px;color:#666;font-weight:600;font-size:12px;">代码</th>
              <th style="padding:10px 12px;color:#666;font-weight:600;font-size:12px;">涨跌</th>
              <th style="padding:10px 12px;color:#666;font-weight:600;font-size:12px;">换手率</th>
              <th style="padding:10px 12px;color:#666;font-weight:600;font-size:12px;">信号</th>
            </tr>
          </thead>
          <tbody>{tr_warnings_html}</tbody>
        </table>
      </div>
    </div>

    <!-- 操作策略参考 -->
    <div style="margin:28px 0;">
      <div style="display:flex;align-items:center;gap:8px;font-size:17px;font-weight:700;color:#1a1a1a;margin-bottom:14px;padding-bottom:10px;border-bottom:2px solid #f0f0f0;">
        <span style="background:#e6f4ff;width:28px;height:28px;border-radius:8px;display:inline-flex;align-items:center;justify-content:center;font-size:14px;">💡</span>
        操作策略参考
      </div>
      <div style="background:#f8f9fa;border-radius:10px;padding:14px 16px;margin-bottom:12px;border-left:3px solid #e03131;">
        <div style="font-size:13px;font-weight:700;color:#e03131;margin-bottom:8px;">📈 关注方向</div>
        <p style="font-size:13px;color:#555;line-height:1.8;">{advice_buy}板块今日表现强势，可重点关注板块内龙头股的回调低吸机会，不建议追高。已涨停个股需观察次日开盘是否能继续封板。</p>
      </div>
      <div style="background:#f8f9fa;border-radius:10px;padding:14px 16px;margin-bottom:12px;border-left:3px solid #2f9e44;">
        <div style="font-size:13px;font-weight:700;color:#2f9e44;margin-bottom:8px;">📉 规避方向</div>
        <p style="font-size:13px;color:#555;line-height:1.8;">{advice_sell}板块今日相对弱势，持仓者注意控制仓位，放量下跌个股建议严格止损。不建议抄底，需等待企稳信号。</p>
      </div>
      <div style="background:#fff9db;border-radius:10px;padding:14px 16px;border-left:3px solid #f08c00;">
        <div style="font-size:13px;font-weight:700;color:#f08c00;margin-bottom:8px;">⚠️ 高换手预警</div>
        <p style="font-size:13px;color:#555;line-height:1.8;">换手率超过20%的个股需结合涨跌方向判断：放量上涨可能是主力建仓，放量下跌则是出货信号。中利集团、韶能股份等高换手大跌个股，主力出货特征明显，坚决回避。</p>
      </div>
    </div>

    <!-- 明日重点关注 -->
    <div style="margin:28px 0;">
      <div style="display:flex;align-items:center;gap:8px;font-size:17px;font-weight:700;color:#1a1a1a;margin-bottom:14px;padding-bottom:10px;border-bottom:2px solid #f0f0f0;">
        <span style="background:#f0f0f0;width:28px;height:28px;border-radius:8px;display:inline-flex;align-items:center;justify-content:center;font-size:14px;">🔭</span>
        明日重点关注
      </div>
      <div style="background:#f8f9fa;border-radius:10px;padding:14px 16px;margin-bottom:12px;border-left:3px solid #fa8c16;">
        <div style="font-size:13px;font-weight:700;color:#d46b08;margin-bottom:8px;">📌 涨停板次日跟踪</div>
        <p style="font-size:13px;color:#555;line-height:1.8;">今日{len(zt_stocks)}只涨停股中，重点关注高换手涨停股（换手率>20%）— 若低开则为出货信号；板块龙头涨停 — 关注是否延续强势；低价涨停股 — 关注是否能继续封板。</p>
      </div>
      <div style="background:#f8f9fa;border-radius:10px;padding:14px 16px;margin-bottom:12px;border-left:3px solid #722ed1;">
        <div style="font-size:13px;font-weight:700;color:#722ed1;margin-bottom:8px;">📌 弱势股反弹观察</div>
        <p style="font-size:13px;color:#555;line-height:1.8;">华工科技、协鑫集成等科技、光伏龙头跌至支撑位附近；浙江新能、韶能股份等能源弱势股需等待止跌信号。明日若出现缩量企稳可关注超跌反弹机会（高风险，仅供参考）。</p>
      </div>
      <div style="background:#f8f9fa;border-radius:10px;padding:14px 16px;border-left:3px solid #52c41a;">
        <div style="font-size:13px;font-weight:700;color:#389e0d;margin-bottom:8px;">📌 板块联动机会</div>
        <p style="font-size:13px;color:#555;line-height:1.8;">光通信板块 — 长飞光纤、天孚通信等龙头持续走强，AI算力需求驱动，可持续关注；锂电板块 — 宁德时代等龙头稳健，可在回调时分批布局；化工板块 — 已涨停个股次日需观察，未涨停个股可关注低吸机会。</p>
      </div>
    </div>

    <!-- 免责声明 -->
    <div style="background:#f5f5f5;border-radius:8px;padding:12px 14px;font-size:11px;color:#999;line-height:1.7;margin-top:20px;">
      ⚠️ <strong>风险提示：</strong>本报告基于东方财富股吧人气榜实时数据，由AI系统自动生成，仅供参考，不构成任何投资建议。股市有风险，投资需谨慎。人气榜数据反映市场关注度，不代表股票基本面质量。请投资者根据自身风险承受能力独立决策，对因参考本报告造成的损失，本系统不承担任何责任。
    </div>

  </div>

  <!-- Footer -->
  <div style="text-align:center;padding:20px;font-size:12px;color:#bbb;border-top:1px solid #f0f0f0;margin-top:20px;">
    <strong style="color:#888;">东财人气榜 · AI智能日报</strong><br>
    数据来源：东方财富股吧人气榜 · 腾讯财经行情<br>
    生成时间：{now_str}
  </div>

</div>
</body>
</html>'''


def is_trading_time():
    """判断是否在交易时间 9:30-15:00"""
    now = datetime.now()
    h, m = now.hour, now.minute
    if h < 9 or h >= 15:
        return False
    if h == 9 and m < 30:
        return False
    return True


def news_scheduler():
    """后台新闻采集调度器"""
    from fetch_news import fetch_all_news
    
    while True:
        try:
            fetch_all_news()
        except Exception as e:
            print(f'[News] Error: {e}')
        
        # 根据交易时间决定下次采集间隔
        interval = 10 * 60 if is_trading_time() else 60 * 60
        time.sleep(interval)


def stock_data_scheduler():
    """后台股票数据采集调度器"""
    import subprocess
    
    while True:
        try:
            print('[StockData] 开始采集股票数据...')
            # 运行 quick_fetch.py 进行完整采集
            result = subprocess.run(
                [sys.executable, 'quick_fetch.py'],
                cwd=str(BASE_DIR),
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore',
                timeout=180
            )
            if result.returncode == 0:
                print('[StockData] 采集完成')
            else:
                print(f'[StockData] 采集失败')
        except Exception as e:
            print(f'[StockData] Error: {e}')
        
        # 开盘时间3分钟，其余时间1小时
        interval = 3 * 60 if is_trading_time() else 60 * 60
        print(f'[StockData] 下次采集: {interval//60} 分钟后')
        time.sleep(interval)


def main():
    print('=' * 50)
    print('Stock Rank Server')
    print('=' * 50)
    print(f'Open: http://localhost:{PORT}')
    print('Press Ctrl+C to stop')
    print()

    signals_file = OUTPUT_DIR / 'signals_latest.json'
    stocks_file  = OUTPUT_DIR / 'hot_stocks.json'

    if signals_file.exists() and stocks_file.exists():
        print('Generating page...')
        generate_page(signals_file, stocks_file, OUTPUT_DIR / 'index.html')

    # 启动股票数据采集后台线程
    stock_thread = threading.Thread(target=stock_data_scheduler, daemon=True)
    stock_thread.start()
    print('Stock data scheduler started (trading: 3min, off-hours: 60min)')

    # 启动新闻采集后台线程
    news_thread = threading.Thread(target=news_scheduler, daemon=True)
    news_thread.start()
    print('News scheduler started (trading: 10min, off-hours: 60min)')

    server = HTTPServer(('', PORT), Handler)
    print(f'Server running on port {PORT}...')

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nServer stopped')


# ─────────────────────────────────────────────────────────────────────────────
# 个股分析报告生成
# ─────────────────────────────────────────────────────────────────────────────

def _build_stock_report_html(stock, signal, market_indices, sector_info):
    """生成专业个股分析报告HTML（多空辩论风格）"""
    today_str = datetime.now().strftime('%Y年%m月%d日')
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    code = str(stock.get('code', ''))
    name = stock.get('name', code)
    price = float(stock.get('price', 0) or 0)
    change = float(stock.get('change', 0) or 0)
    change_pct = float(stock.get('change_pct', 0) or 0)
    turnover = float(stock.get('turnover_rate', 0) or 0)
    volume = stock.get('volume', 0)
    rank = stock.get('rank', '')
    
    signal_type = signal.get('signal', 'Hold')
    signal_score = float(signal.get('score', 50) or 50)
    signal_strength = int(signal.get('strength', 3) or 3)
    up_proba = float(signal.get('up_proba', 0.5) or 0.5)
    reasons = signal.get('reasons', [])
    agent_details = signal.get('agent_details', {})
    
    if change_pct > 0:
        price_color = '#e03131'; price_icon = '▲'
        change_text = f"+{change:.2f}"; change_pct_text = f"+{change_pct:.2f}%"
    elif change_pct < 0:
        price_color = '#2f9e44'; price_icon = '▼'
        change_text = f"{change:.2f}"; change_pct_text = f"{change_pct:.2f}%"
    else:
        price_color = '#666'; price_icon = '■'
        change_text = '0.00'; change_pct_text = '0.00%'
    
    signal_colors = {'Strong Buy': '#e03131', 'Buy': '#f08c00', 'Hold': '#666', 'Caution': '#fa5252', 'Risk': '#c92a2a'}
    signal_color = signal_colors.get(signal_type, '#666')
    
    bullish_signals = ['Strong Buy', 'Buy']
    bearish_signals = ['Caution', 'Risk']
    
    if signal_type in bullish_signals:
        trend_icon = '📈'; trend_text = '多头趋势'; trend_color = '#e03131'; debate_direction = 'bull'
    elif signal_type in bearish_signals:
        trend_icon = '📉'; trend_text = '空头趋势'; trend_color = '#2f9e44'; debate_direction = 'bear'
    else:
        trend_icon = '⚖️'; trend_text = '震荡整理'; trend_color = '#666'; debate_direction = 'neutral'
    
    indices_html = ''
    for idx in market_indices:
        idx_change = idx.get('change_pct', 0)
        idx_color = '#e03131' if idx_change > 0 else '#2f9e44' if idx_change < 0 else '#666'
        idx_arrow = '▲' if idx_change > 0 else '▼' if idx_change < 0 else '■'
        indices_html += f'''<div style="flex:1;background:#f8f9fa;padding:12px;border-radius:8px;text-align:center;min-width:120px;">
            <div style="font-size:12px;color:#666;margin-bottom:4px;">{idx.get('name','')}</div>
            <div style="font-size:18px;font-weight:700;color:#1a1a1a;">{idx.get('price',0):.2f}</div>
            <div style="font-size:13px;color:{idx_color};">{idx_arrow} {idx.get('change_pct',0):.2f}%</div>
        </div>'''
    
    sector_name = sector_info.get('sector', '未知')
    sector_stocks_count = sector_info.get('stocks_in_sector', 0)
    sector_avg_change = sector_info.get('avg_change', 0)
    
    rsi = stock.get('rsi'); macd = stock.get('macd'); bb_position = stock.get('bb_position')
    tech_indicators = []
    if rsi is not None:
        rsi_status = '超卖' if rsi < 30 else '超买' if rsi > 70 else '正常'
        rsi_color = '#2f9e44' if rsi < 30 else '#e03131' if rsi > 70 else '#666'
        tech_indicators.append(f"RSI: {rsi:.1f} ({rsi_status})")
    if macd is not None:
        macd_status = '金叉' if macd > 0 else '死叉'
        macd_color = '#2f9e44' if macd > 0 else '#e03131'
        tech_indicators.append(f"MACD: {macd:.4f} ({macd_status})")
    if bb_position is not None:
        bb_status = '布林下轨' if bb_position < 0.2 else '布林上轨' if bb_position > 0.8 else '布林中轨'
        tech_indicators.append(f"布林带: {bb_position:.0%} ({bb_status})")
    tech_html = '<br>'.join(tech_indicators) if tech_indicators else '暂无详细数据'
    
    analyst_html = ''
    if agent_details:
        reports = [v for k, v in agent_details.items() if isinstance(v, dict)][:3]
        if reports:
            analyst_html = '<div style="margin-top:12px;">'
            for rep in reports:
                rep_signal = rep.get('signal', 'neutral')
                rep_conf = rep.get('confidence', 0)
                rep_report = str(rep.get('report', ''))[:100]
                analyst_html += f'<div style="background:#f8f9fa;padding:10px;border-radius:6px;margin-bottom:8px;font-size:13px;"><strong>{rep_signal}</strong> ({rep_conf*100:.0f}%)<br>{rep_report}</div>'
            analyst_html += '</div>'
    
    reasons_html = ''.join(f"<li>{r}</li>" for r in reasons[:3]) if reasons else '<li>技术面呈现多头排列</li>'
    
    if debate_direction == 'bull':
        bull_html = f'''<div style="background:#fff9f9;padding:16px;border-radius:10px;border-left:4px solid #e03131;margin-bottom:16px;">
            <div style="font-size:16px;font-weight:700;color:#e03131;margin-bottom:10px;">🐂 多头论点</div>
            <ul style="margin:0;padding-left:20px;font-size:14px;color:#555;line-height:2;">{reasons_html}<li>信号评分 {signal_score}，强度 {signal_strength}/5，整体偏多</li><li>上涨概率 {up_proba*100:.1f}%，概率优势明显</li><li>所属行业 {sector_name} 板块，平均涨幅 {sector_avg_change:.2f}%</li></ul>
        </div>'''
        bear_html = f'''<div style="background:#f8f9fa;padding:16px;border-radius:10px;border-left:4px solid #ccc;margin-bottom:16px;">
            <div style="font-size:16px;font-weight:700;color:#666;margin-bottom:10px;">🐻 空头论点</div>
            <ul style="margin:0;padding-left:20px;font-size:14px;color:#555;line-height:2;"><li>当前价格 {price:.2f} 元，需关注追高风险</li><li>涨幅较大时存在回调压力</li><li>市场整体走弱时需谨慎</li></ul>
        </div>'''
    elif debate_direction == 'bear':
        bull_html = f'''<div style="background:#fff9f9;padding:16px;border-radius:10px;border-left:4px solid #e03131;margin-bottom:16px;">
            <div style="font-size:16px;font-weight:700;color:#e03131;margin-bottom:10px;">🐂 多头论点</div>
            <ul style="margin:0;padding-left:20px;font-size:14px;color:#555;line-height:2;"><li>超跌反弹机会，需等待企稳信号</li><li>设好止损，控制最大亏损</li><li>耐心等待底部确认</li></ul>
        </div>'''
        bear_html = f'''<div style="background:#f8f9fa;padding:16px;border-radius:10px;border-left:4px solid #2f9e44;margin-bottom:16px;">
            <div style="font-size:16px;font-weight:700;color:#2f9e44;margin-bottom:10px;">🐻 空头论点</div>
            <ul style="margin:0;padding-left:20px;font-size:14px;color:#555;line-height:2;">{reasons_html}<li>信号评分 {signal_score}，强度 {signal_strength}/5，整体偏空</li><li>上涨概率 {up_proba*100:.1f}%，概率优势在空头</li><li>所属行业 {sector_name} 板块，平均涨幅 {sector_avg_change:.2f}%</li></ul>
        </div>'''
    else:
        bull_html = f'''<div style="background:#fff9f9;padding:16px;border-radius:10px;border-left:4px solid #e03131;margin-bottom:16px;">
            <div style="font-size:16px;font-weight:700;color:#e03131;margin-bottom:10px;">🐂 多头论点</div>
            <ul style="margin:0;padding-left:20px;font-size:14px;color:#555;line-height:2;"><li>价格处于相对低位，有反弹可能</li><li>等待放量突破确认</li></ul>
        </div>'''
        bear_html = f'''<div style="background:#f8f9fa;padding:16px;border-radius:10px;border-left:4px solid #2f9e44;margin-bottom:16px;">
            <div style="font-size:16px;font-weight:700;color:#2f9e44;margin-bottom:10px;">🐻 空头论点</div>
            <ul style="margin:0;padding-left:20px;font-size:14px;color:#555;line-height:2;"><li>缺乏明确方向，震荡整理</li><li>等待趋势明朗后再操作</li></ul>
        </div>'''
    
    if signal_type in bullish_signals:
        stop_loss = price * (1 - max(0.03, abs(change_pct) / 100 * 0.8))
        target1 = price * 1.03; target2 = price * 1.05
        action_html = f'''<div style="background:#fff9db;padding:16px;border-radius:10px;border-left:4px solid #f08c00;margin-bottom:16px;">
            <div style="font-size:16px;font-weight:700;color:#f08c00;margin-bottom:10px;">💡 操作建议</div>
            <div style="font-size:14px;color:#555;line-height:1.8;"><p><strong>短线策略：</strong>回调至 {stop_loss:.2f} 元附近可考虑轻仓介入，止损设在 {stop_loss * 0.97:.2f} 元。</p><p><strong>目标价位：</strong>第一目标 {target1:.2f} 元，第二目标 {target2:.2f} 元。</p><p><strong>仓位建议：</strong>建议仓位不超过总资金的 20%。</p></div>
        </div>'''
    elif signal_type in bearish_signals:
        stop_loss = price * (1 + max(0.03, abs(change_pct) / 100 * 0.8))
        action_html = f'''<div style="background:#fff0f0;padding:16px;border-radius:10px;border-left:4px solid #c92a2a;margin-bottom:16px;">
            <div style="font-size:16px;font-weight:700;color:#c92a2a;margin-bottom:10px;">⚠️ 操作建议</div>
            <div style="font-size:14px;color:#555;line-height:1.8;"><p><strong>空头趋势：</strong>当前信号偏空，建议观望为主。</p><p><strong>止损价位：</strong>若持有，注意止损设在 {stop_loss:.2f} 元。</p><p><strong>入场条件：</strong>等待企稳信号出现后再考虑介入。</p></div>
        </div>'''
    else:
        action_html = f'''<div style="background:#f8f9fa;padding:16px;border-radius:10px;border-left:4px solid #666;margin-bottom:16px;">
            <div style="font-size:16px;font-weight:700;color:#666;margin-bottom:10px;">⚖️ 操作建议</div>
            <div style="font-size:14px;color:#555;line-height:1.8;"><p><strong>观望策略：</strong>当前趋势不明确，建议等待。</p><p><strong>关注价位：</strong>突破 {price * 1.02:.2f} 元可看多，跌破 {price * 0.98:.2f} 元需谨慎。</p></div>
        </div>'''
    
    risk_level = '低' if signal_type in bullish_signals else '高' if signal_type in bearish_signals else '中'
    risk_html = f'''<div style="background:#f8f9fa;padding:16px;border-radius:10px;border-left:4px solid #ccc;">
        <div style="font-size:16px;font-weight:700;color:#1a1a1a;margin-bottom:10px;">🛡️ 风险提示</div>
        <ul style="margin:0;padding-left:20px;font-size:13px;color:#666;line-height:1.8;"><li>市场有风险，投资需谨慎</li><li>本报告仅供参考，不构成投资建议</li><li>当前风险等级：<strong>{risk_level}</strong></li><li>设置止损是控制风险的有效手段</li></ul>
    </div>'''
    
    return f'''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>{name}({code}) 个股分析报告 - {today_str}</title><style>*{{margin:0;padding:0;box-sizing:border-box;}}body{{font-family:'PingFang SC','Microsoft YaHei',sans-serif;background:#fafafa;color:#1a1a1a;padding:16px;}}.container{{max-width:800px;margin:0 auto;}}.header{{background:linear-gradient(135deg,#1a1a1a,#333);color:#fff;padding:24px 20px;border-radius:12px 12px 0 0;}}.header-top{{display:flex;justify-content:space-between;align-items:flex-start;}}.stock-info{{flex:1;}}.stock-name{{font-size:26px;font-weight:700;margin-bottom:4px;}}.stock-code{{font-size:14px;color:#aaa;}}.price-box{{text-align:right;}}.price{{font-size:32px;font-weight:700;color:{price_color};}}.change{{font-size:16px;color:{price_color};margin-top:4px;}}.signal-badge{{display:inline-block;background:{signal_color};color:#fff;padding:6px 14px;border-radius:20px;font-size:14px;font-weight:600;margin-top:12px;}}.market{{background:#fff;padding:20px;border-radius:0 0 12px 12px;margin-bottom:20px;display:flex;gap:12px;flex-wrap:wrap;}}.content{{background:#fff;padding:20px;border-radius:12px;margin-bottom:20px;}}.section-title{{font-size:18px;font-weight:700;color:#1a1a1a;margin-bottom:16px;padding-bottom:10px;border-bottom:2px solid #f0f0f0;}}.data-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;}}.data-item{{background:#f8f9fa;padding:12px;border-radius:8px;text-align:center;}}.data-label{{font-size:12px;color:#666;margin-bottom:4px;}}.data-value{{font-size:18px;font-weight:700;color:#1a1a1a;}}.footer{{text-align:center;padding:20px;color:#999;font-size:12px;}}</style></head><body><div class="container"><div class="header"><div class="header-top"><div class="stock-info"><div class="stock-name">{name}</div><div class="stock-code">{code} | 人气榜第{rank}位 | {today_str} {now_str}</div></div><div class="price-box"><div class="price">{price_icon} {price:.2f}</div><div class="change">{change_text} ({change_pct_text})</div><div class="signal-badge">{trend_icon} {signal_type}</div></div></div></div><div class="market">{indices_html}</div><div class="content"><div class="section-title">📊 基础行情数据</div><div class="data-grid"><div class="data-item"><div class="data-label">换手率</div><div class="data-value">{turnover:.2f}%</div></div><div class="data-item"><div class="data-label">成交量</div><div class="data-value">{volume}</div></div><div class="data-item"><div class="data-label">板块</div><div class="data-value">{sector_name}</div></div><div class="data-item"><div class="data-label">板块内股票</div><div class="data-value">{sector_stocks_count}只</div></div><div class="data-item"><div class="data-label">板块均涨幅</div><div class="data-value">{sector_avg_change:.2f}%</div></div><div class="data-item"><div class="data-label">上涨概率</div><div class="data-value">{up_proba*100:.1f}%</div></div></div></div><div class="content"><div class="section-title">📈 技术指标分析</div><div style="font-size:14px;color:#555;line-height:1.8;">{tech_html}</div><div style="margin-top:12px;">{analyst_html}</div></div><div class="content"><div class="section-title">🗣️ 多空辩论</div>{bull_html}{bear_html}</div><div class="content">{action_html}</div><div class="content">{risk_html}</div><div class="footer"><p>本报告由 AI 多智能体分析系统生成</p><p>数据仅供参考，不构成投资建议</p></div></div></body></html>'''


if __name__ == '__main__':
    main()

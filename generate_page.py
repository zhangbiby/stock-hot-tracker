#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate HTML page with portfolio management
"""

import json
import sys
import os
from datetime import datetime
from pathlib import Path

if sys.platform == 'win32':
    try:
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
    except:
        pass

from portfolio import Portfolio


def generate_page(signals_file, stocks_file, output_file):
    # Load data
    with open(signals_file, 'r', encoding='utf-8') as f:
        signals_data = json.load(f)
    with open(stocks_file, 'r', encoding='utf-8') as f:
        stocks_data = json.load(f)

    signals = signals_data.get('signals', [])
    stocks  = stocks_data.get('stocks', [])
    
    # 为前端JS准备的JSON数据
    signals_json = json.dumps(signals, ensure_ascii=False)
    stocks_json = json.dumps(stocks, ensure_ascii=False)

    # 热门榜股票名称映射
    stock_name_map = {s['code']: s['name'] for s in stocks if 'code' in s and 'name' in s}

    # 完整A股名称映射（从 stock_name_map.json 加载，内嵌到 HTML 避免 CORS）
    full_name_map_file = Path(__file__).parent / "output" / "stock_name_map.json"
    if full_name_map_file.exists():
        with open(full_name_map_file, 'r', encoding='utf-8') as f:
            full_stock_name_map = json.load(f)
        # 合并：热门榜优先
        full_stock_name_map.update(stock_name_map)
    else:
        full_stock_name_map = stock_name_map

    # Portfolio
    portfolio = Portfolio()
    holdings  = portfolio.get_holdings_with_status()
    holding_codes = {h['code']: h for h in holdings}

    # 更新持仓名称
    for h in holdings:
        if h['code'] in stock_name_map:
            h['name'] = stock_name_map[h['code']]

    # 当前价格
    stock_prices = {s.get('code',''): float(s.get('price',0) or 0) for s in stocks}

    # 信号映射（提前，持仓卡片需要用到卖出信号）
    signal_map = {s['code']: s for s in signals}

    total_profit = 0
    holdings_html = ""
    holdings_js   = []

    for h in holdings:
        code          = h['code']
        current_price = stock_prices.get(code, 0)
        profit        = (current_price - h['buy_price']) * h['quantity']
        profit_pct    = ((current_price - h['buy_price']) / h['buy_price'] * 100) if h['buy_price'] > 0 else 0
        total_profit += profit

        can_sell   = h['can_sell']
        badge      = '<span class="sell-ready">Can Sell</span>' if can_sell else f'<span class="sell-wait">{h["sell_status"]}</span>'
        profit_cls = "profit-up" if profit >= 0 else "profit-down"
        profit_str = f"+{profit:.0f}({profit_pct:+.1f}%)" if profit >= 0 else f"{profit:.0f}({profit_pct:.1f}%)"

        # 从 signals 里找卖出信号
        sig_data = signal_map.get(code, {})
        sell_signal   = sig_data.get('sell_signal', '')
        sell_strength = sig_data.get('sell_strength', 0)
        sell_score    = sig_data.get('sell_score', 0)

        # 根据卖出信号确定卡片样式
        card_class = ""
        sell_progress_class = "low"
        if sell_score >= 60:
            card_class = "urgent-sell"
            sell_progress_class = "high"
        elif sell_score >= 40:
            card_class = "suggest-sell"
            sell_progress_class = "medium"

        sell_signal_cls_map = {
            '强力卖出': 'sell-sig-strong',
            '建议卖出': 'sell-sig-suggest',
            '考虑减仓': 'sell-sig-reduce',
            '持有观察': 'sell-sig-watch',
            '继续持有': 'sell-sig-hold',
        }
        sell_sig_cls = sell_signal_cls_map.get(sell_signal, '')
        
        # 卖出信号徽章
        if sell_signal == '强力卖出':
            sell_sig_html = f'<span class="badge-strong-sell">🔴 {sell_signal}</span>'
        elif sell_signal == '建议卖出':
            sell_sig_html = f'<span class="badge-suggest-sell">🟠 {sell_signal}</span>'
        else:
            sell_sig_html = f'<span class="sell-signal-badge {sell_sig_cls}">{sell_signal}</span>' if sell_signal else ''

        # 卖出进度条
        sell_progress_html = f'''
            <div class="sell-progress">
                <div class="sell-progress-bar {sell_progress_class}" style="width:{min(100, sell_score)}%"></div>
            </div>
        ''' if sell_score > 0 else ''

        # 卖出按钮（仅当可卖出时显示）
        sell_button_html = ''
        if can_sell:
            sell_button_html = f'''
                <button class="btn-sell" onclick="event.stopPropagation();sellHolding('{code}', '{h['name']}', {current_price}, {h['quantity']})" title="卖出">
                    💰卖出
                </button>
            '''

        holdings_html += f'''
            <div class="holding-card {card_class}" onclick="showHoldingDetail('{code}')">
                <div class="holding-header">
                    <span class="holding-name">{h['name']}({code})</span>
                    {badge}
                    {sell_button_html}
                    <button class="btn-delete" onclick="event.stopPropagation();deleteHolding('{code}','{h['name']}')" title="删除持仓">✕</button>
                </div>
                <div class="holding-info">
                    <span>Buy:{h['buy_price']:.2f}</span>
                    <span>Cur:{current_price:.2f}</span>
                    <span>Qty:{h['quantity']}</span>
                </div>
                <div class="holding-profit {profit_cls}">{profit_str}</div>
                {sell_sig_html}
                {sell_progress_html}
            </div>'''

        holdings_js.append({
            'code': code, 'name': h['name'],
            'buy_price': h['buy_price'], 'quantity': h['quantity'],
            'current_price': current_price, 'profit': profit,
            'profit_pct': profit_pct, 'can_sell': can_sell,
            'sell_status': h['sell_status'],
            # 卖出信号
            'sell_signal':   sell_signal,
            'sell_strength': sell_strength,
            'sell_score':    sell_score,
            'sell_reasons':  sig_data.get('holding_info', {}).get('sell_reasons', []) if sig_data.get('holding_info') else [],
            'sell_risks':    sig_data.get('holding_info', {}).get('sell_risks', [])   if sig_data.get('holding_info') else [],
        })

    if not holdings:
        holdings_html = '<div class="no-holdings">No holdings. Add below to track.</div>'

    # Stock rows
    stock_rows = ""
    signal_class_map = {
        'Strong Buy': 'signal-strong-buy', 'Buy': 'signal-buy',
        'Hold': 'signal-hold', 'Caution': 'signal-caution', 'Risk': 'signal-risk',
    }

    for s in stocks:
        code = s.get('code', '')
        sig  = signal_map.get(code, {})
        in_portfolio = code in holding_codes

        change_pct = s.get('change_pct', 0)
        if change_pct > 0:
            change_display, change_class = f"+{change_pct:.2f}%", "up"
        elif change_pct < 0:
            change_display, change_class = f"{change_pct:.2f}%", "down"
        else:
            change_display, change_class = "0.00%", ""

        signal       = sig.get('signal', 'Hold')
        strength     = sig.get('strength', 0)
        signal_class = signal_class_map.get(signal, 'signal-hold')
        stars        = "★" * strength + "☆" * (5 - strength)

        turnover = s.get('turnover_rate', 0)
        volume   = s.get('volume', 0)
        turnover_display = f"{turnover:.2f}%" if turnover else "-"
        volume_display   = f"{volume/10000:.1f}W" if volume > 10000 else str(volume)

        portfolio_badge = sell_warning = profit_info = ""
        if in_portfolio:
            h          = holding_codes[code]
            cur        = stock_prices.get(code, 0)
            p          = (cur - h['buy_price']) * h['quantity']
            p_pct      = ((cur - h['buy_price']) / h['buy_price'] * 100) if h['buy_price'] > 0 else 0
            can_sell   = h['can_sell']
            badge_cls  = "sell-ready-badge" if can_sell else "owned-badge"
            badge_txt  = "Can Sell" if can_sell else "Holding"
            portfolio_badge = f'<span class="{badge_cls}">{badge_txt}</span>'
            p_cls      = "up" if p >= 0 else "down"
            p_tag      = f"{p_pct:+.1f}%" if p >= 0 else f"{p_pct:.1f}%"
            profit_info = f'<span class="profit-tag {p_cls}">{p_tag}</span>'

            # 卖出信号标签
            row_sell_signal   = sig.get('sell_signal', '')
            row_sell_strength = sig.get('sell_strength', 0)
            sell_badge_map = {
                '强力卖出': ('sell-row-strong',  '🔴强力卖出'),
                '建议卖出': ('sell-row-suggest', '🟠建议卖出'),
                '考虑减仓': ('sell-row-reduce',  '🟡考虑减仓'),
                '持有观察': ('sell-row-watch',   '⚪持有观察'),
                '继续持有': ('sell-row-hold',    '🟢继续持有'),
            }
            if row_sell_signal in sell_badge_map:
                cls, txt = sell_badge_map[row_sell_signal]
                sell_warning = f'<span class="sell-row-badge {cls}">{txt}</span>'

        rank = s.get('rank', '')
        rank_cls = f"rank-{rank}" if rank in [1,2,3] else "rank-other"
        
        # ML 模型提示
        up_proba = sig.get('up_proba')
        if up_proba is not None:
            ml_tooltip = f"ML预测上涨概率: {up_proba*100:.0f}%"
            ml_badge   = f'<span class="ml-proba">ML {up_proba*100:.0f}%</span>'
        else:
            ml_tooltip = "规则模型（ML未启用）"
            ml_badge   = ""
        
        stock_rows += f'''
        <tr class="stock-row {'in-holding' if in_portfolio else ''}">
            <td class="rank-col"><span class="rank-badge {rank_cls}">{rank}</span></td>
            <td class="code-col">{code}</td>
            <td class="name-col" onclick="openGuba('{code}')">{s.get('name','')} {portfolio_badge}{sell_warning}{profit_info}</td>
            <td class="price-col">{s.get('price','-')}</td>
            <td class="change-col {change_class}">{change_display}</td>
            <td class="turnover-col">{turnover_display}</td>
            <td class="volume-col">{volume_display}</td>
            <td class="signal-col">
                <span class="signal-badge {signal_class}" title="{ml_tooltip}">{signal}</span>
                <span class="strength-stars">{stars}</span>
                {ml_badge}
            </td>
            <td class="action-col">
                <button class="btn-stock-report" onclick="generateStockReport('{code}', '{s.get('name','')}')" title="生成个股报告">📊</button>
            </td>
        </tr>'''

    update_time     = signals_data.get('update_time', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    strong_buy_count = len([s for s in signals if s.get('signal') == 'Strong Buy'])
    buy_count        = len([s for s in signals if s.get('signal') == 'Buy'])
    hold_count       = len([s for s in signals if s.get('signal') in ['Hold', 'Caution']])
    risk_count       = len([s for s in signals if s.get('signal') == 'Risk'])

    profit_display   = f"+{total_profit:.0f}" if total_profit >= 0 else f"{total_profit:.0f}"
    profit_cls_total = "up" if total_profit >= 0 else "down"

    holdings_js_json    = json.dumps(holdings_js, ensure_ascii=False)
    stock_name_map_json = json.dumps(full_stock_name_map, ensure_ascii=False)

    # ── JavaScript (单一、无重复) ──────────────────────────────────────────
    js_code = f'''
        // ① 完整A股名称映射（内嵌，5000+只，无需 fetch，无 CORS 问题）
        const stockNameMap = {stock_name_map_json};

        // ② 后端持仓（Python生成）
        const backendHoldings = {holdings_js_json};

        // ③ 查询股票名称
        function getStockName(code) {{
            return stockNameMap[code] || code;
        }}

        // 全角转半角（处理输入法导致的全角数字）
        function toHalfWidth(str) {{
            return str.replace(/[\uFF10-\uFF19]/g, c => String.fromCharCode(c.charCodeAt(0) - 0xFEE0));
        }}

        // ④ 输入代码后自动填充名称
        function autoFillStockName() {{
            const raw   = document.getElementById('addCode').value.trim();
            const code  = toHalfWidth(raw);
            // 自动回写半角
            if (code !== raw) document.getElementById('addCode').value = code;

            const nameInput = document.getElementById('addName');
            if (code.length !== 6) return;

            const name = stockNameMap[code];
            if (name) {{
                nameInput.value       = name;
                nameInput.style.color = '#00d4ff';
                nameInput.style.borderColor = '#00d4ff';
            }} else {{
                nameInput.value       = '';
                nameInput.placeholder = '未找到，请手动输入';
                nameInput.style.color = '#ffc107';
                nameInput.style.borderColor = '#ffc107';
            }}
        }}

        // ⑦ localStorage 持仓工具
        function loadCustomHoldings() {{
            try {{
                const list = JSON.parse(localStorage.getItem('customHoldings') || '[]');
                // 过滤掉无效条目（code 必须是6位数字）
                return list.filter(h => h.code && /^[0-9]{{6}}$/.test(h.code));
            }} catch (e) {{ return []; }}
        }}
        function saveCustomHoldings(list) {{
            try {{ localStorage.setItem('customHoldings', JSON.stringify(list)); return true; }}
            catch (e) {{ return false; }}
        }}
        // 清理 localStorage 里的乱码/无效持仓
        function cleanLocalStorage() {{
            const list = JSON.parse(localStorage.getItem('customHoldings') || '[]');
            const valid = list.filter(h => h.code && /^[0-9]{{6}}$/.test(h.code));
            if (valid.length !== list.length) {{
                localStorage.setItem('customHoldings', JSON.stringify(valid));
                console.log(`Cleaned ${{list.length - valid.length}} invalid holdings from localStorage`);
            }}
        }}

        // ⑧ 合并持仓（后端 + localStorage）
        function buildHoldingsData() {{
            const custom = loadCustomHoldings();
            const map = {{}};
            backendHoldings.forEach(h => {{ map[h.code] = {{...h, source:'backend'}}; }});
            custom.forEach(h => {{ map[h.code] = {{...h, source:'custom'}}; }});
            return Object.values(map);
        }}
        let holdingsData = buildHoldingsData();

        // ⑨ 页面初始化（同步，无需 async）
        function initPage() {{
            // 清理 localStorage 里的乱码/无效持仓
            cleanLocalStorage();
            // 日期默认今天
            const dateInput = document.getElementById('addDate');
            if (dateInput && !dateInput.value) {{
                dateInput.value = new Date().toISOString().split('T')[0];
            }}
            // 加载新闻
            scheduleNewsUpdate();
        }}

        // ⑩ 添加持仓
        function addHolding() {{
            const code  = toHalfWidth(document.getElementById('addCode').value.trim());
            const nameV = document.getElementById('addName').value.trim();
            const name  = nameV || getStockName(code);
            const price = parseFloat(document.getElementById('addPrice').value);
            const qty   = parseInt(document.getElementById('addQty').value);
            const date  = document.getElementById('addDate').value || new Date().toISOString().split('T')[0];

            if (!code || !price || !qty) {{ alert('请填写：股票代码、买入价格、数量'); return; }}
            if (code.length !== 6)       {{ alert('股票代码必须是6位数字'); return; }}

            // 先尝试服务器（持久化到 holdings.json）
            fetch('/add_holding?' + new URLSearchParams({{code, name, price, qty, date}}))
                .then(r => r.json())
                .then(data => {{
                    if (data.success) {{
                        alert(data.message);
                        setTimeout(() => location.reload(), 500);
                    }} else {{
                        alert('保存失败: ' + data.message);
                    }}
                }})
                .catch(() => {{
                    // 服务器不可用 → 存 localStorage
                    const newH = {{
                        code, name, buy_price: price, quantity: qty,
                        buy_date: date, source: 'custom',
                        current_price: 0, profit: 0, profit_pct: 0,
                        can_sell: false, sell_status: '持仓中'
                    }};
                    const list = loadCustomHoldings();
                    const idx  = list.findIndex(h => h.code === code);
                    if (idx >= 0) list[idx] = newH; else list.push(newH);

                    if (saveCustomHoldings(list)) {{
                        alert('已临时保存（localStorage）：' + name + '(' + code + ')\\n启动 server.py 可持久化到 JSON 文件');
                        setTimeout(() => location.reload(), 500);
                    }} else {{
                        alert('保存失败，请检查浏览器存储权限');
                    }}
                }});
        }}

        // ⑪ 持仓详情弹窗
        function showHoldingDetail(code) {{
            const h = holdingsData.find(x => x.code === code);
            if (!h) return;
            const pc = h.profit >= 0 ? '#ff4757' : '#2ed573';
            const ps = h.profit >= 0 ? '+' : '';

            // 卖出信号颜色
            const sellColorMap = {{
                '强力卖出': '#ef4444',
                '建议卖出': '#f97316',
                '考虑减仓': '#fbbf24',
                '持有观察': '#94a3b8',
                '继续持有': '#4ade80',
            }};
            const sellSignal   = h.sell_signal   || '继续持有';
            const sellStrength = h.sell_strength || 1;
            const sellScore    = h.sell_score    || 0;
            const sellColor    = sellColorMap[sellSignal] || '#94a3b8';
            const sellStars    = '●'.repeat(sellStrength) + '○'.repeat(5 - sellStrength);
            const sellReasons  = (h.sell_reasons || []).map(r => `<li>${{r}}</li>`).join('');
            const sellRisks    = (h.sell_risks   || []).map(r => `<li style="color:#ef4444">${{r}}</li>`).join('');

            document.getElementById('modalBody').innerHTML = `
                <div style="margin-bottom:12px;font-size:1.4rem;font-weight:bold;">${{h.name}} (${{h.code}})</div>

                <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px;">
                    <div><div style="color:#7a8fa6;font-size:.75rem;">Buy Price</div><div style="font-size:1.1rem;">${{h.buy_price.toFixed(2)}} CNY</div></div>
                    <div><div style="color:#7a8fa6;font-size:.75rem;">Current Price</div><div style="font-size:1.1rem;">${{h.current_price.toFixed(2)}} CNY</div></div>
                    <div><div style="color:#7a8fa6;font-size:.75rem;">Quantity</div><div style="font-size:1.1rem;">${{h.quantity}} shares</div></div>
                    <div><div style="color:#7a8fa6;font-size:.75rem;">P/L</div><div style="font-size:1.1rem;color:${{pc}};">${{ps}}${{h.profit.toFixed(2)}} (${{ps}}${{h.profit_pct.toFixed(2)}}%)</div></div>
                    <div><div style="color:#7a8fa6;font-size:.75rem;">T+1 Status</div><div style="font-size:.95rem;color:${{h.can_sell?'#4ade80':'#fbbf24'}};">${{h.sell_status}}</div></div>
                    <div><div style="color:#7a8fa6;font-size:.75rem;">Source</div><div style="font-size:.85rem;color:#7a8fa6;">${{h.source === 'backend' ? '📁 JSON' : '💾 localStorage'}}</div></div>
                </div>

                <div style="background:rgba(0,0,0,.3);border-radius:12px;padding:14px;margin-bottom:14px;border:1px solid ${{sellColor}}40;">
                    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;">
                        <span style="font-size:.8rem;color:#7a8fa6;">卖出信号</span>
                        <span style="font-size:.75rem;color:#7a8fa6;">得分: ${{sellScore}}</span>
                    </div>
                    <div style="font-size:1.3rem;font-weight:700;color:${{sellColor}};margin-bottom:6px;">
                        ${{sellSignal}}
                        <span style="font-size:.9rem;letter-spacing:2px;margin-left:8px;">${{sellStars}}</span>
                    </div>
                    ${{(sellReasons || sellRisks) ? `
                    <ul style="font-size:.78rem;color:#ccc;padding-left:16px;margin-top:8px;line-height:1.8;">
                        ${{sellReasons}}${{sellRisks}}
                    </ul>` : ''}}
                </div>

                <div class="action-buttons">
                    <button class="btn btn-cancel" onclick="closeModal()">Close</button>
                    <button class="btn btn-danger" onclick="deleteHolding('${{h.code}}','${{h.name}}')">🗑 删除持仓</button>
                </div>`;
            document.getElementById('holdingModal').classList.add('active');
        }}

        // ⑫ 删除持仓
        function deleteHolding(code, name) {{
            if (!confirm('确认删除持仓：' + name + '(' + code + ')？')) return;
            closeModal();

            // 先尝试服务器删除（持久化）
            fetch('/delete_holding?code=' + code)
                .then(r => r.json())
                .then(data => {{
                    // 无论服务器是否成功，都同步删除 localStorage
                    const list = loadCustomHoldings().filter(h => h.code !== code);
                    saveCustomHoldings(list);
                    setTimeout(() => location.reload(), 300);
                }})
                .catch(() => {{
                    // 服务器不可用，只删 localStorage
                    const list = loadCustomHoldings().filter(h => h.code !== code);
                    saveCustomHoldings(list);
                    setTimeout(() => location.reload(), 300);
                }});
        }}

        function closeModal() {{
            document.getElementById('holdingModal').classList.remove('active');
        }}

        function openGuba(code) {{
            if (code && code.length === 6)
                window.open('https://guba.eastmoney.com/list,' + code + '.html', '_blank');
        }}

        // ⑫ 事件绑定
        const holdingModal = document.getElementById('holdingModal');
        if (holdingModal) {{
            holdingModal.addEventListener('click', e => {{ if (e.target === holdingModal) closeModal(); }});
        }}
        document.addEventListener('keydown', e => {{
            if (e.key === 'r' || e.key === 'R') location.reload();
            if (e.key === 'Escape') closeModal();
        }});

        // ⑭ 大盘指数（腾讯财经 JSONP）
        function loadMarketIndices() {{
            const indices = [
                {{ code: 'sh000001', name: '上证指数', short: 'SH' }},
                {{ code: 'sz399001', name: '深证成指', short: 'SZ' }},
                {{ code: 'sz399006', name: '创业板指', short: 'CYB' }},
                {{ code: 'sh000688', name: '科创50',   short: 'KC50' }},
            ];
            const codes = indices.map(i => i.code).join(',');
            const script = document.createElement('script');
            window._indexCallback = function(data) {{
                const wrap = document.getElementById('marketIndices');
                if (!wrap) return;
                let html = '';
                indices.forEach(idx => {{
                    const raw = data[idx.code];
                    if (!raw) return;
                    const parts = raw.split('~');
                    const price  = parseFloat(parts[3]  || 0);
                    const close  = parseFloat(parts[4]  || 0);
                    const chgAmt = parseFloat(parts[31] || 0);
                    const chgPct = parseFloat(parts[32] || 0);
                    const dir    = chgPct > 0 ? 'up' : chgPct < 0 ? 'down' : 'flat';
                    const sign   = chgPct > 0 ? '+' : '';
                    html += `<div class="index-item index-${{dir}}">
                        <div class="index-name">${{idx.name}}</div>
                        <div class="index-price">${{price.toFixed(2)}}</div>
                        <div class="index-change">${{sign}}${{chgAmt.toFixed(2)}} (${{sign}}${{chgPct.toFixed(2)}}%)</div>
                    </div>`;
                }});
                wrap.innerHTML = html || '<div class="index-loading">暂无数据</div>';
            }};
            script.src = `https://web.sqt.gtimg.cn/q=${{codes}}`;
            script.onload = function() {{
                // 腾讯财经返回 var v_xxx="..." 格式，解析它
                const wrap = document.getElementById('marketIndices');
                let html = '';
                indices.forEach(idx => {{
                    const varName = 'v_' + idx.code;
                    if (typeof window[varName] === 'undefined') return;
                    const raw = window[varName];
                    const parts = raw.split('~');
                    const price  = parseFloat(parts[3]  || 0);
                    const chgAmt = parseFloat(parts[31] || 0);
                    const chgPct = parseFloat(parts[32] || 0);
                    const dir    = chgPct > 0 ? 'up' : chgPct < 0 ? 'down' : 'flat';
                    const sign   = chgPct > 0 ? '+' : '';
                    html += `<div class="index-item index-${{dir}}">
                        <div class="index-name">${{idx.name}}</div>
                        <div class="index-price">${{price.toFixed(2)}}</div>
                        <div class="index-change">${{sign}}${{chgAmt.toFixed(2)}} (${{sign}}${{chgPct.toFixed(2)}}%)</div>
                    </div>`;
                }});
                if (html) wrap.innerHTML = html;
            }};
            script.onerror = function() {{
                const wrap = document.getElementById('marketIndices');
                if (wrap) wrap.innerHTML = '<div class="index-loading">⚠️ 指数加载失败（需联网）</div>';
            }};
            document.head.appendChild(script);
            // 每60秒刷新一次
            setTimeout(loadMarketIndices, 60000);
        }}

        // ⑮ 生成日报
        function generateReport() {{
            const btn = document.getElementById('btnReport');
            const toast = document.getElementById('reportToast');
            btn.disabled = true;
            btn.innerHTML = '<span class="spin">⏳</span> 生成中...';

            // 调用 server.py 的 /generate_report 接口
            fetch('/generate_report', {{ method: 'POST' }})
                .then(r => r.json())
                .then(data => {{
                    btn.disabled = false;
                    btn.innerHTML = '📄 生成日报';
                    if (data.success) {{
                        toast.textContent = '✅ 报告已生成，正在打开...';
                        toast.className = 'report-toast show';
                        setTimeout(() => {{ toast.className = 'report-toast'; }}, 3000);
                        // 新标签页打开报告
                        window.open(data.url, '_blank');
                    }} else {{
                        toast.textContent = '❌ 生成失败: ' + (data.error || '未知错误');
                        toast.className = 'report-toast show';
                        setTimeout(() => {{ toast.className = 'report-toast'; }}, 4000);
                    }}
                }})
                .catch(err => {{
                    btn.disabled = false;
                    btn.innerHTML = '📄 生成日报';
                    // 如果不是通过 server.py 访问，直接本地生成
                    toast.textContent = '⚠️ 请通过 python server.py 启动后使用报告功能';
                    toast.className = 'report-toast show';
                    setTimeout(() => {{ toast.className = 'report-toast'; }}, 4000);
                }});
        }}

        // ⑬ 启动
        if (document.readyState === 'loading') {{
            document.addEventListener('DOMContentLoaded', () => {{ 
                initPage(); 
                loadMarketIndices(); 
                updateBuySignals();
                requestNotificationPermission();
                setInterval(checkNewSignals, 60000); // 每分钟检查新信号
            }});
        }} else {{
            initPage();
            loadMarketIndices();
            updateBuySignals();
            requestNotificationPermission();
            setInterval(checkNewSignals, 60000);
        }}

        // 买入信号面板功能
        function toggleBuyPanel() {{
            const content = document.getElementById('buySignalList');
            const icon = document.getElementById('buyPanelToggle');
            content.classList.toggle('collapsed');
            icon.classList.toggle('collapsed');
        }}

        // 浏览器通知功能
        function requestNotificationPermission() {{
            if ('Notification' in window && Notification.permission === 'default') {{
                Notification.requestPermission();
            }}
        }}

        function sendNotification(title, body) {{
            if ('Notification' in window && Notification.permission === 'granted') {{
                new Notification(title, {{
                    body: body,
                    icon: '📈',
                    tag: 'stock-signal'
                }});
            }}
        }}

        // 检查新信号并发送通知
        let lastStrongBuyCodes = [];
        function checkNewSignals() {{
            const signals = {signals_json};
            const strongBuys = signals.filter(s => s.signal === 'Strong Buy');
            const currentCodes = strongBuys.map(s => s.code);
            
            // 找出新出现的Strong Buy
            const newSignals = strongBuys.filter(s => !lastStrongBuyCodes.includes(s.code));
            
            if (newSignals.length > 0 && lastStrongBuyCodes.length > 0) {{
                newSignals.forEach(s => {{
                    sendNotification(
                        '🔥 新的买入信号',
                        `${{s.name || s.code}} 出现 Strong Buy 信号，得分: ${{s.score}}`
                    );
                }});
            }}
            
            lastStrongBuyCodes = currentCodes;
        }}

        function updateBuySignals() {{
            const signals = {signals_json};
            const stocks = {stocks_json};
            
            // 筛选 Strong Buy 和 Buy 信号
            const buySignals = signals.filter(s => s.signal === 'Strong Buy' || s.signal === 'Buy');
            
            // 按得分排序，取前5
            buySignals.sort((a, b) => b.score - a.score);
            const top5 = buySignals.slice(0, 5);
            
            const container = document.getElementById('buySignalList');
            if (top5.length === 0) {{
                container.innerHTML = '<div style="color:#888;text-align:center;padding:20px;">暂无买入信号</div>';
                return;
            }}
            
            container.innerHTML = top5.map(s => {{
                const stock = stocks.find(st => st.code === s.code) || {{}};
                const signalClass = s.signal === 'Strong Buy' ? 'strong-buy' : 'buy';
                return `
                    <div class="buy-item">
                        <div class="buy-item-header">
                            <span class="buy-item-name">${{s.name || s.code}}</span>
                            <span class="buy-item-signal ${{signalClass}}">${{s.signal}}</span>
                        </div>
                        <div class="buy-item-details">
                            得分: ${{s.score}} | 排名: ${{stock.rank || '-'}} | 价格: ${{stock.price || '-'}}
                        </div>
                        <div class="buy-item-actions">
                            <button class="btn-quick-buy" onclick="quickBuy('${{s.code}}', '${{s.name}}', ${{stock.price || 0}})">买入</button>
                            <button class="btn-view-detail" onclick="showSignalDetail('${{s.code}}')">详情</button>
                        </div>
                    </div>
                `;
            }}).join('');
        }}

        function quickBuy(code, name, price) {{
            document.getElementById('addCode').value = code;
            document.getElementById('addName').value = name || code;
            document.getElementById('addPrice').value = price ? price.toFixed(2) : '';
            document.getElementById('addQty').value = 100;
            document.getElementById('addDate').value = new Date().toISOString().split('T')[0];
            
            // 滚动到表单
            document.querySelector('.add-holding-form').scrollIntoView({{ behavior: 'smooth' }});
            document.getElementById('addQty').focus();
        }}

        function showSignalDetail(code) {{
            const modal = document.getElementById('signalDetailModal');
            const title = document.getElementById('signalDetailTitle');
            const body = document.getElementById('signalDetailBody');
            
            // 查找信号数据
            const signals = {signals_json};
            const stocks = {stocks_json};
            const signal = signals.find(s => s.code === code);
            const stock = stocks.find(s => s.code === code);
            
            if (!signal) {{
                body.innerHTML = '<div style="text-align:center;padding:40px;">未找到该股票的信号数据</div>';
                modal.style.display = 'flex';
                return;
            }}
            
            title.textContent = (signal.name || code) + ' - 信号详情';
            
            // 构建详情内容
            const signalClass = signal.signal === 'Strong Buy' ? 'strong-buy' : 
                               signal.signal === 'Buy' ? 'buy' :
                               signal.signal === 'Risk' ? 'risk' : 'hold';
            
            let factorsHtml = '';
            if (signal.factors && signal.factors.length > 0) {{
                factorsHtml = `
                    <table class="factor-table">
                        <thead>
                            <tr><th>因子</th><th>得分</th><th>说明</th></tr>
                        </thead>
                        <tbody>
                            ${{signal.factors.map(f => `
                                <tr>
                                    <td>${{f.name}}</td>
                                    <td class="factor-score ${{f.score >= 0 ? 'positive' : 'negative'}}">${{f.score > 0 ? '+' : ''}}${{f.score}}</td>
                                    <td class="factor-reason">${{f.reason}}</td>
                                </tr>
                            `).join('')}}
                        </tbody>
                    </table>
                `;
            }} else {{
                factorsHtml = '<div style="color:#888;padding:20px;text-align:center;">暂无因子详情</div>';
            }}
            
            body.innerHTML = `
                <div class="signal-summary-box">
                    <div class="signal-summary-row">
                        <span class="signal-summary-label">信号类型</span>
                        <span class="signal-summary-value ${{signalClass}}">${{signal.signal}}</span>
                    </div>
                    <div class="signal-summary-row">
                        <span class="signal-summary-label">综合得分</span>
                        <span class="signal-summary-value">${{signal.score}}</span>
                    </div>
                    <div class="signal-summary-row">
                        <span class="signal-summary-label">当前排名</span>
                        <span class="signal-summary-value">${{stock ? stock.rank : '-'}}</span>
                    </div>
                    <div class="signal-summary-row">
                        <span class="signal-summary-label">当前价格</span>
                        <span class="signal-summary-value">${{stock ? stock.price : '-'}}</span>
                    </div>
                    ${{signal.ml_proba ? `
                    <div class="signal-summary-row">
                        <span class="signal-summary-label">ML预测概率</span>
                        <span class="signal-summary-value">${{(signal.ml_proba * 100).toFixed(1)}}%</span>
                    </div>
                    ` : ''}}
                </div>
                <h4 style="margin-bottom:10px;color:#00d4ff;">因子分解</h4>
                ${{factorsHtml}}
            `;
            
            modal.style.display = 'flex';
        }}

        function closeSignalDetail() {{
            document.getElementById('signalDetailModal').style.display = 'none';
        }}

        // 卖出持仓
        function sellHolding(code, name, price, maxQty) {{
            const qty = prompt(`卖出 ${{name}}(${{code}})\\n当前价格: ${{price.toFixed(2)}}\\n请输入卖出数量 (最多 ${{maxQty}} 股):`, maxQty);
            if (!qty || isNaN(qty) || qty <= 0) return;
            if (parseInt(qty) > maxQty) {{
                alert('卖出数量不能超过持仓数量');
                return;
            }}
            
            const toast = document.getElementById('reportToast');
            toast.textContent = '正在卖出...';
            toast.className = 'report-toast show';
            
            fetch(`/sell_holding?code=${{code}}&price=${{price}}&quantity=${{qty}}`)
                .then(r => r.json())
                .then(data => {{
                    if (data.success) {{
                        toast.textContent = '✅ ' + data.message;
                        setTimeout(() => location.reload(), 1500);
                    }} else {{
                        toast.textContent = '❌ ' + data.message;
                        setTimeout(() => {{ toast.className = 'report-toast'; }}, 3000);
                    }}
                }})
                .catch(err => {{
                    toast.textContent = '❌ 卖出失败: ' + err;
                    setTimeout(() => {{ toast.className = 'report-toast'; }}, 3000);
                }});
        }}

        // ⑯ 生成个股报告
        function generateStockReport(code, name) {{
            const toast = document.getElementById('reportToast');
            toast.textContent = '正在生成 ' + name + ' 的分析报告...';
            toast.className = 'report-toast show';
            
            fetch('/generate_stock_report', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/x-www-form-urlencoded' }},
                body: 'code=' + encodeURIComponent(code) + '&name=' + encodeURIComponent(name)
            }})
            .then(r => r.json())
            .then(data => {{
                if (data.success) {{
                    toast.textContent = '报告已生成，正在打开...';
                    setTimeout(() => {{ toast.className = 'report-toast'; }}, 2000);
                    window.open(data.url, '_blank');
                }} else {{
                    toast.textContent = '生成失败: ' + (data.error || '未知错误');
                    setTimeout(() => {{ toast.className = 'report-toast'; }}, 3000);
                }}
            }})
            .catch(err => {{
                toast.textContent = '请求失败: ' + err.message;
                setTimeout(() => {{ toast.className = 'report-toast'; }}, 3000);
            }});
        }}

        // ⑮ 加载财经新闻
        function loadNews() {{
            fetch('/get_news')
                .then(r => r.json())
                .then(data => {{
                    if (data.success && data.news && data.news.length > 0) {{
                        const ticker = document.getElementById('newsTicker');
                        const content = document.getElementById('newsContent');
                        
                        let html = '';
                        data.news.forEach(news => {{
                            // 根据新闻源生成对应的链接
                            let url = '#';
                            switch(news.source) {{
                                case '财联社':
                                    url = 'https://www.cls.cn/';
                                    break;
                                case '新浪财经':
                                    url = 'https://finance.sina.com.cn/';
                                    break;
                                case '东方财富':
                                    url = 'https://www.eastmoney.com/';
                                    break;
                                case '同花顺':
                                    url = 'https://www.10jqka.com.cn/';
                                    break;
                                case '人民网':
                                    url = 'http://finance.people.com.cn/';
                                    break;
                            }}
                            
                            html += `
                                <div class="news-item" onclick="openNewsSource('${{news.source}}', event)">
                                    <div>
                                        <span class="news-source">${{news.source}}</span>
                                        <span class="news-time">${{news.time}}</span>
                                    </div>
                                    <div class="news-title">${{news.title}}</div>
                                </div>
                            `;
                        }});
                        
                        content.innerHTML = html;
                        content.classList.remove('news-loading');
                        ticker.style.display = 'block';
                    }}
                }})
                .catch(e => {{
                    console.log('News load error:', e);
                }});
        }}

        // ⑯ 折叠/展开新闻卡片
        function toggleNewsTicker() {{
            const ticker = document.getElementById('newsTicker');
            ticker.classList.toggle('collapsed');
        }}

        // ⑰ 打开新闻源
        function openNewsSource(source, event) {{
            event.stopPropagation();
            const urls = {{
                '财联社': 'https://www.cls.cn/',
                '新浪财经': 'https://finance.sina.com.cn/',
                '东方财富': 'https://www.eastmoney.com/',
                '同花顺': 'https://www.10jqka.com.cn/',
                '人民网': 'http://finance.people.com.cn/'
            }};
            if (urls[source]) {{
                window.open(urls[source], '_blank');
            }}
        }}

        // ⑱ 定时更新新闻
        function scheduleNewsUpdate() {{
            const now = new Date();
            const hour = now.getHours();
            const min = now.getMinutes();
            
            // 交易时间 9:30-15:00 每10分钟更新
            // 非交易时间 1小时更新
            const isTrading = hour >= 9 && hour < 15 && !(hour === 15 && min > 0);
            const interval = isTrading ? 10 * 60 * 1000 : 60 * 60 * 1000;
            
            loadNews(); // 立即加载一次
            setInterval(loadNews, interval);
        }}
    '''

    # ── HTML ──────────────────────────────────────────────────────────────
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Stock Rank + Trading Signals</title>
    <meta http-equiv="refresh" content="120">
    <style>
        * {{ margin:0; padding:0; box-sizing:border-box; }}
        body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; background:linear-gradient(135deg,#0c1929,#1a2a4a); min-height:100vh; color:#e8e8e8; padding:20px; }}
        .container {{ max-width:1200px; margin:0 auto; }}
        .header {{ text-align:center; margin-bottom:25px; padding:20px; background:rgba(255,255,255,.03); border-radius:20px; }}
        .title {{ font-size:1.8rem; margin-bottom:8px; }}
        .title-text {{ background:linear-gradient(90deg,#ff6b6b,#ffd93d,#6bcb77); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }}
        .live-badge {{ background:#ff4444; color:white; padding:4px 12px; border-radius:20px; font-size:.7rem; animation:pulse 2s infinite; }}
        @keyframes pulse {{ 0%,100%{{opacity:1}} 50%{{opacity:.7}} }}
        .disclaimer {{ background:rgba(255,193,7,.15); color:#ffc107; padding:10px 20px; border-radius:10px; margin-bottom:20px; text-align:center; font-size:.85rem; }}
        .signal-summary {{ display:flex; justify-content:center; gap:30px; margin:20px 0; }}
        .signal-stat {{ text-align:center; padding:12px 20px; border-radius:12px; }}
        .signal-stat.strong-buy {{ background:rgba(255,50,50,.15); }}
        .signal-stat.buy {{ background:rgba(255,100,100,.15); }}
        .signal-stat.hold {{ background:rgba(128,128,128,.15); }}
        .signal-stat.risk {{ background:rgba(0,200,0,.15); }}
        .signal-stat-value {{ font-size:1.5rem; font-weight:700; }}
        .signal-stat-label {{ font-size:.75rem; color:#aaa; margin-top:3px; }}
        
        /* 买入信号面板 */
        .buy-panel {{ background:linear-gradient(135deg,rgba(255,100,100,.1),rgba(255,50,50,.05)); border-radius:15px; margin:20px 0; border:1px solid rgba(255,100,100,.3); overflow:hidden; }}
        .panel-header {{ display:flex; justify-content:space-between; align-items:center; padding:15px 20px; cursor:pointer; background:rgba(255,100,100,.1); }}
        .panel-header span:first-child {{ font-weight:600; color:#ff6b6b; }}
        .toggle-icon {{ transition:transform .3s; }}
        .toggle-icon.collapsed {{ transform:rotate(-90deg); }}
        .panel-content {{ padding:15px 20px; display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:15px; }}
        .panel-content.collapsed {{ display:none; }}
        .buy-item {{ background:rgba(0,0,0,.2); padding:12px; border-radius:10px; border-left:3px solid #ff6b6b; }}
        .buy-item-header {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; }}
        .buy-item-name {{ font-weight:600; color:#fff; }}
        .buy-item-signal {{ font-size:.75rem; padding:2px 8px; border-radius:10px; background:#ff6b6b; color:#fff; }}
        .buy-item-details {{ font-size:.8rem; color:#aaa; margin-bottom:8px; }}
        .buy-item-actions {{ display:flex; gap:8px; }}
        .btn-quick-buy {{ background:linear-gradient(135deg,#ff6b6b,#ee5a5a); color:#fff; border:none; padding:6px 12px; border-radius:6px; font-size:.8rem; cursor:pointer; }}
        .btn-quick-buy:hover {{ transform:scale(1.05); }}
        .btn-view-detail {{ background:rgba(255,255,255,.1); color:#fff; border:none; padding:6px 12px; border-radius:6px; font-size:.8rem; cursor:pointer; }}
        
        /* 信号详情弹窗 */
        .signal-modal {{ position:fixed; top:0; left:0; width:100%; height:100%; z-index:1000; display:flex; align-items:center; justify-content:center; }}
        .modal-overlay {{ position:absolute; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,.7); }}
        .modal-content {{ position:relative; background:linear-gradient(135deg,#1a1f2e,#0f1419); border-radius:15px; width:90%; max-width:600px; max-height:80vh; overflow:auto; border:1px solid rgba(0,212,255,.3); box-shadow:0 20px 60px rgba(0,0,0,.5); }}
        .modal-header {{ display:flex; justify-content:space-between; align-items:center; padding:20px; border-bottom:1px solid rgba(255,255,255,.1); }}
        .modal-header h3 {{ margin:0; color:#00d4ff; }}
        .modal-close {{ background:none; border:none; color:#fff; font-size:1.5rem; cursor:pointer; }}
        .modal-body {{ padding:20px; }}
        .signal-overview {{ display:flex; align-items:center; gap:20px; margin-bottom:20px; }}
        .signal-badge-large {{ padding:10px 20px; border-radius:20px; font-weight:600; font-size:1.1rem; }}
        .signal-badge-large.strong-buy {{ background:rgba(255,50,50,.3); color:#ff6b6b; }}
        .signal-badge-large.buy {{ background:rgba(255,100,100,.3); color:#ff9999; }}
        .signal-badge-large.hold {{ background:rgba(128,128,128,.3); color:#aaa; }}
        .signal-badge-large.risk {{ background:rgba(0,200,0,.3); color:#6bcb77; }}
        .factors-section, .suggestion-section {{ margin-bottom:20px; }}
        .factors-section h4, .suggestion-section h4 {{ color:#00d4ff; margin-bottom:10px; }}
        .factors-table {{ width:100%; border-collapse:collapse; }}
        .factors-table th {{ text-align:left; padding:10px; background:rgba(0,212,255,.1); color:#00d4ff; }}
        .factors-table td {{ padding:10px; border-bottom:1px solid rgba(255,255,255,.05); }}
        .factors-table tr.positive {{ color:#6bcb77; }}
        .factors-table tr.negative {{ color:#ff6b6b; }}
        .factors-table tr.neutral {{ color:#aaa; }}
        
        /* 持仓卖出提示增强 */
        .holding-card.urgent-sell {{ background:linear-gradient(135deg,rgba(255,0,0,.2),rgba(200,0,0,.1)); border-color:#ff4444; animation:urgentPulse 2s infinite; }}
        @keyframes urgentPulse {{ 0%,100%{{box-shadow:0 0 10px rgba(255,0,0,.3)}} 50%{{box-shadow:0 0 20px rgba(255,0,0,.5)}} }}
        .holding-card.suggest-sell {{ background:linear-gradient(135deg,rgba(255,165,0,.15),rgba(200,100,0,.1)); border-color:#ffa500; }}
        .sell-progress {{ height:4px; background:rgba(255,255,255,.1); border-radius:2px; margin-top:8px; overflow:hidden; }}
        .sell-progress-bar {{ height:100%; transition:width .3s; }}
        .sell-progress-bar.high {{ background:linear-gradient(90deg,#ff4444,#ff6666); }}
        .sell-progress-bar.medium {{ background:linear-gradient(90deg,#ffa500,#ffcc00); }}
        .sell-progress-bar.low {{ background:linear-gradient(90deg,#4caf50,#8bc34a); }}
        .badge-strong-sell {{ background:#ff4444; color:#fff; padding:2px 8px; border-radius:4px; font-size:.7rem; animation:blink 1s infinite; }}
        @keyframes blink {{ 0%,100%{{opacity:1}} 50%{{opacity:.6}} }}
        .badge-suggest-sell {{ background:#ffa500; color:#fff; padding:2px 8px; border-radius:4px; font-size:.7rem; }}
        
        /* 卖出按钮 */
        .btn-sell {{ background:linear-gradient(135deg,#4caf50,#45a049); color:#fff; border:none; padding:4px 10px; border-radius:6px; font-size:.75rem; cursor:pointer; margin-right:5px; }}
        .btn-sell:hover {{ transform:scale(1.05); box-shadow:0 2px 8px rgba(76,175,80,.4); }}
        
        /* 信号详情模态框 */
        .modal-large {{ max-width:600px; }}
        .signal-detail-loading {{ text-align:center; padding:40px; color:#888; }}
        .factor-table {{ width:100%; border-collapse:collapse; margin-top:15px; }}
        .factor-table th {{ text-align:left; padding:10px; background:rgba(0,212,255,.1); color:#00d4ff; font-size:.85rem; }}
        .factor-table td {{ padding:10px; border-bottom:1px solid rgba(255,255,255,.1); font-size:.9rem; }}
        .factor-score {{ font-weight:600; }}
        .factor-score.positive {{ color:#4caf50; }}
        .factor-score.negative {{ color:#ff4444; }}
        .factor-reason {{ color:#aaa; font-size:.8rem; }}
        .signal-summary-box {{ background:rgba(0,0,0,.2); padding:15px; border-radius:10px; margin-bottom:20px; }}
        .signal-summary-row {{ display:flex; justify-content:space-between; margin-bottom:8px; }}
        .signal-summary-label {{ color:#888; }}
        .signal-summary-value {{ font-weight:600; }}
        .signal-summary-value.strong-buy {{ color:#ff4444; }}
        .signal-summary-value.buy {{ color:#ff6b6b; }}
        .signal-summary-value.hold {{ color:#888; }}
        .signal-summary-value.risk {{ color:#4caf50; }}
        .add-holding-form {{ background:rgba(255,255,255,.03); border-radius:15px; padding:20px; margin-bottom:20px; border:1px solid rgba(0,212,255,.2); }}
        .form-title {{ font-size:1rem; color:#00d4ff; margin-bottom:15px; }}
        .form-row {{ display:flex; gap:10px; flex-wrap:wrap; align-items:flex-end; }}
        .form-group {{ display:flex; flex-direction:column; gap:5px; }}
        .form-group label {{ font-size:.75rem; color:#7a8fa6; }}
        .form-group input {{ background:rgba(0,0,0,.3); border:1px solid rgba(255,255,255,.1); border-radius:8px; padding:8px 12px; color:#fff; font-size:.9rem; width:120px; }}
        .form-group input.wide {{ width:150px; }}
        .form-group input:focus {{ outline:none; border-color:#00d4ff; }}
        .btn {{ padding:10px 20px; border:none; border-radius:10px; font-size:.9rem; cursor:pointer; font-weight:600; transition:all .2s; }}
        .btn-add {{ background:linear-gradient(135deg,#00d4ff,#0099cc); color:white; }}
        .btn:hover {{ transform:scale(1.05); }}
        .holdings-panel {{ background:rgba(255,255,255,.03); border-radius:15px; padding:15px; margin-bottom:20px; border:1px solid rgba(0,212,255,.2); }}
        .holdings-title {{ font-size:1rem; color:#00d4ff; margin-bottom:10px; display:flex; align-items:center; gap:8px; }}
        .holdings-title .total-profit {{ margin-left:auto; font-size:.9rem; }}
        .holdings-title .total-profit.up {{ color:#ff4757; }}
        .holdings-title .total-profit.down {{ color:#2ed573; }}
        .holdings-list {{ display:flex; flex-wrap:wrap; gap:10px; }}
        .holding-card {{ background:rgba(0,0,0,.3); border-radius:10px; padding:10px 15px; cursor:pointer; border:1px solid rgba(255,255,255,.1); min-width:150px; position:relative; }}
        .holding-card:hover {{ border-color:rgba(0,212,255,.5); }}
        .holding-header {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:5px; gap:6px; }}
        .holding-name {{ font-weight:600; color:#fff; font-size:.9rem; flex:1; }}
        .btn-delete {{ background:rgba(255,71,87,.2); border:1px solid rgba(255,71,87,.4); color:#ff4757; border-radius:6px; width:22px; height:22px; font-size:.75rem; cursor:pointer; display:flex; align-items:center; justify-content:center; flex-shrink:0; transition:all .2s; line-height:1; padding:0; }}
        .btn-delete:hover {{ background:#ff4757; color:white; transform:scale(1.1); }}
        .sell-ready {{ background:#ff4757; color:white; padding:2px 8px; border-radius:10px; font-size:.7rem; }}
        .sell-wait {{ background:rgba(255,255,255,.1); color:#888; padding:2px 8px; border-radius:10px; font-size:.7rem; }}
        .holding-info {{ font-size:.75rem; color:#7a8fa6; margin-bottom:5px; }}
        .holding-info span {{ margin-right:6px; }}
        .holding-profit {{ font-weight:600; font-size:.9rem; }}
        .holding-profit.profit-up {{ color:#ff4757; }}
        .holding-profit.profit-down {{ color:#2ed573; }}
        .btn-stock-report {{ background:linear-gradient(135deg,#6366f1,#8b5cf6); color:white; border:none; border-radius:8px; padding:6px 12px; font-size:.85rem; cursor:pointer; transition:all .2s; }}
        .btn-stock-report:hover {{ transform:scale(1.1); box-shadow:0 4px 15px rgba(99,102,241,.4); }}
        .action-col {{ width:60px; text-align:center; }}
        .sell-signal-badge {{ display:inline-block; margin-top:5px; padding:3px 10px; border-radius:10px; font-size:.72rem; font-weight:700; width:100%; text-align:center; }}
        .sell-sig-strong {{ background:linear-gradient(135deg,#7f1d1d,#ef4444); color:#fff; animation:pulse 1s infinite; }}
        .sell-sig-suggest {{ background:rgba(239,68,68,.2); color:#ef4444; border:1px solid rgba(239,68,68,.5); }}
        .sell-sig-reduce {{ background:rgba(251,191,36,.15); color:#fbbf24; border:1px solid rgba(251,191,36,.4); }}
        .sell-sig-watch {{ background:rgba(148,163,184,.1); color:#94a3b8; border:1px solid rgba(148,163,184,.3); }}
        .sell-sig-hold {{ background:rgba(34,197,94,.1); color:#4ade80; border:1px solid rgba(34,197,94,.3); }}
        .no-holdings {{ color:#7a8fa6; text-align:center; padding:20px; }}
        .table-container {{ background:rgba(255,255,255,.02); border-radius:20px; overflow:hidden; max-height:60vh; overflow-y:auto; }}
        table {{ width:100%; border-collapse:collapse; }}
        th {{ background:rgba(255,107,107,.1); padding:14px 10px; text-align:left; font-weight:600; color:#ff6b6b; font-size:.85rem; position:sticky; top:0; }}
        td {{ padding:12px 10px; border-bottom:1px solid rgba(255,255,255,.03); font-size:.9rem; }}
        tr:hover td {{ background:rgba(255,255,255,.03); }}
        tr.in-holding td {{ background:rgba(0,212,255,.05) !important; }}
        .rank-col {{ width:50px; text-align:center; }}
        .rank-badge {{ display:inline-flex; width:28px; height:28px; border-radius:50%; font-weight:700; font-size:.8rem; align-items:center; justify-content:center; }}
        .rank-1 {{ background:linear-gradient(135deg,#ffd700,#ff8c00); color:#000; }}
        .rank-2 {{ background:linear-gradient(135deg,#c0c0c0,#a8a8a8); color:#000; }}
        .rank-3 {{ background:linear-gradient(135deg,#cd7f32,#b8860b); color:#fff; }}
        .rank-other {{ background:rgba(255,255,255,.08); }}
        .code-col {{ font-family:monospace; color:#7a8fa6; }}
        .name-col {{ font-weight:600; cursor:pointer; }}
        .name-col:hover {{ color:#00d4ff; }}
        .price-col {{ font-family:monospace; }}
        .change-col {{ font-weight:600; font-family:monospace; }}
        .change-col.up {{ color:#ff4757; }}
        .change-col.down {{ color:#2ed573; }}
        .turnover-col,.volume-col {{ color:#7a8fa6; font-size:.85rem; }}
        .signal-col {{ min-width:120px; }}
        .signal-badge {{ display:inline-block; padding:4px 10px; border-radius:15px; font-size:.75rem; font-weight:600; cursor:help; }}
        .ml-proba {{ display:block; font-size:.65rem; color:#a0c4ff; margin-top:2px; opacity:.85; }}
        .signal-strong-buy {{ background:linear-gradient(135deg,#ff4444,#cc0000); color:white; }}
        .signal-buy {{ background:rgba(255,80,80,.8); color:white; }}
        .signal-hold {{ background:rgba(128,128,128,.5); color:#ddd; }}
        .signal-caution {{ background:rgba(255,165,0,.5); color:#ffd700; }}
        .signal-risk {{ background:rgba(0,200,0,.5); color:white; }}
        .strength-stars {{ display:block; font-size:.65rem; color:#ffd700; margin-top:2px; }}
        .owned-badge {{ background:rgba(0,212,255,.3); color:#00d4ff; padding:2px 6px; border-radius:8px; font-size:.65rem; margin-left:5px; }}
        .sell-ready-badge {{ background:#ff4757; color:white; padding:2px 6px; border-radius:8px; font-size:.65rem; margin-left:5px; animation:pulse 1s infinite; }}
        .sell-warning {{ background:#ff4757; color:white; padding:2px 8px; border-radius:8px; font-size:.65rem; margin-left:5px; font-weight:bold; }}
        .sell-row-badge {{ padding:2px 7px; border-radius:8px; font-size:.65rem; margin-left:5px; font-weight:600; }}
        .sell-row-strong  {{ background:rgba(239,68,68,.25); color:#ef4444; border:1px solid rgba(239,68,68,.5); animation:pulse 1s infinite; }}
        .sell-row-suggest {{ background:rgba(249,115,22,.2); color:#f97316; border:1px solid rgba(249,115,22,.4); }}
        .sell-row-reduce  {{ background:rgba(251,191,36,.15); color:#fbbf24; border:1px solid rgba(251,191,36,.3); }}
        .sell-row-watch   {{ background:rgba(148,163,184,.1); color:#94a3b8; border:1px solid rgba(148,163,184,.3); }}
        .sell-row-hold    {{ background:rgba(74,222,128,.1); color:#4ade80; border:1px solid rgba(74,222,128,.3); }}
        .profit-tag {{ font-size:.75rem; margin-left:5px; padding:1px 5px; border-radius:5px; font-weight:600; }}
        .profit-tag.up {{ background:rgba(255,71,87,.2); color:#ff4757; }}
        .profit-tag.down {{ background:rgba(46,213,115,.2); color:#2ed573; }}
        .modal {{ display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,.8); z-index:1000; justify-content:center; align-items:center; }}
        .modal.active {{ display:flex; }}
        .modal-content {{ background:linear-gradient(135deg,#1a2a4a,#0c1929); border-radius:20px; padding:30px; max-width:500px; width:90%; border:1px solid rgba(0,212,255,.3); }}
        .modal-header {{ display:flex; justify-content:space-between; margin-bottom:20px; }}
        .modal-title {{ font-size:1.3rem; color:#fff; }}
        .modal-close {{ background:none; border:none; color:#7a8fa6; font-size:1.5rem; cursor:pointer; }}
        .action-buttons {{ display:flex; gap:10px; margin-top:20px; }}
        .btn-cancel {{ background:rgba(255,255,255,.1); color:#fff; }}
        .btn-danger {{ background:linear-gradient(135deg,#ff4757,#cc0000); color:white; }}
        .footer {{ text-align:center; margin-top:30px; padding:20px; color:#5a6a7a; font-size:.8rem; }}
        .auto-refresh {{ position:fixed; top:20px; right:20px; background:rgba(0,0,0,.6); padding:10px 15px; border-radius:10px; font-size:.8rem; }}

        /* ── 大盘指数 ── */
        .market-indices {{
            display:flex; gap:12px; flex-wrap:wrap; margin-bottom:18px;
            padding:12px 16px; background:rgba(255,255,255,.03);
            border-radius:14px; border:1px solid rgba(255,255,255,.06);
        }}
        .index-item {{
            display:flex; flex-direction:column; align-items:flex-start;
            padding:8px 14px; border-radius:10px; min-width:130px;
            background:rgba(0,0,0,.25); border:1px solid rgba(255,255,255,.07);
            cursor:default; transition:border-color .2s;
        }}
        .index-item:hover {{ border-color:rgba(0,212,255,.3); }}
        .index-name {{ font-size:.7rem; color:#7a8fa6; margin-bottom:3px; letter-spacing:.5px; }}
        .index-price {{ font-size:1.1rem; font-weight:700; font-family:monospace; }}
        .index-change {{ font-size:.75rem; font-weight:600; margin-top:2px; }}
        .index-up .index-price {{ color:#ff4757; }}
        .index-up .index-change {{ color:#ff4757; }}
        .index-down .index-price {{ color:#2ed573; }}
        .index-down .index-change {{ color:#2ed573; }}
        .index-flat .index-price {{ color:#e8e8e8; }}
        .index-flat .index-change {{ color:#7a8fa6; }}
        .index-loading {{ color:#7a8fa6; font-size:.8rem; padding:8px 14px; }}

        /* ── 报告按钮 ── */
        .report-btn-wrap {{ display:flex; align-items:center; gap:10px; }}
        .btn-refresh {{ background:rgba(255,255,255,.1); border:1px solid rgba(255,255,255,.2); color:#fff; padding:10px 15px; border-radius:10px; cursor:pointer; font-size:1.2rem; transition:all .2s; }}
        .btn-refresh:hover {{ background:rgba(255,255,255,.2); transform:rotate(180deg); }}
        .btn-report {{
            background:linear-gradient(135deg,#f59e0b,#d97706);
            color:#fff; border:none; border-radius:10px;
            padding:9px 18px; font-size:.85rem; font-weight:700;
            cursor:pointer; display:flex; align-items:center; gap:6px;
            transition:all .2s; white-space:nowrap;
        }}
        .btn-report:hover {{ transform:scale(1.05); box-shadow:0 4px 15px rgba(245,158,11,.4); }}
        .btn-report:disabled {{ opacity:.6; cursor:not-allowed; transform:none; }}
        .btn-report .spin {{ display:inline-block; animation:spin .8s linear infinite; }}
        @keyframes spin {{ to {{ transform:rotate(360deg); }} }}
        .report-toast {{
            position:fixed; bottom:30px; right:30px; z-index:9999;
            background:rgba(0,0,0,.85); color:#fff; padding:12px 20px;
            border-radius:12px; font-size:.85rem; display:none;
            border:1px solid rgba(245,158,11,.4); max-width:300px;
        }}
        .report-toast.show {{ display:block; animation:fadeIn .3s; }}
        @keyframes fadeIn {{ from{{opacity:0;transform:translateY(10px)}} to{{opacity:1;transform:translateY(0)}} }}

        /* ── Header 布局 ── */
        .header-top {{
            display:flex; align-items:flex-start; justify-content:space-between;
            gap:16px; margin-bottom:16px; flex-wrap:wrap;
        }}
        .header-center {{ flex:1; text-align:center; min-width:200px; }}

        @media (max-width:900px) {{ .turnover-col,.volume-col {{ display:none; }} }}
        @media (max-width:700px) {{ .header-top {{ flex-direction:column; }} .market-indices {{ justify-content:center; }} }}
        /* 新闻提示区域 */
        .news-ticker {{ position:fixed; bottom:20px; right:20px; width:320px; max-height:200px; background:rgba(15,32,39,.95); border:1px solid rgba(255,255,255,.1); border-radius:12px; padding:0; box-shadow:0 8px 32px rgba(0,0,0,.3); z-index:999; font-size:12px; color:#e8e8e8; overflow:hidden; transition:all 0.3s ease; }}
        .news-ticker.collapsed {{ max-height:40px; }}
        .news-ticker::-webkit-scrollbar {{ width:4px; }}
        .news-ticker::-webkit-scrollbar-track {{ background:rgba(255,255,255,.05); border-radius:2px; }}
        .news-ticker::-webkit-scrollbar-thumb {{ background:rgba(255,255,255,.2); border-radius:2px; }}
        .news-ticker::-webkit-scrollbar-thumb:hover {{ background:rgba(255,255,255,.3); }}
        .news-header {{ display:flex; align-items:center; justify-content:space-between; gap:6px; padding:10px 12px; border-bottom:1px solid rgba(255,255,255,.1); font-weight:600; color:#a0c4ff; cursor:pointer; user-select:none; background:rgba(255,255,255,.02); }}
        .news-header:hover {{ background:rgba(255,255,255,.05); }}
        .news-header-left {{ display:flex; align-items:center; gap:6px; }}
        .news-icon {{ font-size:14px; }}
        .news-toggle {{ font-size:12px; color:#7a8fa6; transition:transform 0.3s ease; }}
        .news-ticker.collapsed .news-toggle {{ transform:rotate(-90deg); }}
        .news-content {{ padding:8px 12px; max-height:160px; overflow-y:auto; }}
        .news-item {{ padding:8px 0; border-bottom:1px solid rgba(255,255,255,.05); line-height:1.5; cursor:pointer; transition:all 0.2s ease; }}
        .news-item:last-child {{ border-bottom:none; }}
        .news-item:hover {{ background:rgba(255,255,255,.05); padding-left:4px; }}
        .news-source {{ display:inline-block; background:rgba(255,215,0,.15); color:#ffd700; padding:2px 6px; border-radius:3px; font-size:10px; font-weight:600; margin-right:4px; }}
        .news-time {{ color:#5a6f7f; font-size:11px; margin-left:4px; }}
        .news-title {{ color:#e8e8e8; margin-top:3px; word-break:break-word; font-size:12px; }}
        .news-loading {{ text-align:center; color:#5a6f7f; padding:12px 0; }}
        .news-error {{ color:#ff6b6b; padding:8px 0; }}
    </style>
</head>
<body>
    <div class="auto-refresh">Auto-refresh: 5min | Press R to reload</div>
    <div class="report-toast" id="reportToast"></div>
    <div class="news-ticker" id="newsTicker" style="display:none;">
        <div class="news-header" onclick="toggleNewsTicker()">
            <div class="news-header-left">
                <span class="news-icon">📰</span>
                <span>财经快讯</span>
            </div>
            <span class="news-toggle">▼</span>
        </div>
        <div id="newsContent" class="news-content news-loading">加载中...</div>
    </div>

    <div class="container">
        <div class="header">
            <!-- 三栏布局：大盘指数 | 标题 | 报告按钮 -->
            <div class="header-top">

                <!-- 左：大盘指数 -->
                <div class="market-indices" id="marketIndices">
                    <div class="index-loading">⏳ 加载大盘数据...</div>
                </div>

                <!-- 中：标题 -->
                <div class="header-center">
                    <div class="title">
                        <span class="title-text">Stock Rank + Trading Signals</span>
                        <span class="live-badge">LIVE</span>
                    </div>
                    <div style="color:#7a8fa6;margin-top:6px;font-size:.85rem;">Update: {update_time}</div>
                </div>

                <!-- 右：报告按钮 -->
                <div class="report-btn-wrap">
                    <button class="btn-refresh" onclick="location.reload()" title="手动刷新">
                        🔄
                    </button>
                    <button class="btn-report" id="btnReport" onclick="generateReport()">
                        📄 生成日报
                    </button>
                </div>
            </div>
        </div>

        <div class="disclaimer">
            Signals are for reference only. Not investment advice. Trade at your own risk!
        </div>

        <div class="signal-summary">
            <div class="signal-stat strong-buy"><div class="signal-stat-value">{strong_buy_count}</div><div class="signal-stat-label">Strong Buy</div></div>
            <div class="signal-stat buy"><div class="signal-stat-value">{buy_count}</div><div class="signal-stat-label">Buy</div></div>
            <div class="signal-stat hold"><div class="signal-stat-value">{hold_count}</div><div class="signal-stat-label">Hold/Caution</div></div>
            <div class="signal-stat risk"><div class="signal-stat-value">{risk_count}</div><div class="signal-stat-label">Risk</div></div>
        </div>

        <!-- 买入信号面板 -->
        <div id="buySignalPanel" class="buy-panel">
            <div class="panel-header" onclick="toggleBuyPanel()">
                <span>🔥 今日买入机会 (Top 5)</span>
                <span class="toggle-icon" id="buyPanelToggle">▼</span>
            </div>
            <div id="buySignalList" class="panel-content">
                <!-- 动态填充 -->
            </div>
        </div>

        <div class="add-holding-form">
            <div class="form-title">+ Add Custom Holding</div>
            <div class="form-row">
                <div class="form-group">
                    <label>Stock Code</label>
                    <input type="text" id="addCode" placeholder="e.g. 600519" maxlength="6"
                           oninput="this.value=toHalfWidth(this.value)"
                           onblur="autoFillStockName()">
                </div>
                <div class="form-group">
                    <label>Stock Name</label>
                    <input type="text" id="addName" class="wide" placeholder="Auto-fill or manual">
                </div>
                <div class="form-group">
                    <label>Buy Price (CNY)</label>
                    <input type="number" id="addPrice" placeholder="100.00" step="0.01" min="0">
                </div>
                <div class="form-group">
                    <label>Quantity</label>
                    <input type="number" id="addQty" placeholder="100" min="1">
                </div>
                <div class="form-group">
                    <label>Buy Date</label>
                    <input type="date" id="addDate" class="wide">
                </div>
                <button class="btn btn-add" onclick="addHolding()">Add</button>
            </div>
        </div>

        <div class="holdings-panel">
            <div class="holdings-title">
                <span>Portfolio ({len(holdings)} stocks)</span>
                <span class="total-profit {profit_cls_total}">{profit_display} CNY</span>
            </div>
            <div class="holdings-list">{holdings_html}</div>
        </div>

        <div class="table-container">
            <table>
                <thead>
                    <tr><th>#</th><th>Code</th><th>Name</th><th>Price</th><th>Change</th><th>Turnover</th><th>Volume</th><th>Signal</th><th>Report</th></tr>
                </thead>
                <tbody>{stock_rows}</tbody>
            </table>
        </div>

        <div class="footer">
            <p>Source: EastMoney Guba | T+1 Trading Rules Apply | Signals for reference only</p>
        </div>
    </div>

    <div class="modal" id="holdingModal">
        <div class="modal-content">
            <div class="modal-header">
                <span class="modal-title">Portfolio Detail</span>
                <button class="modal-close" onclick="closeModal()">&times;</button>
            </div>
            <div class="modal-body" id="modalBody"></div>
        </div>
    </div>

    <script>
{js_code}
    </script>
</body>
</html>'''

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"Generated: {output_file}")


def main():
    base_dir    = Path(__file__).parent
    signals_file = base_dir / "output" / "signals_latest.json"
    stocks_file  = base_dir / "output" / "hot_stocks.json"
    output_file  = base_dir / "output" / "index.html"

    if signals_file.exists() and stocks_file.exists():
        generate_page(signals_file, stocks_file, output_file)
    else:
        print("Data files not found. Run fetch_hot_stocks.py first.")


if __name__ == "__main__":
    main()

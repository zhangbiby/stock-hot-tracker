import json
import sys
sys.path.insert(0, '.')
from server import _build_report_html
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = Path('output')

# 加载最新数据
with open(OUTPUT_DIR / 'hot_stocks.json', 'r', encoding='utf-8') as f:
    stocks = json.load(f).get('stocks', [])

with open(OUTPUT_DIR / 'signals_latest.json', 'r', encoding='utf-8') as f:
    signals = json.load(f).get('signals', [])

print(f"Loaded {len(stocks)} stocks, {len(signals)} signals")

# 生成报告
html = _build_report_html(stocks, signals)

# 保存
today = datetime.now().strftime('%Y%m%d')
report_file = OUTPUT_DIR / f'daily_report_{today}.html'
with open(report_file, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"Report saved: {report_file}")
print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

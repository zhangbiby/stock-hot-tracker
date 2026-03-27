# Test encoding
from pathlib import Path
import json

BASE_DIR = Path('.')
OUTPUT_DIR = BASE_DIR / 'output'

# Read data
with open(OUTPUT_DIR / 'hot_stocks.json', 'r', encoding='utf-8') as f:
    stocks_data = json.load(f)
stocks = stocks_data.get('stocks', [])

print('Loaded', len(stocks), 'stocks')
print('Sample:')
for s in stocks[:3]:
    print(' ', s.get('code'), ':', s.get('name'))

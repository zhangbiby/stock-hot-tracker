with open('output/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Check for key elements
checks = [
    ('深证成指', 'Shenzhen Index'),
    ('btn-stock-report', 'Report Button Style'),
    ('generateStockReport', 'Report Function'),
    ('📊', 'Report Icon'),
]

print('Content check:')
for keyword, desc in checks:
    found = keyword in content
    status = 'OK' if found else 'MISSING'
    print(f'  {desc}: {status}')

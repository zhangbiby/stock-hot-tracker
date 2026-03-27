import json
from portfolio import Portfolio

portfolio = Portfolio()
holdings = portfolio.get_holdings_with_status()

print(f'Total holdings: {len(holdings)}')

for h in holdings:
    print(f"\n{h.get('code')} {h.get('name')}")
    print(f"  Buy price: {h.get('buy_price')}")
    print(f"  Quantity: {h.get('quantity')}")
    print(f"  Can sell: {h.get('can_sell')}")
    print(f"  Sell status: {h.get('sell_status')}")

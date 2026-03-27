from portfolio import Portfolio

portfolio = Portfolio()
holdings = portfolio.get_holdings_with_status()

print(f'Total holdings: {len(holdings)}')

for h in holdings:
    print(f"\n{h.get('code')} {h.get('name')}")
    print(f"  buy_price: {h.get('buy_price')}")
    print(f"  quantity: {h.get('quantity')}")
    print(f"  buy_date: {h.get('buy_date')}")
    print(f"  can_sell: {h.get('can_sell')}")
    print(f"  sell_status: {h.get('sell_status')}")

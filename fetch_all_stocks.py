#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重新抓取全A股名称，正确处理编码
腾讯财经返回 GBK，需先 decode('gbk') 再存为 UTF-8
"""
import json, urllib.request, urllib.parse, os, sys

def generate_codes():
    codes = []
    # 沪市: 600000-605999, 688000-688999
    for i in range(600000, 606000): codes.append(str(i))
    for i in range(688000, 689000): codes.append(str(i))
    # 深市主板: 000001-003999
    for i in range(1, 4000): codes.append(f"{i:06d}")
    # 创业板: 300000-301999
    for i in range(300000, 302000): codes.append(str(i))
    return codes

def fetch_batch(codes):
    """批量查询，腾讯财经返回 GBK 编码"""
    q_list = []
    for code in codes:
        q_list.append(f"sh{code}" if code.startswith('6') else f"sz{code}")
    
    url = "https://web.sqt.gtimg.cn/q=" + ",".join(q_list)
    results = {}
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as r:
            # 腾讯财经返回 GBK，必须用 gbk 解码
            content = r.read().decode('gbk', errors='ignore')
        
        for line in content.split(';'):
            line = line.strip()
            if '~' not in line or '=' not in line:
                continue
            try:
                eq = line.find('=')
                data = line[eq+1:].strip('"')
                parts = data.split('~')
                if len(parts) >= 3:
                    code = parts[2]
                    name = parts[1]
                    if code.isdigit() and len(code) == 6 and name:
                        results[code] = name
            except:
                continue
    except Exception as e:
        pass
    
    return results

def main():
    print("Generating codes...")
    all_codes = generate_codes()
    print(f"Total codes: {len(all_codes)}")
    
    all_stocks = {}
    batch_size = 150
    total = (len(all_codes) + batch_size - 1) // batch_size
    
    for i in range(0, len(all_codes), batch_size):
        batch = all_codes[i:i+batch_size]
        n = i // batch_size + 1
        stocks = fetch_batch(batch)
        all_stocks.update(stocks)
        sys.stderr.write(f"\rBatch {n}/{total} | Found: {len(all_stocks)}")
        sys.stderr.flush()
    
    print(f"\nTotal found: {len(all_stocks)}")
    
    # 验证几个已知股票
    tests = {'000001': '平安银行', '600519': '贵州茅台', '002079': '苏州固锝', '601016': '节能风电', '300676': '艾为电子'}
    print("\nVerification:")
    for code, expected in tests.items():
        got = all_stocks.get(code, 'NOT FOUND')
        ok = "OK" if got == expected else f"GOT: {got}"
        print(f"  {code} {expected}: {ok}")
    
    # 排序保存
    sorted_map = dict(sorted(all_stocks.items()))
    os.makedirs("output", exist_ok=True)
    
    with open("output/stock_name_map.json", 'w', encoding='utf-8') as f:
        json.dump(sorted_map, f, ensure_ascii=False, indent=2)
    
    print(f"\nSaved {len(sorted_map)} stocks to output/stock_name_map.json")

if __name__ == "__main__":
    main()

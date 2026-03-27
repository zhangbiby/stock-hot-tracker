#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fetch financial news from multiple RSS/API sources
Sources: 财联社, 新浪财经, 同花顺, 人民网, 东方财富
"""

import json
import sys
import re
import requests
from datetime import datetime
from pathlib import Path

if sys.platform == 'win32':
    try:
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
    except:
        pass

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9',
}
TIMEOUT = 8


def clean_html(text):
    """去除 HTML 标签"""
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)
    text = re.sub(r'&quot;', '"', text)
    return text.strip()


def parse_rss(url, source_name, max_items=5):
    """通用 RSS 解析"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.encoding = 'utf-8'
        content = resp.text

        # 提取 <item> 块
        items = re.findall(r'<item>(.*?)</item>', content, re.DOTALL)
        news_list = []

        for item in items[:max_items]:
            # 提取标题
            title_match = re.search(r'<title><!\[CDATA\[(.*?)\]\]></title>', item, re.DOTALL)
            if not title_match:
                title_match = re.search(r'<title>(.*?)</title>', item, re.DOTALL)
            if not title_match:
                continue
            title = clean_html(title_match.group(1)).strip()
            if not title or len(title) < 5:
                continue

            # 提取时间
            pub_match = re.search(r'<pubDate>(.*?)</pubDate>', item)
            if pub_match:
                try:
                    from email.utils import parsedate
                    from time import mktime
                    t = parsedate(pub_match.group(1))
                    if t:
                        dt = datetime.fromtimestamp(mktime(t))
                        time_str = dt.strftime('%H:%M')
                    else:
                        time_str = datetime.now().strftime('%H:%M')
                except:
                    time_str = datetime.now().strftime('%H:%M')
            else:
                time_str = datetime.now().strftime('%H:%M')

            news_list.append({
                'source': source_name,
                'title': title[:80],
                'time': time_str
            })

        return news_list
    except Exception as e:
        print(f'[{source_name}] RSS error: {e}')
        return []


def fetch_sina_finance_news():
    """新浪财经 RSS"""
    return parse_rss(
        'https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2516&k=&num=10&page=1&r=0.1',
        '新浪财经',
        max_items=5
    )


def fetch_sina_finance_rss():
    """新浪财经 RSS 备用"""
    try:
        url = 'https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2516&num=10&page=1'
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.encoding = 'utf-8'
        data = resp.json()

        news_list = []
        result = data.get('result', {}).get('data', [])
        for item in result[:5]:
            title = item.get('title', '').strip()
            if not title:
                continue
            # 时间戳转换
            ts = item.get('ctime', 0)
            if ts:
                try:
                    dt = datetime.fromtimestamp(int(ts))
                    time_str = dt.strftime('%H:%M')
                except:
                    time_str = datetime.now().strftime('%H:%M')
            else:
                time_str = datetime.now().strftime('%H:%M')

            news_list.append({
                'source': '新浪财经',
                'title': title[:80],
                'time': time_str
            })
        return news_list
    except Exception as e:
        print(f'[新浪财经] API error: {e}')
        return []


def fetch_eastmoney_news():
    """东方财富快讯"""
    try:
        url = 'https://np-anotice-stock.eastmoney.com/api/security/ann?sr=-1&page_size=10&page_index=1&ann_type=A&client_source=web'
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.encoding = 'utf-8'
        data = resp.json()

        news_list = []
        items = data.get('data', {}).get('list', [])
        for item in items[:5]:
            title = item.get('title', '').strip()
            if not title:
                continue
            # 时间
            notice_date = item.get('notice_date', '')
            if notice_date and len(notice_date) >= 16:
                time_str = notice_date[11:16]
            else:
                time_str = datetime.now().strftime('%H:%M')

            news_list.append({
                'source': '东方财富',
                'title': title[:80],
                'time': time_str
            })
        return news_list
    except Exception as e:
        print(f'[东方财富] error: {e}')
        return []


def fetch_cailian_news():
    """财联社快讯（通过东方财富接口）"""
    try:
        url = 'https://np-cmsapi.eastmoney.com/api/cls/telegraph?category=&page_size=10&page_index=1&client_source=web'
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.encoding = 'utf-8'
        data = resp.json()

        news_list = []
        items = data.get('data', {}).get('roll_data', [])
        for item in items[:5]:
            title = item.get('title', '').strip()
            content = item.get('content', '').strip()
            text = title or content[:60]
            if not text:
                continue
            # 时间戳
            ts = item.get('ctime', 0)
            if ts:
                try:
                    dt = datetime.fromtimestamp(int(ts))
                    time_str = dt.strftime('%H:%M')
                except:
                    time_str = datetime.now().strftime('%H:%M')
            else:
                time_str = datetime.now().strftime('%H:%M')

            news_list.append({
                'source': '财联社',
                'title': text[:80],
                'time': time_str
            })
        return news_list
    except Exception as e:
        print(f'[财联社] error: {e}')
        return []


def fetch_ths_news():
    """同花顺快讯"""
    try:
        url = 'https://news.10jqka.com.cn/tapp/news/push/stock/?page=1&tag=&track=website&pagesize=10'
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.encoding = 'utf-8'
        data = resp.json()

        news_list = []
        items = data.get('data', {}).get('list', [])
        for item in items[:5]:
            title = item.get('title', '').strip()
            if not title:
                continue
            # 时间
            ctime = item.get('ctime', '')
            if ctime and len(ctime) >= 16:
                time_str = ctime[11:16]
            else:
                time_str = datetime.now().strftime('%H:%M')

            news_list.append({
                'source': '同花顺',
                'title': title[:80],
                'time': time_str
            })
        return news_list
    except Exception as e:
        print(f'[同花顺] error: {e}')
        return []


def fetch_people_finance_rss():
    """人民网财经 RSS"""
    return parse_rss(
        'http://finance.people.com.cn/rss/finance.xml',
        '人民网',
        max_items=3
    )


def fetch_all_news():
    """采集所有新闻源，合并去重"""
    all_news = []

    print('Fetching news from multiple sources...')

    # 按优先级采集
    sources = [
        ('财联社', fetch_cailian_news),
        ('新浪财经', fetch_sina_finance_rss),
        ('东方财富', fetch_eastmoney_news),
        ('同花顺', fetch_ths_news),
        ('人民网', fetch_people_finance_rss),
    ]

    for name, func in sources:
        try:
            items = func()
            print(f'  [{name}] {len(items)} items')
            all_news.extend(items)
        except Exception as e:
            print(f'  [{name}] failed: {e}')

    # 去重（按标题）
    seen = set()
    unique_news = []
    for news in all_news:
        key = news['title'][:30]  # 前30字去重
        if key not in seen and len(news['title']) > 5:
            seen.add(key)
            unique_news.append(news)

    # 最多保留 15 条
    unique_news = unique_news[:15]

    # 保存
    output = {
        'timestamp': datetime.now().isoformat(),
        'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'count': len(unique_news),
        'news': unique_news
    }

    news_file = OUTPUT_DIR / 'news_latest.json'
    with open(news_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f'✅ Total: {len(unique_news)} news items saved')
    return unique_news


if __name__ == '__main__':
    news = fetch_all_news()
    print('\n--- Preview ---')
    for n in news[:5]:
        print(f"[{n['source']}] {n['time']} {n['title']}")

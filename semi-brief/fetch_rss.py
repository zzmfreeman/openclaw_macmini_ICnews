#!/usr/bin/env python3
"""RSS 聚合抓取模块 - 替代 NewsAPI"""
import os, sys, json, re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import xml.etree.ElementTree as ET
import urllib.request, ssl

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

RSS_SOURCES = [
    # 国内源（部分可能403）
    {"name": "集微网", "url": "https://rsshub.app/jiwei/news", "region": "domestic", "lang": "zh"},
    {"name": "财联社电报", "url": "https://rsshub.app/cls/telegraph", "region": "domestic", "lang": "zh"},
    {"name": "36氪-半导体", "url": "https://rsshub.app/36kr/search/article/半导体", "region": "domestic", "lang": "zh"},
    
    # 国外源
    {"name": "SemiEngineering", "url": "https://semiengineering.com/feed/", "region": "overseas", "lang": "en"},
    {"name": "EE Times", "url": "https://www.eetimes.com/rss.xml", "region": "overseas", "lang": "en"},
    {"name": "AnandTech", "url": "https://www.anandtech.com/rss/", "region": "overseas", "lang": "en"},
    {"name": "Tom's Hardware", "url": "https://www.tomshardware.com/feeds/all", "region": "overseas", "lang": "en"},
    
    # Nitter (Twitter/X 镜像)
    {"name": "Twitter-TSMC", "url": "https://nitter.net/tsmccorp/rss", "region": "overseas", "lang": "en"},
    {"name": "Twitter-SamsungSemi", "url": "https://nitter.net/SamsungSemiUS/rss", "region": "overseas", "lang": "en"},
    {"name": "Twitter-Intel", "url": "https://nitter.net/intel/rss", "region": "overseas", "lang": "en"},
    {"name": "Twitter-AMD", "url": "https://nitter.net/AMD/rss", "region": "overseas", "lang": "en"},
    {"name": "Twitter-NVIDIA", "url": "https://nitter.net/nvidia/rss", "region": "overseas", "lang": "en"},
    {"name": "Twitter-ASML", "url": "https://nitter.net/ASML/rss", "region": "overseas", "lang": "en"},
]

KEYWORDS = ["芯片", "半导体", "晶圆", "代工", "台积电", "TSMC", "三星", "Samsung", "中芯", "SMIC", "光刻", "EDA", "封装", "Chiplet", "chip", "semiconductor", "wafer", "foundry", "lithography", "process", "nm", "Intel", "AMD", "NVIDIA", "ASML"]

def fetch_rss(url: str) -> Optional[str]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15, context=ssl_context) as resp:
            return resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"[RSS] 失败 {url}: {e}", file=sys.stderr)
        return None

def parse_rss(xml: str, src: Dict) -> List[Dict]:
    items = []
    try:
        root = ET.fromstring(xml)
        if root.tag == "rss":
            channel = root.find("channel")
            if channel is None:
                return items
            for item in channel.findall("item"):
                title = item.findtext("title", "").strip()
                link = item.findtext("link", "").strip()
                desc = item.findtext("description", "")[:300]
                pub = item.findtext("pubDate", "")
                items.append({
                    "title": title,
                    "url": link,
                    "summary": desc,
                    "published": pub,
                    "source": src["name"],
                    "region": src["region"],
                    "lang": src["lang"]
                })
    except Exception as e:
        print(f"[RSS] 解析失败 {src['name']}: {e}", file=sys.stderr)
    return items

def fetch_all(slot: str = "midday", window: int = 6, target: int = 5) -> Dict:
    print(f"[RSS] slot={slot}, window={window}h", file=sys.stderr)
    all_items = []
    for src in RSS_SOURCES:
        xml = fetch_rss(src["url"])
        if xml:
            items = parse_rss(xml, src)
            print(f"[RSS] {src['name']}: {len(items)}条", file=sys.stderr)
            all_items.extend(items)
        else:
            print(f"[RSS] {src['name']}: 失败", file=sys.stderr)
    
    # 去重
    seen = set()
    unique = [i for i in all_items if not (i["url"] in seen or seen.add(i["url"]))]
    
    # 关键词过滤
    filtered = [i for i in unique if any(k.lower() in f"{i['title']} {i['summary']}".lower() for k in KEYWORDS)]
    
    print(f"[RSS] 去重后: {len(unique)}条, 关键词过滤: {len(filtered)}条", file=sys.stderr)
    return {"items": filtered[:target], "slot": slot, "count": len(filtered[:target])}

if __name__ == "__main__":
    result = fetch_all()
    print(json.dumps(result, ensure_ascii=False, indent=2))

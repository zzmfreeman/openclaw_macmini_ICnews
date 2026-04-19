#!/usr/bin/env python3
"""Collect and parse all semi-brief news sources into a unified raw JSON."""
import json, os, re, xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

WORK = "/tmp/semi_brief_work"
os.makedirs(WORK, exist_ok=True)

items = []

BLACKLIST_DOMAINS = ["globenewswire.com", "prnewswire.com", "digitimes.com"]

def is_blacklisted(url):
    for d in BLACKLIST_DOMAINS:
        if d in url:
            return True
    return False

# --- NewsAPI ---
for fn in ["newsapi_fab.json", "newsapi_design.json", "newsapi_eda.json"]:
    fp = os.path.join(WORK, fn)
    try:
        with open(fp) as f:
            d = json.load(f)
        for a in d.get("articles", []):
            url = a.get("url", "")
            if is_blacklisted(url):
                continue
            pub = a.get("publishedAt", "")
            title = a.get("title", "")
            if not title or title == "[Removed]":
                continue
            desc = a.get("description", "") or ""
            src = a.get("source", {}).get("name", "") or "NewsAPI"
            items.append({
                "title": title, "url": url, "published": pub,
                "description": desc, "source": src, "source_type": "NewsAPI"
            })
    except Exception as e:
        print(f"Error reading {fn}: {e}")

# --- Serper ---
for fn in ["serper_fab.json", "serper_cn.json", "serper_finance.json", "serper_en.json"]:
    fp = os.path.join(WORK, fn)
    try:
        with open(fp) as f:
            d = json.load(f)
        for a in d.get("news", []):
            url = a.get("link", "")
            if is_blacklisted(url):
                continue
            title = a.get("title", "")
            pub = a.get("date", "")
            desc = a.get("snippet", "") or ""
            items.append({
                "title": title, "url": url, "published": pub,
                "description": desc, "source": "Serper", "source_type": "Serper"
            })
    except Exception as e:
        print(f"Error reading {fn}: {e}")

# --- SerpAPI Baidu ---
BAIDU_SKIP = ["baike.baidu", "b2b.baidu", "wenku.baidu", "tieba.baidu", "zhidao.baidu",
              "baby.baidu", "stock.baidu", "trading.baidu", "haokan.baidu"]

for fn in ["serpapi_baidu1.json", "serpapi_baidu2.json"]:
    fp = os.path.join(WORK, fn)
    try:
        with open(fp) as f:
            d = json.load(f)
        for a in d.get("organic_results", []):
            url = a.get("link", "")
            skip = False
            for s in BAIDU_SKIP:
                if s in url:
                    skip = True
                    break
            if skip or is_blacklisted(url):
                continue
            title = a.get("title", "")
            desc = a.get("snippet", "") or ""
            items.append({
                "title": title, "url": url, "published": "",
                "description": desc, "source": "SerpAPI/Baidu", "source_type": "SerpAPI"
            })
    except Exception as e:
        print(f"Error reading {fn}: {e}")

# --- RSS feeds (XML) ---
def parse_rss_xml(fp, source_name):
    result = []
    try:
        with open(fp, "rb") as f:
            content = f.read()
        if len(content) < 100:
            return result
        root = ET.fromstring(content)
        channel = root.find("channel")
        if channel is None:
            return result
        for item in channel.findall("item"):
            title = item.findtext("title") or ""
            link = item.findtext("link") or ""
            pub = item.findtext("pubDate") or ""
            desc_el = item.find("description")
            desc = (desc_el.text or "")[:200] if desc_el is not None else ""
            if is_blacklisted(link):
                continue
            result.append({
                "title": title, "url": link, "published": pub,
                "description": desc, "source": source_name, "source_type": "RSS"
            })
    except Exception as e:
        print(f"Error parsing RSS {fp}: {e}")
    return result

for xml_fn, src_name in [
    ("rss_semiwiki.json", "SemiWiki"),   # saved as .json but is xml content
    ("rss_wccftech.json", "WCCFtech"),
    ("rss_spectrum.xml", "IEEE Spectrum"),
]:
    fp = os.path.join(WORK, xml_fn)
    items.extend(parse_rss_xml(fp, src_name))

# Also try the original .json files if they contain RSS xml
for json_fn, src_name in [
    ("rss_semiwiki.json", "SemiWiki"),
    ("rss_wccftech.json", "WCCFtech"),
]:
    fp = os.path.join(WORK, json_fn)
    items.extend(parse_rss_xml(fp, src_name))

# --- Brave Search ---
for fn in ["brave_1.json", "brave_2.json", "brave_3.json"]:
    fp = os.path.join(WORK, fn)
    try:
        with open(fp) as f:
            d = json.load(f)
        for a in d.get("web", {}).get("results", []):
            url = a.get("url", "")
            if is_blacklisted(url):
                continue
            title = a.get("title", "")
            pub = a.get("age", "") or ""
            desc = a.get("description", "") or ""
            items.append({
                "title": title, "url": url, "published": pub,
                "description": desc[:200], "source": "Brave", "source_type": "Brave"
            })
    except Exception as e:
        print(f"Error reading {fn}: {e}")

print(f"Total raw items collected: {len(items)}")
# Source breakdown
from collections import Counter
c = Counter(i.get("source_type","unknown") for i in items)
for k,v in c.items():
    print(f"  {k}: {v}")

with open("/tmp/semi_brief_raw.json", "w") as f:
    json.dump(items, f, ensure_ascii=False, indent=2)
print("Saved to /tmp/semi_brief_raw.json")

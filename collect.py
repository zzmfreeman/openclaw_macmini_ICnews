import json, urllib.request, urllib.parse, xml.etree.ElementTree as ET, ssl, datetime

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

results = []

def fetch(url, headers=None, data=None, timeout=30):
    req = urllib.request.Request(url, headers=headers or {})
    if data:
        req.data = json.dumps(data).encode() if isinstance(data, dict) else data.encode()
        req.add_header('Content-Type', 'application/json')
    try:
        resp = urllib.request.urlopen(req, timeout=timeout, context=ctx)
        return resp.read().decode('utf-8', errors='replace')
    except Exception as e:
        print(f"  FETCH ERROR {url[:80]}: {e}")
        return None

blacklist_domains = ["globenewswire.com", "prnewswire.com", "digitimes.com"]

# ---- A. NewsAPI ----
from_time_newsapi = "2026-04-26T12:00:00Z"
api_key = "33d2998e031444a2aa69acb28bed547c"
newsapi_queries = [
    "semiconductor+foundry+OR+wafer+OR+TSMC+OR+Samsung+foundry+OR+Intel+foundry",
    "fabless+OR+chip+design+OR+Qualcomm+OR+AMD+OR+MediaTek+OR+Marvell+OR+Broadcom+semiconductor",
    "EDA+OR+electronic+design+automation+OR+chip+IP+OR+Synopsys+OR+Cadence+OR+Arm+RISC-V"
]
for q in newsapi_queries:
    url = f"https://newsapi.org/v2/everything?q={q}&sortBy=publishedAt&language=en&pageSize=20&from={from_time_newsapi}&apiKey={api_key}"
    raw = fetch(url)
    if raw:
        try:
            data = json.loads(raw)
            for art in data.get("articles", []):
                u = art.get("url","")
                if any(bl in u for bl in blacklist_domains): continue
                if not u: continue
                results.append({"title": art.get("title",""), "url": u, "summary": (art.get("description","") or "")[:300], "source": "NewsAPI", "published": art.get("publishedAt","")})
        except Exception as ex: print(f"  NewsAPI parse error: {ex}")
na_count = len([r for r in results if r["source"]=="NewsAPI"])
print(f"NewsAPI: {na_count}")

# ---- B. Serper ----
serper_key = "f4dd8bc7f76655c990f4777dcd6549f4d536d893"
serper_queries = [
    {"q":"半导体 芯片 晶圆 封测 最新","gl":"cn","hl":"zh-cn","num":10,"tbs":"qdr:d"},
    {"q":"中芯国际 华虹 长鑫 EDA 设计公司 最新","gl":"cn","hl":"zh-cn","num":10,"tbs":"qdr:d"},
    {"q":"半导体 投资 并购 上市 融资 2026","gl":"cn","hl":"zh-cn","num":10,"tbs":"qdr:d"},
    {"q":"semiconductor foundry chip investment acquisition 2026","gl":"cn","hl":"zh-cn","num":10,"tbs":"qdr:d"}
]
for payload in serper_queries:
    raw = fetch("https://google.serper.dev/news", headers={"X-API-KEY": serper_key}, data=payload)
    if raw:
        try:
            data = json.loads(raw)
            for art in data.get("news", []):
                u = art.get("link","")
                if any(bl in u for bl in blacklist_domains): continue
                if not u: continue
                results.append({"title": art.get("title",""), "url": u, "summary": art.get("snippet",""), "source": "Serper", "published": art.get("date","")})
        except: pass
sp_count = len([r for r in results if r["source"]=="Serper"])
print(f"Serper: {sp_count}")

# ---- C. Exa ----
exa_key = "2fc36c68-6552-49be-9127-94cb8609d47c"
from_date_exa = "2026-04-26T00:00:00.000Z"
exa_queries = [
    {"query":"semiconductor foundry fab capacity yield expansion latest news","type":"neural","numResults":10,"startPublishedDate":from_date_exa,"contents":{"text":{"maxCharacters":300}}},
    {"query":"芯片 半导体 代工 封测 晶圆 最新进展","type":"neural","numResults":10,"startPublishedDate":from_date_exa,"contents":{"text":{"maxCharacters":300}}},
    {"query":"EDA IP chip design fabless acquisition investment","type":"neural","numResults":10,"startPublishedDate":from_date_exa,"contents":{"text":{"maxCharacters":300}}}
]
for payload in exa_queries:
    raw = fetch("https://api.exa.ai/search", headers={"x-api-key": exa_key, "User-Agent": "Mozilla/5.0", "Origin": "https://api.exa.ai"}, data=payload)
    if raw:
        try:
            data = json.loads(raw)
            for art in data.get("results", []):
                u = art.get("url","")
                if any(bl in u for bl in blacklist_domains): continue
                if not u: continue
                results.append({"title": art.get("title",""), "url": u, "summary": (art.get("text","") or "")[:300], "source": "Exa", "published": art.get("publishedDate","")})
        except: pass
ex_count = len([r for r in results if r["source"]=="Exa"])
print(f"Exa: {ex_count}")

# ---- D. RSS ----
rss_feeds = [
    "https://semiwiki.com/feed/",
    "https://wccftech.com/feed/",
    "https://www.eetimes.com/rss/",
    "https://spectrum.ieee.org/rss/",
    "https://www.electronicsweekly.com/rss/"
]
for feed_url in rss_feeds:
    raw = fetch(feed_url)
    if raw:
        try:
            root = ET.fromstring(raw)
            source_name = feed_url.split('/')[2]
            for item in root.findall('.//item'):
                link = item.find('link')
                title_el = item.find('title')
                desc_el = item.find('description')
                pub_el = item.find('pubDate')
                u = link.text if link is not None and link.text else ""
                if any(bl in u for bl in blacklist_domains): continue
                if not u: continue
                results.append({
                    "title": title_el.text if title_el is not None else "",
                    "url": u,
                    "summary": (desc_el.text[:300] if desc_el is not None and desc_el.text else ""),
                    "source": f"RSS-{source_name}",
                    "published": pub_el.text if pub_el is not None else ""
                })
        except Exception as e:
            print(f"  RSS parse error {feed_url}: {e}")
rss_count = len([r for r in results if r["source"].startswith("RSS")])
print(f"RSS: {rss_count}")

# ---- E. Brave Search ----
brave_key = "BSAZM4BK5rloHV8rrP42PpF1NW5tbhF"
brave_queries = [
    "semiconductor fab capacity yield 2026",
    "chip equipment EDA IP acquisition",
    "芯片 设计 公司 融资 上市 最新"
]
for q in brave_queries:
    encoded = urllib.parse.quote(q)
    url = f"https://api.search.brave.com/res/v1/web/search?q={encoded}&freshness=pd&count=10"
    raw = fetch(url, headers={"Accept": "application/json", "Accept-Encoding": "gzip", "X-Subscription-Token": brave_key})
    if raw:
        try:
            data = json.loads(raw)
            for art in data.get("web", {}).get("results", []):
                u = art.get("url", "")
                if any(bl in u for bl in blacklist_domains): continue
                if not u: continue
                results.append({"title": art.get("title",""), "url": u, "summary": (art.get("description","") or "")[:300], "source": "Brave", "published": art.get("page_age","") or ""})
        except: pass
br_count = len([r for r in results if r["source"]=="Brave"])
print(f"Brave: {br_count}")

with open("/tmp/semi_brief_raw.json", "w") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"\nTotal raw items: {len(results)}")

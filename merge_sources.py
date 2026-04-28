import json, re, xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

CST = timezone(timedelta(hours=8))
now_cst = datetime.now(CST)
items = []

def add_item(title, url, source, published, summary="", src_type=""):
    for bl in ["digitimes.com", "globenewswire.com", "prnewswire.com"]:
        if bl in url:
            return
    if not title or not url:
        return
    items.append({
        "title": title.strip(),
        "url": url.strip(),
        "source": source.strip(),
        "published": published,
        "summary": summary.strip() if summary else "",
        "src_type": src_type
    })

for fn in ["newsapi_1.json", "newsapi_2.json", "newsapi_3.json"]:
    try:
        with open(f"/tmp/{fn}") as f:
            d = json.load(f)
        for a in d.get("articles", []):
            t = a.get("title","")
            u = a.get("url","")
            p = a.get("publishedAt","")
            s = a.get("source",{}).get("name","NewsAPI")
            desc = a.get("description","") or ""
            add_item(t, u, s, p, desc, "NewsAPI")
    except: pass

for fn in ["serper_1.json", "serper_2.json", "serper_3.json", "serper_4.json"]:
    try:
        with open(f"/tmp/{fn}") as f:
            d = json.load(f)
        for a in d.get("news", []):
            t = a.get("title","")
            u = a.get("link","")
            p = a.get("date","")
            s = a.get("source","") or "Serper"
            snip = a.get("snippet","") or ""
            add_item(t, u, s, p, snip, "Serper")
    except: pass

for fn in ["exa_1.json", "exa_2.json", "exa_3.json"]:
    try:
        with open(f"/tmp/{fn}") as f:
            d = json.load(f)
        for r in d.get("results", []):
            t = r.get("title","")
            u = r.get("url","")
            p = r.get("publishedDate","") or ""
            txt = ""
            if r.get("contents") and r["contents"].get("text"):
                txt = r["contents"]["text"][:300]
            add_item(t, u, "Exa", p, txt, "Exa")
    except: pass

def parse_rss(fn, src_name):
    try:
        with open(f"/tmp/{fn}") as f:
            content = f.read()
        root = ET.fromstring(content)
        for item in root.iter("item"):
            t = ""
            u = ""
            p = ""
            desc = ""
            for child in item:
                tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                if tag == "title": t = child.text or ""
                elif tag == "link": u = child.text or ""
                elif tag == "pubDate": p = child.text or ""
                elif tag in ("description", "content_encoded"):
                    desc = (child.text or "")[:300]
            add_item(t, u, src_name, p, desc, "RSS")
    except Exception as e:
        print(f"RSS parse error for {fn}: {e}")

parse_rss("rss_semiwiki.xml", "SemiWiki")
parse_rss("rss_wccftech.xml", "WCCFtech")

for fn in ["brave_1.json", "brave_2.json", "brave_3.json"]:
    try:
        with open(f"/tmp/{fn}") as f:
            d = json.load(f)
        for r in d.get("web", {}).get("results", []):
            t = r.get("title","")
            u = r.get("url","")
            p = r.get("page_age","") or r.get("age","") or ""
            s = r.get("source","") or "Brave"
            desc = r.get("description","") or ""
            add_item(t, u, s, p, desc, "Brave")
    except: pass

print(f"Total raw items: {len(items)}")
srcs = {}
for i in items:
    srcs[i["src_type"]] = srcs.get(i["src_type"], 0) + 1
print(f"By source: {srcs}")

with open("/tmp/semi_brief_raw.json", "w") as f:
    json.dump(items, f, ensure_ascii=False, indent=2)

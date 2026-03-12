#!/usr/bin/env python3
"""
fetch.py — NewsAPI 采集 + 清洗 + 去重
读取 config.yaml，输出候选条目列表
"""

import os, sys, json, re, time, hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
import urllib.request, urllib.parse

SCRIPT_DIR = Path(__file__).parent
CONFIG_PATH = SCRIPT_DIR / "config.yaml"
REPO_ROOT   = Path(__file__).parent.parent

# ── 简单 YAML 解析（避免依赖 pyyaml）──────────────────
def load_config():
    import yaml
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)

def try_load_config():
    try:
        return load_config()
    except ImportError:
        # fallback: 用 exec 简单解析
        text = CONFIG_PATH.read_text()
        # 只提取需要的字段，其余用默认值
        return None

# ── 获取当前时段 ───────────────────────────────────────
def get_slot():
    now = datetime.now(timezone(timedelta(hours=8)))
    h = now.hour
    if h < 10:
        return "morning"
    elif h < 16:
        return "midday"
    else:
        return "afternoon"

# ── 规范化 URL（去参数/锚点用于去重）─────────────────
def normalize_url(url):
    u = urllib.parse.urlparse(url)
    return f"{u.scheme}://{u.netloc}{u.path}".rstrip("/").lower()

def url_fingerprint(title, url):
    s = normalize_url(url) + "|" + title.strip().lower()[:60]
    return hashlib.md5(s.encode()).hexdigest()

# ── 加载历史去重集合 ──────────────────────────────────
def load_seen(cfg):
    seen = set()
    repo = REPO_ROOT
    for fname in ["brief.json","brief_midday.json","brief_afternoon.json","history.json"]:
        p = repo / fname
        if p.exists():
            try:
                data = json.loads(p.read_text())
                items = data if isinstance(data, list) else data.get("items", [])
                for it in items:
                    t = it.get("title","")
                    u = it.get("url","") or it.get("link","")
                    if t or u:
                        seen.add(url_fingerprint(t, u))
            except Exception:
                pass
    return seen

# ── URL 可访问性检查（HEAD，3秒超时）─────────────────
def check_url(url, timeout=3):
    try:
        req = urllib.request.Request(url, method="HEAD",
              headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status < 400
    except Exception:
        try:
            req2 = urllib.request.Request(url,
                   headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req2, timeout=timeout) as r:
                return r.status < 400
        except Exception:
            return False

# ── 判断是否国内来源 ─────────────────────────────────
def is_domestic(url, domestic_domains):
    host = urllib.parse.urlparse(url).netloc.lower()
    return any(d in host for d in domestic_domains)

# ── 判断 URL 是否黑名单 ──────────────────────────────
def is_blacklisted(url, patterns):
    for p in patterns:
        if re.search(p, url):
            return True
    return False

# ── NewsAPI 请求 ─────────────────────────────────────
def fetch_newsapi(keywords, from_dt, api_key, page_size=100):
    q = " OR ".join(f'"{k}"' for k in keywords[:5])
    params = urllib.parse.urlencode({
        "q": q,
        "from": from_dt.strftime("%Y-%m-%dT%H:%M:%S"),
        "sortBy": "publishedAt",
        "language": "en",
        "pageSize": page_size,
        "apiKey": api_key
    })
    url = f"https://newsapi.org/v2/everything?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": "semi-brief/1.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read())
    return data.get("articles", [])

# ── 主采集函数 ────────────────────────────────────────
def fetch(slot=None, cfg=None):
    if cfg is None:
        try:
            import yaml
            with open(CONFIG_PATH) as f:
                cfg = yaml.safe_load(f)
        except Exception as e:
            print(f"[ERROR] 无法加载 config.yaml: {e}", file=sys.stderr)
            sys.exit(1)

    if slot is None:
        slot = get_slot()

    api_key = os.environ.get("NEWSAPI_KEY", "")
    if not api_key:
        print("[ERROR] NEWSAPI_KEY 未设置", file=sys.stderr)
        sys.exit(1)

    window_h = cfg["time_window"][slot]
    target_count = cfg["count"][slot]
    domestic_min = cfg["domestic_min"][slot]
    keywords = cfg["keywords"]
    domestic_domains = cfg["domestic_domains"]
    blacklist = cfg["url_blacklist_patterns"]

    now = datetime.now(timezone(timedelta(hours=8)))
    from_dt = now - timedelta(hours=window_h)

    print(f"[fetch] slot={slot}, window={window_h}h, target={target_count}条", flush=True)
    print(f"[fetch] 时间窗: {from_dt.strftime('%Y-%m-%d %H:%M')} ~ {now.strftime('%Y-%m-%d %H:%M')}", flush=True)

    # 加载历史去重
    seen = load_seen(cfg)

    # 调用 NewsAPI
    articles = []
    try:
        articles = fetch_newsapi(keywords, from_dt, api_key)
        print(f"[fetch] NewsAPI 返回 {len(articles)} 条", flush=True)
    except Exception as e:
        print(f"[ERROR] NewsAPI 调用失败: {e}", file=sys.stderr)
        sys.exit(2)

    # 清洗
    results = []
    domestic_count = 0

    for art in articles:
        title = (art.get("title") or "").strip()
        url   = (art.get("url") or "").strip()
        desc  = (art.get("description") or "").strip()
        src   = (art.get("source", {}).get("name") or "").strip()
        pub   = art.get("publishedAt", "")

        if not title or not url:
            continue
        if "[Removed]" in title:
            continue

        # 时间过滤
        try:
            pub_dt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
            if pub_dt > now:       # 未来日期剔除
                continue
            if pub_dt < from_dt.replace(tzinfo=timezone.utc) if from_dt.tzinfo is None else from_dt:
                continue
        except Exception:
            pass

        # URL 黑名单
        if is_blacklisted(url, blacklist):
            continue

        # 去重
        fp = url_fingerprint(title, url)
        if fp in seen:
            continue
        seen.add(fp)

        # URL 可达性检查（只检查前 target_count*3 条，节省时间）
        if len(results) < target_count * 3:
            if not check_url(url):
                print(f"[skip] URL 不可达: {url[:60]}", flush=True)
                continue

        dom = is_domestic(url, domestic_domains)
        if dom:
            domestic_count += 1

        results.append({
            "title": title,
            "url": url,
            "description": desc,
            "source": src,
            "publishedAt": pub,
            "domestic": dom
        })

        if len(results) >= target_count * 3:
            break

    print(f"[fetch] 清洗后候选: {len(results)} 条（国内来源: {domestic_count}）", flush=True)
    return results, slot, cfg

if __name__ == "__main__":
    slot_arg = sys.argv[1] if len(sys.argv) > 1 else None
    items, slot, cfg = fetch(slot_arg)
    print(json.dumps(items, ensure_ascii=False, indent=2))

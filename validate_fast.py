#!/usr/bin/env python3
"""Fast URL validation with parallel requests and short timeout."""
import json, sys, urllib.request, urllib.parse, ssl, time, concurrent.futures

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

BLACKLIST_REDIR = ["/404.htm", "/404.html", "/404", "moneydj.com/404", "businesstoday.com.tw/", "msn.cn/zh-cn"]

def validate_url(url, timeout=8):
    try:
        parsed = urllib.parse.urlparse(url)
        full = url
        req = urllib.request.Request(full, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            final_url = resp.url or full
            final_parsed = urllib.parse.urlparse(final_url)
            final_domain = final_parsed.netloc.lower().replace('www.', '')
            orig_domain = parsed.netloc.lower().replace('www.', '')
            redir_lower = final_url.lower()
            for blk in BLACKLIST_REDIR:
                if blk in redir_lower:
                    return {"valid": False, "final_url": final_url, "reason": f"dead_page:{blk}"}
            if final_domain != orig_domain and orig_domain not in final_domain and final_domain not in orig_domain:
                return {"valid": False, "final_url": final_url, "reason": f"cross_domain:{orig_domain}->{final_domain}"}
            return {"valid": True, "final_url": final_url, "reason": "ok"}
    except urllib.error.HTTPError as e:
        if e.code in (403, 404, 410, 451):
            return {"valid": False, "final_url": url, "reason": f"http_{e.code}"}
        return {"valid": True, "final_url": url, "reason": f"http_{e.code}_accepted"}
    except Exception as e:
        return {"valid": True, "final_url": url, "reason": f"error_{type(e).__name__}"}

input_file = sys.argv[1]
output_file = sys.argv[2]

with open(input_file) as f:
    items = json.load(f)

valid_items = []
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    future_map = {executor.submit(validate_url, item["url"]): i for i, item in enumerate(items)}
    for future in concurrent.futures.as_completed(future_map, timeout=120):
        idx = future_map[future]
        result = future.result()
        if result["valid"]:
            items[idx]["url"] = result.get("final_url", items[idx]["url"])
            valid_items.append(items[idx])
        else:
            print(f"  ❌ {items[idx].get('title','')[:40]} | {result['reason']}")

print(f"Validated: {len(items)} -> {len(valid_items)} valid")
with open(output_file, "w") as f:
    json.dump(valid_items, f, ensure_ascii=False, indent=2)

#!/usr/bin/env python3
"""
URL 可达性校验脚本
用法: python3 validate_urls.py <input.json> <output.json>
对每条新闻的 url 字段做 HTTP 校验，过滤已失效链接。
"""
import json, sys, urllib.request, urllib.parse, ssl, time

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# 已知的占位页模式（内容已删除，重定向到这些页面）
BLACKLIST_REDIR = [
    "/404.htm", "/404.html", "/404",
    "moneydj.com/404",
    "businesstoday.com.tw/",
    "msn.cn/zh-cn",  # msn 重定向到首页
]

def validate_url(url: str, timeout: int = 10) -> dict:
    """校验单个 URL，返回 {valid, final_url, reason}"""
    try:
        parsed = urllib.parse.urlparse(url)
        path = urllib.parse.quote(parsed.path, safe='/:@!$&\'()*+,;=%._~')
        full = urllib.parse.urlunparse((parsed.scheme, parsed.netloc, path, '', parsed.query, ''))

        req = urllib.request.Request(full, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            final_url = resp.url or full
            final_parsed = urllib.parse.urlparse(final_url)
            final_domain = final_parsed.netloc.lower().replace('www.', '')
            orig_domain = parsed.netloc.lower().replace('www.', '')

            # 重定向到已知的占位页/首页（内容已删除）
            redir_lower = final_url.lower()
            for blk in BLACKLIST_REDIR:
                if blk in redir_lower:
                    return {"valid": False, "final_url": final_url, "reason": f"dead_page:{blk}"}

            # 重定向到陌生域名（内容转移/丢失）
            if final_domain != orig_domain and orig_domain not in final_domain and final_domain not in orig_domain:
                return {"valid": False, "final_url": final_url, "reason": f"cross_domain:{orig_domain}→{final_domain}"}

            # 非 200 状态码
            if resp.status not in (200, 301, 302):
                return {"valid": False, "final_url": final_url, "reason": f"http_{resp.status}"}

            # 如果有重定向且最终 URL 不同，更新为最终 URL
            return {"valid": True, "final_url": final_url, "reason": None}

    except urllib.error.HTTPError as e:
        return {"valid": False, "final_url": None, "reason": f"http_{e.code}"}
    except Exception as e:
        return {"valid": False, "final_url": None, "reason": f"{type(e).__name__}"}


def main():
    input_path = sys.argv[1]
    output_path = sys.argv[2]

    with open(input_path, encoding='utf-8') as f:
        data = json.load(f)

    items = data if isinstance(data, list) else data.get('items', [])
    if not isinstance(items, list):
        print("Error: input must be a list of items", file=sys.stderr)
        sys.exit(1)

    valid_items = []
    invalid_items = []

    for item in items:
        url = item.get('url', '')
        if not url:
            invalid_items.append((item.get('title', '?')[:50], "no_url"))
            continue

        result = validate_url(url)
        if result["valid"]:
            # 更新为最终 URL（可能有重定向修正）
            if result["final_url"] and result["final_url"] != url:
                item["url"] = result["final_url"]
            valid_items.append(item)
        else:
            invalid_items.append((item.get('title', '?')[:50], result["reason"]))

        time.sleep(0.3)  # 避免过快请求

    # 保留原始数据结构
    if isinstance(data, dict):
        data['items'] = valid_items
        output = data
    else:
        output = valid_items

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f'[validate] 输入 {len(items)} 条 → 有效 {len(valid_items)} 条 → 失效 {len(invalid_items)} 条', file=sys.stderr)
    for title, reason in invalid_items:
        print(f'  ❌ {title} → {reason}', file=sys.stderr)

    return 0 if len(valid_items) > 0 else 1


if __name__ == '__main__':
    sys.exit(main())

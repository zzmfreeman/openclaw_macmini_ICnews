#!/usr/bin/env python3
"""
semi-brief 新闻抓取模块 v2
整合 RSS 抓取 + 关键词过滤
支持国内外半导体新闻源
"""

import os
from pathlib import Path
import sys
import json
import yaml
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, asdict
import xml.etree.ElementTree as ET
import urllib.request
import ssl

# 禁用 SSL 验证
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE


@dataclass
class NewsItem:
    """新闻条目"""
    title: str
    url: str
    summary: str
    published: str
    source: str
    region: str  # domestic / overseas
    lang: str    # zh / en
    category: str = ""  # design / manufacturing / packaging / industry
    keywords_matched: List[str] = None
    
    def __post_init__(self):
        if self.keywords_matched is None:
            self.keywords_matched = []
    
    def to_dict(self) -> Dict:
        return asdict(self)


class KeywordManager:
    """关键词管理器"""
    
    def __init__(self, yaml_path: str):
        self.yaml_path = yaml_path
        self.data = self._load()
        self.all_keywords = self._build_keyword_set()
    
    def _load(self) -> Dict:
        with open(self.yaml_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _build_keyword_set(self) -> Set[str]:
        """构建所有关键词的集合（小写）"""
        keywords = set()
        for category, info in self.data.items():
            if category.startswith('meta'):
                continue
            if isinstance(info, dict) and 'keywords' in info:
                for kw in info['keywords']:
                    keywords.add(kw.lower())
        return keywords
    
    def match(self, text: str) -> List[str]:
        """匹配关键词，返回匹配到的关键词列表"""
        text_lower = text.lower()
        matched = []
        for kw in self.all_keywords:
            if kw in text_lower:
                matched.append(kw)
        return matched
    
    def get_category_for_keyword(self, keyword: str) -> str:
        """获取关键词所属分类"""
        kw_lower = keyword.lower()
        for category, info in self.data.items():
            if category.startswith('meta'):
                continue
            if isinstance(info, dict) and 'keywords' in info:
                for k in info['keywords']:
                    if k.lower() == kw_lower:
                        return category
        return ""


class RSSFetcher:
    """RSS 抓取器"""
    
    # RSS 源配置
    SOURCES = [
        # 国外专业媒体
        {"name": "SemiEngineering", "url": "https://semiengineering.com/feed/", "region": "overseas", "lang": "en", "weight": 10},
        {"name": "EE Times", "url": "https://www.eetimes.com/rss.xml", "region": "overseas", "lang": "en", "weight": 9},
        {"name": "AnandTech", "url": "https://www.anandtech.com/rss/", "region": "overseas", "lang": "en", "weight": 8},
        {"name": "Tom's Hardware", "url": "https://www.tomshardware.com/feeds/all", "region": "overseas", "lang": "en", "weight": 8},
        
        # 公司官方 Twitter (Nitter)
        {"name": "TSMC", "url": "https://nitter.net/tsmccorp/rss", "region": "overseas", "lang": "en", "weight": 10},
        {"name": "SamsungSemi", "url": "https://nitter.net/SamsungSemiUS/rss", "region": "overseas", "lang": "en", "weight": 10},
        {"name": "Intel", "url": "https://nitter.net/intel/rss", "region": "overseas", "lang": "en", "weight": 9},
        {"name": "AMD", "url": "https://nitter.net/AMD/rss", "region": "overseas", "lang": "en", "weight": 9},
        {"name": "NVIDIA", "url": "https://nitter.net/nvidia/rss", "region": "overseas", "lang": "en", "weight": 9},
    ]
    
    def __init__(self):
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
    
    def fetch(self, url: str, timeout: int = 15) -> Optional[str]:
        """抓取 RSS 内容"""
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            )
            with urllib.request.urlopen(req, timeout=timeout, context=self.ssl_context) as resp:
                return resp.read().decode('utf-8', errors='ignore')
        except Exception as e:
            return None
    
    def parse(self, xml: str, source: Dict) -> List[NewsItem]:
        """解析 RSS XML"""
        items = []
        try:
            root = ET.fromstring(xml)
            if root.tag == "rss":
                channel = root.find("channel")
                if channel:
                    for item in channel.findall("item"):
                        title = item.findtext("title", "").strip()
                        link = item.findtext("link", "").strip()
                        desc = item.findtext("description", "")[:500]
                        pub = item.findtext("pubDate", "")
                        
                        items.append(NewsItem(
                            title=title,
                            url=link,
                            summary=desc,
                            published=pub,
                            source=source["name"],
                            region=source["region"],
                            lang=source["lang"]
                        ))
        except:
            pass
        return items
    
    def fetch_all(self) -> List[NewsItem]:
        """抓取所有源"""
        all_items = []
        for source in self.SOURCES:
            xml = self.fetch(source["url"])
            if xml:
                items = self.parse(xml, source)
                print(f"[RSS] {source['name']}: {len(items)}条", file=sys.stderr)
                all_items.extend(items)
            else:
                print(f"[RSS] {source['name']}: 失败", file=sys.stderr)
        return all_items


class NewsProcessor:
    """新闻处理器"""
    
    def __init__(self, keyword_manager: KeywordManager):
        self.kw_manager = keyword_manager
    
    def deduplicate(self, items: List[NewsItem]) -> List[NewsItem]:
        """去重"""
        seen = set()
        result = []
        for item in items:
            if item.url and item.url not in seen:
                seen.add(item.url)
                result.append(item)
        return result
    
    def filter_by_keywords(self, items: List[NewsItem]) -> List[NewsItem]:
        """关键词过滤"""
        for item in items:
            text = f"{item.title} {item.summary}"
            matched = self.kw_manager.match(text)
            item.keywords_matched = matched
            # 设置分类
            if matched:
                cat = self.kw_manager.get_category_for_keyword(matched[0])
                item.category = cat
        
        # 只保留有匹配的
        return [i for i in items if i.keywords_matched]
    
    def sort_by_weight(self, items: List[NewsItem]) -> List[NewsItem]:
        """按权重排序（匹配关键词数量 + 来源权重）"""
        def weight(item):
            kw_score = len(item.keywords_matched)
            source_score = 0
            for src in RSSFetcher.SOURCES:
                if src["name"] == item.source:
                    source_score = src.get("weight", 5)
                    break
            return kw_score * 10 + source_score
        
        return sorted(items, key=weight, reverse=True)
    
    def validate_urls(self, items: List[NewsItem]) -> List[NewsItem]:
        """URL 可达性校验：过滤已失效的链接"""
        valid, invalid = [], []
        for item in items:
            ok, final_url, reason = validate_url(item.url, timeout=8)
            if ok:
                # 如果有重定向，更新 URL
                if final_url and final_url != item.url:
                    item.url = final_url
                valid.append(item)
            else:
                invalid.append((item.title[:50], reason))
        for title, reason in invalid:
            print(f"  ❌ [URL失效] {title} → {reason}", file=sys.stderr)
        print(f"[fetch] URL校验: {len(valid)}/{len(items)} 有效", file=sys.stderr)
        return valid

    def process(self, items: List[NewsItem], target: int = 5) -> List[NewsItem]:
        """完整处理流程"""
        # URL 校验（新增，放最前优先过滤无效项）
        items = self.validate_urls(items)
        # 去重
        items = self.deduplicate(items)
        # 关键词过滤
        items = self.filter_by_keywords(items)
        # 排序
        items = self.sort_by_weight(items)
        # 限制数量
        return items[:target]


def main():
    """主入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='semi-brief 新闻抓取')
    parser.add_argument('--slot', default='midday', help='时段: morning/midday/evening')
    parser.add_argument('--target', type=int, default=5, help='目标条数')
    parser.add_argument('--output', help='输出JSON文件路径')
    args = parser.parse_args()
    
    # 加载关键词
    kw_path = Path(__file__).parent / "keywords.yaml"
    kw_manager = KeywordManager(str(kw_path))
    
    # 抓取 RSS
    fetcher = RSSFetcher()
    print(f"[fetch] slot={args.slot}, target={args.target}条", file=sys.stderr)
    raw_items = fetcher.fetch_all()
    
    # 处理
    processor = NewsProcessor(kw_manager)
    final_items = processor.process(raw_items, args.target)
    
    # 输出
    result = {
        "items": [item.to_dict() for item in final_items],
        "slot": args.slot,
        "count": len(final_items),
        "generated_at": datetime.now().isoformat()
    }
    
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"[fetch] 已保存到 {args.output}", file=sys.stderr)
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    return 0 if len(final_items) > 0 else 1


if __name__ == "__main__":
    sys.exit(main())


# -------------------------------------------------------------------
# URL 可达性校验（新增）
# -------------------------------------------------------------------
BLACKLIST_REDIR = {
    "moneydj.com/404",   # 跳转目标为404占位页
    "businesstoday.com.tw/",  # 台媒新闻删除后跳转首页
}
BLOCKED_DOMAINS = {
    "semi-analysis.com",
    "ft.com",  # paywall
    "tmtpost.com",  # 大量中文站URL编码问题
}

def validate_url(url: str, timeout: int = 8) -> tuple:
    """
    校验 URL 是否可访问且内容有效。
    返回 (is_valid: bool, final_url: str, reason: str)
    - is_valid=True  → 内容页存在，可保留
    - is_valid=False → 已失效，需过滤
    """
    try:
        parsed = urllib.parse.urlparse(url)
        # 1. URL 编码：处理中文路径
        path_enc = urllib.parse.quote(parsed.path, safe='/:@!$&\'()*+,;=%')
        full_url = urllib.parse.urlunparse((parsed.scheme, parsed.netloc, path_enc, '', parsed.query, ''))

        req = urllib.request.Request(
            full_url,
            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"},
            method="GET"
        )
        with urllib.request.urlopen(req, timeout=timeout, context=ssl_context) as resp:
            final_url = resp.url
            final_parsed = urllib.parse.urlparse(final_url)
            final_domain = final_parsed.netloc.lower().replace('www.', '')
            orig_domain = parsed.netloc.lower().replace('www.', '')

            # 2. SSL/TLS 协议层屏蔽
            if final_domain in BLOCKED_DOMAINS:
                return False, final_url, f"blocked_domain:{final_domain}"

            # 3. 重定向到陌生域名
            if final_domain != orig_domain and final_domain not in orig_domain:
                return False, final_url, f"cross_domain:{orig_domain}→{final_domain}"

            # 4. 重定向到已知的占位页/首页（内容已删除）
            redir_lower = final_url.lower()
            for blk in BLACKLIST_REDIR:
                if blk in redir_lower:
                    return False, final_url, f"dead_page:{blk}"

            # 5. 状态码非 200
            if resp.status != 200:
                return False, final_url, f"http_{resp.status}"

            return True, final_url, None

    except urllib.error.HTTPError as e:
        return False, None, f"http_error_{e.code}"
    except urllib.error.HTTPError:  # Python 3.9 compat - HTTPErr is base class
        return False, None, "http_error"
    except Exception as e:
        return False, None, f"exception_{type(e).__name__}"

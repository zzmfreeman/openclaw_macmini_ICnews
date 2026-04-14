#!/usr/bin/env python3
"""
Semi-brief 硬去重脚本
用法: python3 dedup.py <input.json> <history.json> <output.json>
- URL 精确去重
- 标题前30字符去重
- 标题 Jaccard 相似度 > 0.6 去重
"""
import json, sys, re
from collections import Counter

def normalize(s):
    return re.sub(r'[\s\u3000]+', '', s.lower())

def jaccard(s1, s2):
    a, b = set(normalize(s1)), set(normalize(s2))
    if not a or not b: return 0
    return len(a & b) / len(a | b)

def main():
    input_path = sys.argv[1]
    history_path = sys.argv[2]
    output_path = sys.argv[3]
    
    with open(input_path) as f:
        items = json.load(f)
    if not isinstance(items, list):
        items = items.get('items', [])
    
    with open(history_path) as f:
        hist = json.load(f)
    
    # Build dedup sets from history
    seen_urls = set()
    seen_title_prefix = set()
    seen_titles = []
    for e in hist:
        if isinstance(e, dict):
            u = e.get('url', '')
            if u: seen_urls.add(u)
            t = e.get('title', '')
            if t:
                seen_title_prefix.add(normalize(t[:30]))
                seen_titles.append(t)
    
    # Filter items
    kept = []
    rejected = []
    for it in items:
        url = it.get('url', '')
        title = it.get('title', '')
        
        # 1. URL exact match
        if url and url in seen_urls:
            rejected.append((title[:50], 'URL dup'))
            continue
        
        # 2. Title prefix match (first 30 chars)
        if normalize(title[:30]) in seen_title_prefix:
            rejected.append((title[:50], 'title prefix dup'))
            continue
        
        # 3. Jaccard similarity > 0.6 against history titles
        is_sim = False
        for ht in seen_titles:
            if jaccard(title, ht) > 0.6:
                is_sim = True
                rejected.append((title[:50], f'similar to: {ht[:40]}'))
                break
        if is_sim:
            continue
        
        # 4. Also dedup within current batch
        batch_prefix = set(normalize(x.get('title','')[:30]) for x in kept)
        if normalize(title[:30]) in batch_prefix:
            rejected.append((title[:50], 'batch internal dup'))
            continue
        
        kept.append(it)
        # Add to seen sets so later items in batch also dedup
        if url: seen_urls.add(url)
        if title:
            seen_title_prefix.add(normalize(title[:30]))
            seen_titles.append(title)
    
    with open(output_path, 'w') as f:
        json.dump(kept, f, ensure_ascii=False, indent=2)
    
    print(f'Input: {len(items)} → Kept: {len(kept)} → Rejected: {len(rejected)}')
    for r in rejected:
        print(f'  ❌ {r[0]} ({r[1]})')

if __name__ == '__main__':
    main()

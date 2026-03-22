#!/usr/bin/env python3
"""
关键词管理工具
用于读取、验证、更新 keywords.yaml
"""

import yaml
import sys
from pathlib import Path
from datetime import datetime

KEYWORDS_FILE = Path(__file__).parent / "keywords.yaml"


def load_keywords():
    """加载关键词配置"""
    with open(KEYWORDS_FILE, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def save_keywords(data):
    """保存关键词配置"""
    with open(KEYWORDS_FILE, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False)


def get_all_keywords():
    """获取所有关键词列表（扁平化）"""
    data = load_keywords()
    all_kws = []
    for category, info in data.items():
        if category.startswith('meta'):
            continue
        if isinstance(info, dict) and 'keywords' in info:
            all_kws.extend(info['keywords'])
    return list(set(all_kws))  # 去重


def add_keyword(category: str, keyword: str, note: str = ""):
    """添加关键词"""
    data = load_keywords()
    
    if category not in data:
        print(f"错误：分类 '{category}' 不存在")
        return False
    
    if keyword in data[category]['keywords']:
        print(f"关键词 '{keyword}' 已存在")
        return False
    
    data[category]['keywords'].append(keyword)
    
    # 更新 changelog
    data['meta']['changelog'].append({
        'date': datetime.now().strftime('%Y-%m-%d'),
        'action': 'add',
        'category': category,
        'keyword': keyword,
        'note': note
    })
    data['meta']['updated'] = datetime.now().strftime('%Y-%m-%d')
    
    save_keywords(data)
    print(f"已添加: [{category}] {keyword}")
    return True


def remove_keyword(category: str, keyword: str, note: str = ""):
    """删除关键词"""
    data = load_keywords()
    
    if category not in data:
        print(f"错误：分类 '{category}' 不存在")
        return False
    
    if keyword not in data[category]['keywords']:
        print(f"关键词 '{keyword}' 不存在")
        return False
    
    data[category]['keywords'].remove(keyword)
    
    # 更新 changelog
    data['meta']['changelog'].append({
        'date': datetime.now().strftime('%Y-%m-%d'),
        'action': 'remove',
        'category': category,
        'keyword': keyword,
        'note': note
    })
    data['meta']['updated'] = datetime.now().strftime('%Y-%m-%d')
    
    save_keywords(data)
    print(f"已删除: [{category}] {keyword}")
    return True


def list_keywords():
    """列出所有关键词"""
    data = load_keywords()
    
    print(f"\n=== 关键词体系 (v{data['meta']['version']}, 更新于 {data['meta']['updated']}) ===\n")
    
    for category, info in data.items():
        if category.startswith('meta'):
            continue
        print(f"\n【{info['name']}】({len(info['keywords'])}个)")
        for kw in sorted(info['keywords']):
            print(f"  - {kw}")
    
    print(f"\n总计: {len(get_all_keywords())} 个唯一关键词")


def show_changelog():
    """显示变更历史"""
    data = load_keywords()
    print("\n=== 变更历史 ===\n")
    for entry in data['meta']['changelog']:
        print(f"[{entry['date']}] {entry.get('action', 'init'):6} | {entry.get('note', '')}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法:")
        print("  python keywords.py list              # 列出所有关键词")
        print("  python keywords.py changelog         # 显示变更历史")
        print("  python keywords.py add <分类> <关键词> [备注]    # 添加关键词")
        print("  python keywords.py remove <分类> <关键词> [备注] # 删除关键词")
        print("\n分类: design, design_companies, eda_ip, manufacturing, packaging, industry")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "list":
        list_keywords()
    elif cmd == "changelog":
        show_changelog()
    elif cmd == "add" and len(sys.argv) >= 4:
        add_keyword(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "")
    elif cmd == "remove" and len(sys.argv) >= 4:
        remove_keyword(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "")
    else:
        print("参数错误")
        sys.exit(1)

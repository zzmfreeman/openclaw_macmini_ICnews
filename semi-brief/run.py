#!/usr/bin/env python3
"""
semi-brief 运行脚本 v2
整合抓取 -> 生成 -> 推送
"""

import os
import sys
import json
import subprocess
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
SEMI_DIR = Path(__file__).parent

def run_fetch(slot: str, target: int = 5) -> dict:
    """运行抓取"""
    output_file = SEMI_DIR / f"raw_{slot}.json"
    
    cmd = [
        sys.executable,
        str(SEMI_DIR / "fetch.py"),
        "--slot", slot,
        "--target", str(target),
        "--output", str(output_file)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"[run] 抓取失败: {result.stderr}", file=sys.stderr)
        return None
    
    with open(output_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def generate_brief(data: dict, slot: str) -> dict:
    """生成简报（简化版，直接返回抓取结果）"""
    # TODO: 后续接入 LLM 生成摘要
    return {
        "version": f"v{datetime.now().strftime('%Y%m%d-%H%M')}",
        "generatedAt": datetime.now().isoformat(),
        "period": slot,
        "items": data.get("items", [])
    }


def save_and_push(brief: dict, slot: str):
    """保存并推送到 GitHub"""
    # 保存到本地
    brief_file = BASE_DIR / f"brief_{slot}.json"
    with open(brief_file, 'w', encoding='utf-8') as f:
        json.dump(brief, f, ensure_ascii=False, indent=2)
    
    # 同步到 docs/
    docs_file = BASE_DIR / "docs" / f"brief_{slot}.json"
    with open(docs_file, 'w', encoding='utf-8') as f:
        json.dump(brief, f, ensure_ascii=False, indent=2)
    
    # Git 提交
    os.chdir(BASE_DIR)
    subprocess.run(["git", "add", "-A"], check=False)
    subprocess.run(["git", "commit", "-m", f"semi-brief {brief['version']}"], check=False)
    subprocess.run(["git", "push"], check=False)
    
    return brief_file


def main():
    """主入口"""
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--slot', default='midday', help='时段')
    parser.add_argument('--target', type=int, default=5, help='目标条数')
    args = parser.parse_args()
    
    print(f"[run] slot={args.slot}, target={args.target}条", file=sys.stderr)
    
    # 抓取
    data = run_fetch(args.slot, args.target)
    if not data or data.get("count", 0) == 0:
        print("[run] 无可用条目，退出", file=sys.stderr)
        return 1
    
    # 生成简报
    brief = generate_brief(data, args.slot)
    
    # 保存并推送
    save_and_push(brief, args.slot)
    
    print(f"[run] 完成: {brief['version']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

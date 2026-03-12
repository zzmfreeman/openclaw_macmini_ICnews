#!/usr/bin/env python3
"""
run.py — 主入口
流程: fetch → (LLM 摘要 + glossary) → render → publish
LLM 只介入最小任务：中文摘要生成 + glossary 提取
"""

import os, sys, json, subprocess
from pathlib import Path
from datetime import datetime, timedelta, timezone

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from fetch import fetch
from render import render

PAGES = {
    "morning":   "https://zzmfreeman.github.io/openclaw_macmini_ICnews/",
    "midday":    "https://zzmfreeman.github.io/openclaw_macmini_ICnews/midday.html",
    "afternoon": "https://zzmfreeman.github.io/openclaw_macmini_ICnews/afternoon.html",
}

SLOT_LABEL = {
    "morning":   "早报",
    "midday":    "午间快讯",
    "afternoon": "晚间快讯",
}

def summarize_and_glossary(items, slot, cfg):
    """
    最小化 LLM 调用：
    输入：候选条目列表（英文标题+摘要+来源）
    输出：中文摘要版条目 + glossary
    
    NOTE: 这个函数由 cron agentTurn 中的 LLM 调用，
    而非 Python 直接调用 API。
    run.py 会把需要 LLM 处理的内容写到 llm_input.json，
    cron 任务读取后只处理这一步，返回 llm_output.json。
    """
    llm_input = {
        "task": "translate_and_glossary",
        "slot": slot,
        "items": [
            {
                "title": it["title"],
                "description": it.get("description",""),
                "source": it.get("source",""),
                "url": it["url"],
                "publishedAt": it.get("publishedAt",""),
                "domestic": it.get("domestic", False)
            }
            for it in items
        ],
        "glossary_min": cfg.get("glossary_min", {}).get(slot, 2),
        "glossary_skip": cfg.get("glossary_skip", []),
        "count": cfg.get("count", {}).get(slot, 5),
        "domestic_min": cfg.get("domestic_min", {}).get(slot, 3),
    }
    llm_input_path = SCRIPT_DIR / "llm_input.json"
    llm_input_path.write_text(json.dumps(llm_input, ensure_ascii=False, indent=2))
    print(f"[run] LLM 输入已写入 {llm_input_path}", flush=True)
    print(f"[run] 条目数: {len(items)}", flush=True)
    return llm_input_path

def load_llm_output():
    p = SCRIPT_DIR / "llm_output.json"
    if p.exists():
        return json.loads(p.read_text())
    return None

def run(slot=None):
    # 1. 采集
    items, slot, cfg = fetch(slot)

    if not items:
        print(f"[run] 无可用条目，退出", flush=True)
        sys.exit(0)

    # 2. 写入 LLM 输入文件（cron agentTurn 会读取并处理）
    llm_input_path = summarize_and_glossary(items, slot, cfg)

    # 3. 检查是否已有 LLM 输出（二阶段执行）
    llm_out = load_llm_output()
    if llm_out:
        processed_items = llm_out.get("items", items)
        glossary = llm_out.get("glossary", [])
        print(f"[run] 使用 LLM 输出: {len(processed_items)} 条, glossary {len(glossary)} 条", flush=True)
        # 清理 llm_output.json
        (SCRIPT_DIR / "llm_output.json").unlink(missing_ok=True)
    else:
        # 直接用原始条目（无中文摘要），等待 LLM 补填
        processed_items = items
        glossary = []
        print(f"[run] 无 LLM 输出，使用原始英文条目", flush=True)

    # 4. 渲染写入 JSON + 更新 history
    brief, version, gen_time, commit = render(processed_items, slot, cfg, glossary)

    # 5. Git push
    try:
        result = subprocess.run(
            ["bash", str(SCRIPT_DIR / "publish.sh"), version],
            capture_output=True, text=True, cwd=SCRIPT_DIR.parent
        )
        print(result.stdout, flush=True)
        if result.returncode != 0:
            print(f"[WARN] publish 失败: {result.stderr}", flush=True)
    except Exception as e:
        print(f"[WARN] publish 异常: {e}", flush=True)

    # 6. 输出结果摘要
    page_url = PAGES[slot]
    summary = {
        "slot": slot,
        "label": SLOT_LABEL[slot],
        "version": version,
        "generatedAt": gen_time,
        "commit": commit,
        "count": len(processed_items),
        "glossary_count": len(glossary),
        "page_url": page_url,
    }
    print("\n=== RESULT ===")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary

if __name__ == "__main__":
    slot_arg = sys.argv[1] if len(sys.argv) > 1 else None
    run(slot_arg)

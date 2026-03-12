#!/usr/bin/env python3
"""
render.py — 生成 brief*.json + history.json + docs 镜像
接收 fetch.py 的候选条目，调用 LLM 只做"中文摘要 + glossary"
"""

import os, sys, json, re
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
REPO_ROOT   = Path(__file__).parent.parent

SLOT_FILES = {
    "morning":   "brief.json",
    "midday":    "brief_midday.json",
    "afternoon": "brief_afternoon.json",
}

SLOT_LABEL = {
    "morning":   "早报",
    "midday":    "午间快讯",
    "afternoon": "晚间快讯",
}

def get_version():
    now = datetime.now(timezone(timedelta(hours=8)))
    return now.strftime("v%Y%m%d-%H%M"), now.strftime("%Y-%m-%d %H:%M")

def get_git_hash():
    try:
        import subprocess
        r = subprocess.run(["git","rev-parse","--short","HEAD"],
            cwd=REPO_ROOT, capture_output=True, text=True)
        return r.stdout.strip()
    except Exception:
        return "unknown"

def build_brief_json(items, slot, cfg, version, gen_time, commit):
    glossary = []  # 由 run.py 调 LLM 填充
    out = {
        "asOf": gen_time,
        "slot": slot,
        "label": SLOT_LABEL[slot],
        "version": version,
        "commit": commit,
        "items": items,
        "glossary": glossary,
        "footer": {
            "version": version,
            "generatedAt": gen_time,
            "commit": commit
        }
    }
    return out

def write_json(data, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2))

def update_history(items, history_path):
    hist = []
    if Path(history_path).exists():
        try:
            hist = json.loads(Path(history_path).read_text())
        except Exception:
            hist = []
    hist = items + hist
    # 保留最近 500 条
    hist = hist[:500]
    write_json(hist, history_path)

def render(items, slot, cfg, glossary=None):
    version, gen_time = get_version()
    commit = get_git_hash()

    if glossary is None:
        glossary = []

    brief = build_brief_json(items, slot, cfg, version, gen_time, commit)
    brief["glossary"] = glossary

    repo = REPO_ROOT
    fname = SLOT_FILES[slot]
    out_path   = repo / fname
    docs_path  = repo / "docs" / fname
    hist_path  = repo / "history.json"
    hist_docs  = repo / "docs" / "history.json"

    write_json(brief, out_path)
    write_json(brief, docs_path)
    print(f"[render] 写入 {out_path}", flush=True)
    print(f"[render] 写入 {docs_path}", flush=True)

    update_history(items, hist_path)
    update_history(items, hist_docs)
    print(f"[render] 更新 history.json", flush=True)

    return brief, version, gen_time, commit

if __name__ == "__main__":
    # 测试用：从 stdin 读 JSON
    data = json.loads(sys.stdin.read())
    items = data.get("items", [])
    slot  = data.get("slot", "midday")
    render(items, slot, {})

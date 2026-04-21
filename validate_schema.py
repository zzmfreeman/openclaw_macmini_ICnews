#!/usr/bin/env python3
"""
Semi-brief JSON schema 校验脚本
用法: python3 validate_schema.py <input.json> <output.json>

对每条新闻条目做字段类型校验和自动修正：
- 必填字段缺失 → 补充默认值或丢弃
- 类型错误 → 自动转换（string→array 等）
- 内容质量 → 空洞见/建议补充默认提示

Schema 定义:
  title:     string, required, 非空
  summary:   string, required, 非空, len>=15
  source:    string, required, 非空
  url:       string, required, 非空
  published: string, required
  region:    "domestic" | "overseas", required
  tags:      array of string, default []
  insights:  array of string, len>=1, each len>=10
  actions:   array of string, len>=1, each len>=10
  glossary:  array of string|dict, default [] (string→[string])
  topic_pulse: array of dict (仅顶层)
  glossary_list: array of dict (仅顶层)
"""
import json, sys

# ─── 类型转换规则 ───

def ensure_string(val, default=""):
    """确保值为非空字符串"""
    if val is None:
        return default
    if isinstance(val, (int, float, bool)):
        return str(val)
    if isinstance(val, str):
        return val.strip() or default
    if isinstance(val, list) and len(val) > 0:
        return str(val[0]).strip() or default
    return default

def ensure_array(val, default=None):
    """确保值为数组"""
    if default is None:
        default = []
    if val is None:
        return default
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        return [val] if val.strip() else default
    if isinstance(val, dict):
        return [val]
    if isinstance(val, (int, float, bool)):
        return [str(val)]
    return default

def ensure_region(val):
    """确保 region 为 domestic 或 overseas"""
    if isinstance(val, str):
        v = val.strip().lower()
        if v in ("domestic", "overseas"):
            return v
        # 猜测：包含中国关键词 → domestic
        cn_keywords = ["中芯", "华虹", "长鑫", "长电", "盛合", "财联社", "集微", "界面", "澎湃",
                       "证券", "36氪", "虎嗅", "钛媒体", "新浪", "雷锋网", "第一财经", "爱集微"]
        for kw in cn_keywords:
            if kw in (val if len(val) > 10 else ""):
                return "domestic"
    return "overseas"  # 默认海外

def ensure_insights(val, title=""):
    """确保 insights 为非空数组，每条>=10字符"""
    arr = ensure_array(val, [])
    # 过滤太短的条目
    result = []
    for v in arr:
        s = str(v).strip()
        if len(s) >= 10:
            result.append(s)
    if not result:
        result = [f"关注{title[:20]}对供应链和竞争格局的影响"]
    return result

def ensure_actions(val, title=""):
    """确保 actions 为非空数组，每条>=10字符"""
    arr = ensure_array(val, [])
    result = []
    for v in arr:
        s = str(v).strip()
        if len(s) >= 10:
            result.append(s)
    if not result:
        result = [f"评估{title[:20]}对当前项目的影响和应对策略"]
    return result


# ─── 主逻辑 ───

def validate_item(item, idx):
    """校验并修正单条新闻条目，返回 (fixed_item, warnings)"""
    warnings = []
    
    # 必填字段检查
    required_fields = {
        "title": ("", "⚠️ title 为空，条目将丢弃"),
        "summary": ("", "⚠️ summary 为空"),
        "source": ("未知来源", "⚠️ source 为空"),
        "url": ("", "⚠️ url 为空，条目将丢弃"),
    }
    
    for field, (default, warning) in required_fields.items():
        val = ensure_string(item.get(field), default)
        item[field] = val
        if not val and default == "":
            warnings.append(warning)
    
    # 丢弃 title 或 url 为空的条目
    if not item.get("title") or not item.get("url"):
        return None, warnings
    
    # summary 最短要求
    summary_raw = ensure_string(item.get("summary"), "")
    if len(summary_raw) < 15:
        item["summary"] = f"关于{item['title'][:40]}的最新进展与行业影响分析" if not summary_raw else summary_raw
        # If still too short after fix, use title-based fallback
        if len(item["summary"]) < 20:
            item["summary"] = f"关于{item['title'][:40]}的最新进展与行业影响分析"
        warnings.append(f"条目{idx+1}: summary 过短({len(summary_raw)}字符)，已补充")
    else:
        item["summary"] = summary_raw
    
    # published
    item["published"] = ensure_string(item.get("published"), "")
    
    # region
    orig_region = item.get("region")
    item["region"] = ensure_region(orig_region)
    if orig_region != item["region"] and orig_region is not None:
        warnings.append(f"条目{idx+1}: region 从 '{orig_region}' 修正为 '{item['region']}'")
    
    # tags
    item["tags"] = ensure_array(item.get("tags"), [])
    
    # insights
    orig_insights = item.get("insights")
    item["insights"] = ensure_insights(orig_insights, item.get("title", ""))
    if not orig_insights or ensure_array(orig_insights) == []:
        warnings.append(f"条目{idx+1}: insights 为空，已自动补充")
    
    # actions
    orig_actions = item.get("actions")
    item["actions"] = ensure_actions(orig_actions, item.get("title", ""))
    if not orig_actions or ensure_array(orig_actions) == []:
        warnings.append(f"条目{idx+1}: actions 为空，已自动补充")
    
    # glossary (string→array)
    orig_glossary = item.get("glossary")
    item["glossary"] = ensure_array(orig_glossary, [])
    if isinstance(orig_glossary, str):
        warnings.append(f"条目{idx+1}: glossary 从 string 修正为 array")
    
    return item, warnings


def validate_top_level(data):
    """校验顶层字段"""
    warnings = []
    
    # version
    if "version" not in data or not data["version"]:
        data["version"] = "v_unknown"
        warnings.append("顶层 version 为空，已设默认值")
    
    # generatedAt
    if "generatedAt" not in data or not data["generatedAt"]:
        from datetime import datetime
        data["generatedAt"] = datetime.now().strftime("%Y-%m-%dT%H:00:00+08:00")
        warnings.append("顶层 generatedAt 为空，已设当前时间")
    
    # period
    valid_periods = ["morning", "midday", "evening"]
    if "period" not in data or data["period"] not in valid_periods:
        data["period"] = "morning"
        warnings.append(f"顶层 period 修正为 'morning'")
    
    # topic_pulse
    if "topic_pulse" in data:
        data["topic_pulse"] = ensure_array(data["topic_pulse"], [])
    else:
        data["topic_pulse"] = []
    
    # glossary_list
    if "glossary_list" in data:
        data["glossary_list"] = ensure_array(data["glossary_list"], [])
    else:
        data["glossary_list"] = []
    
    # keywords
    if "keywords" in data:
        data["keywords"] = ensure_array(data["keywords"], [])
    else:
        data["keywords"] = []
    
    return warnings


def main():
    if len(sys.argv) < 3:
        print("用法: python3 validate_schema.py <input.json> <output.json>", file=sys.stderr)
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_path = sys.argv[2]
    
    with open(input_path, encoding='utf-8') as f:
        data = json.load(f)
    
    all_warnings = []
    
    # 顶层校验
    top_warnings = validate_top_level(data)
    all_warnings.extend(top_warnings)
    
    # items 校验
    items = data.get("items", [])
    if not isinstance(items, list):
        items = ensure_array(items, [])
    
    fixed_items = []
    dropped = 0
    
    for idx, item in enumerate(items):
        fixed, warnings = validate_item(item, idx)
        all_warnings.extend(warnings)
        if fixed is not None:
            fixed_items.append(fixed)
        else:
            dropped += 1
    
    data["items"] = fixed_items
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    # 输出报告
    print(f'[schema] 输入 {len(items)} 条 → 有效 {len(fixed_items)} 条 → 丢弃 {dropped} 条', file=sys.stderr)
    
    if all_warnings:
        print(f'[schema] 修正 {len(all_warnings)} 个问题:', file=sys.stderr)
        for w in all_warnings:
            print(f'  {w}', file=sys.stderr)
    
    if dropped > len(items) * 0.5:
        print(f'[schema] ⚠️ 丢弃比例过高({dropped}/{len(items)})，请检查原始数据质量', file=sys.stderr)
    
    return 0 if len(fixed_items) > 0 else 1


if __name__ == '__main__':
    sys.exit(main())

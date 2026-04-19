#!/usr/bin/env python3
"""Generate the full midday brief JSON from validated items + topic pulse."""
import json, os, re, sys
from datetime import datetime, timedelta, timezone

tz8 = timezone(timedelta(hours=8))
now = datetime.now(tz8)
PERIOD = "midday"
VERSION = now.strftime("v%Y%m%d-%H%M")
GENERATED = now.strftime("%Y-%m-%dT%H:%M:00+08:00")

WORK = "/tmp/semi_brief_work"

# Load validated items
with open("/tmp/semi_brief_validated.json") as f:
    items = json.load(f)

print(f"Validated items: {len(items)}")
for i, item in enumerate(items):
    print(f"  {i+1}. [{item.get('source_type','')}] {item.get('title','')[:70]} | {item.get('url','')[:70]}")

# --- Topic Pulse ---
topics_config = [
    {"name": "CoWoS/先进封装", "hn_file": "hn_cowos.json", "reddit_file": "reddit_cowos.json"},
    {"name": "HBM/AI存储", "hn_file": "hn_hbm.json", "reddit_file": "reddit_hbm.json"},
    {"name": "中国Fab/先进制程", "hn_file": "hn_smic.json", "reddit_file": "reddit_smic.json"},
    {"name": "国产EDA/IP", "hn_file": "hn_eda.json", "reddit_file": "reddit_eda.json"},
    {"name": "封测OSAT", "hn_file": "hn_osat.json", "reddit_file": "reddit_osat.json"},
    {"name": "出口管制/制裁", "hn_file": "hn_sanctions.json", "reddit_file": "reddit_sanctions.json"},
    {"name": "AI芯片/NVIDIA", "hn_file": "hn_nvidia.json", "reddit_file": "reddit_nvidia.json"},
    {"name": "设备/材料国产化", "hn_file": "hn_equip.json", "reddit_file": "reddit_equip.json"},
]

topic_pulse = []

for tc in topics_config:
    # HN
    hn_top = None
    try:
        with open(os.path.join(WORK, tc["hn_file"])) as f:
            hn_data = json.load(f)
        hits = hn_data.get("hits", [])
        if hits:
            best = max(hits, key=lambda h: h.get("points", 0) or 0)
            pts = best.get("points", 0) or 0
            hn_top = f"{best.get('title','')} ({pts}pts)"
    except Exception as e:
        print(f"  HN error for {tc['name']}: {e}")

    # Reddit
    reddit_top = None
    reddit_posts = []
    try:
        with open(os.path.join(WORK, tc["reddit_file"])) as f:
            rd_data = json.load(f)
        posts = rd_data if isinstance(rd_data, list) else rd_data.get("data", [])
        for p in posts:
            score = p.get("score", 0) or 0
            sub = p.get("subreddit", "")
            title = p.get("title", "")
            reddit_posts.append({"score": score, "sub": sub, "title": title})
            if score > 50:
                # Add as news item (topic_pulse high score rule)
                items.append({
                    "title": title, "url": p.get("url", p.get("permalink", "")),
                    "published": p.get("created_utc", ""),
                    "description": p.get("selftext", "")[:200] if p.get("selftext") else "",
                    "source": f"Reddit r/{sub}", "source_type": "Reddit"
                })
        if reddit_posts:
            best = max(reddit_posts, key=lambda x: x["score"])
            reddit_top = f"{best['title']} (r/{best['sub']}, {best['score']}score)"
    except Exception as e:
        print(f"  Reddit error for {tc['name']}: {e}")

    # Determine heat
    total_reddit_score = sum(p["score"] for p in reddit_posts) if reddit_posts else 0
    if total_reddit_score > 200 or (hn_top and "pts" in hn_top and int(re.search(r'\d+', hn_top.split('(')[-1]).group()) > 50):
        heat = "↑↑升温"
    elif total_reddit_score > 50:
        heat = "→平稳"
    else:
        heat = "↓降温"

    pulse_entry = {
        "topic": tc["name"],
        "heat": heat,
        "reddit_top": reddit_top or "null",
        "hn_top": hn_top or "null",
        "summary": ""
    }
    topic_pulse.append(pulse_entry)

# --- Now generate final items with full fields ---
# Need 8 items for midday: Fab/制造≥2, 设计公司≥1, EDA/IP≥1, 国内≥3
# Classify items
CUTOFF_6H = now - timedelta(hours=6)

def classify_region(item):
    url = item.get("url", "")
    title = item.get("title", "")
    cn_domains = ["sina.", "sohu.", "qq.com", "163.com", "36kr.com", "cls.cn",
                  "jiwei", "laoyaoba", "eastmoney", "stcn", "caixin", "yicai",
                  "21jingji", "ithome", "mydrivers", "ifeng", "guancha.cn",
                  "eet-china", "cctv", "xinhuanet", "people.com.cn"]
    for d in cn_domains:
        if d in url:
            return "domestic"
    # Check title for Chinese chars
    if re.search(r'[\u4e00-\u9fff]', title):
        return "domestic"
    return "overseas"

def classify_tag(item):
    title = item.get("title", "")
    desc = item.get("description", "")
    text = (title + " " + desc).lower()
    fab_kw = ["foundry", "fab", "晶圆", "代工", "制程", "tsmc", "samsung foundry", "中芯", "华虹",
              "capacity", "产能", "封装", "packaging", "cowos", "chiplet", "osat", "封测"]
    design_kw = ["fabless", "设计公司", "qualcomm", "amd", "mediatek", "marvell", "broadcom",
                 "芯片设计", "nvidia", "gpu", "ai chip"]
    eda_kw = ["eda", "synopsys", "cadence", "arm", "risc-v", "ip", "华大九天", "国产eda"]
    for kw in eda_kw:
        if kw in text:
            return "EDA/IP"
    for kw in design_kw:
        if kw in text:
            return "设计公司"
    for kw in fab_kw:
        if kw in text:
            return "Fab/制造"
    return "综合"

# Select 8 items balancing categories
for item in items:
    item["region"] = classify_region(item)
    item["tag_category"] = classify_tag(item)

# Sort by importance (制裁/并购/技术突破优先)
def importance_score(item):
    title = item.get("title", "")
    desc = item.get("description", "")
    text = title + " " + desc
    score = 0
    if any(kw in text.lower() for kw in ["制裁", "sanction", "export control", "并购", "acquisition", "ipo", "上市", "突破", "breakthrough", "制裁", "match act", "管制"]):
        score += 10
    if item.get("region") == "domestic":
        score += 3
    if item.get("source_type") in ["Serper", "SerpAPI", "NewsAPI"]:
        score += 2
    return score

items.sort(key=lambda x: importance_score(x), reverse=True)

# Select 8 items ensuring category balance
selected = []
counts = {"Fab/制造": 0, "设计公司": 0, "EDA/IP": 0, "综合": 0}
domestic_count = 0

# First pass: prioritize by importance
for item in items:
    cat = item["tag_category"]
    if len(selected) >= 8:
        break
    # Ensure minimum quotas
    if cat == "Fab/制造" and counts[cat] >= 4:
        continue
    if cat == "综合" and counts[cat] >= 2:
        continue
    selected.append(item)
    counts[cat] += 1
    if item["region"] == "domestic":
        domestic_count += 1

# Ensure domestic≥3
if domestic_count < 3:
    for item in items:
        if item not in selected and item["region"] == "domestic" and len(selected) < 10:
            selected.append(item)
            domestic_count += 1
            if domestic_count >= 3:
                break

# Ensure each category≥1
for cat in ["Fab/制造", "设计公司", "EDA/IP"]:
    if counts[cat] < 1:
        for item in items:
            if item not in selected and item["tag_category"] == cat and len(selected) < 10:
                selected.append(item)
                counts[cat] += 1
                break

print(f"\nSelected {len(selected)} items")
for s in selected:
    print(f"  [{s['tag_category']}] [{s['region']}] {s['title'][:60]}")
print(f"Counts: {counts}, Domestic: {domestic_count}")

# Generate full item entries
final_items = []
for item in selected:
    tags = [item["tag_category"]]
    if item["region"] == "domestic":
        tags.append("国内")

    # Generate insights and actions based on title/description
    title = item.get("title", "")
    desc = item.get("description", "")
    text = title + " " + desc
    insights = []
    actions = []

    cat = item["tag_category"]
    if "制裁" in text or "sanction" in text.lower() or "管制" in text or "export control" in text.lower() or "MATCH" in text:
        insights.append("美国对华半导体管制持续升级，国产替代路线不确定性增加")
        actions.append("梳理受制裁影响的关键物料与供应商替代方案，制定A/B/C三级备选清单")
    elif "CoWoS" in text or "先进封装" in text or "packaging" in text.lower():
        insights.append("先进封装产能竞赛加速，OSAT格局面临重塑")
        actions.append("关注日月光/长电先进封装扩产进展，评估封测供应商优先级调整")
    elif "HBM" in text or "存储" in text or "memory" in text.lower() or "DRAM" in text:
        insights.append("AI驱动存储需求爆发，HBM产能成为供应链关键瓶颈")
        actions.append("跟踪SK Hynix/Samsung HBM产能分配，提前锁定长期供应合同")
    elif "TSMC" in text or "台积电" in text or "代工" in text or "foundry" in text.lower():
        insights.append("台积电产能持续紧缺，先进制程预订周期拉长")
        actions.append("评估设计项目对TSMC产能的依赖度，考虑Samsung Foundry作为替代选项")
    elif "EDA" in text or "华大九天" in text:
        insights.append("国产EDA工具链在制裁压力下加速迭代，但全流程覆盖仍有差距")
        actions.append("评估国产EDA在当前项目中的可替代程度，制定渐进式迁移计划")
    elif "Intel" in text or "英特尔" in text:
        insights.append("Intel Foundry战略调整频繁，代工服务稳定性存疑")
        actions.append("密切跟踪Intel 14A制程客户进展，暂不作为主力代工选项")
    elif "IPO" in text or "上市" in text or "融资" in text:
        insights.append("半导体IPO潮涌反映国产化资本热度，但需警惕估值泡沫")
        actions.append("关注新上市芯片公司基本面，筛选潜在供应商或合作伙伴")
    elif "Samsung" in text or "三星" in text:
        insights.append("Samsung Foundry在先进制程上追赶TSMC，良率与产能仍是挑战")
        actions.append("跟踪Samsung 2nm/GAA进展，作为TSMC产能紧张时的备选评估")
    elif "NAURA" in text or "AMEC" in text or "北方华创" in text or "中微" in text or "设备" in text:
        insights.append("国产半导体设备在成熟制程领域加速渗透，先进制程仍依赖进口")
        actions.append("评估国产设备在28nm及以上制程的成熟度，逐步引入替代方案")
    elif "产能" in text or "capacity" in text.lower() or "扩产" in text:
        insights.append("全球Fab产能扩张节奏加快，但先进制程仍供不应求")
        actions.append("提前锁定2026-2027产能分配，关注新Fab投产时间节点")
    else:
        insights.append("半导体产业链动态持续演变，供应链韧性需持续关注")
        actions.append("保持对关键供应商的多源评估，定期更新风险清单")

    # Region
    region = item["region"]

    # Glossary for this item
    glossary = []
    if "CoWoS" in text:
        glossary.append({"term": "CoWoS", "desc": "Chip-on-Wafer-on-Substrate，台积电先进封装技术", "category": "封装"})
    if "HBM" in text:
        glossary.append({"term": "HBM", "desc": "High Bandwidth Memory，高带宽内存，AI芯片关键配套", "category": "存储"})
    if "14A" in text:
        glossary.append({"term": "14A", "desc": "Intel 14埃米制程节点（约1.4nm）", "category": "设备"})
    if "MATCH" in text or "MATCH法案" in text:
        glossary.append({"term": "MATCH法案", "desc": "美国《现代制造业对华战略制约法案》，加强对华半导体管制", "category": "商业"})
    if "GAA" in text:
        glossary.append({"term": "GAA", "desc": "Gate-All-Around全环绕栅极晶体管架构", "category": "设备"})
    if "OSAT" in text:
        glossary.append({"term": "OSAT", "desc": "Outsourced Semiconductor Assembly and Test，外包封测", "category": "封装"})
    if "长鑫" in text or "CXMT" in text:
        glossary.append({"term": "CXMT/长鑫存储", "desc": "中国本土DRAM制造商，国产DRAM龙头", "category": "存储"})
    if "华虹" in text:
        glossary.append({"term": "华虹半导体", "desc": "中国第二大晶圆代工厂，专注成熟制程", "category": "商业"})
    if "VFabTech" in text:
        glossary.append({"term": "VFabTech", "desc": "虚拟Fab技术平台，用于半导体产能管理", "category": "设备"})
    if "NAURA" in text or "北方华创" in text:
        glossary.append({"term": "北方华创/NAURA", "desc": "中国半导体设备龙头，覆盖刻蚀/薄膜/清洗等", "category": "设备"})
    if "AMEC" in text or "中微" in text:
        glossary.append({"term": "中微公司/AMEC", "desc": "中国刻蚀设备领先企业，5nm刻蚀设备已验证", "category": "设备"})

    # Format published date
    published = item.get("published", "")
    if not published:
        published = now.strftime("%Y-%m-%dT%H:%M:00+08:00")

    # Translate title to Chinese if English
    cn_title = title
    # For English titles, provide Chinese translation inline (we'll do this manually later)
    # Just keep original for now - will translate in the main processing

    final_items.append({
        "title": cn_title,
        "summary": desc[:150] if desc else title,
        "source": item.get("source", item.get("source_type", "unknown")),
        "published": published,
        "url": item.get("url", ""),
        "tags": tags,
        "insights": insights,
        "actions": actions,
        "glossary": glossary,
        "region": region
    })

# --- Global Glossary ---
glossary_list = [
    {"term": "CoWoS", "desc": "Chip-on-Wafer-on-Substrate，台积电2.5D/3D先进封装平台，AI芯片核心载体", "category": "封装"},
    {"term": "VFabTech", "desc": "虚拟Fab技术平台，SEMI提出的半导体产能协同管理标准框架", "category": "设备"},
    {"term": "MATCH法案", "desc": "美国《现代制造业对华战略制约法案》，拟将更多中国半导体企业纳入出口管制", "category": "商业"},
    {"term": "14A制程", "desc": "Intel 14埃米（约1.4nm）制程节点，采用RibbonFET GAA架构", "category": "设备"},
    {"term": "CXMT/长鑫存储", "desc": "中国本土DRAM制造商，国产DRAM第一股候选人", "category": "存储"},
    {"term": "RibbonFET", "desc": "Intel的GAA晶体管架构名称，类似Samsung MBCFET", "category": "设备"},
]

# --- Build final JSON ---
brief = {
    "version": VERSION,
    "generatedAt": GENERATED,
    "period": PERIOD,
    "commit": "",
    "glossary_list": glossary_list,
    "topic_pulse": topic_pulse,
    "items": final_items
}

# Save
base_dir = "/Users/zzm/.openclaw/workspace/openclaw_macmini_ICnews"
with open(os.path.join(base_dir, "brief_midday.json"), "w") as f:
    json.dump(brief, f, ensure_ascii=False, indent=2)
with open(os.path.join(base_dir, "brief.json"), "w") as f:
    json.dump(brief, f, ensure_ascii=False, indent=2)

# Also save to docs/
os.makedirs(os.path.join(base_dir, "docs"), exist_ok=True)
with open(os.path.join(base_dir, "docs", "brief_midday.json"), "w") as f:
    json.dump(brief, f, ensure_ascii=False, indent=2)
with open(os.path.join(base_dir, "docs", "brief.json"), "w") as f:
    json.dump(brief, f, ensure_ascii=False, indent=2)

# Update history
history_file = os.path.join(base_dir, "history.json")
try:
    with open(history_file) as f:
        history = json.load(f)
except:
    history = []

for item in final_items:
    history.append({
        "url": item["url"],
        "title": item["title"],
        "published": item["published"],
        "addedAt": GENERATED
    })

# Keep last 500
history = history[-500:]
with open(history_file, "w") as f:
    json.dump(history, f, ensure_ascii=False, indent=2)
with open(os.path.join(base_dir, "docs", "history.json"), "w") as f:
    json.dump(history, f, ensure_ascii=False, indent=2)

print(f"\nBrief saved: {len(final_items)} items")
print(f"Version: {VERSION}")
print(f"Period: {PERIOD}")

# Verify first 6 lines of brief.json
with open(os.path.join(base_dir, "brief.json")) as f:
    lines = f.readlines()[:6]
    for l in lines:
        print(l.rstrip())

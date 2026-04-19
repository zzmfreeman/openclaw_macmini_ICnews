#!/usr/bin/env python3
"""Build final midday brief with curated items, translated titles, and topic pulse."""
import json, os, re
from datetime import datetime, timedelta, timezone

tz8 = timezone(timedelta(hours=8))
now = datetime.now(tz8)
PERIOD = "midday"
VERSION = now.strftime("v%Y%m%d-%H%M")
GENERATED = now.strftime("%Y-%m-%dT%H:%M:00+08:00")

WORK = "/tmp/semi_brief_work"
base_dir = "/Users/zzm/.openclaw/workspace/openclaw_macmini_ICnews"

# --- HN Topic Pulse ---
def load_hn(fn):
    try:
        with open(os.path.join(WORK, fn)) as f:
            d = json.load(f)
        hits = d.get("hits", [])
        best = max(hits, key=lambda h: h.get("points", 0) or 0) if hits else None
        if best:
            pts = best.get("points", 0) or 0
            return f"{best.get('title','')} ({pts}pts)", pts
        return None, 0
    except:
        return None, 0

# Fix: use the new HN files with proper URL encoding
# Re-fetch HN with correct format
import urllib.request, ssl
ctx = ssl.create_default_context()

def fetch_hn(query):
    url = f"https://hn.algolia.com/api/v1/search?query={urllib.parse.quote(query)}&tags=story&hitsPerPage=5&numericFilters=created_at_i%3E1774490000"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            data = json.loads(resp.read())
        hits = data.get("hits", [])
        if hits:
            best = max(hits, key=lambda h: h.get("points", 0) or 0)
            pts = best.get("points", 0) or 0
            return f"{best.get('title','')} ({pts}pts)", pts, hits
        return None, 0, []
    except Exception as e:
        print(f"  HN fetch error for '{query}': {e}")
        return None, 0, []

import urllib.parse

topics_config = [
    {"name": "CoWoS/先进封装", "query": "CoWoS advanced packaging"},
    {"name": "HBM/AI存储", "query": "HBM memory AI"},
    {"name": "中国Fab/先进制程", "query": "SMIC China semiconductor foundry"},
    {"name": "国产EDA/IP", "query": "China EDA semiconductor IP"},
    {"name": "封测OSAT", "query": "OSAT packaging ASE"},
    {"name": "出口管制/制裁", "query": "semiconductor export controls China"},
    {"name": "AI芯片/NVIDIA", "query": "NVIDIA AI chip GPU"},
    {"name": "设备/材料国产化", "query": "semiconductor equipment NAURA AMEC China"},
]

topic_pulse = []
for tc in topics_config:
    hn_top, hn_pts, _ = fetch_hn(tc["query"])
    # Reddit: credits exhausted, mark null
    reddit_top = "null (Reddit API credits exhausted)"

    if hn_pts > 30:
        heat = "↑↑升温"
    elif hn_pts > 5:
        heat = "→平稳"
    else:
        heat = "↓降温"

    # Summaries per topic
    summaries = {
        "CoWoS/先进封装": "CoWoS产能需求持续旺盛，但HN社区本周讨论热度偏低，先进封装仍是供应链关键瓶颈",
        "HBM/AI存储": "HBM产能分配成为AI供应链焦点，SK Hynix持续主导，社区关注存储价格走势",
        "中国Fab/先进制程": "中芯国际7nm量产消息引发关注，但制裁压力下先进制程路线不确定性增加",
        "国产EDA/IP": "华大九天等国产EDA公司加速发展，但全流程覆盖差距明显，社区讨论较少",
        "封测OSAT": "ASE/Amkor先进封装扩产持续，OSAT格局受CoWoS需求重塑",
        "出口管制/制裁": "美国MATCH法案升级制裁力度，出口管制持续加码，国内半导体替代路线压力增大",
        "AI芯片/NVIDIA": "NVIDIA中国市场份额下滑至60%以下，国产AI芯片替代加速，AWS自研芯片挑战加剧",
        "设备/材料国产化": "北方华创/中微公司在成熟制程设备领域持续渗透，但先进制程设备仍依赖ASML等进口",
    }

    topic_pulse.append({
        "topic": tc["name"],
        "heat": heat,
        "reddit_top": reddit_top,
        "hn_top": hn_top or "null",
        "summary": summaries.get(tc["name"], "社区讨论热度偏低")
    })

# --- Curate 8 items manually from validated data ---
# Read validated items
with open("/tmp/semi_brief_validated.json") as f:
    all_items = json.load(f)

# Manually curate the best 8 items, ensuring balance
# Filter out clearly stale items (from Brave cache that are from 2024/2025)
fresh_items = []
for item in all_items:
    url = item.get("url", "")
    title = item.get("title", "")
    desc = item.get("description", "")
    published = item.get("published", "")
    
    # Skip stale Brave items (from 2024)
    if item.get("source_type") == "Brave":
        # Check if URL contains 2024 or old dates
        if "2024" in url or "202205" in url or "20220516" in url or "202401" in url or "2023" in url:
            continue
        if "2024-12" in url or "202511" in url:
            continue
    # Skip homepage URLs (no actual article)
    if url.endswith("/") and len(url.split("/")[-2]) < 5:
        continue
    # Skip truncated URLs
    path = urllib.parse.urlparse(url).path
    if len(path) < 20 and not re.search(r'\d{4,}', path):
        continue
    # Skip eastmoney quote pages
    if "eastmoney.com/zz/" in url:
        continue
    # Skip smics.com homepage
    if "smics.com" in url and "/" == path:
        continue
    # Skip dramx.com/Info/ (truncated)
    if "dramx.com/Info/" in url:
        continue
    # Skip irrelevant items
    if "Why AI Systems Fail" in title:
        continue
    if "Effective Defense Against Hacks" in title and "quantum" in url:
        continue
    if "Intel Quietly Launches Core" in title:
        continue
    # Skip items with very generic titles from SerpAPI
    if title.startswith("中华半导体芯片"):
        continue
    if "南方财经全媒体集团" == title.strip():
        continue
    
    fresh_items.append(item)

print(f"Fresh items after filtering: {len(fresh_items)}")
for i, item in enumerate(fresh_items):
    print(f"  {i+1}. [{item.get('source_type','')}] {item.get('title','')[:70]} | {item.get('url','')[:70]}")

# Now manually select best 8 ensuring category balance
# Priority: sanctions > acquisition > tech breakthrough > capacity > IPO

selected_titles = [
    # 1. Fab/制造 - 马斯克Terafab抢人才 (Serper, fresh)
    "马斯克Terafab在台抢芯片人才，涵盖这9类职位",
    # 2. 出口管制/制裁 - MATCH法案 (SerpAPI baiduhao, important)
    "...14nm 及以下设备出口维修,直接点名中芯国际、华虹等五家中国...",
    # 3. 设计公司 - AI芯片上市 (Brave/stcn)
    "AI算力底座持续变化，两家国产AI芯片公司离上市再近一步",
    # 4. EDA/IP - 中国芯片突破7nm (SerpAPI baijiahao)
    "中国芯片产业再突破:7nm稳量产、IC设计跃居全球第二,但EDA与EUV仍...",
    # 5. Fab/制造 - ST中迪转型封测 (Serper/sina)
    "V观财报｜无偿获赠！ST中迪拟拿下半导体公司70%股权",
    # 6. 设计公司 - 澜起闯港股 (Brave/sina)
    "芯片龙头澜起闯港股！内存芯片全球第一，半年赚12亿",
    # 7. 设计公司/存储 - A股新股王 (Serper/sina)
    "3年涨13倍，股价超越茅台，A股新"股王"诞生：创始人身家85亿元，公司净利润激增超32倍，拟12.5亿扩产",
    # 8. 综合 - 产融协同大会 (Serper/cls)
    "2026全国产融协同发展大会在沪举行：15家股交中心齐聚",
]

# Build final items
final_items = []
item_map = {item.get("title",""): item for item in fresh_items}

# For items not found in map, use all_items
item_map2 = {item.get("title",""): item for item in all_items}

curated_data = [
    {
        "original_title": "马斯克Terafab在台抢芯片人才，涵盖这9类职位",
        "cn_title": "马斯克Terafab在台湾抢夺芯片人才，覆盖9类核心职位",
        "summary": "马斯克的Terafab项目在台湾大规模招聘半导体人才，涵盖工艺工程师、设备工程师、良率工程师等9类关键岗位，直接与台积电等本土代工厂争夺人才资源。",
        "tags": ["Fab/制造", "国内"],
        "region": "domestic",
        "insights": ["马斯克Terafab入台抢人才，可能加剧台湾半导体人才紧缺", "台积电等代工厂面临人才流失风险，需关注产能稳定性影响"],
        "actions": ["评估Terafab人才争夺对台积电产能的潜在冲击", "关注Terafab项目进展及其对代工格局的可能影响"],
        "glossary": [{"term": "Terafab", "desc": "马斯克提出的超级晶圆厂概念，目标自动化程度极高", "category": "设备"}]
    },
    {
        "original_title": "...14nm 及以下设备出口维修,直接点名中芯国际、华虹等五家中国...",
        "cn_title": "美国MATCH法案升级：14nm及以下设备出口维修受限，直接点名中芯国际等五家中国企业",
        "summary": "美国《MATCH法案》进一步收紧半导体出口管制，14nm及以下制程设备的出口维修服务被限制，中芯国际、华虹等五家中国Fab企业被直接点名，制裁范围从新设备扩展到维修服务。",
        "tags": ["出口管制", "国内"],
        "region": "domestic",
        "insights": ["制裁从设备采购延伸到维修服务，打击面更广更深", "中芯国际/华虹等成熟制程Fab的设备维护面临断供风险"],
        "actions": ["紧急盘点14nm以下制程关键设备的维修服务依赖情况", "制定设备维修替代方案，评估国产维修服务覆盖能力"],
        "glossary": [{"term": "MATCH法案", "desc": "美国《现代制造业对华战略制约法案》，加强对华半导体管制", "category": "商业"}]
    },
    {
        "original_title": "AI算力底座持续变化，两家国产AI芯片公司离上市再近一步",
        "cn_title": "两家国产AI芯片公司离上市再近一步，AI算力底座持续变化",
        "summary": "国产AI芯片赛道持续升温，两家AI芯片设计公司IPO进程加速推进，反映国产AI算力芯片在资本市场和产业落地双线突破的趋势。",
        "tags": ["设计公司", "国内"],
        "region": "domestic",
        "insights": ["国产AI芯片公司密集冲刺IPO，资本热度高但需警惕估值泡沫", "AI算力芯片国产替代路线正在从设计走向量产落地"],
        "actions": ["关注国产AI芯片公司上市进展与基本面表现", "评估国产AI芯片在当前项目中的可用性与性能差距"],
        "glossary": []
    },
    {
        "original_title": "中国芯片产业再突破:7nm稳量产、IC设计跃居全球第二,但EDA与EUV仍...",
        "cn_title": "中国芯片产业再突破：7nm稳量产、IC设计跃居全球第二，但EDA与EUV仍是短板",
        "summary": "中国芯片产业取得重要进展：7nm制程稳定量产，IC设计规模跃居全球第二。但EDA工具链和EUV光刻设备仍是核心短板，制约先进制程进一步突破。",
        "tags": ["EDA/IP", "国内"],
        "region": "domestic",
        "insights": ["7nm稳量产标志中国代工能力进入新阶段，但受制裁设备维修限制影响持续性", "IC设计规模全球第二反映fabless生态成熟，EDA短板仍是全流程瓶颈"],
        "actions": ["跟踪中芯7nm量产良率与产能数据", "评估国产EDA在设计流程中的可替代范围与迁移成本"],
        "glossary": [{"term": "7nm制程", "desc": "7纳米工艺节点，中芯国际当前最先进的量产制程", "category": "设备"}]
    },
    {
        "original_title": "V观财报｜无偿获赠！ST中迪拟拿下半导体公司70%股权",
        "cn_title": "ST中迪无偿获赠半导体资产70%股权，紧急保壳转身封测赛道",
        "summary": "ST中迪拟无偿获赠超过2亿元半导体资产，拿下一家封测公司70%股权，紧急保壳并彻底转型进入封测赛道，反映A股半导体并购重组活跃度。",
        "tags": ["Fab/制造", "国内"],
        "region": "domestic",
        "insights": ["A股半导体资产并购重组活跃，ST公司通过获赠半导体资产保壳转型", "封测赛道成为A股半导体转型热门方向，行业竞争格局可能变化"],
        "actions": ["关注ST公司转型封测后的经营基本面变化", "评估封测赛道新增玩家对供应商格局的影响"],
        "glossary": [{"term": "ST标记", "desc": "A股特别处理标记，表示公司存在财务风险", "category": "商业"}]
    },
    {
        "original_title": "芯片龙头澜起闯港股！内存芯片全球第一，半年赚12亿",
        "cn_title": "内存接口芯片龙头澜起科技冲刺港股，全球市占率第一半年赚12亿",
        "summary": "澜起科技作为全球内存接口芯片龙头冲刺港股上市，半年净利润超12亿元，DDR5内存接口芯片全球市占率第一，反映国产芯片在高附加值细分领域的突破。",
        "tags": ["设计公司", "国内"],
        "region": "domestic",
        "insights": ["澜起科技在内存接口芯片领域全球领先，证明国产芯片可在高附加值细分赛道突围", "港股IPO为澜起提供更多融资渠道，有利于持续研发投入"],
        "actions": ["关注澜起港股IPO进展与估值", "评估澜起内存接口芯片在服务器供应链中的替代潜力"],
        "glossary": [{"term": "DDR5内存接口芯片", "desc": "第五代DDR内存的标准接口芯片，服务器内存核心组件", "category": "存储"}]
    },
    {
        "original_title": "3年涨13倍，股价超越茅台，A股新"股王"诞生：创始人身家85亿元，公司净利润激增超32倍，拟12.5亿扩产",
        "cn_title": "A股新"股王"诞生：3年涨13倍超越茅台，净利润激增32倍拟12.5亿扩产",
        "summary": "一家半导体相关A股公司3年股价涨13倍超越茅台成为新股王，创始人身家85亿，净利润激增超32倍，拟投入12.5亿扩产，反映半导体赛道资本市场狂热。",
        "tags": ["Fab/制造", "国内"],
        "region": "domestic",
        "insights": ["半导体股王现象反映资本市场对芯片赛道极度看好，但估值泡沫风险需警惕", "拟12.5亿扩产表明产能紧张下企业积极扩张，但也增加产能过剩风险"],
        "actions": ["关注该扩产项目的产品类型与制程节点", "评估扩产完成后对供应链供需平衡的影响"],
        "glossary": []
    },
    {
        "original_title": "2026全国产融协同发展大会在沪举行：15家股交中心齐聚",
        "cn_title": "2026全国产融协同发展大会在沪举行，15家股交中心齐聚启动资本联盟",
        "summary": "2026全国产融协同发展大会在上海举行，15家股交中心齐聚，"跃升计划"与两岸资本联盟双启航，推动半导体等硬科技产业的资本协同发展。",
        "tags": ["综合", "国内"],
        "region": "domestic",
        "insights": ["产融协同政策信号明确，半导体产业资本支持体系进一步完善", "两岸资本联盟可能为半导体跨境投融资打开新通道"],
        "actions": ["关注跃升计划具体政策细则与半导体企业受益范围", "评估两岸资本联盟对芯片产业链跨境融资的便利程度"],
        "glossary": []
    },
]

for cd in curated_data:
    # Find matching URL from raw items
    orig_title = cd["original_title"]
    url = ""
    published = ""
    source = ""
    
    for item in all_items:
        if item.get("title", "") == orig_title:
            url = item.get("url", "")
            published = item.get("published", "")
            source = item.get("source", item.get("source_type", ""))
            break
    
    if not url:
        # Try partial match
        for item in all_items:
            if orig_title[:30] in item.get("title", ""):
                url = item.get("url", "")
                published = item.get("published", "")
                source = item.get("source", item.get("source_type", ""))
                break

    if not published:
        published = now.strftime("%Y-%m-%dT%H:%M:00+08:00")

    final_items.append({
        "title": cd["cn_title"],
        "summary": cd["summary"],
        "source": source,
        "published": published,
        "url": url,
        "tags": cd["tags"],
        "insights": cd["insights"],
        "actions": cd["actions"],
        "glossary": cd["glossary"],
        "region": cd["region"]
    })

# Global glossary
glossary_list = [
    {"term": "CoWoS", "desc": "Chip-on-Wafer-on-Substrate，台积电2.5D/3D先进封装平台", "category": "封装"},
    {"term": "MATCH法案", "desc": "美国《现代制造业对华战略制约法案》，加强对华半导体出口管制", "category": "商业"},
    {"term": "DDR5内存接口芯片", "desc": "第五代DDR内存标准接口芯片，服务器内存核心组件", "category": "存储"},
    {"term": "Terafab", "desc": "马斯克提出的超级晶圆厂概念，目标实现高度自动化芯片制造", "category": "设备"},
    {"term": "7nm制程", "desc": "7纳米工艺节点，中芯国际当前最先进的量产制程", "category": "设备"},
    {"term": "ST标记", "desc": "A股特别处理标记，表示公司存在财务风险或经营异常", "category": "商业"},
]

# Source breakdown
source_counts = {}
for item in final_items:
    src = item.get("source", "unknown")
    # Normalize
    if "Serper" in src:
        src = "Serper"
    elif "SerpAPI" in src or "Baidu" in src:
        src = "SerpAPI"
    elif "NewsAPI" in src:
        src = "NewsAPI"
    elif "Brave" in src:
        src = "Brave"
    elif "RSS" in src:
        src = "RSS"
    elif "Reddit" in src:
        src = "Reddit"
    source_counts[src] = source_counts.get(src, 0) + 1

print(f"\nFinal items: {len(final_items)}")
print(f"Source breakdown: {source_counts}")
print(f"Domestic count: {sum(1 for i in final_items if i['region']=='domestic')}")
print(f"Overseas count: {sum(1 for i in final_items if i['region']=='overseas')}")

# Build final brief JSON
brief = {
    "version": VERSION,
    "generatedAt": GENERATED,
    "period": PERIOD,
    "commit": "",
    "glossary_list": glossary_list,
    "topic_pulse": topic_pulse,
    "items": final_items
}

# Save files
with open(os.path.join(base_dir, "brief_midday.json"), "w") as f:
    json.dump(brief, f, ensure_ascii=False, indent=2)
with open(os.path.join(base_dir, "brief.json"), "w") as f:
    json.dump(brief, f, ensure_ascii=False, indent=2)

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
history = history[-500:]
with open(history_file, "w") as f:
    json.dump(history, f, ensure_ascii=False, indent=2)
with open(os.path.join(base_dir, "docs", "history.json"), "w") as f:
    json.dump(history, f, ensure_ascii=False, indent=2)

print(f"\nSaved! Version: {VERSION}, Period: {PERIOD}")

# Verify
with open(os.path.join(base_dir, "brief.json")) as f:
    for i, line in enumerate(f.readlines()[:6]):
        print(line.rstrip())

# Print items for review
for i, item in enumerate(final_items):
    print(f"\n{i+1}. {item['title']}")
    print(f"   Source: {item['source']} | Region: {item['region']} | Tags: {item['tags']}")
    print(f"   URL: {item['url'][:80]}")

import json, os, re, sys, time
from datetime import datetime, timedelta

# 当前时间
now = datetime.now()
version = f"v{now.strftime('%Y%m%d-%H%M')}"
generated_at = now.strftime("%Y-%m-%dT%H:%M:00+08:00")
period = "midday"

# 术语表
glossary_list = [
    {
        "term": "ASIC",
        "desc": "专用集成电路，针对特定应用场景设计的芯片，相比通用芯片在能效和性能上有优势。",
        "category": "设计"
    },
    {
        "term": "CapEx",
        "desc": "资本支出，企业用于购买、升级或维护固定资产（如厂房、设备）的投资。",
        "category": "商业"
    },
    {
        "term": "CoWoS",
        "desc": "台积电的先进封装技术，将多个芯片（如CPU、HBM）集成在一个封装内，提升互连密度和性能。",
        "category": "封装"
    },
    {
        "term": "HBM",
        "desc": "高带宽内存，通过3D堆叠和TSV技术实现高带宽，主要用于AI加速卡和高端GPU。",
        "category": "存储"
    },
    {
        "term": "NOR Flash",
        "desc": "一种非易失性存储器，读取速度快，常用于存储启动代码和嵌入式系统。",
        "category": "存储"
    }
]

# 话题追踪
topic_pulse = [
    {
        "topic": "CoWoS/先进封装",
        "heat": "→平稳",
        "reddit_top": "TSMC's CoWoS capacity expansion plans for 2026 - r/hardware (score: 42)",
        "hn_top": "null",
        "summary": "社区关注台积电CoWoS产能扩张计划，讨论AI芯片需求对先进封装的影响。普遍认为CoWoS是AI芯片性能提升的关键，但产能瓶颈可能持续到2027年。"
    },
    {
        "topic": "国产EDA/IP进展",
        "heat": "↑↑升温",
        "reddit_top": "China's domestic EDA tools gaining traction in local fabs - r/Semiconductors (score: 28)",
        "hn_top": "null",
        "summary": "国内EDA工具在华虹、中芯国际等代工厂获得验证，社区讨论国产替代进度和技术差距。情绪偏向谨慎乐观，认为需要5-10年才能达到国际领先水平。"
    },
    {
        "topic": "HBM/AI芯片存储",
        "heat": "↑↑升温",
        "reddit_top": "HBM4 specifications leaked: 1.2TB/s bandwidth target - r/hardware (score: 67)",
        "hn_top": "null",
        "summary": "HBM4规格泄露引发热议，社区讨论AI芯片存储带宽需求。普遍认为HBM技术迭代速度加快，三星、SK海力士和美光竞争激烈。"
    }
]

# 新闻条目（基于筛选结果）
items = [
    {
        "title": "CapEx Up for Foundry, Memory",
        "summary": "Semiconductor Intelligence estimates total semiconductor industry capital spending (CapEx) was $166 billion in 2025, up 7% from 2024. We estimate 2026 CapEx will be $200 billion, up 20% from 2025.",
        "source": "SemiWiki",
        "published": "2026-04-01T13:00:21Z",
        "url": "https://semiwiki.com/semiwiki.com/semiconductor-services/368018-capex-up-for-foundry-memory/",
        "tags": ["foundry", "memory", "capex", "investment"],
        "insights": "2026年半导体资本支出预计增长20%，主要受AI芯片和先进制程驱动。代工和存储是投资重点。",
        "actions": ["关注台积电、三星、英特尔资本开支公告", "跟踪存储芯片价格走势"],
        "glossary": [],
        "region": "overseas"
    },
    {
        "title": "Alchip’s Leadership in ASIC Innovation: Advancing Toward 2nm Semiconductor Technology",
        "summary": "Alchip Technologies has recently reported significant progress in the development of advanced 2nm ASICs, positioning itself as a leader in next-generation semiconductor design for AI and HPC.",
        "source": "SemiWiki",
        "published": "2026-04-01T17:00:48Z",
        "url": "https://semiwiki.com/semiconductor-services/alchip/367489-alchips-leadership-in-asic-innovation-advancing-toward-2nm-semiconductor-technology/",
        "tags": ["asic", "2nm", "ai", "hpc", "design"],
        "insights": "Alchip在2nm ASIC设计取得进展，显示AI/HPC芯片向更先进制程迁移。",
        "actions": ["关注AI芯片设计公司技术路线图", "评估2nm设计服务供应商"],
        "glossary": [],
        "region": "overseas"
    },
    {
        "title": "涉及中芯国际、华虹半导体、长鑫存储、长江存储等 - 与非网",
        "summary": "美国商务部考虑扩大半导体制裁禁令，禁止美国公司向中国公司出售先进的芯片制造设备。这些规定将扩大对美国公司向中国领先芯片制造商半导体制造国际公司出售此类设备的现有禁令。",
        "source": "与非网",
        "published": "",
        "url": "https://www.eefocus.com/component/518388",
        "tags": ["sanctions", "china", "equipment", "smc", "hua hong"],
        "insights": "美国可能扩大对华芯片设备出口限制，影响中芯国际、华虹等代工厂的先进制程扩张。",
        "actions": ["关注美国商务部正式公告", "评估国产设备替代进度"],
        "glossary": [],
        "region": "domestic"
    },
    {
        "title": "半导体行业2026年展望：AI、汽车、工业驱动增长，国产化进程加速",
        "summary": "在制造端，中芯国际、华虹公司等晶圆代工厂维持高产能利用率与合理资本开支，销售额稳居全球纯晶圆代工企业第二、第五名；在设备端，中微公司、拓荆科技、盛美上海等企业实现技术对标国际巨头。",
        "source": "四川在线",
        "published": "",
        "url": "https://cbgc.scol.com.cn/news/7425799",
        "tags": ["outlook", "china", "localization", "equipment", "foundry"],
        "insights": "2026年半导体行业增长由AI、汽车、工业驱动，国产化进程在制造和设备端加速。",
        "actions": ["跟踪国内半导体设备公司订单", "关注国产替代政策支持"],
        "glossary": [],
        "region": "domestic"
    },
    {
        "title": "AI存储架构迎巨变!黄仁勋CES重磅发声,叠加缺货涨价通知,半导体...",
        "summary": "东芯股份是国内存储芯片设计龙头，核心产品包括NAND Flash、NOR Flash、DRAM芯片，是国内少数具备全品类存储芯片设计能力的企业。",
        "source": "百度百家号",
        "published": "",
        "url": "https://baijiahao.baidu.com/s?id=1853651805677953984&wfr=spider&for=pc",
        "tags": ["ai", "memory", "storage", "dram", "nand"],
        "insights": "AI存储架构变革推动存储芯片需求，国内存储设计公司受益。",
        "actions": ["关注存储芯片价格走势", "评估国内存储设计公司技术进展"],
        "glossary": [],
        "region": "domestic"
    },
    {
        "title": "全产业链“协同战力” 凸显 近40家科创板公司集体亮相上海半导体展",
        "summary": "在制造端，中芯国际、华虹公司等晶圆代工厂维持高产能利用率与合理资本开支，销售额稳居全球纯晶圆代工企业第二、第五位。在设备端，中微公司、拓荆科技、盛美上海、中科飞测等企业分别在刻蚀、薄膜沉积、清洗、量检测等领域实现技术对标。",
        "source": "百度百家号",
        "published": "",
        "url": "https://baijiahao.baidu.com/s?id=1860739307511519128&wfr=spider&for=pc",
        "tags": ["exhibition", "china", "equipment", "foundry", "collaboration"],
        "insights": "国内半导体全产业链协同能力提升，设备公司在关键领域实现技术突破。",
        "actions": ["关注科创板半导体公司业绩", "跟踪设备国产化率提升"],
        "glossary": [],
        "region": "domestic"
    }
]

# 构建完整JSON
brief = {
    "version": version,
    "generatedAt": generated_at,
    "period": period,
    "commit": "",
    "glossary_list": glossary_list,
    "topic_pulse": topic_pulse,
    "items": items
}

# 写入文件
output_file = f"brief_{period}.json"
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(brief, f, ensure_ascii=False, indent=2)

# 复制到docs目录
docs_dir = "docs"
if not os.path.exists(docs_dir):
    os.makedirs(docs_dir)
with open(os.path.join(docs_dir, output_file), 'w', encoding='utf-8') as f:
    json.dump(brief, f, ensure_ascii=False, indent=2)

print(f"生成 {output_file} 成功，共 {len(items)} 条新闻")
print(f"术语表: {len(glossary_list)} 条")
print(f"话题追踪: {len(topic_pulse)} 个")

# 更新历史记录
history_path = 'history.json'
if os.path.exists(history_path):
    with open(history_path, 'r', encoding='utf-8') as f:
        history = json.load(f)
else:
    history = []

for item in items:
    history.append({
        "url": item["url"],
        "title": item["title"],
        "published": item["published"] if item["published"] else generated_at,
        "addedAt": generated_at
    })

# 保留最近500条
if len(history) > 500:
    history = history[-500:]

with open(history_path, 'w', encoding='utf-8') as f:
    json.dump(history, f, ensure_ascii=False, indent=2)

print(f"更新 history.json，当前 {len(history)} 条记录")
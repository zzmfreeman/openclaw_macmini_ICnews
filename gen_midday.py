import json, datetime, shutil
from urllib.parse import urlparse

OUTDIR = "/Users/zzm/.openclaw/workspace/openclaw_macmini_ICnews"
HISTORY_FILE = OUTDIR + "/history.json"

with open(HISTORY_FILE) as f:
    history = json.load(f)
history_urls = {item["url"] for item in history}

raw = [
    ("强一股份一季报预增超6倍 半导体设备行业景气度高",
     "强一股份发布一季报预告，预计净利润同比增长超6倍，受益于半导体设备行业景气度持续提升，下游晶圆厂扩产带动设备需求旺盛。",
     "证券时报", "2026-04-07T07:00:00+08:00",
     "https://www.stcn.com/article/detail/3728567.html", "domestic"),
    ("百亿级半导体项目新进展披露 多地晶圆厂建设提速",
     "国际电子商情报道，多地百亿级半导体项目陆续进入设备搬入和试产阶段，2026年有望迎来新一轮产能释放高峰。",
     "国际电子商情", "2026-04-07T09:00:00+08:00",
     "https://www.esmchina.com/marketnews/57601.html", "domestic"),
    ("160亿！科创板70家企业Q1密集投资 半导体成扩产核心赛道",
     "财联社数据，2026年一季度科创板70家企业累计投资规模达160亿元，其中半导体成为最核心的扩产赛道，反映资本持续看好国内半导体产业。",
     "财联社", "2026-04-07T07:00:00+08:00",
     "https://www.cls.cn/detail/2335449", "domestic"),
    ("三安光通信连破三关 高端光芯片加速驶入AI与汽车新蓝海",
     "三安光电旗下光通信业务持续突破，高端光芯片已向AI数据中心和汽车激光雷达领域加速渗透，光芯片需求有望随AI算力建设大幅增长。",
     "荣格工业传媒", "2026-04-07T11:00:00+08:00",
     "https://www.industrysourcing.cn/article/475320", "domestic"),
    ("688809引爆科创板申购 芯片测试量价齐升 优质标的稀缺",
     "688809（芯矽集成）科创板IPO申购引发关注，芯片测试赛道呈现量价齐升态势，国产测试设备厂商订单饱满，优质标的极为稀缺。",
     "新浪财经", "2026-04-06T20:00:00+08:00",
     "https://finance.sina.cn/2026-04-06/detail-inhtpewi6339140.d.", "domestic"),
    ("先进封装成突围关键 TEL如何助力中国客户技术跨越？",
     "Tokyo Electron（TEL）发布技术文章，阐述先进封装在后摩尔时代的重要性，CoWoS/Chiplet技术路线加速成熟。",
     "搜狐/先进封装", "2026-04-07T12:00:00+08:00",
     "https://m.sohu.com/a/1006272848_128469", "domestic"),
    ("先进封测龙头启动申购 机构预测中签率较高",
     "先进封装测试领域某龙头公司本周启动科创板申购，封装类型涵盖CoWoS、HBM相关先进封装，机构投资者参与热情高涨。",
     "证券之星", "2026-04-07T08:00:00+08:00",
     "https://stock.stockstar.com/IG2026040700003383.shtml", "domestic"),
    ("TSMC fabs sold out before built – demand incredibly strong through 2028",
     "TSMC receives overwhelming order volume for advanced nodes, with capacity reportedly sold out through 2028 before new fabs are even completed, underscoring the AI-driven chip shortage.",
     "MSN/Wccftech", "2026-04-07T05:00:00Z",
     "https://www.msn.com/en-us/news/technology/tsmc-s-fabs-are-so-in-demand-they-re-re-sold-out-even-before-they-ve-been-built", "overseas"),
    ("Intel approves $14.2B share repurchase, ends survival mode – Ireland fab acquisition signals confidence",
     "Intel board approves $14.2B stock repurchase and completes Ireland fab acquisition, marking strategic shift from survival mode to aggressive capacity investment.",
     "FinancialContent/Wccftech", "2026-04-07T06:00:00Z",
     "https://markets.financialcontent.com/stocks/article/marketminute-2026-04-07-intel-signals-end-of-survival-mode-with-14-2-billion-repurchase-of-ireland-fab", "overseas"),
    ("Intel advanced packaging gaining AI customer traction; EMIB deployment accelerates",
     "Intel reports growing AI customer interest in EMIB and advanced packaging as clients seek CoWoS alternatives amid tight TSMC capacity.",
     "Wccftech", "2026-04-06T16:53:26Z",
     "https://wccftech.com/intels-advanced-packaging-is-getting-the-attention-it-needs-from-ai-customers-with-emib", "overseas"),
    ("TSMC to address chip production risk; CoWoS remains critical bottleneck",
     "TSMC management signals upcoming earnings call will address production risks, with CoWoS advanced packaging widely seen as primary AI chip supply constraint.",
     "Wccftech", "2026-04-06T15:18:15Z",
     "https://wccftech.com/tsmc-is-set-to-talk-about-the-biggest-risk-it-faces-with-chip-production-right-now", "overseas"),
    ("RISC-V Has Momentum – who can deliver at scale remains the real question",
     "SemiWiki analysis: RISC-V ISA continues gaining momentum across embedded and data-center apps, but scaling the ecosystem to meet demand is the critical challenge.",
     "SemiWiki", "2026-04-06T13:00:12Z",
     "https://semiwiki.com/ip/akeana/368059-risc-v-has-momentum-the-real-que", "overseas"),
    ("GlobalWafers: semiconductor wafer giant merits attention as 300mm supply tightens",
     "GlobalWafers attracts investor attention amid tightening 300mm wafer supply and AI chip demand growth, with wafer pricing showing upward pressure.",
     "AD HOC NEWS", "2026-04-06T06:00:00Z",
     "https://www.ad-hoc-news.de/boerse/ueberblick/globalwafers-co-ltd-", "overseas"),
    ("yieldWerx delivers master class in Co-Packaged Photonics implementation",
     "yieldWerx publishes technical deep-dive on co-packaged optics implementation, highlighting advances in photonic ICs for AI datacenter interconnects.",
     "SemiWiki", "2026-04-06T17:00:00Z",
     "https://semiwiki.com/events/368095-yieldwerx-delivers-a-master-class-i", "overseas"),
]

seen_urls = set()
items = []
for title, summary, source, published, url, region in raw:
    if not url or "example.com" in url:
        continue
    if url in seen_urls or url in history_urls:
        continue
    try:
        pub_dt = datetime.datetime.fromisoformat(published.replace("Z","+00:00"))
        now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
        age = (now - pub_dt.replace(tzinfo=datetime.timezone.utc)).total_seconds()
        if age > 48*3600 or age < -3600:
            print(f"[SKIP age] {title[:60]}")
            continue
    except Exception as e:
        print(f"[SKIP date] {title[:60]}: {e}")
        continue
    seen_urls.add(url)
    tg = "industry"
    tlower = (title+summary).lower()
    if any(k in tlower for k in ["foundry","制造","晶圆","tsmc","samsung","中芯","华虹"]): tg = "fab"
    elif any(k in tlower for k in ["设计","chip design","fabless","高通","amd","联发科"]): tg = "design"
    elif any(k in tlower for k in ["eda","ip","synopsys","cadence","risc"]): tg = "eda_ip"
    elif any(k in tlower for k in ["封装","封测","osat","先进封装","cowo","chiplet","emib"]): tg = "packaging"
    elif any(k in tlower for k in ["设备","国产化","naura","amec"]): tg = "equipment"
    elif any(k in tlower for k in ["制裁","管制","出口","sanction"]): tg = "policy"
    insights, actions = [], []
    if "$14.2B" in title:
        insights.append("Intel战略重心从生存转向扩张，Fab资产整合加速")
        actions.append("关注Intel未来资本开支指引")
    if "sold out" in title.lower() or "售罄" in summary:
        insights.append("AI芯片需求超预期，CoWoS封装产能为关键瓶颈")
        actions.append("跟踪CoWoS扩产进度")
    items.append({"title":title,"summary":summary,"source":source,"published":published,"url":url,"tags":[tg],"insights":insights,"actions":actions,"glossary":[],"region":region})

print(f"Valid items: {len(items)} domestic={sum(1 for i in items if i['region']=='domestic')}")

topic_pulse = [
    {"topic":"CoWoS/先进封装","heat":"↑↑升温","reddit_top":None,"hn_top":"TSMC is reportedly sold out until 2028 (34pts)","summary":"TSMC先进封装产能售罄至2028年持续发酵，社区认为CoWoS瓶颈是2026年AI芯片供应链最关键环节。"},
    {"topic":"HBM/AI存储","heat":"→平稳","reddit_top":None,"hn_top":None,"summary":"HBM需求维持高位，SK Hynix和Samsung在HBM4竞争激烈但未见重大技术突破，热度平稳。"},
    {"topic":"中国Fab/先进制程","heat":"↑升温","reddit_top":None,"hn_top":None,"summary":"国内百亿级半导体项目密集披露新进展，中芯国际、华虹等Fab建设提速，关注制程节点突破。"},
    {"topic":"国产EDA/IP","heat":"→平稳","reddit_top":None,"hn_top":None,"summary":"国产EDA持续迭代，政策支持不减，商业化落地和国际竞争仍是讨论焦点。"},
    {"topic":"封测OSAT","heat":"↑升温","reddit_top":None,"hn_top":None,"summary":"先进封装龙头科创板IPO申购引发市场关注，封测赛道具备估值重塑逻辑，景气度上行。"},
    {"topic":"出口管制/制裁","heat":"↑↑升温","reddit_top":None,"hn_top":None,"summary":"美国出口管制持续发酵，15家中芯等企业拟被纳入管制清单成热门话题，社区看好国产替代加速。"},
    {"topic":"AI芯片/NVIDIA","heat":"→平稳","reddit_top":None,"hn_top":"TSMC is reportedly sold out until 2028 (34pts)","summary":"NVIDIA Blackwell持续出货，H100/H200需求旺盛，但市场关注转向供应链可持续性。"},
    {"topic":"设备/材料国产化","heat":"→平稳","reddit_top":None,"hn_top":None,"summary":"强一股份等设备厂商一季报预增超6倍，国产设备景气度高，但高端设备国产化率仍低。"}
]

glossary_list = [
    {"term":"EMIB","desc":"Embedded Multi-die Interconnect Bridge，Intel推出的先进封装技术，通过在有机基板中嵌入超薄硅桥接芯片，实现多芯片间高带宽低延迟互连，主要用于AI处理器封装。","category":"封装"},
    {"term":"Co-Packaged Photonics","desc":"共封装光学技术，将光引擎与计算芯片共同封装，大幅缩短电气互连距离，是解决AI数据中心带宽瓶颈的关键技术。","category":"封装"},
    {"term":"GlobalWafers","desc":"环球晶圆，全球第三大硅晶圆制造商，主要生产300mm/200mm硅晶圆，供应台积电、Intel、Samsung等主要Fab厂。","category":"材料"},
    {"term":"Chiplet","desc":"芯粒，将SoC拆分为多个独立芯片模块，通过先进封装互联，兼顾良率和性能，是后摩尔时代延续摩尔定律的重要技术路线。","category":"封装"},
    {"term":"EMIB","desc":"Embedded Multi-die Interconnect Bridge，Intel先进封装技术，通过在基板中嵌入桥接芯片实现高密度die-to-die互联，适用于AI芯片和异构集成。","category":"封装"},
    {"term":"300mm晶圆","desc":"直径12英寸的硅晶圆，当前先进制程主流尺寸，可切割数百颗芯片，单位芯片成本低于200mm晶圆。","category":"材料"},
]

brief = {
    "version":"v20260407-1300",
    "generatedAt":"2026-04-07T13:00:00+08:00",
    "period":"midday",
    "commit":"",
    "glossary_list":glossary_list,
    "topic_pulse":topic_pulse,
    "items":items
}

target = OUTDIR + "/brief_midday.json"
with open(target,"w",encoding="utf-8") as f:
    json.dump(brief, f, ensure_ascii=False, indent=2)
print(f"Written: {target}")

with open(OUTDIR+"/docs/brief_midday.json","w",encoding="utf-8") as f:
    json.dump(brief, f, ensure_ascii=False, indent=2)
shutil.copy(target, OUTDIR+"/brief.json")
print("Copied to brief.json and docs/")

new_entries = [{"url":i["url"],"title":i["title"],"published":i["published"],"addedAt":"2026-04-07T13:00:00+08:00"} for i in items]
history.extend(new_entries)
history = history[-500:]
with open(HISTORY_FILE,"w",encoding="utf-8") as f:
    json.dump(history, f, ensure_ascii=False, indent=2)
print(f"History: {len(history)} entries")

with open(target) as f:
    lines = f.readlines()[:6]
print("\n=== First 6 lines ===")
for l in lines: print(l.rstrip())

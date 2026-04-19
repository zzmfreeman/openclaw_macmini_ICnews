const fs = require('fs');
const path = require('path');

const now = new Date();
const tz8 = new Date(now.getTime() + 8*3600000);
const VERSION = `v${tz8.toISOString().slice(0,10).replace(/-/g,'')}-${tz8.toISOString().slice(11,13)}${tz8.toISOString().slice(14,16)}`;
const GENERATED = `${tz8.toISOString().slice(0,10)}T${tz8.toISOString().slice(11,16)}:00+08:00`;
const PERIOD = 'midday';

const baseDir = '/Users/zzm/.openclaw/workspace/openclaw_macmini_ICnews';

// Topic pulse
const topic_pulse = [
  {"topic":"CoWoS/先进封装","heat":"↓降温","reddit_top":"null (API credits exhausted)","hn_top":"null","summary":"CoWoS产能需求持续旺盛，HN本周讨论热度偏低，先进封装仍是供应链关键瓶颈"},
  {"topic":"HBM/AI存储","heat":"↓降温","reddit_top":"null","hn_top":"null","summary":"HBM产能分配成为AI供应链焦点，SK Hynix持续主导"},
  {"topic":"中国Fab/先进制程","heat":"↓降温","reddit_top":"null","hn_top":"null","summary":"中芯7nm量产消息引发关注，制裁压力下先进制程不确定性增加"},
  {"topic":"国产EDA/IP","heat":"↓降温","reddit_top":"null","hn_top":"null","summary":"国产EDA加速迭代，全流程覆盖差距仍明显"},
  {"topic":"封测OSAT","heat":"↓降温","reddit_top":"null","hn_top":"null","summary":"ASE/Amkor先进封装扩产持续，OSAT格局受CoWoS需求重塑"},
  {"topic":"出口管制/制裁","heat":"↑↑升温","reddit_top":"null","hn_top":"null","summary":"MATCH法案升级制裁力度，出口管制加码，国产替代路线压力增大"},
  {"topic":"AI芯片/NVIDIA","heat":"→平稳","reddit_top":"null","hn_top":"Nvidia market share in China falls to less than 60% (3pts)","summary":"NVIDIA中国市场份额下滑至60%以下，国产AI芯片替代加速"},
  {"topic":"设备/材料国产化","heat":"↓降温","reddit_top":"null","hn_top":"null","summary":"北方华创/中微在成熟制程持续渗透，先进制程仍依赖进口"}
];

// Final curated items
const items = [
  {
    "title": "美国MATCH法案升级：14nm及以下设备出口维修受限，直接点名中芯国际等五家中国企业",
    "summary": "美国《MATCH法案》进一步收紧半导体出口管制，14nm及以下制程设备的出口维修服务被限制，中芯国际、华虹等五家中国Fab企业被直接点名，制裁范围从新设备扩展到维修服务。",
    "source": "SerpAPI/Baidu",
    "published": GENERATED,
    "url": "https://baijiahao.baidu.com/s?id=1861692254565414263&wfr=spider&for=pc",
    "tags": ["出口管制", "国内"],
    "insights": ["制裁从设备采购延伸到维修服务，打击面更广更深", "中芯国际/华虹等成熟制程Fab的设备维护面临断供风险"],
    "actions": ["紧急盘点14nm以下制程关键设备的维修服务依赖情况", "制定设备维修替代方案，评估国产维修服务覆盖能力"],
    "glossary": [{"term":"MATCH法案","desc":"美国《现代制造业对华战略制约法案》，加强对华半导体出口管制","category":"商业"}],
    "region": "domestic"
  },
  {
    "title": "马斯克Terafab在台湾抢夺芯片人才，覆盖9类核心职位",
    "summary": "马斯克的Terafab项目在台湾大规模招聘半导体人才，涵盖工艺工程师、设备工程师、良率工程师等9类关键岗位，直接与台积电等本土代工厂争夺人才资源。",
    "source": "Serper",
    "published": GENERATED,
    "url": "https://m.sohu.com/a/1011553167_128469",
    "tags": ["Fab/制造", "国内"],
    "insights": ["马斯克Terafab入台抢人才，可能加剧台湾半导体人才紧缺", "台积电等代工厂面临人才流失风险，需关注产能稳定性影响"],
    "actions": ["评估Terafab人才争夺对台积电产能的潜在冲击", "关注Terafab项目进展及其对代工格局的可能影响"],
    "glossary": [{"term":"Terafab","desc":"马斯克提出的超级晶圆厂概念，目标实现高度自动化芯片制造","category":"设备"}],
    "region": "domestic"
  },
  {
    "title": "中国芯片产业再突破：7nm稳量产、IC设计跃居全球第二，但EDA与EUV仍是短板",
    "summary": "中国芯片产业取得重要进展：7nm制程稳定量产，IC设计规模跃居全球第二。但EDA工具链和EUV光刻设备仍是核心短板，制约先进制程进一步突破。",
    "source": "SerpAPI/Baidu",
    "published": GENERATED,
    "url": "https://baijiahao.baidu.com/s?id=1862599419984140817&wfr=spider&for=pc",
    "tags": ["EDA/IP", "国内"],
    "insights": ["7nm稳量产标志中国代工能力进入新阶段，受制裁设备维修限制影响持续性", "IC设计规模全球第二反映fabless生态成熟，EDA短板仍是全流程瓶颈"],
    "actions": ["跟踪中芯7nm量产良率与产能数据", "评估国产EDA在设计流程中的可替代范围与迁移成本"],
    "glossary": [{"term":"7nm制程","desc":"7纳米工艺节点，中芯国际当前最先进的量产制程","category":"设备"}],
    "region": "domestic"
  },
  {
    "title": "两家国产AI芯片公司离上市再近一步，AI算力底座持续变化",
    "summary": "国产AI芯片赛道持续升温，两家AI芯片设计公司IPO进程加速推进，反映国产AI算力芯片在资本市场和产业落地双线突破的趋势。",
    "source": "Brave",
    "published": GENERATED,
    "url": "https://www.stcn.com/article/detail/2223418.html",
    "tags": ["设计公司", "国内"],
    "insights": ["国产AI芯片公司密集冲刺IPO，资本热度高但需警惕估值泡沫", "AI算力芯片国产替代路线正在从设计走向量产落地"],
    "actions": ["关注国产AI芯片公司上市进展与基本面表现", "评估国产AI芯片在当前项目中的可用性与性能差距"],
    "glossary": [],
    "region": "domestic"
  },
  {
    "title": "内存接口芯片龙头澜起科技冲刺港股，全球市占率第一半年赚12亿",
    "summary": "澜起科技作为全球内存接口芯片龙头冲刺港股上市，半年净利润超12亿元，DDR5内存接口芯片全球市占率第一，反映国产芯片在高附加值细分领域的突破。",
    "source": "Brave",
    "published": GENERATED,
    "url": "https://cj.sina.com.cn/articles/view/7986389890/1dc06a38200101gjby",
    "tags": ["设计公司", "国内"],
    "insights": ["澜起科技在内存接口芯片领域全球领先，证明国产芯片可在高附加值细分赛道突围", "港股IPO为澜起提供更多融资渠道，有利于持续研发投入"],
    "actions": ["关注澜起港股IPO进展与估值", "评估澜起内存接口芯片在服务器供应链中的替代潜力"],
    "glossary": [{"term":"DDR5内存接口芯片","desc":"第五代DDR内存标准接口芯片，服务器内存核心组件","category":"存储"}],
    "region": "domestic"
  },
  {
    "title": "A股新\u201c股王\u201d诞生：3年涨13倍超越茅台，净利润激增32倍拟12.5亿扩产",
    "summary": "一家半导体相关A股公司3年股价涨13倍超越茅台成为新股王，创始人身家85亿，净利润激增超32倍，拟投入12.5亿扩产，反映半导体赛道资本市场狂热。",
    "source": "Serper",
    "published": GENERATED,
    "url": "https://finance.sina.cn/2026-04-17/detail-inhuupte2307688.d.html",
    "tags": ["Fab/制造", "国内"],
    "insights": ["半导体股王现象反映资本市场对芯片赛道极度看好，但估值泡沫风险需警惕", "拟12.5亿扩产表明产能紧张下企业积极扩张，但也增加产能过剩风险"],
    "actions": ["关注该扩产项目的产品类型与制程节点", "评估扩产完成后对供应链供需平衡的影响"],
    "glossary": [],
    "region": "domestic"
  },
  {
    "title": "ST中迪无偿获赠半导体资产70%股权，紧急保壳转身封测赛道",
    "summary": "ST中迪拟无偿获赠超过2亿元半导体资产，拿下一家封测公司70%股权，紧急保壳并彻底转型进入封测赛道，反映A股半导体并购重组活跃度。",
    "source": "Serper",
    "published": GENERATED,
    "url": "https://finance.sina.cn/tech/2026-04-18/detail-inhuxiqe0184964.d.html",
    "tags": ["Fab/制造", "国内"],
    "insights": ["A股半导体资产并购重组活跃，ST公司通过获赠半导体资产保壳转型", "封测赛道成为A股半导体转型热门方向，行业竞争格局可能变化"],
    "actions": ["关注ST公司转型封测后的经营基本面变化", "评估封测赛道新增玩家对供应商格局的影响"],
    "glossary": [{"term":"ST标记","desc":"A股特别处理标记，表示公司存在财务风险","category":"商业"}],
    "region": "domestic"
  },
  {
    "title": "NVIDIA中国市场份额跌破60%，国产AI芯片替代加速推进",
    "summary": "NVIDIA在中国AI芯片市场份额已下滑至60%以下，国产芯片厂商交付了约165万颗AI GPU，中国政府数据中心推进国产芯片替代政策，市场竞争格局正在重塑。",
    "source": "HN",
    "published": "2026-04-02T17:50:46Z",
    "url": "https://www.tomshardware.com/tech-industry/nvidia-market-share-in-china-falls-to-less-than-60-percent-chinese-chip-makers-deliver-1-65-million-ai-gpus-as-the-government-pushes-data-centers-to-use-domestic-chips",
    "tags": ["设计公司", "overseas"],
    "insights": ["NVIDIA中国市场份额持续下滑，国产替代政策正在实质性改变市场格局", "165万颗国产AI GPU交付量标志着国产算力芯片进入规模化部署阶段"],
    "actions": ["评估国产AI GPU在数据中心场景的性能与生态成熟度", "关注国产替代政策对NVIDIA后续产品在中国上市的影响"],
    "glossary": [],
    "region": "overseas"
  }
];

const glossary_list = [
  {"term":"CoWoS","desc":"Chip-on-Wafer-on-Substrate，台积电2.5D/3D先进封装平台","category":"封装"},
  {"term":"MATCH法案","desc":"美国《现代制造业对华战略制约法案》，加强对华半导体出口管制","category":"商业"},
  {"term":"DDR5内存接口芯片","desc":"第五代DDR内存标准接口芯片，服务器内存核心组件","category":"存储"},
  {"term":"Terafab","desc":"马斯克提出的超级晶圆厂概念，目标实现高度自动化芯片制造","category":"设备"},
  {"term":"7nm制程","desc":"7纳米工艺节点，中芯国际当前最先进的量产制程","category":"设备"},
  {"term":"ST标记","desc":"A股特别处理标记，表示公司存在财务风险","category":"商业"}
];

const brief = {
  version: VERSION,
  generatedAt: GENERATED,
  period: PERIOD,
  commit: "",
  glossary_list: glossary_list,
  topic_pulse: topic_pulse,
  items: items
};

// Save files
const files = [
  path.join(baseDir, 'brief_midday.json'),
  path.join(baseDir, 'brief.json'),
  path.join(baseDir, 'docs', 'brief_midday.json'),
  path.join(baseDir, 'docs', 'brief.json')
];

fs.mkdirSync(path.join(baseDir, 'docs'), {recursive: true});

for (const fp of files) {
  fs.writeFileSync(fp, JSON.stringify(brief, null, 2));
}

// Update history
const histPath = path.join(baseDir, 'history.json');
let history = [];
try { history = JSON.parse(fs.readFileSync(histPath, 'utf8')); } catch {}

for (const item of items) {
  history.push({url: item.url, title: item.title, published: item.published, addedAt: GENERATED});
}
history = history.slice(-500);
fs.writeFileSync(histPath, JSON.stringify(history, null, 2));
fs.writeFileSync(path.join(baseDir, 'docs', 'history.json'), JSON.stringify(history, null, 2));

// Verify
const first6 = fs.readFileSync(path.join(baseDir, 'brief.json'), 'utf8').split('\n').slice(0,6);
console.log(first6.join('\n'));

// Stats
const srcCount = {};
items.forEach(i => {
  let s = i.source;
  if (s.includes('Serper')) s = 'Serper';
  else if (s.includes('SerpAPI')) s = 'SerpAPI';
  else if (s.includes('NewsAPI')) s = 'NewsAPI';
  else if (s.includes('Brave')) s = 'Brave';
  else if (s.includes('RSS')) s = 'RSS';
  else if (s.includes('HN')) s = 'HN';
  srcCount[s] = (srcCount[s]||0) + 1;
});

console.log(`\nItems: ${items.length} | Domestic: ${items.filter(i=>i.region==='domestic').length} | Overseas: ${items.filter(i=>i.region==='overseas').length}`);
console.log(`Sources: ${JSON.stringify(srcCount)}`);
console.log(`Version: ${VERSION} | Period: ${PERIOD}`);

items.forEach((i,idx) => {
  console.log(`${idx+1}. [${i.tags.join(',')}] [${i.region}] ${i.title}`);
  console.log(`   URL: ${i.url.substring(0,80)}`);
});

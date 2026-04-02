#!/usr/bin/env python3
import json
import re
from datetime import datetime, timedelta
from urllib.parse import urlparse
import hashlib

# 读取原始数据
with open('/Users/zzm/.openclaw/workspace/openclaw_macmini_ICnews/raw_results.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 读取历史去重库
try:
    with open('/Users/zzm/.openclaw/workspace/openclaw_macmini_ICnews/history.json', 'r', encoding='utf-8') as f:
        history = json.load(f)
        history_urls = {item['url'] for item in history}
except:
    history_urls = set()

# 黑名单域名
blacklist_domains = {
    'digitimes.com',
    'globenewswire.com', 
    'prnewswire.com'
}

# 已知常见术语（不解释）
common_terms = {
    'TSMC', '台积电', 'Samsung', '三星', 'NVIDIA', 'Intel', 'AMD', 'Qualcomm',
    'DRAM', 'NAND', 'SSD', 'CPU', 'GPU', 'AI', 'HBM', 'EDA', 'ASML', 'Arm',
    'RISC-V', '晶圆', '封装', '代工', 'Foundry', 'fabless', '芯片', '半导体',
    '光刻机', 'MCU', 'SoC', 'IP', '存储', '内存', 'FinFET'
}

def extract_domain(url):
    try:
        return urlparse(url).netloc
    except:
        return ''

def is_semiconductor_related(title, description):
    """判断是否与半导体/芯片/供应链相关"""
    keywords = [
        '半导体', '芯片', '晶圆', '封测', '代工', 'foundry', 'fab',
        'wafer', 'semiconductor', 'chip', 'IC', '集成电路',
        'EDA', 'IP', '设计', 'design', '制造', 'manufacturing',
        'TSMC', '台积电', 'Samsung', 'Intel', '中芯', '华虹',
        'Synopsys', 'Cadence', 'Arm', 'RISC-V', 'AMD', 'Qualcomm',
        'MediaTek', '功率半导体', '碳化硅', 'SiC', 'GaN'
    ]
    
    text = (title + ' ' + description).lower()
    for keyword in keywords:
        if keyword.lower() in text:
            return True
    return False

def normalize_text(text):
    """文本归一化用于语义去重"""
    # 移除特殊字符、空格，转换为小写
    text = re.sub(r'[^\w\s]', '', text.lower())
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extract_glossary_terms(texts):
    """从文本中提取专业术语"""
    terms = set()
    
    # 专业术语模式
    patterns = [
        r'\b(N2P|N3E|N3P|N2|N3|N5|N7|N10|N16)\b',  # 制程节点
        r'\b(18A|20A|Intel 4|Intel 3)\b',  # Intel制程
        r'\b(CoWoS|InFO|SoIC|X-Cube)\b',  # 先进封装
        r'\b(HBM4|HBM3E|GDDR7|LPDDR6)\b',  # 内存技术
        r'\b(GAA|Gate-All-Around|FinFET)\b',  # 晶体管结构
        r'\b(SiC|GaN|功率半导体)\b',  # 材料
        r'\b(车规级|AEC-Q100|ISO 26262)\b',  # 认证标准
        r'\b(特色工艺|specialty process)\b',
        r'\b(国产替代|localization)\b',
        r'\b(大基金|National IC Fund)\b',
        r'\b(产能利用率|capacity utilization)\b',
        r'\b(先进封测|advanced packaging and testing)\b'
    ]
    
    for text in texts:
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                if match and match not in common_terms:
                    terms.add(match)
    
    return list(terms)

# 收集所有新闻条目
all_articles = []
seen_urls = set()
seen_semantic = set()

for search in data['search_results']:
    for article in search['results']:
        url = article['url']
        domain = extract_domain(url)
        
        # 检查黑名单
        if any(black in domain for black in blacklist_domains):
            continue
            
        # URL去重
        if url in seen_urls or url in history_urls:
            continue
            
        # 检查是否半导体相关
        title = article.get('title', '')
        description = article.get('description', '')
        if not is_semiconductor_related(title, description):
            continue
            
        # 语义去重
        semantic_key = normalize_text(title[:100])
        if semantic_key in seen_semantic:
            continue
            
        # 添加到集合
        seen_urls.add(url)
        seen_semantic.add(semantic_key)
        
        # 解析发布时间
        published = article.get('published', '')
        published_date = None
        
        # 处理相对时间（如"17 hours ago"）
        if 'hour' in published.lower() or 'day' in published.lower():
            try:
                hours_ago = 0
                if 'hour' in published:
                    match = re.search(r'(\d+)\s*hour', published)
                    if match:
                        hours_ago = int(match.group(1))
                elif 'day' in published:
                    match = re.search(r'(\d+)\s*day', published)
                    if match:
                        hours_ago = int(match.group(1)) * 24
                
                if hours_ago > 0:
                    published_date = (datetime.now() - timedelta(hours=hours_ago)).strftime('%Y-%m-%d')
            except:
                published_date = '2026-04-01'
        else:
            published_date = published
            
        all_articles.append({
            'title': title,
            'url': url,
            'description': description,
            'published': published_date or '2026-04-01',
            'siteName': article.get('siteName', ''),
            'category': article.get('category', '综合'),
            'isChinese': article.get('isChinese', False),
            'domain': domain
        })

print(f"原始文章数: {sum(len(search['results']) for search in data['search_results'])}")
print(f"清洗后文章数: {len(all_articles)}")

# 分类统计
categories = {
    'Fab/制造': [],
    '设计公司': [],
    'EDA/IP': [],
    '综合': []
}

chinese_count = 0
for article in all_articles:
    cat = article['category']
    if cat in categories:
        categories[cat].append(article)
    else:
        categories['综合'].append(article)
    
    if article['isChinese']:
        chinese_count += 1

print(f"\n分类统计:")
for cat, articles in categories.items():
    print(f"  {cat}: {len(articles)}条")
print(f"国内来源: {chinese_count}条")

# 早报配额：15条，Fab/制造 ≤6条，设计公司 ≥3条，EDA/IP ≥2条，国内来源 ≥6条
selected_articles = []

# 1. 优先选择国内来源
chinese_articles = [a for a in all_articles if a['isChinese']]
selected_articles.extend(chinese_articles[:6])  # 先选6条国内

# 2. 按类别补充
remaining_quota = 15 - len(selected_articles)

# Fab/制造最多6条
fab_articles = [a for a in categories['Fab/制造'] if a not in selected_articles]
fab_to_select = min(6 - len([a for a in selected_articles if a['category'] == 'Fab/制造']), 
                    len(fab_articles), remaining_quota)
selected_articles.extend(fab_articles[:fab_to_select])
remaining_quota -= fab_to_select

# 设计公司至少3条
design_articles = [a for a in categories['设计公司'] if a not in selected_articles]
design_needed = max(3 - len([a for a in selected_articles if a['category'] == '设计公司']), 0)
design_to_select = min(design_needed, len(design_articles), remaining_quota)
selected_articles.extend(design_articles[:design_to_select])
remaining_quota -= design_to_select

# EDA/IP至少2条
eda_articles = [a for a in categories['EDA/IP'] if a not in selected_articles]
eda_needed = max(2 - len([a for a in selected_articles if a['category'] == 'EDA/IP']), 0)
eda_to_select = min(eda_needed, len(eda_articles), remaining_quota)
selected_articles.extend(eda_articles[:eda_to_select])
remaining_quota -= eda_to_select

# 3. 用其他文章补足配额
other_articles = [a for a in all_articles if a not in selected_articles]
selected_articles.extend(other_articles[:remaining_quota])

print(f"\n最终选择 {len(selected_articles)} 条新闻:")
for i, article in enumerate(selected_articles, 1):
    print(f"{i:2d}. [{article['category']}] {article['title'][:60]}...")

# 提取术语
all_texts = [a['title'] + ' ' + a['description'] for a in selected_articles]
glossary_terms = extract_glossary_terms(all_texts)

print(f"\n提取到 {len(glossary_terms)} 个专业术语:")
for term in glossary_terms:
    print(f"  - {term}")

# 生成术语解释
glossary_list = []
term_descriptions = {
    'N2P': '台积电第二代2纳米工艺技术，相比N2性能提升约10-15%，功耗降低25-30%',
    '18A': '英特尔18埃米制程节点，采用RibbonFET晶体管和PowerVia背面供电技术',
    'CoWoS': '台积电的Chip-on-Wafer-on-Substrate先进封装技术，用于高带宽内存与逻辑芯片集成',
    'HBM4': '第四代高带宽内存技术，预计2026年量产，带宽可达1.5TB/s以上',
    'GAA': '全环绕栅极晶体管技术，三星在3纳米节点首次商用，英特尔和台积电将在2纳米采用',
    'SiC': '碳化硅功率半导体材料，用于新能源汽车、充电桩等高压高频应用',
    '车规级': '符合汽车电子委员会AEC-Q100等标准的半导体产品认证等级',
    '特色工艺': '针对特定应用优化的半导体制造工艺，如高压、射频、嵌入式存储等',
    '国产替代': '中国半导体产业减少对外依赖，提升本土供应链自主可控能力的战略',
    '大基金': '国家集成电路产业投资基金，支持中国半导体产业发展的政策性基金',
    '产能利用率': '半导体制造工厂实际产量与最大产能的比率，反映行业景气度',
    '先进封测': '包括2.5D/3D封装、晶圆级封装等高端封装测试技术'
}

for term in glossary_terms[:8]:  # 最多8条
    desc = term_descriptions.get(term, '')
    if not desc:
        # 根据术语类型生成默认描述
        if any(x in term.lower() for x in ['nm', 'n2', 'n3', 'n5', 'n7']):
            desc = '半导体制造工艺节点，数字越小代表技术越先进'
        elif any(x in term.lower() for x in ['hbm', 'gddr', 'lpddr']):
            desc = '内存技术标准，用于高性能计算和移动设备'
        elif any(x in term.lower() for x in ['cowos', 'info', '3d']):
            desc = '先进封装技术，用于提升芯片集成度和性能'
        elif 'sic' in term.lower() or 'gan' in term.lower():
            desc = '第三代半导体材料，用于功率电子和射频应用'
        else:
            desc = '半导体行业专业术语'
    
    category = '材料' if 'SiC' in term or 'GaN' in term else \
               '封装' if any(x in term for x in ['CoWoS', 'InFO', '封测']) else \
               '设备' if any(x in term for x in ['车规级', 'AEC', 'ISO']) else \
               '存储' if any(x in term for x in ['HBM', 'GDDR', 'LPDDR']) else \
               '商业' if any(x in term for x in ['国产替代', '大基金', '产能']) else '工艺'
    
    glossary_list.append({
        'term': term,
        'desc': desc,
        'category': category
    })

# 生成最终简报
brief = {
    'version': '20260402-0829',
    'generatedAt': '2026-04-02T08:29:00+08:00',
    'period': 'morning',
    'count': len(selected_articles),
    'glossary_list': glossary_list,
    'news': []
}

# 重大新闻置顶判断
major_keywords = ['并购', '收购', 'M&A', 'acquisition', 'CEO', 'CTO', '人事变动', 'resign', 'appoint']

for article in selected_articles:
    title = article['title']
    is_major = any(keyword in title for keyword in major_keywords)
    
    # 生成insights和actions
    insights = []
    actions = []
    
    if '印度' in title or 'India' in title:
        insights.append('印度半导体产业加速发展，政策支持力度加大')
        actions.append('关注印度半导体生态建设对全球供应链的影响')
    
    if '国产替代' in title or '本土化' in title:
        insights.append('国产替代进程加速，政策支持持续加强')
        actions.append('关注国产半导体设备材料企业的投资机会')
    
    if '2nm' in title or 'N2' in title or '18A' in title:
        insights.append('先进制程竞争白热化，技术迭代加速')
        actions.append('跟踪各厂商2nm工艺量产进度和良率表现')
    
    if '产能' in title or 'capacity' in title:
        insights.append('产能扩张反映市场需求旺盛，但需警惕过剩风险')
        actions.append('监控全球半导体产能利用率变化')
    
    if '融资' in title or '投资' in title or 'funding' in title:
        insights.append('资本市场持续关注半导体赛道，融资活跃')
        actions.append('关注新获融资企业的技术进展和商业化能力')
    
    # 默认insights和actions
    if not insights:
        insights.append('行业技术升级和市场竞争格局变化值得关注')
    
    if not actions:
        actions.append('持续跟踪相关公司技术进展和财务表现')
    
    # 生成tags
    tags = [article['category']]
    if article['isChinese']:
        tags.append('国内')
    if 'AI' in title or '人工智能' in title:
        tags.append('AI')
    if '汽车' in title or '车规' in title or 'automotive' in title:
        tags.append('汽车电子')
    if '存储' in title or '内存' in title or 'memory' in title:
        tags.append('存储')
    
    brief['news'].append({
        'title': title,
        'summary': article['description'],
        'source': article['siteName'] or article['domain'],
        'published': article['published'],
        'url': article['url'],
        'tags': tags,
        'insights': insights,
        'actions': actions,
        'glossary': [],
        'isMajor': is_major
    })

# 按isMajor排序，重大新闻在前
brief['news'].sort(key=lambda x: (not x['isMajor'], x['published']), reverse=True)

# 保存简报
with open('/Users/zzm/.openclaw/workspace/openclaw_macmini_ICnews/brief.json', 'w', encoding='utf-8') as f:
    json.dump(brief, f, ensure_ascii=False, indent=2)

print(f"\n简报已保存到 brief.json")
print(f"包含 {len(brief['news'])} 条新闻，{len(brief['glossary_list'])} 个术语")

# 更新历史文件
new_history_entries = []
for article in selected_articles:
    new_history_entries.append({
        'url': article['url'],
        'title': article['title'],
        'published': article['published'],
        'addedAt': datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')
    })

# 读取现有历史，保留最近500条
try:
    with open('/Users/zzm/.openclaw/workspace/openclaw_macmini_ICnews/history.json', 'r', encoding='utf-8') as f:
        existing_history = json.load(f)
except:
    existing_history = []

# 合并并限制500条
updated_history = existing_history + new_history_entries
if len(updated_history) > 500:
    updated_history = updated_history[-500:]

with open('/Users/zzm/.openclaw/workspace/openclaw_macmini_ICnews/history.json', 'w', encoding='utf-8') as f:
    json.dump(updated_history, f, ensure
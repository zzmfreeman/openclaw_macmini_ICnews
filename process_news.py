import json, os, re, sys, time
from datetime import datetime, timedelta

# 读取历史记录
history_path = 'history.json'
if os.path.exists(history_path):
    with open(history_path, 'r', encoding='utf-8') as f:
        history = json.load(f)
else:
    history = []
existing_urls = {item.get('url', '') for item in history[-500:] if 'url' in item}

# 模拟采集到的原始数据（从之前的输出中提取）
raw_lines = '''TITLE:Alchip’s Leadership in ASIC Innovation: Advancing Toward 2nm Semiconductor Technology|DATE:Wed, 01 Apr 2026 17:00:48 +0000|URL:https://semiwiki.com/semiconductor-services/alchip/367489-alchips-leadership-in-asic-innovation-advancing-toward-2nm-semiconductor-technology/|SRC:SemiWiki|DESC:<p>Alchip Technologies has recently reported significant progress in the development of advanced 2nm ASICs, positioning itself as a leader in next-generation semiconductor design for AI and HPC. The
TITLE:CapEx Up for Foundry, Memory|DATE:Wed, 01 Apr 2026 13:00:21 +0000|URL:https://semiwiki.com/semiwiki.com/semiconductor-services/368018-capex-up-for-foundry-memory/|SRC:SemiWiki|DESC:<p>Semiconductor Intelligence estimates total semiconductor industry capital spending (CapEx) was $166 billion in 2025, up 7% from 2024. We estimate 2026 CapEx will be $200 billion, up 20% from 2025.
TITLE:AI存储架构迎巨变!黄仁勋CES重磅发声,叠加缺货涨价通知,半导体...|DATE:|URL:https://baijiahao.baidu.com/s?id=1853651805677953984&wfr=spider&for=pc|SRC:|DESC:27. 东芯股份（688110）是国内存储芯片设计龙头，核心产品包括NAND Flash、NOR Flash、DRAM芯片，是国内少数具备全品类存储芯片设计能力的企业。公司的存储芯片采用40nm、28nm制程工艺，已实现量产并供应给国内消费电子、工业控制企业。同时，公司与中芯国际、华虹公司合作，推动国产存储芯片的制造落地，在NOR Flash领域的...
TITLE:...涉及中芯国际、华虹半导体、长鑫存储、长江存储等 - 与非网|DATE:|URL:https://www.eefocus.com/component/518388|SRC:|DESC:5月9日上午,据硅谷科技媒体The Information报道《The U.S. Weighs a Broader Crackdown on Chinese Chipmakers》称,美国商务部正在考虑一项扩大半导体制裁禁令,禁止美国公司向中国公司出售先进的芯片制造设备。 这些规定将扩大对美国公司向中国领先芯片制造商半导体制造国际公司出售此类设备的现有禁令。更广泛的禁令将影响...
TITLE:全产业链“协同战力” 凸显 近40家科创板公司集体亮相上海半导体展|DATE:|URL:https://baijiahao.baidu.com/s?id=1860739307511519128&wfr=spider&for=pc|SRC:|DESC:在制造端，中芯国际、华虹公司等晶圆代工厂维持高产能利用率与合理资本开支，销售额稳居全球纯晶圆代工企业第二、第五位，在中国大陆企业中排名第一、第二位。在设备端，中微公司、拓荆科技、盛美上海、中科飞测、屹唐股份、富创精密等企业分别在刻蚀、薄膜沉积、清洗、量检测、热处理、精密零部件等领域实现技术对标...
TITLE:半导体行业2026年展望：AI、汽车、工业驱动增长，国产化进程加速|DATE:|URL:https://cbgc.scol.com.cn/news/7425799|SRC:|DESC:在制造端,中芯国际、华虹公司等晶圆代工厂维持高产能利用率与合理资本开支,销售额稳居全球纯晶圆代工企业第二、第五名;在设备端,中微公司、拓荆科技、盛美上海、中科飞测、屹唐股份、富创精密等企业分别在刻蚀、薄膜沉积、清洗、量检测、热处理、精密零部件等领域实现技术对标国际巨头,并加速开发面向先进逻辑、存储...
'''

# 解析原始数据
articles = []
for line in raw_lines.strip().split('\n'):
    if not line.startswith('TITLE:'):
        continue
    parts = line.split('|')
    if len(parts) < 5:
        continue
    title = parts[0].replace('TITLE:', '').strip()
    date = parts[1].replace('DATE:', '').strip()
    url = parts[2].replace('URL:', '').strip()
    src = parts[3].replace('SRC:', '').strip()
    desc = parts[4].replace('DESC:', '').strip() if len(parts) > 4 else ''
    
    # 过滤黑名单
    if 'digitimes.com' in url or 'globenewswire.com' in url or 'prnewswire.com' in url:
        continue
    
    # 去重
    if url in existing_urls:
        continue
    
    # 分类
    tags = []
    region = 'domestic' if any(x in src.lower() for x in ['baidu', 'eefocus', 'cbgc', '与非网']) or any(x in title for x in ['中芯', '华虹', '长鑫', '长江', '国产']) else 'overseas'
    
    # 判断类别
    category = 'other'
    title_lower = title.lower()
    if any(x in title_lower for x in ['foundry', 'wafer', 'fab', '代工', '晶圆', '制造', 'tsmc', 'samsung', 'intel']):
        category = 'fab'
    elif any(x in title_lower for x in ['design', 'fabless', 'qualcomm', 'amd', 'mediatek', 'marvell', 'broadcom', '设计公司', '芯片设计']):
        category = 'design'
    elif any(x in title_lower for x in ['eda', 'ip', 'synopsys', 'cadence', 'arm', 'risc-v', '电子设计自动化']):
        category = 'eda_ip'
    
    articles.append({
        'title': title,
        'date': date,
        'url': url,
        'src': src,
        'desc': desc,
        'category': category,
        'region': region
    })

# 配额：midday 8条，三类各≥1，国内≥3
fab = [a for a in articles if a['category'] == 'fab']
design = [a for a in articles if a['category'] == 'design']
eda = [a for a in articles if a['category'] == 'eda_ip']
other = [a for a in articles if a['category'] == 'other']

selected = []
# 每类至少1条
if fab:
    selected.append(fab[0])
if design:
    selected.append(design[0])
if eda:
    selected.append(eda[0])

# 补充国内来源
domestic = [a for a in articles if a['region'] == 'domestic' and a not in selected]
if len(domestic) > 0:
    selected.extend(domestic[:max(0, 3 - len([a for a in selected if a['region'] == 'domestic']))])

# 补足到8条
remaining = [a for a in articles if a not in selected]
selected.extend(remaining[:max(0, 8 - len(selected))])

print(f'筛选后 {len(selected)} 条新闻')
for i, a in enumerate(selected):
    print(f'{i+1}. [{a["category"]}] {a["title"]} ({a["region"]})')
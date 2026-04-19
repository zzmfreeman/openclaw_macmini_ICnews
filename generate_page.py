#!/usr/bin/env python3
"""
为每份 semi-brief 生成独立 HTML 页面 + 更新主页索引 + 清理30天以上旧文件

用法: python3 generate_page.py <brief_json_path> [--base-dir /path/to/repo]

生成的 HTML 页面命名: YYYY-MM-DD-{morning,midday,evening}.html
每个 HTML 独立加载对应的 JSON 数据文件
主页 index.html 列出所有可用简报的链接
"""
import json, sys, os, re, glob, shutil
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(BASE_DIR, 'docs')
ARCHIVE_DIR = os.path.join(DOCS_DIR, 'archive')

PERIOD_INFO = {
    'morning': {'icon': '☀️', 'label': '早报', 'bg': '#f0f9ff', 'accent': '#2563eb', 'border': '#bfdbfe'},
    'midday':  {'icon': '🌤️', 'label': '午报', 'bg': '#fffbeb', 'accent': '#f59e0b', 'border': '#fde68a'},
    'evening': {'icon': '🌙', 'label': '晚报', 'bg': '#1e293b', 'accent': '#8b5cf6', 'border': '#6d28d9',
                'text': '#e2e8f0', 'muted': '#94a3b8', 'card': '#334155', 'item_bg': '#374151',
                'insight_bg': '#451a03', 'action_bg': '#064e3b'},
}

def get_period_style(period):
    p = PERIOD_INFO.get(period, PERIOD_INFO['morning'])
    is_dark = period == 'evening'
    return p, is_dark

HTML_TEMPLATE = '''<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>%%PAGE_TITLE%%</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg:%%BG%%; --panel:%%PANEL%%; --text:%%TEXT%%; --muted:%%MUTED%%;
      --accent:%%ACCENT%%; --border:%%BORDER%%; --card:%%CARD%%;
      --tag-bg:%%TAG_BG%%; --tag-text:%%TAG_TEXT%%;
      --sans: 'Noto Sans SC', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", sans-serif;
    }}
    body{{margin:0; background:var(--bg); color:var(--text); font-family:var(--sans)}}
    .wrap{{max-width:1100px;margin:0 auto;padding:40px 24px 60px}}
    .topbar{{margin-bottom:32px; border-bottom:1px solid var(--border); padding-bottom:24px; text-align:center}}
    .title{{font-size:32px; font-weight:700; color:var(--text); letter-spacing:-0.5px; margin-bottom:8px}}
    .meta{{display:flex; justify-content:center; gap:12px; font-size:14px; color:var(--muted); flex-wrap:wrap}}
    .pill{{background:var(--panel); border:1px solid var(--border); padding:4px 12px; border-radius:999px; color:var(--muted); font-weight:500; text-decoration:none}}
    .pill:hover{{background:var(--accent); color:#fff}}
    .buildmeta{{margin-top:8px;font-size:13px;color:var(--muted)}}
    
    .grid-main{{display:grid; grid-template-columns: 1fr; gap:32px}}
    .headline-card{{background:var(--panel); border:1px solid var(--border); border-radius:12px; box-shadow:0 2px 4px rgba(0,0,0,0.05); padding:20px}}
    .headline-card h2{{margin:0 0 16px; font-size:18px; font-weight:700; color:var(--text); border-bottom:2px solid var(--accent)}}
    .headline-list{{display:grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap:16px; padding:0}}
    .headline{{background:var(--tag_bg); border:1px solid var(--border); padding:16px; border-radius:8px; text-decoration:none; color:inherit; display:block}}
    .headline:hover{{transform:translateY(-2px); box-shadow:0 4px 6px rgba(0,0,0,0.1); background:var(--panel)}}
    .headline .t{{font-size:15px; font-weight:600; color:var(--text); line-height:1.5}}
    .headline .s{{font-size:12px; color:var(--muted); margin-top:4px}}
    
    .keyword-row{{margin-bottom:24px; padding:16px; background:var(--panel); border:1px solid var(--border); border-radius:8px; display:flex; flex-wrap:wrap; gap:8px; align-items:center}}
    .kw-label{{font-size:13px; font-weight:700; color:var(--muted); margin-right:12px}}
    
    .section-title{{font-size:20px; font-weight:600; border-bottom:3px solid var(--accent); padding-bottom:8px; margin:40px 0 24px; color:var(--text); display:flex; align-items:center; gap:8px}}
    
    .item{{background:var(--panel); border-left:4px solid var(--accent); border-radius:8px; padding:24px; margin-bottom:24px; box-shadow:0 2px 4px rgba(0,0,0,0.05)}}
    .item:hover{{transform:translateX(4px)}}
    .item .header{{margin-bottom:16px}}
    .item .title2{{font-size:22px; font-weight:600; color:var(--text); margin-bottom:10px; line-height:1.4}}
    .item .meta-row{{display:flex; gap:12px; align-items:center; flex-wrap:wrap; font-size:13px; color:var(--muted)}}
    .item .meta-row a{{color:var(--accent); text-decoration:none; font-weight:500}}
    .item .meta-row a:hover{{text-decoration:underline}}
    
    .badge{{font-size:12px; padding:2px 10px; border-radius:12px; font-weight:500}}
    .badge.domestic{{background:#eff6ff; color:#1d4ed8}}
    .badge.overseas{{background:#f5f3ff; color:#7c3aed}}
    .badge-tag{{background:var(--tag_bg); color:var(--tag_text); border:1px solid var(--border)}}
    
    .summary{{color:var(--text); line-height:1.8}}
    .summary ul{{margin:0; padding-left:18px}}
    .summary li{{margin-bottom:6px}}
    
    .box{{padding:20px; border-radius:8px; font-size:15px; line-height:1.6}}
    .box-insight{{background:%%INSIGHT_BG%%; border-left:3px solid #f59e0b; color:%%INSIGHT_TEXT%%}}
    .box-insight .lbl{{color:#b45309; font-weight:700; font-size:12px; margin-bottom:8px}}
    .box-action{{background:%%ACTION_BG%%; border-left:3px solid #10b981; color:%%ACTION_TEXT%%}}
    .box-action .lbl{{color:#15803d; font-weight:700; font-size:12px; margin-bottom:8px}}
    
    .glossary-box{{margin-top:20px; padding:16px; background:var(--tag_bg); border:1px dashed var(--border); border-radius:8px}}
    .glossary-title{{font-size:12px; font-weight:700; color:var(--muted); margin-bottom:8px}}
    .glossary-item{{font-size:13px; color:var(--tag_text); margin-bottom:6px; line-height:1.5}}
    .glossary-term{{font-weight:700; color:var(--text); background:var(--border); padding:1px 6px; border-radius:4px; margin-right:6px; font-size:12px}}
    
    .search-row{{margin-bottom:16px}}
    #q{{width:100%; padding:12px 16px; border:1px solid var(--border); border-radius:8px; font-family:inherit; background:var(--panel); font-size:14px; box-sizing:border-box; color:var(--text)}}
    #q:focus{{outline:none; border-color:var(--accent); box-shadow:0 0 0 3px rgba(37,99,235,0.1)}}
    
    .foot{{margin-top:40px; text-align:center; color:var(--muted); font-size:12px; padding-top:20px; border-top:1px solid var(--border)}}
    
    .warnbox{{padding:12px; border-radius:8px; margin-bottom:20px}}
    
    @media (max-width: 900px){{.headline-list{{grid-template-columns:1fr}}}}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="topbar">
      <div class="title" id="pageTitle">%%PAGE_TITLE%%</div>
      <div class="buildmeta" id="buildmeta"></div>
      <div class="meta">
        <a href="index.html" class="pill">🏠 主页</a>
        <span id="asof">📅 -</span>
        <span id="count">📊 -</span>
      </div>
    </div>
    <div class="grid-main">
      <div class="sidebar">
        <div class="search-row"><input id="q" placeholder="🔍 搜索标题、摘要、洞见..." /></div>
        <div class="headline-card"><h2>🔥 今日标题总览</h2><div class="headline-list" id="headlines"></div></div>
      </div>
      <div>
        <div class="keyword-row"><div class="kw-label">🏷️ 本期关键词</div><div id="keywords" style="display:contents"></div></div>
      <div id="glossarySection" class="glossary-card" style="margin-bottom:24px;padding:16px;background:var(--panel);border:1px solid var(--border);border-radius:8px"></div>
        <div class="section-title" id="domestic">🇨🇳 国内</div>
        <div id="domesticItems"></div>
        <div class="section-title" id="overseas">🌍 国外</div>
        <div id="overseasItems"></div>
      </div>
    </div>
    <div class="foot" id="footer">Generated by OpenClaw</div>
  </div>
  <script>
    const state={{data:null,filtered:null}};
    const el=(id)=>document.getElementById(id);
    const esc=(s)=>String(s||'').replace(/[&<>"']/g,c=>({{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}}[c]));
    const DOMESTIC=['财联社','集微网','36氪','半导体行业观察','爱集微','界面新闻','第一财经','澎湃新闻','新浪科技','雷锋网','虎嗅','钛媒体'];
    function isDom(it){{if(it.region==='domestic')return true;if(it.region==='overseas')return false;return DOMESTIC.some(s=>(it.source||'').includes(s))}}
    function render(){{const d=state.filtered||state.data;if(!d)return;if(!d.items)d.items=[];
      el('buildmeta').textContent=`版本号(${d.version||'-'})｜生成时间(${d.generatedAt||'-'})`;
      el('asof').textContent=`更新: ${d.generatedAt||'-'}`;
      el('count').textContent=`条数: ${d.items.length}`;
      el('keywords').innerHTML=(d.keywords||[]).map(k=>`<span class="badge badge-tag">${{esc(k)}}</span>`).join('');
      el('headlines').innerHTML=d.items.map((it,i)=>`<a href="#item-${{i}}" class="headline"><div class="t">${{esc(it.title)}}</div><div class="s">${{esc(it.source||'')}} · ${{esc(it.published||'')}}</div></a>`).join('');
      const ri=(it,i)=>`<div class="item" id="item-${{i}}"><div class="header"><div class="title2">${{esc(it.title)}}</div><div class="meta-row"><span>#${{i+1}}</span><span>📰 ${{esc(it.source||'')}}</span><span>📅 ${{esc(it.published||'')}}</span>${{it.url?`<a href="${{esc(it.url)}}" target="_blank">🔗 原文</a>`:''}}${{(it.tags||[]).map(t=>`<span class="badge badge-tag">${{esc(t)}}</span>`).join('')}}</div></div><div class="summary">${{it.summary}}</div><div class="box box-insight"><div class="lbl">💡 洞见</div><ul>${{(it.insights||[]).map(x=>`<li>${{esc(x)}}</li>`).join('')}}</ul></div><div class="box box-action"><div class="lbl">🎯 建议</div><ul>${{(it.actions||[]).map(x=>`<li>${{esc(x)}}</li>`).join('')}}</ul></div></div>${{(it.glossary||[]).length?`<div class="glossary-box"><div class="glossary-title">📚 术语</div>${{it.glossary.map(g=>typeof g==="string"?`<div class="glossary-item"><span class="glossary-term">${{esc(g)}}</span></div>`:`<div class="glossary-item"><span class="glossary-term">${{esc(g.term)}}</span>${{esc(g.desc)}}</div>`).join('')}}</div>`:''}}`;
      const dm=d.items.filter(isDom),ov=d.items.filter(x=>!isDom(x));
      el('domesticItems').innerHTML=dm.length?dm.map(ri).join(''):'<div class="warnbox">暂无国内</div>';
      el('overseasItems').innerHTML=ov.length?ov.map(ri).join(''):'<div class="warnbox">暂无国外</div>';
      el('footer').textContent=d.footer||'Generated by OpenClaw';
    }}
    function filter(q){{q=(q||'').trim().toLowerCase();if(!q){{state.filtered=null;render();return}}state.filtered={{...state.data,items:state.data.items.filter(it=>[it.title,it.source,it.summary,(it.insights||[]).join(' '),(it.tags||[]).join(' ')].join(' ').toLowerCase().includes(q))}};render()}}
    el('q').addEventListener('input',e=>filter(e.target.value));
    fetch('./%%JSON_FILE%%?t='+Date.now(),{{cache:'no-store'}}).then(r=>r.json()).then(j=>{{state.data=j;render()}}).catch(err=>{{el('headlines').innerHTML=`<div class="warnbox">暂无数据: ${{esc(err.message)}}</div>`}});
  </script>
</body>
</html>'''

def generate_brief_page(brief_json_path, base_dir=None):
    base_dir = base_dir or BASE_DIR
    docs_dir = os.path.join(base_dir, 'docs')
    os.makedirs(docs_dir, exist_ok=True)
    
    with open(brief_json_path) as f:
        data = json.load(f)
    
    period = data.get('period', 'morning')
    generated_at = data.get('generatedAt', '')
    version = data.get('version', '')
    
    # Parse date from generatedAt
    dt = datetime.fromisoformat(generated_at.replace('+08:00', '+08:00'))
    date_str = dt.strftime('%Y-%m-%d')
    
    # Unique filenames
    html_name = f"{date_str}-{period}.html"
    json_name = f"{date_str}-{period}.json"
    
    pinfo, is_dark = get_period_style(period)
    
    # Style variables
    if is_dark:
        bg = '#1e293b'
        panel = '#334155'
        text = '#e2e8f0'
        muted = '#94a3b8'
        accent = '#8b5cf6'
        border = '#475569'
        card = '#374151'
        tag_bg = '#374151'
        tag_text = '#e2e8f0'
        insight_bg = '#451a03'
        insight_text = '#fbbf24'
        action_bg = '#064e3b'
        action_text = '#34d399'
    else:
        bg = pinfo['bg']
        panel = '#ffffff'
        text = '#1e293b'
        muted = '#64748b'
        accent = pinfo['accent']
        border = '#e2e8f0'
        card = '#f8fafc'
        tag_bg = '#f1f5f9'
        tag_text = '#475569'
        insight_bg = '#fffbeb'
        insight_text = '#92400e'
        action_bg = '#f0fdf4'
        action_text = '#166534'
    
    page_title = f"{pinfo['icon']} {date_str} {pinfo['label']}｜半导体简报"
    
    html_content = HTML_TEMPLATE
    # Replace style placeholders (using %% markers to avoid JS brace conflicts)
    replacements = {
        '%%PAGE_TITLE%%': page_title,
        '%%JSON_FILE%%': json_name,
        '%%BG%%': bg,
        '%%PANEL%%': panel,
        '%%TEXT%%': text,
        '%%MUTED%%': muted,
        '%%ACCENT%%': accent,
        '%%BORDER%%': border,
        '%%CARD%%': card,
        '%%TAG_BG%%': tag_bg,
        '%%TAG_TEXT%%': tag_text,
        '%%INSIGHT_BG%%': insight_bg,
        '%%INSIGHT_TEXT%%': insight_text,
        '%%ACTION_BG%%': action_bg,
        '%%ACTION_TEXT%%': action_text,
    }
    for key, val in replacements.items():
        html_content = html_content.replace(key, val)

    # Fix double braces for GitHub Pages/Jekyll compatibility
    html_content = html_content.replace("{{", "{").replace("}}", "}")
    
    # Write JSON and HTML to docs/
    json_path = os.path.join(docs_dir, json_name)
    html_path = os.path.join(docs_dir, html_name)
    
    with open(json_path, 'w') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    with open(html_path, 'w') as f:
        f.write(html_content)
    
    print(f"Generated: {html_name} + {json_name}")
    return html_name, json_name


def generate_index_page(base_dir=None):
    """Generate index.html listing all available briefs"""
    base_dir = base_dir or BASE_DIR
    docs_dir = os.path.join(base_dir, 'docs')
    
    # Scan docs/ for dated HTML files
    pattern = re.compile(r'(\d{4}-\d{2}-\d{2})-(morning|midday|evening)\.html$')
    briefs = []
    for f in os.listdir(docs_dir):
        m = pattern.match(f)
        if m:
            date_str, period = m.groups()
            pinfo = PERIOD_INFO.get(period, PERIOD_INFO['morning'])
            briefs.append({
                'date': date_str,
                'period': period,
                'html': f,
                'json': f.replace('.html', '.json'),
                'icon': pinfo['icon'],
                'label': pinfo['label'],
                'sort_key': f,  # YYYY-MM-DD-period sorts naturally
            })
    
    # Sort descending (newest first)
    briefs.sort(key=lambda x: x['sort_key'], reverse=True)
    
    # Build index HTML
    items_html = ''
    for b in briefs[:30]:  # Show max 30
        items_html += f'''
        <a href="{b['html']}" class="brief-card">
          <div class="brief-icon">{b['icon']}</div>
          <div class="brief-info">
            <div class="brief-title">{b['date']} {b['label']}</div>
            <div class="brief-period">{b['period']}</div>
          </div>
        </a>'''
    
    # Also show the "current" brief link — point to the latest dated HTML
    latest = briefs[0] if briefs else None
    if latest:
        current_link = f'''
        <a href="{latest['html']}" class="brief-card current">
          <div class="brief-icon">📡</div>
          <div class="brief-info">
            <div class="brief-title">最新简报（{latest['date']} {latest['label']}）</div>
            <div class="brief-period">{latest['period']}</div>
          </div>
        </a>'''
    else:
        current_link = ''
    
    index_html = '''<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>半导体简报｜Semi Brief</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root { --bg:#f8fafc; --text:#1e293b; --muted:#64748b; --accent:#2563eb; --border:#e2e8f0; --sans:'Noto Sans SC',-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"PingFang SC",sans-serif }
    body { margin:0; background:var(--bg); color:var(--text); font-family:var(--sans) }
    .wrap { max-width:900px; margin:0 auto; padding:40px 24px 60px }
    .hero { text-align:center; margin-bottom:40px; border-bottom:2px solid var(--border); padding-bottom:32px }
    .hero-title { font-size:36px; font-weight:700; letter-spacing:-1px }
    .hero-sub { font-size:16px; color:var(--muted); margin-top:12px }
    .brief-grid { display:grid; grid-template-columns:1fr; gap:16px }
    .brief-card { display:flex; align-items:center; gap:16px; background:#fff; border:1px solid var(--border); border-radius:12px; padding:20px; text-decoration:none; color:inherit; transition:transform 0.2s, box-shadow 0.2s }
    .brief-card:hover { transform:translateY(-2px); box-shadow:0 4px 8px rgba(0,0,0,0.08); border-color:var(--accent) }
    .brief-card.current { background:#eff6ff; border-color:var(--accent); border-width:2px }
    .brief-icon { font-size:32px; width:48px; text-align:center }
    .brief-info { flex:1 }
    .brief-title { font-size:18px; font-weight:600 }
    .brief-period { font-size:13px; color:var(--muted); margin-top:4px }
    .foot { margin-top:40px; text-align:center; color:var(--muted); font-size:12px; padding-top:20px; border-top:1px solid var(--border) }
    .section-label { font-size:14px; font-weight:700; color:var(--muted); margin:24px 0 8px; text-transform:uppercase; letter-spacing:1px }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="hero">
      <div class="hero-title">📡 半导体简报</div>
      <div class="hero-sub">芯片供应链 · Fab/封测/EDA/IP · 每天3次更新</div>
    </div>
    <div class="section-label">📌 最新</div>
    ''' + current_link + '''
    <div class="section-label">📅 历史简报</div>
    <div class="brief-grid">
    ''' + items_html + '''
    </div>
    <div class="foot">Generated by OpenClaw · Semi Brief</div>
  </div>
</body>
</html>'''
    
    with open(os.path.join(docs_dir, 'index.html'), 'w') as f:
        f.write(index_html)
    # Also copy to root
    with open(os.path.join(base_dir, 'index.html'), 'w') as f:
        f.write(index_html)
    
    print(f"Generated index.html with {len(briefs)} brief links")


def cleanup_old_files(base_dir=None, max_days=30):
    """Delete brief HTML/JSON files older than max_days"""
    base_dir = base_dir or BASE_DIR
    docs_dir = os.path.join(base_dir, 'docs')
    archive_dir = os.path.join(docs_dir, 'archive')
    os.makedirs(archive_dir, exist_ok=True)
    
    cutoff = datetime.now() - timedelta(days=max_days)
    pattern = re.compile(r'(\d{4}-\d{2}-\d{2})-(morning|midday|evening)\.(html|json)$')
    
    deleted = []
    for f in os.listdir(docs_dir):
        m = pattern.match(f)
        if m:
            date_str = m.group(1)
            try:
                dt = datetime.strptime(date_str, '%Y-%m-%d')
                if dt < cutoff:
                    os.remove(os.path.join(docs_dir, f))
                    deleted.append(f)
            except ValueError:
                pass
    
    # Also cleanup archive JSON files older than max_days
    archive_pattern = re.compile(r'brief_(\d{4}\d{2}\d{2})\.json$')
    for f in os.listdir(archive_dir):
        m = archive_pattern.match(f)
        if m:
            date_str_raw = m.group(1)
            try:
                dt = datetime.strptime(date_str_raw, '%Y%m%d')
                if dt < cutoff:
                    os.remove(os.path.join(archive_dir, f))
                    deleted.append(f)
            except ValueError:
                pass
    
    if deleted:
        print(f"Cleaned up {len(deleted)} files older than {max_days} days:")
        for d in deleted:
            print(f"  ❌ {d}")
    else:
        print(f"No files older than {max_days} days to clean up")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('brief_json', help='Path to brief JSON file')
    parser.add_argument('--base-dir', default=BASE_DIR, help='Repo base directory')
    parser.add_argument('--cleanup-days', type=int, default=30, help='Delete files older than N days')
    args = parser.parse_args()
    
    # 1. Generate unique page for this brief
    html_name, json_name = generate_brief_page(args.brief_json, args.base_dir)
    
    # 2. Generate index page
    generate_index_page(args.base_dir)
    
    # 3. Cleanup old files
    cleanup_old_files(args.base_dir, args.cleanup_days)

# semi-brief Skill

## 用途
半导体行业新闻简报生产线（早报/午报/晚报），NewsAPI 采集 + 脚本清洗 + 最小化 LLM 介入。

## 目录结构
```
semi-brief/
├── SKILL.md        ← 本文件（规则入口）
├── config.yaml     ← 可调参数（时间窗/条数/来源/关键词）
├── fetch.py        ← NewsAPI 采集 + 清洗 + 去重 + URL 自检
├── render.py       ← 写入 brief*.json + history.json + docs 镜像
├── publish.sh      ← git commit + push
└── run.py          ← 主入口，协调上述模块
```

## 触发方式（cron agentTurn）
cron 任务 `semi brief` 按以下流程执行：

1. 调用 `python3 semi-brief/run.py`（自动判断当前时段：06→morning / 13→midday / 20→afternoon）
2. 脚本完成采集/清洗/去重后，将候选条目写入 `semi-brief/llm_input.json`
3. **LLM 只做一件事**：读取 `llm_input.json`，生成中文摘要 + glossary，写入 `semi-brief/llm_output.json`
4. 再次调用 `python3 semi-brief/run.py` 完成渲染 + 发布
5. 回传对应 GitHub Pages 链接 + 版本号 + 生成时间 + commit

## LLM 最小化介入（节省 token）
LLM 不做：
- 搜索新闻
- 判断哪条是重要新闻（由脚本按时间/来源/热度排序）
- URL 可达性检查（脚本完成）
- 文件写入 / git 操作（脚本完成）

LLM 只做：
- 将英文标题+摘要翻译为中文（保留原意，不夸大）
- 提取 glossary（低共识词，数量见 config.yaml）
- 最终输出前做一次"重大人事/并购置顶"重排序

## 修改规则
| 修改内容 | 改哪里 |
|----------|--------|
| 时间窗/条数/来源占比 | `config.yaml` |
| 关键词/国内域名白名单 | `config.yaml` |
| 高共识词（不写 glossary）| `config.yaml` → `glossary_skip` |
| 采集/清洗/去重逻辑 | `fetch.py` |
| 输出格式/文件路径 | `render.py` |
| LLM 提示词 | `SKILL.md` 下方 → `## LLM Prompt Template` |

## LLM Prompt Template
当 `llm_input.json` 存在时，LLM 执行以下任务：

```
你是半导体行业新闻编辑。
输入：llm_input.json 中的 items（英文标题+摘要+来源）
任务：
1. 将每条新闻翻译为简洁中文（标题20字内，摘要50字内）
2. 优先保留：并购/人事变动/政策/重大投资 → 这类条目置顶
3. 国内来源（domestic=true）优先保留，不足时保留英文来源
4. 生成 glossary：仅包含 config.yaml glossary_skip 以外的低共识词
   - 每条格式：{"term": "缩写", "explanation": "一句话解释"}
5. 输出格式写入 semi-brief/llm_output.json：
   {"items": [...已翻译条目...], "glossary": [...]}
不要修改 url / publishedAt / source 字段。
```

## 质量约束（硬规则）
- 无未来日期
- URL 必须可直开（非首页/聚合页），脚本已完成 HEAD 检��
- 宁缺毋滥：实际条目不足时，说明原因，不补旧闻
- 版本号 / 生成时间 / commit 必须出现在回传消息和页面顶部

## 发布链接（固定）
- 早报：https://zzmfreeman.github.io/openclaw_macmini_ICnews/
- 午报：https://zzmfreeman.github.io/openclaw_macmini_ICnews/midday.html
- 晚报：https://zzmfreeman.github.io/openclaw_macmini_ICnews/afternoon.html

---
name: wsj-brief
description: Generate a structured Chinese WSJ-style financial brief from a Wall Street Journal URL or pasted article text using the local WSJ AI Brief API.
user-invocable: true
metadata: {"openclaw":{"emoji":"W","requires":{"bins":["node"]},"tags":["finance","news","wsj","brief"]}}
---

# WSJ Brief

Use this skill when the user asks for a WSJ brief, Wall Street Journal summary, Chinese financial news digest, or asks to summarize a WSJ article URL or pasted article text.

## What It Does

The local helper calls the WSJ AI Brief API at `http://127.0.0.1:8000/api/summarize` and returns:

- headline
- web lede
- AI summary
- key points
- risks
- market impact
- source URL when provided

## Run

Use the host shell tool to run:

```bash
/opt/homebrew/opt/node@22/bin/node /Users/zzm/.openclaw/workspace/scripts/wsj-brief.mjs --title "Article title" --content "Article text" --url "https://www.wsj.com/..."
```

For long pasted articles or text with quotes, pass JSON on stdin:

```bash
/opt/homebrew/opt/node@22/bin/node /Users/zzm/.openclaw/workspace/scripts/wsj-brief.mjs <<'JSON'
{"title":"Article title","content":"Long article text...","article_url":"https://www.wsj.com/...","max_bullets":5}
JSON
```

If shell quoting is awkward, write a temporary JSON request and pass it with `--input-json`:

```bash
/opt/homebrew/opt/node@22/bin/node /Users/zzm/.openclaw/workspace/scripts/wsj-brief.mjs --input-json /tmp/wsj-brief-request.json
```

If the user only gives a URL and no article body, still run the helper with `title` and `article_url`; it will let the local API attempt article fetching. Tell the user if the result says it used the local fallback summary.

## Output Rules

- Reply in Chinese unless the user asks otherwise.
- Keep the structure produced by the helper.
- Do not invent facts beyond the helper output.
- If the helper reports API or validation failure, explain the failure briefly and ask for either article text or a reachable URL.
- Do not give investment advice.

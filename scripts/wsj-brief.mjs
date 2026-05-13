#!/usr/bin/env node

import { readFile } from "node:fs/promises";

const DEFAULT_API = "http://127.0.0.1:8000/api/summarize";

function printHelp() {
  console.log(`Usage:
  wsj-brief.mjs --title "Article title" --content "Article text" [--url URL]
  wsj-brief.mjs --title "Article title" --url URL
  printf '%s' '{"title":"...","content":"...","article_url":"..."}' | wsj-brief.mjs

Options:
  --title TEXT        Article title.
  --content TEXT      Article body text. Use "-" to read body text from stdin.
  --input-json PATH   Read the full request JSON from a file.
  --file PATH         Read article body text from a file.
  --url URL           Source URL, passed through to the local API.
  --max-bullets N     Number of key points, 3-8. Default: 5.
  --api URL           Summarize endpoint. Default: ${DEFAULT_API}
  --json              Print the raw JSON response.
  --help              Show this help.`);
}

function parseArgs(argv) {
  const out = { api: DEFAULT_API, max_bullets: 5, rawJson: false };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    const next = () => {
      i += 1;
      if (i >= argv.length) throw new Error(`Missing value for ${arg}`);
      return argv[i];
    };

    if (arg === "--help" || arg === "-h") out.help = true;
    else if (arg === "--json") out.rawJson = true;
    else if (arg === "--title") out.title = next();
    else if (arg === "--content") out.content = next();
    else if (arg === "--input-json") out.inputJson = next();
    else if (arg === "--file") out.file = next();
    else if (arg === "--url" || arg === "--article-url") out.article_url = next();
    else if (arg === "--api") out.api = next();
    else if (arg === "--max-bullets" || arg === "--bullets") {
      const parsed = Number.parseInt(next(), 10);
      if (!Number.isFinite(parsed)) throw new Error(`Invalid bullet count: ${argv[i]}`);
      out.max_bullets = parsed;
    } else {
      throw new Error(`Unknown argument: ${arg}`);
    }
  }
  return out;
}

async function readStdin() {
  const chunks = [];
  for await (const chunk of process.stdin) chunks.push(Buffer.from(chunk));
  return Buffer.concat(chunks).toString("utf8");
}

function normalizeUrl(value) {
  if (!value) return undefined;
  const trimmed = String(value).trim();
  if (!trimmed) return undefined;
  try {
    return new URL(trimmed).toString();
  } catch {
    throw new Error(`Invalid URL: ${trimmed}`);
  }
}

function normalizeBulletCount(value) {
  const parsed = Number.parseInt(String(value ?? 5), 10);
  if (!Number.isFinite(parsed)) return 5;
  return Math.max(3, Math.min(8, parsed));
}

function padContent(content, title, url) {
  const text = String(content || "").trim();
  if (text.length >= 50) return text;
  const sourceHint = url ? ` Source URL: ${url}.` : "";
  const padded = `${text} Article title: ${title}.${sourceHint} Please fetch or infer only from the provided source and mark uncertainty clearly.`;
  return padded.length >= 50 ? padded : `${padded} Additional context was not provided.`;
}

function formatBrief(result) {
  const cleanListItem = (value) => String(value).trim().replace(/^[-*]\s+/, "");
  const keyPoints = Array.isArray(result.key_points)
    ? result.key_points.map(cleanListItem).filter(Boolean)
    : [];
  const risks = Array.isArray(result.risks)
    ? result.risks.map(cleanListItem).filter(Boolean)
    : [];
  const lines = [];

  lines.push(`# ${result.headline || "WSJ AI Brief"}`);
  if (result.web_lede) lines.push("", result.web_lede);
  if (result.ai_summary) lines.push("", "## AI Summary", result.ai_summary);
  if (keyPoints.length) {
    lines.push("", "## Key Points");
    keyPoints.forEach((item, index) => lines.push(`${index + 1}. ${item}`));
  }
  if (result.market_impact) lines.push("", "## Market Impact", result.market_impact);
  if (risks.length) {
    lines.push("", "## Risks");
    risks.forEach((item) => lines.push(`- ${item}`));
  }
  if (result.source) lines.push("", `Source: ${result.source}`);
  return lines.join("\n");
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) {
    printHelp();
    return;
  }

  let stdin = "";
  if (args.content === "-" || process.stdin.isTTY !== true) {
    stdin = (await readStdin()).trim();
  }

  let payload = {};
  if (args.inputJson) {
    payload = JSON.parse(await readFile(args.inputJson, "utf8"));
  }
  if (stdin.startsWith("{")) {
    payload = { ...payload, ...JSON.parse(stdin) };
  } else if (stdin && args.content === "-") {
    payload.content = stdin;
  }

  if (args.file) payload.content = await readFile(args.file, "utf8");
  if (args.title) payload.title = args.title;
  if (args.content && args.content !== "-") payload.content = args.content;
  if (args.article_url) payload.article_url = args.article_url;
  if (args.max_bullets) payload.max_bullets = args.max_bullets;

  const articleUrl = normalizeUrl(payload.article_url || payload.url);
  const title = String(payload.title || "WSJ Article Brief").trim();
  if (title.length < 5) throw new Error("Title must be at least 5 characters.");

  const requestBody = {
    title,
    content: padContent(payload.content, title, articleUrl),
    max_bullets: normalizeBulletCount(payload.max_bullets),
  };
  if (articleUrl) requestBody.article_url = articleUrl;

  const response = await fetch(args.api, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(requestBody),
  });

  const text = await response.text();
  if (!response.ok) {
    throw new Error(`WSJ Brief API returned HTTP ${response.status}: ${text}`);
  }

  const result = JSON.parse(text);
  console.log(args.rawJson ? JSON.stringify(result, null, 2) : formatBrief(result));
}

main().catch((error) => {
  console.error(`wsj-brief failed: ${error.message}`);
  process.exitCode = 1;
});

#!/usr/bin/env node

import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";
import process from "node:process";

const DEFAULT_SOURCES = ["baidu", "toutiao", "zhihu", "bilibili", "github"];
const SUPPORTED_SOURCES = new Set([
  "baidu", "toutiao", "douyin", "zhihu", "bilibili", "bili", "36kr", "ithome", "juejin", "github", "github_trending",
]);

function usage() {
  return [
    "Usage: node collect_public_hot_signals.mjs [--sources baidu,toutiao] [--out signals.json] [--timeout-ms 20000]",
    "",
    `Supported sources: ${[...SUPPORTED_SOURCES].join(", ")}`,
  ].join("\n");
}

function parseArgs(argv) {
  const options = { sources: DEFAULT_SOURCES, out: "", timeoutMs: 20_000 };
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--help" || arg === "-h") {
      console.log(usage());
      process.exit(0);
    }
    if (arg === "--sources") {
      options.sources = String(argv[++index] || "").split(/[,，\s]+/).map((item) => item.trim().toLowerCase()).filter(Boolean);
      continue;
    }
    if (arg.startsWith("--sources=")) {
      options.sources = arg.slice("--sources=".length).split(/[,，\s]+/).map((item) => item.trim().toLowerCase()).filter(Boolean);
      continue;
    }
    if (arg === "--out") {
      options.out = String(argv[++index] || "").trim();
      continue;
    }
    if (arg.startsWith("--out=")) {
      options.out = arg.slice("--out=".length).trim();
      continue;
    }
    if (arg === "--timeout-ms") {
      options.timeoutMs = Number(argv[++index]);
      continue;
    }
    if (arg.startsWith("--timeout-ms=")) {
      options.timeoutMs = Number(arg.slice("--timeout-ms=".length));
      continue;
    }
    throw new Error(`Unknown option: ${arg}`);
  }
  if (!options.sources.length) throw new Error("At least one source is required.");
  if (!Number.isFinite(options.timeoutMs) || options.timeoutMs < 1_000) throw new Error("--timeout-ms must be at least 1000.");
  for (const source of options.sources) {
    if (!SUPPORTED_SOURCES.has(source)) throw new Error(`Unsupported source: ${source}`);
  }
  return options;
}

function cleanText(value, maxLength = 240) {
  return String(value ?? "").replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim().slice(0, maxLength);
}

function hash(value) {
  return crypto.createHash("sha256").update(value).digest("hex").slice(0, 16);
}

function normalizeHotNumber(value) {
  const raw = String(value ?? "").replace(/,/g, "").trim();
  if (!raw) return null;
  const number = Number(raw.replace(/[万亿kKmM].*$/, "").replace(/[^\d.]/g, ""));
  if (!Number.isFinite(number)) return null;
  if (/亿/.test(raw)) return Math.round(number * 100_000_000);
  if (/万/.test(raw)) return Math.round(number * 10_000);
  if (/[kK]/.test(raw)) return Math.round(number * 1_000);
  if (/[mM]/.test(raw)) return Math.round(number * 1_000_000);
  return Math.round(number);
}

function normalizeSignal(item, index) {
  const platform = cleanText(item.platform || "unknown", 60);
  const title = cleanText(item.title || item.name || item.word || item.query, 160);
  if (!title) return null;
  const rank = Number(item.rank ?? item.index ?? index + 1);
  return {
    signal_id: `${platform}_${hash(`${platform}:${title}:${item.url || ""}`)}`,
    platform,
    source: cleanText(item.source || "public_hot_board", 80),
    title,
    url: cleanText(item.url || "", 600),
    rank: Number.isFinite(rank) ? rank : index + 1,
    hot_value: normalizeHotNumber(item.hot_value ?? item.hot ?? item.score),
    snippet: cleanText(item.snippet || item.description || item.desc || "", 240),
    category: cleanText(item.category || "", 80),
    collected_at: new Date().toISOString(),
  };
}

function dedupe(signals) {
  const seen = new Set();
  return signals.flatMap((signal, index) => {
    const normalized = normalizeSignal(signal, index);
    if (!normalized) return [];
    const key = `${normalized.platform}:${normalized.title.toLowerCase()}`;
    if (seen.has(key)) return [];
    seen.add(key);
    return [normalized];
  });
}

async function fetchText(url, timeoutMs, headers = {}) {
  const response = await fetch(url, {
    headers: {
      "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/125 Safari/537.36",
      Accept: "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
      ...headers,
    },
    signal: AbortSignal.timeout(timeoutMs),
  });
  const text = await response.text();
  if (!response.ok) throw new Error(`HTTP ${response.status}: ${cleanText(text, 180)}`);
  return text;
}

function baiduSignals(html) {
  const marker = "<!--s-data:";
  const signals = [];
  let offset = 0;
  while (offset < html.length) {
    const start = html.indexOf(marker, offset);
    if (start < 0) break;
    const jsonStart = start + marker.length;
    const end = html.indexOf("-->", jsonStart);
    if (end < 0) break;
    offset = end + 3;
    try {
      const raw = html.slice(jsonStart, end).replace(/&quot;/g, '"').replace(/&amp;/g, "&").replace(/\\u002F/g, "/");
      const cards = JSON.parse(raw)?.data?.cards || [];
      for (const card of cards) {
        for (const item of Array.isArray(card?.content) ? card.content : []) {
          signals.push({
            platform: "baidu",
            source: "baidu_realtime",
            title: item.query || item.word || item.title,
            rank: Number(item.index ?? signals.length) + 1,
            hot_value: item.hotScore,
            snippet: item.desc || item.show?.join?.(" "),
            url: item.rawUrl || item.url || item.appUrl,
            category: item.hotTag,
          });
        }
      }
    } catch {
      // Ignore an unrelated or malformed hydration comment.
    }
  }
  return dedupe(signals);
}

function genericJsonSignals(body, platform, source, options = {}) {
  const items = Array.isArray(body?.data) ? body.data : Array.isArray(body) ? body : [];
  return dedupe(items.map((item, index) => {
    const material = item.templateMaterial || {};
    const url = item.link || item.url || item.mobileUrl || item.pcUrl || item.route || "";
    return {
      platform,
      source,
      title: item.title || item.name || item.word || item.query || item.keyword || material.widgetTitle,
      rank: item.rank || item.index || index + 1,
      hot_value: item.hot || item.hot_value || item.score || item.extra || item.heat || item.hotScore || material.statRead,
      snippet: item.desc || item.description || item.summary || material.authorName,
      url: options.urlPrefix && url && !/^https?:\/\//i.test(url) ? `${options.urlPrefix}${url.replace(/^\/+/, "")}` : url,
      category: item.category || item.type || item.label,
    };
  }));
}

async function collectBaidu(options) {
  const html = await fetchText("https://top.baidu.com/board?tab=realtime", options.timeoutMs);
  return { source: "baidu_realtime", signals: baiduSignals(html) };
}

async function collectToutiao(options) {
  const body = JSON.parse(await fetchText("https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc", options.timeoutMs));
  return {
    source: "toutiao_hot_board",
    signals: dedupe((body.data || []).map((item, index) => ({
      platform: "toutiao",
      source: "toutiao_hot_board",
      title: item.Title || item.QueryWord,
      rank: index + 1,
      hot_value: item.HotValue,
      snippet: item.Label,
      url: item.Url,
      category: Array.isArray(item.InterestCategory) ? item.InterestCategory.join(",") : "",
    }))),
  };
}

async function collectAggregated(options, platform, source, url, extra = {}) {
  const body = JSON.parse(await fetchText(url, options.timeoutMs, { Accept: "application/json,text/plain,*/*" }));
  if (typeof body?.code === "number" && body.code !== 200) throw new Error(`provider_code_${body.code}: ${cleanText(body.msg || body.message, 160)}`);
  return { source, signals: genericJsonSignals(body, platform, source, extra) };
}

function githubTrendingFromHtml(html) {
  const signals = [];
  const articles = html.match(/<article[\s\S]*?<\/article>/gi) || [];
  for (const article of articles) {
    const repo = article.match(/href="\/(?:[^"/]+)\/([^"?#]+)"/)?.[1];
    const pathMatch = article.match(/href="\/(?:[^"/]+)\/([^"?#]+)"/) ? article.match(/href="\/([^"?#]+\/[^"?#]+)"/) : null;
    const repoPath = pathMatch?.[1];
    if (!repoPath || !repoPath.includes("/")) continue;
    const description = cleanText(article.match(/<p[^>]*>([\s\S]*?)<\/p>/i)?.[1] || "", 220);
    signals.push({ platform: "github", source: "github_trending", title: repoPath, rank: signals.length + 1, snippet: description, url: `https://github.com/${repoPath}`, category: "open_source" });
  }
  return dedupe(signals);
}

async function collectGithub(options) {
  try {
    const html = await fetchText("https://github.com/trending?since=daily", options.timeoutMs);
    const signals = githubTrendingFromHtml(html);
    if (signals.length) return { source: "github_trending", signals };
  } catch {
    // Fall through to the documented GitHub API search fallback.
  }
  const since = new Date(Date.now() - 14 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
  const body = JSON.parse(await fetchText(`https://api.github.com/search/repositories?q=${encodeURIComponent(`created:>${since}`)}&sort=stars&order=desc&per_page=25`, options.timeoutMs, { Accept: "application/vnd.github+json" }));
  return {
    source: "github_trending_search_fallback",
    signals: dedupe((body.items || []).map((item, index) => ({
      platform: "github",
      source: "github_trending_search_fallback",
      title: item.full_name,
      rank: index + 1,
      hot_value: item.stargazers_count,
      snippet: [item.description, item.language ? `language=${item.language}` : ""].filter(Boolean).join("; "),
      url: item.html_url,
      category: item.language || "open_source",
    }))),
  };
}

const COLLECTORS = {
  baidu: collectBaidu,
  toutiao: collectToutiao,
  douyin: (options) => collectAggregated(options, "douyin", "douyin_hot_probe", "https://api.zxz.ee/api/hot/?type=douyin"),
  zhihu: (options) => collectAggregated(options, "zhihu", "zhihu_hot_list", "https://api.zxz.ee/api/hot/?type=zhihu"),
  bilibili: (options) => collectAggregated(options, "bilibili", "bilibili_hot_list", "https://api.zxz.ee/api/hot/?type=bilibili"),
  bili: (options) => collectAggregated(options, "bilibili", "bilibili_hot_list", "https://api.zxz.ee/api/hot/?type=bilibili"),
  "36kr": (options) => collectAggregated(options, "36kr", "36kr_hot_list", "https://v2.xxapi.cn/api/hot36kr", { urlPrefix: "https://www.36kr.com/" }),
  ithome: (options) => collectAggregated(options, "ithome", "ithome_hot_list", "https://api.zxz.ee/api/hot/?type=ithome"),
  juejin: (options) => collectAggregated(options, "juejin", "juejin_hot_list", "https://api.zxz.ee/api/hot/?type=juejin"),
  github: collectGithub,
  github_trending: collectGithub,
};

async function main() {
  const options = parseArgs(process.argv.slice(2));
  const results = await Promise.all(options.sources.map(async (requested) => {
    try {
      const result = await COLLECTORS[requested](options);
      return { requested, source: result.source, ok: true, count: result.signals.length, signals: result.signals };
    } catch (error) {
      return { requested, source: requested, ok: false, count: 0, error: cleanText(error.message, 400), signals: [] };
    }
  }));
  const artifact = {
    artifact_type: "public_hot_signals",
    schema_version: 1,
    collected_at: new Date().toISOString(),
    requested_sources: options.sources,
    sources: results.map(({ requested, source, ok, count, error }) => ({ requested, source, ok, count, error: error || null })),
    signals: dedupe(results.flatMap((result) => result.signals)),
  };
  if (!artifact.signals.length) {
    console.error(JSON.stringify(artifact, null, 2));
    throw new Error("No public hot signals were collected.");
  }
  if (options.out) {
    const outputPath = path.resolve(options.out);
    await fs.mkdir(path.dirname(outputPath), { recursive: true });
    await fs.writeFile(outputPath, `${JSON.stringify(artifact, null, 2)}\n`, "utf8");
    console.log(JSON.stringify({ output: outputPath, signal_count: artifact.signals.length, sources: artifact.sources }, null, 2));
  } else {
    console.log(JSON.stringify(artifact, null, 2));
  }
}

main().catch((error) => {
  console.error(`collect_public_hot_signals: ${error.message}`);
  process.exitCode = 1;
});

---
name: public-hot-signals
description: Collect normalized, source-traceable public trending signals across general Chinese web platforms. Use when the user asks for current public hot topics, trending news, cross-platform topic signals, or source-backed ideas outside a specifically AI-only trend report. Do not use to select a final topic or write a script.
---

# Public Hot Signals

Collect signals only. A signal says that a title is trending on a source; it is not a verified fact and it is not a recommended video topic.

## Collect

1. Decide the requested public sources from the user's request. Default to `baidu,toutiao,zhihu,bilibili,github`; omit technical sources unless they fit the request.
2. Save a task-scoped artifact, never a global cache:

```bash
node "${CODEX_HOME:-$HOME/.codex}/skills/public-hot-signals/scripts/collect_public_hot_signals.mjs" \
  --sources baidu,toutiao,zhihu,bilibili \
  --out outputs/hot-signals.json
```

3. Read the JSON artifact. Report successful and failed sources, collection time, and the original title, URL, rank, and metric for every signal used later.
4. Pass the artifact to `content-topic-selection` when the user wants ideas. Do not turn raw ranks into a final recommendation inside this skill.

## Boundaries

- Do not call `ai-trend-report`. That report is a separate, AI-specific source selected by `content-topic-selection` only when the current task warrants it or the user requests it.
- Treat a source outage as a per-source failure. Continue when at least one source returns signals; fail only when none succeed.
- Do not make factual claims from a hot-list title, rank, or metric. Require independent sources during research and script writing.
- Preserve source URLs and source errors. Do not hide use of aggregation endpoints.

Read [sources.md](references/sources.md) before changing source choices or interpreting source reliability.

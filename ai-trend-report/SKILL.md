---
name: ai-trend-report
description: Retrieve and analyze the latest public SciTiger AI trend report. Use when asked in Chinese or English to fetch the AI report, summarize or organize its content, compare AI topics across Douyin, Bilibili, WeChat, Xiaohongshu, and Video Channels, identify trends, select content ideas, or answer follow-up questions about a retrieved report.
---

# AI Trend Report

Retrieve the latest report with `scripts/fetch_report.py`. It reads the public `https://scitiger.cn/reports/daily.json` endpoint and needs no API key.

## Retrieve

1. Run `python3 scripts/fetch_report.py --output <temporary-json-path>` to save the sanitized full response for analysis.
2. Run it without `--output` to print a compact overview.
3. Treat a response as valid only when its root includes `report_meta` and `summary`. Report endpoint or schema failures plainly.
4. Use the root report object as the report body. Use `report_meta.date` and `report_meta.data_window_days` to identify the report date and collection window.

The script removes signed or credential-bearing URL fields if they appear. Do not request, persist, or reproduce those fields.

## Analyze

Start every report answer with collection scope and data health: report date, generated time, collection window, successful sources, source count, and item count. State the difference between the report date and item publication dates when present.

Use the structured fields rather than inferring from titles:

- `summary`, `platforms`, and `top_categories` for coverage and aggregate comparisons.
- `trending_topics` for cross-platform examples and ranked attention.
- `items_by_platform` for platform-specific selection, title grouping, and metric-based evidence.
- `agent_insight`, `agent_recommendations`, and `cross_platform_opportunities` as report-generated suggestions, not independently verified facts.

For follow-up requests, reuse the saved report in the current task when it remains relevant; otherwise retrieve a fresh one. Support topic maps, platform comparisons, editorial calendars, content shortlists, title-angle variants, and briefings.

## Output Rules

- Distinguish report observations from external facts. Describe content titles and engagement as "the report collected" or "the report indicates".
- Preserve source platform, author, publication date, URL, and metrics for any item recommended for action.
- State selection criteria for rankings or shortlists. Do not invent engagement, dates, authors, or URLs.
- Keep initial overviews concise. Expand only the requested slice in follow-up work.
- Do not write application code. Write a user-facing document, table, or spreadsheet only when explicitly requested.

## Examples

- "获取最新 AI 报告，并概览今天的主题。"
- "基于刚才的报告，整理 10 个适合小红书的 AI 创作选题，并保留来源。"
- "对比抖音和公众号中 AI 大模型话题的内容角度。"
- "把 Prompt 类内容按教程、案例和观点分组。"

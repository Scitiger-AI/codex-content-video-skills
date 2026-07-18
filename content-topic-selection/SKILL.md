---
name: content-topic-selection
description: Turn the current user's request into a source-routed, evidence-traceable video topic brief. Use when the user asks what video topic to make, asks for topic ideas or current-trend ideas, wants to decide whether to use public hot signals or the AI trend report, or needs to select an angle before script writing. Do not use for writing a completed script or rendering a video.
---

# Content Topic Selection

Make every decision from the current conversation. Do not load an account profile, persistent audience memory, historical content database, or publishing configuration.

## Route Sources

Extract the task into a `topic_request` with the user's stated domain, audience, platform, desired freshness, and source preference. Resolve `source_mode` in this order:

| Condition | `source_mode` |
|---|---|
| User says not to use trends, or supplies an exact topic without asking for freshness | `none` |
| User explicitly requests public hot topics | `public` |
| User explicitly requests the AI report | `ai_daily` |
| User explicitly requests both | `both` |
| User asks for current AI/model/agent/prompt/AI-product ideas | `both` |
| User asks for current non-AI ideas | `public` |
| Domain is ambiguous | `public` |

Record `source_mode`, `routing_reason`, and `user_override` in the output. Do not fetch `ai-trend-report` merely because the task contains a passing reference to AI. AI must be the topic's substantive subject, or the user must explicitly request that report.

For `public` or `both`, run `public-hot-signals`. For `ai_daily` or `both`, use the existing `ai-trend-report` skill. A source title, rank, or engagement metric is an attention signal, not a factual source.

## Select

1. If the user supplied a precise topic and `source_mode` is `none`, write one candidate from that topic.
2. Otherwise, normalize all fetched signals and produce three materially different candidates. Preserve every referenced signal ID.
3. Prefer a clear viewer question, a teachable core, an honest reason to make it now, and a feasible video form. Do not copy source titles.
4. If the user supplied previous content in this task, avoid the same core question, explanation route, examples, and hook. Do not infer a hidden content history.
5. Select a candidate only when the user requested autonomous selection. Otherwise, present the three candidates and wait for a choice.
6. Save `topic-brief.json` in the task's output directory and pass it to `self-media-script`.

Read [topic-brief.md](references/topic-brief.md) before writing the artifact.

---
name: self-media-script
description: Write original, evidence-bounded, production-ready narration scripts from a user-supplied topic or topic-brief.json. Use when the user asks for a self-media video script, voice-over manuscript, title and hook variants, fact-aware explanatory writing, or a script package for TTS and video production. Do not use to choose current trends or render video.
---

# Self-Media Script

Write from the current task only. Do not load an account profile, imitate a creator, or rely on an unprovided content history.

## Research Boundary

1. Read `topic-brief.json` when supplied. Treat public hot signals and AI-report items as attention evidence only.
2. For factual, current, regulatory, technical, health, financial, or legal claims, collect primary or authoritative sources before asserting them. Record the URL, publisher, date when available, and which claim the source supports.
3. If evidence is absent, reframe as an opinion, a question, or a clearly marked uncertainty. Never invent citations, dates, metrics, quotations, studies, or product behavior.
4. Preserve a user-supplied manuscript verbatim unless the user asks for a rewrite. You may add separately labeled title, description, tags, and production notes.
5. Treat hot-signal ranks, candidate lists, source-mode decisions, and selection rationale as production metadata. Do not put them in audience-facing narration or on-screen copy unless the user explicitly requests a trend, news, or media-analysis video.

## Write

Create `script-package.json` and `script.md` in the task output directory. Use the contract in [script-package.md](references/script-package.md).

- Lead with a viewer-relevant scene, tension, question, outcome, or contrast. Do not open by narrating how the topic was discovered or selected.
- Choose a narrative strategy that fits the topic. Use paths such as scenario-to-principle, contrast-to-resolution, claim-to-counterexample, event-to-implication, or question-to-decision framework when they help; they are options, never a required chapter sequence. Omit an element that does not earn its place.
- Record the chosen strategy, viewer question, and selection reason in `narrative_strategy`. Treat `chapters` as task-specific edit units, not a fixed list of named sections or a required count.
- Shape requested duration with the amount of narration at the normal TTS rate of `1.0`; do not assume slower speech unless the user explicitly asks for it.
- Write for narration, not an article. Keep sentences speakable and avoid displaying the narration verbatim as the main visual.
- Give every chapter a distinct `visual_beat` with a primary information visual and a secondary supporting visual. Explain processes with flows, comparisons with diagrams, and quantities with charts or counters. Only a brief hook or transition may use a text card as the primary visual; a long run of text cards is not a valid visual plan.
- Include claims requiring fact checks, uncertainty notes, and safety notes. A hot signal must never be the sole source for a substantive claim.

Run the validator before handing off:

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/self-media-script/scripts/validate_script_package.py" \
  --input outputs/<project>/script-package.json
```

Only after the requested script review or explicit full-production instruction, pass `script.md` to `tts-generate-audio` and use the same narration text as subtitle reference text.

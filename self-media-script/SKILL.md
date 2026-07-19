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
6. Never use vague authority as a substitute for evidence. Replace wording such as "学术界早就指出" with a specific, supported claim and named source, or remove it.

## Write

Create `script-package.json` and `script.md` in the task output directory. Use the contract in [script-package.md](references/script-package.md).

- Separate the editorial reason for choosing a topic from the viewer's reason to keep watching. The first two spoken sentences must still work when the viewer does not know the topic came from a hot list, report, or candidate-selection process. Do not open with phrases such as "今天热榜里", "这个选题来自", or a source rank unless the user explicitly requests trend, news, or media analysis.
- Lead with a viewer-relevant scene, tension, misconception, decision, outcome, or contrast. Make a concrete viewer promise before giving definitions or architecture names. For an explanatory topic, first create pressure on an intuitive but incomplete belief, then earn the explanation with an example, consequence, or test.
- Choose a narrative strategy that fits the topic. Use paths such as scenario-to-principle, contrast-to-resolution, claim-to-counterexample, event-to-implication, or question-to-decision framework when they help; they are options, never a required chapter sequence. Do not use a generic "definition -> mechanism -> caveat -> checklist" order unless that sequence is uniquely earned by the topic.
- Record the chosen strategy, viewer question, and selection reason in `narrative_strategy`. Treat `chapters` as task-specific edit units, not a fixed list of named sections or a required count.
- Give each chapter a distinct story move: change what the viewer believes, test the previous explanation, reveal a trade-off, or make a decision easier. Do not divide a single textbook explanation into headings and call it a narrative.
- Shape requested duration with the amount of narration at the normal TTS rate of `1.0`; do not assume slower speech unless the user explicitly asks for it.
- Write for narration, not an article. Keep sentences speakable and avoid displaying the narration verbatim as the main visual.
- Give every chapter a distinct `visual_beat` with a primary information visual and a secondary supporting visual. Explain processes with flows, comparisons with diagrams, and quantities with charts or counters. Only a brief hook or transition may use a text card as the primary visual; a long run of text cards is not a valid visual plan.
- Include claims requiring fact checks, uncertainty notes, and safety notes. A hot signal must never be the sole source for a substantive claim. A named company configuration, number, paper finding, or performance statement needs a corresponding primary or authoritative source URL in `claims`.
- Complete `editorial_review` in the script package before handoff. Use it to record the viewer promise and confirm that the hook does not leak discovery metadata or rely on vague attribution.

Run the validator before handing off:

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/self-media-script/scripts/validate_script_package.py" \
  --input outputs/<project>/script-package.json
python3 "${CODEX_HOME:-$HOME/.codex}/skills/self-media-script/scripts/audit_narration.py" \
  --input outputs/<project>/script-package.json --strict
```

Only after the requested script review or explicit full-production instruction, pass `script.md` to `tts-generate-audio` and use the same narration text as subtitle reference text.

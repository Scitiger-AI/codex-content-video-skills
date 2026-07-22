---
name: content-video-workflow
description: Orchestrate a task-scoped narrated video from a user-provided topic or script through topic selection, writing, TTS, subtitles, renderer choice, and local QC. Use when the user asks to make a complete self-media or explainer video, not just one pipeline stage. Reuse existing AI trend, TTS, subtitle, HyperFrames, and Remotion skills; do not use account profiles, publishing queues, or background agents.
---

# Content Video Workflow

Own the task handoffs, not the domain implementations. Work only from the current conversation and files supplied in the current task.

## Route

1. Create one task directory under `outputs/<project-slug>/` and write `request.json` with the user's topic, audience, length, format, style, source preference, renderer preference, and any stated delivery surface. Do not load or create an account profile. A delivery surface is task-local geometry, not a profile: use the user's stated platform, or `generic-short-video` for an unspecified vertical short video.
2. If the user needs a topic, invoke `content-topic-selection`. If a final topic is supplied and no freshness is requested, skip trend collection.
3. Invoke `self-media-script`, review its evidence and audience boundaries plus its topic-specific `narrative_strategy`. Validate `script-package.json`, then run the strict narration audit. Return to writing when the hook leaks hot-list or selection metadata, or when vague attribution has not been resolved.

   ```bash
   python3 "${CODEX_HOME:-$HOME/.codex}/skills/self-media-script/scripts/audit_narration.py" \
     --input outputs/<project>/script-package.json --strict
   ```
4. Before audio production, verify the caller has configured `SCITIGER_API_KEY` in `$CODEX_HOME/scitiger.env`; use `tts-generate-audio` with `script.md` at `tts_rate: 1.0` unless the user supplied another rate, then use `audio-generate-subtitle` with the generated audio and that same `script.md` as `reference_text`.
5. Build and validate a schema-version-2 `video-manifest.json`. Resolve its caption geometry into `caption-layout.json`; it is the only renderer handoff for safe-zone layout. Before every delivery render, run `check_delivery_guides.py` against the delivery source and that layout. It rejects a visible left-edge guide whose height matches `visual_content.bottom_y`; remove or rework any finding and rerender automatically. Keep debug-only guides in a separate debug or preview source tree.
6. Dispatch by explicit user choice: `remotion` -> `remotion-content-video`; `hyperframes` -> `hyperframes-content-video`. Default to HyperFrames only when the user did not choose a renderer. Treat a selected renderer as a delivery contract: a blocked renderer may be diagnosed and recovered according to its skill, but must not be silently substituted. Request an explicit renderer change only when its own recovery path cannot produce a local render.
7. Return the output video, QC report, source brief, and editable project directory. Never enqueue, publish, upload, or notify a third party.

The request to make a finished video authorizes autonomous production through renderer QC. Do not request preview approval for normal quality findings: repair layout, text, audio, or render defects and rerender. If the user asks only for ideas, a script, audio, subtitles, or a preview, stop at that requested stage.

## Handoffs

- Treat audio duration and SRT timestamps as the timing authority. Do not retype narration into a renderer.
- Plan the requested duration for `tts_rate: 1.0` by default. Add or remove evidence-backed narration beats instead of slowing speech to fill time.
- Keep public signals, AI reports, and topic-selection rationale as internal input unless the user specifically requests that provenance as audience-facing content.
- Use the resolved caption layout, not hard-coded screen coordinates. Keep captions above the platform UI exclusion and keep every non-caption element above `visual_content.bottom_y`. On a vertical video, reserve the generic short-video layout unless the current task specifies another delivery surface.
- Use `visual_beats` as the creative brief. A video must use diagrams, comparisons, data, objects, or scene changes when they explain the narration; it may not become a deck of transcript cards.
- Run the manifest validator before dispatch and preserve all source artifact paths.

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/content-video-workflow/scripts/validate_video_manifest.py" \
  --input outputs/<project>/video-manifest.json --check-paths
python3 "${CODEX_HOME:-$HOME/.codex}/skills/content-video-workflow/scripts/resolve_caption_layout.py" \
  --manifest outputs/<project>/video-manifest.json --out outputs/<project>/caption-layout.json
```

Read [video-manifest.md](references/video-manifest.md) before producing a renderer handoff.

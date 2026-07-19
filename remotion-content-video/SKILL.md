---
name: remotion-content-video
description: Build and render a task-scoped narrated content video in Remotion from a renderer-neutral video-manifest.json, existing audio, existing SRT subtitles, and visual beats. Use when the user explicitly chooses Remotion, provides an existing Remotion project, or needs a React-based renderer for a content video. Do not generate topics, scripts, TTS audio, or subtitles.
---

# Remotion Content Video

Use `video-manifest.json` as the source of truth. Read `remotion-best-practices`; also use `remotion-create`, `remotion-captions`, `remotion-markup`, `remotion-interactivity`, and `remotion-render` when installed.

## Build

1. Validate the manifest with `content-video-workflow`'s validator. Verify the audio and SRT exist before creating scenes.
2. Reuse an existing Remotion project when one is supplied. Otherwise scaffold a blank project inside `project_dir`; do not overwrite an existing user project.
3. Stage audio, SRT, and required local assets under `public/`. Keep source paths in the manifest unchanged.
4. Set dimensions, FPS, and duration from the manifest and probed narration duration. Audio owns duration; only add a minimal tail when needed.
5. Parse the supplied SRT using Remotion caption utilities. Render exactly one active segment at a time, preserve timestamps, and keep captions in the manifest's keepout band. Do not write a second independent caption transcript.
6. Implement the supplied `visual_beats` as an evolving visual explanation. Use frame-driven Remotion animation only; do not use CSS transitions or CSS keyframe animations. Do not make transcript cards the primary scene visual. When visible text needs a line break, use a JSX string expression such as `{"line one\nline two"}` with `whiteSpace: "pre-line"`, or separate text elements. Never write `\n`, `\t`, or `\r` directly in a bare JSX text node.
7. Before rendering, run the JSX text-escape check. Render at least one still from each visual beat and inspect it for raw escape characters, clipped text, caption overlap, and missing assets. Fix failures before proceeding.

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/remotion-content-video/scripts/check_jsx_text_escapes.py" \
  --src <project_dir>/src
```

8. Render an MP4 to `output.video_path`, then run the QC helper.

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/remotion-content-video/scripts/qc_video.py" \
  --video renders/final.mp4 --srt subtitles/subtitle.srt \
  --expected-width 1920 --expected-height 1080 --expected-fps 30 \
  --out renders/qc-report.json
```

Fix blocking QC failures before calling the video finished. Read [render-contract.md](references/render-contract.md) for output requirements.

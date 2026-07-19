---
name: hyperframes-content-video
description: Build and render a task-scoped narrated content video in HyperFrames from a renderer-neutral video-manifest.json, existing narration audio, existing SRT subtitles, and visual beats. Use when the user explicitly chooses HyperFrames, provides a HyperFrames project for a narrated content video, or needs an HTML-based renderer after script, TTS, and subtitles already exist. Do not select topics, write narration, synthesize TTS, generate subtitles, or publish a video.
---

# HyperFrames Content Video

Use `video-manifest.json` as the source of truth. This is the HyperFrames-specific renderer handoff from `content-video-workflow`; it does not reopen topic, script, or profile decisions.

Read `hyperframes`, `hyperframes-core`, `hyperframes-animation`, `hyperframes-creative`, and `hyperframes-cli` before authoring. Read the matching `hyperframes-cli` reference before running `init`, `check`, `preview`, or `render`.

## Build

1. Run the shared manifest validator, then the HyperFrames validator. Require `renderer: "hyperframes"`, existing audio and SRT files, and an FPS supported by HyperFrames. Resolve `caption-layout.json`; it defines the only permitted caption and visual-content boundaries. Do not silently alter the requested dimensions, FPS, or aspect ratio.

   ```bash
   python3 "${CODEX_HOME:-$HOME/.codex}/skills/content-video-workflow/scripts/validate_video_manifest.py" \
     --input outputs/<project>/video-manifest.json --check-paths
   python3 "${CODEX_HOME:-$HOME/.codex}/skills/hyperframes-content-video/scripts/validate_hyperframes_manifest.py" \
     --input outputs/<project>/video-manifest.json --check-paths
   python3 "${CODEX_HOME:-$HOME/.codex}/skills/content-video-workflow/scripts/resolve_caption_layout.py" \
     --manifest outputs/<project>/video-manifest.json --out outputs/<project>/caption-layout.json
   ```

2. Resolve `project_dir` relative to the manifest. Reuse a supplied HyperFrames project without overwriting unrelated work. Otherwise scaffold an empty project with `npx hyperframes init <project_dir> --non-interactive --example blank` and the matching standard resolution preset. For a non-preset size, author the exact manifest dimensions in the composition root after scaffolding.

3. Stage the supplied narration and subtitles into the project. This creates only `content-media/` and `content-inputs.json`; it never modifies the source media or the manifest.

   ```bash
   python3 "${CODEX_HOME:-$HOME/.codex}/skills/hyperframes-content-video/scripts/prepare_content_assets.py" \
     --manifest outputs/<project>/video-manifest.json --project-dir <project_dir> \
     --caption-layout outputs/<project>/caption-layout.json
   ```

4. Build one standalone `index.html` composition. Set its fixed width, height, FPS, and `data-duration` from the manifest and probed narration duration. Keep the staged `<audio>` as a direct child of the composition root for the full narration; HyperFrames owns its playback. Read the staged `caption_layout` from `content-inputs.json`; captions must stay in `caption_box` and all non-caption content must end above `visual_content.bottom_y`.

5. Parse the staged SRT or `subtitle-segments.json` at build time and render exactly one active caption segment at a time. Preserve timestamps and do not write a second independent transcript. Derive the caption box bottom, maximum height, and line limit from `caption_layout`; keep captions distinct from the primary visual. Do not continuously rotate readable text, and deliberately break or measure Chinese visible text so a phrase cannot wrap at an arbitrary character.

6. Implement every `visual_beat` as an evolving visual explanation. Use diagrams, comparisons, objects, charts, or processes where they clarify the narration. Do not make a sequence of transcript cards. Keep all media local, build a synchronous seekable timeline, and do not use render-time network requests, clocks, random state, CSS transitions, or infinite loops.

7. Run `npx hyperframes check <project_dir> --snapshots` and the shared delivery-guide check before rendering. It rejects a visible left-edge bar extending to `visual_content.bottom_y`, which indicates a leaked safe-zone guide. Inspect snapshots autonomously and render a still from every visual beat plus the longest subtitle segment with safe-zone overlays. Render those guides only in debug stills or preview mode; never include an overlay, ruler, boundary line, or safe-zone marker in the delivery composition. Remove or rework any guide finding, then rerun the checks and render; do not request preview approval.

   ```bash
   python3 "${CODEX_HOME:-$HOME/.codex}/skills/content-video-workflow/scripts/check_delivery_guides.py" \
     --src <project_dir> --caption-layout outputs/<project>/caption-layout.json
   ```

8. Render a local MP4 at the manifest FPS and run QC. Do not publish, upload, enqueue, use cloud rendering, or send telemetry as part of this workflow.

   ```bash
   npx hyperframes render <project_dir> --format mp4 --fps <manifest-fps> --quality high --output <video-path>
   python3 "${CODEX_HOME:-$HOME/.codex}/skills/hyperframes-content-video/scripts/qc_video.py" \
     --manifest outputs/<project>/video-manifest.json --video <video-path> \
     --caption-layout outputs/<project>/caption-layout.json --out <qc-report-path>
   ```

The final handoff contains the editable HyperFrames project, MP4, QC report, and the unchanged source artifacts. Resolve normal quality defects autonomously; only report unrecoverable environment or source-media errors. Read [render-contract.md](references/render-contract.md) before implementation or QC changes.

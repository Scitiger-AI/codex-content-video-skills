# HyperFrames Renderer Contract

The renderer consumes a valid `video-manifest.json` whose `renderer` is `hyperframes` and produces:

- an editable HyperFrames project at `project_dir`;
- one local MP4 at `output.video_path`;
- one JSON QC report at `output.qc_report_path`.

Preserve the manifest's requested width, height, FPS, aspect ratio, audio, SRT, caption policy, and visual beats. Resolve and stage the shared `caption-layout.json`; captions stay within `caption_box`, platform UI begins at `platform_ui_exclusion.top_y`, and every non-caption element ends above `visual_content.bottom_y`. HyperFrames supports output frame rates 24, 30, and 60 only. Do not silently substitute another frame rate; repair normal layout defects without requesting user approval.

Stage a project-local copy of narration plus subtitles under `content-media/`. The narration `<audio>` must be a direct child of the standalone composition root and span the narration. Embed or otherwise precompute the supplied SRT timing before render; do not fetch it at render time and do not author a second transcript.

The composition must have fixed manifest dimensions and a finite, seekable timeline. Derive root duration from audio duration, allowing only a minimal ending tail. Keep visible captions in the resolved caption box and make each visual beat an explanatory visual, not a transcript card. Inspect safe-zone overlay snapshots automatically and rerender after correcting ordinary text, caption, or layout defects.

QC records a non-passing result when the MP4 is missing, has no video stream, has no audio stream, has the wrong dimensions or FPS, truncates narration, has an excessive tail, has invalid/empty captions when captions are enabled, or lacks valid caption geometry. The report includes actual media metadata, source narration duration, subtitle count and longest segment, final subtitle end time, resolved caption layout, and `passed`. A normal non-passing result is an automatic repair signal, not a user approval gate.

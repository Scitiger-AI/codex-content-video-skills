# HyperFrames Renderer Contract

The renderer consumes a valid `video-manifest.json` whose `renderer` is `hyperframes` and produces:

- an editable HyperFrames project at `project_dir`;
- one local MP4 at `output.video_path`;
- one JSON QC report at `output.qc_report_path`.

Preserve the manifest's requested width, height, FPS, aspect ratio, audio, SRT, caption policy, and visual beats. HyperFrames supports output frame rates 24, 30, and 60 only. Do not silently substitute another frame rate; ask for a renderer or manifest change when needed.

Stage a project-local copy of narration plus subtitles under `content-media/`. The narration `<audio>` must be a direct child of the standalone composition root and span the narration. Embed or otherwise precompute the supplied SRT timing before render; do not fetch it at render time and do not author a second transcript.

The composition must have fixed manifest dimensions and a finite, seekable timeline. Derive root duration from audio duration, allowing only a minimal ending tail. Keep visible captions in the caption keepout and make each visual beat an explanatory visual, not a transcript card.

QC must fail when the MP4 is missing, has no video stream, has no audio stream, has the wrong dimensions or FPS, truncates narration, has an excessive tail, or has invalid/empty captions when captions are enabled. The report includes actual media metadata, source narration duration, subtitle count and longest segment, final subtitle end time, and `passed`.

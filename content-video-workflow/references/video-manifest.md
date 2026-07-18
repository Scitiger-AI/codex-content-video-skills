# Video Manifest Contract

`video-manifest.json` is renderer-neutral. Paths are relative to the task directory where possible.

```json
{
  "schema_version": 1,
  "renderer": "hyperframes",
  "project_dir": "",
  "source": {
    "topic_brief": "topic-brief.json",
    "script_package": "script-package.json",
    "script": "script.md"
  },
  "media": {
    "audio_path": "",
    "subtitle_srt_path": "",
    "subtitle_segments_path": null
  },
  "format": {"width": 1920, "height": 1080, "fps": 30, "aspect_ratio": "16:9", "language": "zh-CN"},
  "caption_policy": {"enabled": true, "keepout": "bottom 18% reserved for captions", "max_lines": 2},
  "visual_beats": [],
  "output": {"video_path": "renders/final.mp4", "qc_report_path": "renders/qc-report.json"}
}
```

Use renderer values `hyperframes` or `remotion`. `project_dir`, `media.audio_path`, `media.subtitle_srt_path`, `format`, and `visual_beats` are required. Preserve a user-selected width, height, fps, and aspect ratio; do not use profile defaults.

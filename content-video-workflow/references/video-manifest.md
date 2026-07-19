# Video Manifest Contract

`video-manifest.json` is renderer-neutral. Paths are relative to the task directory where possible.

```json
{
  "schema_version": 2,
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
  "caption_policy": {
    "enabled": true,
    "max_lines": 2,
    "delivery_surface": "generic-short-video",
    "platform_ui_bottom_ratio": 0.18,
    "caption_bottom_ratio": 0.22,
    "caption_max_height_ratio": 0.10,
    "visual_clearance_ratio": 0.02
  },
  "visual_beats": [],
  "output": {"video_path": "renders/final.mp4", "qc_report_path": "renders/qc-report.json"}
}
```

Use renderer values `hyperframes` or `remotion`. `project_dir`, `media.audio_path`, `media.subtitle_srt_path`, `format`, and `visual_beats` are required. Preserve a user-selected width, height, fps, and aspect ratio; do not use profile defaults.

`caption_policy` separates platform controls from captions. `platform_ui_bottom_ratio` is an exclusion where captions cannot appear. `caption_bottom_ratio` anchors the bottom edge of the caption box above that exclusion. `caption_max_height_ratio` reserves room for the maximum allowed caption lines, and `visual_clearance_ratio` separates the caption box from every non-caption element. Ratios use frame height.

For a vertical task without a stated platform, write `delivery_surface: "generic-short-video"`; its conservative defaults are the values above. Use `clean-player` only when the current task explicitly targets a player without short-video UI. Run `resolve_caption_layout.py` and use its `visual_content.bottom_y` as a hard layout boundary. Schema version 1 manifests remain readable and receive a derived layout, but new tasks must write version 2.

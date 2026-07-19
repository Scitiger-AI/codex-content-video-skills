# Remotion Renderer Contract

The renderer consumes a valid `video-manifest.json` and produces:

- a Remotion source project under `project_dir`;
- one MP4 at `output.video_path`;
- one JSON QC report at `output.qc_report_path`;
- sampled frames or a contact sheet when the task requests visual QA.

Use a named composition. Mount the audio once for the full timeline. Derive visible subtitle timing from the supplied SRT; never hard-code a second transcript. Resolve the shared `caption-layout.json` before authoring: captions live within `caption_box`, platform UI starts at `platform_ui_exclusion.top_y`, and every non-caption element ends above `visual_content.bottom_y`. Do not hard-code a vertical caption offset.

Before rendering, run `scripts/check_jsx_text_escapes.py --src <project_dir>/src`. It rejects `\n`, `\t`, and `\r` written as bare JSX text, which browsers render literally. For intentional multiline visible text, use a JSX string expression with `whiteSpace: "pre-line"` or separate text elements. Inspect a rendered still from every visual beat and the longest subtitle segment with safe-zone overlays; a passed TypeScript lint or media QC report does not prove that visible text is correct. Correct normal layout defects autonomously and rerender.

The QC report must include duration, width, height, frame rate, SRT segment count, longest subtitle segment, the resolved caption layout, and `passed`. A missing video, no video stream, invalid dimensions, invalid frame rate, invalid caption geometry, or zero subtitle segments when captions are enabled is a failure. A normal quality failure triggers autonomous correction rather than user approval.

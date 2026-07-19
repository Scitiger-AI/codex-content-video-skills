#!/usr/bin/env python3

import argparse
import json
from pathlib import Path
import sys

from resolve_caption_layout import CaptionLayoutError, resolve_caption_layout


def main():
    parser = argparse.ArgumentParser(description="Validate a renderer-neutral video manifest.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--check-paths", action="store_true")
    args = parser.parse_args()
    manifest_path = Path(args.input).resolve()
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as error:
        print(json.dumps({"passed": False, "errors": [str(error)]}, ensure_ascii=False, indent=2))
        return 1

    errors = []
    if manifest.get("schema_version") not in {1, 2}:
        errors.append("schema_version must be 1 or 2")
    if manifest.get("renderer") not in {"hyperframes", "remotion"}:
        errors.append("renderer must be hyperframes or remotion")
    if not isinstance(manifest.get("project_dir"), str) or not manifest["project_dir"].strip():
        errors.append("project_dir is required")
    media = manifest.get("media") if isinstance(manifest.get("media"), dict) else {}
    for field in ("audio_path", "subtitle_srt_path"):
        if not isinstance(media.get(field), str) or not media[field].strip():
            errors.append(f"media.{field} is required")
    fmt = manifest.get("format") if isinstance(manifest.get("format"), dict) else {}
    for field in ("width", "height", "fps", "aspect_ratio"):
        if not fmt.get(field):
            errors.append(f"format.{field} is required")
    for field in ("width", "height"):
        if not isinstance(fmt.get(field), int) or fmt[field] <= 0:
            errors.append(f"format.{field} must be a positive integer")
    if not isinstance(fmt.get("fps"), (int, float)) or isinstance(fmt.get("fps"), bool) or fmt["fps"] <= 0:
        errors.append("format.fps must be a positive number")
    if not isinstance(manifest.get("visual_beats"), list) or not manifest["visual_beats"]:
        errors.append("visual_beats must be a non-empty array")

    caption_layout = None
    warnings = []
    try:
        caption_layout, warnings = resolve_caption_layout(manifest)
    except CaptionLayoutError as error:
        errors.append(str(error))

    if args.check_paths:
        base = manifest_path.parent
        for label, raw_path in {"audio": media.get("audio_path"), "srt": media.get("subtitle_srt_path")}.items():
            if raw_path and not (base / raw_path).resolve().exists() and not Path(raw_path).is_absolute():
                errors.append(f"missing {label} file: {raw_path}")
            elif raw_path and Path(raw_path).is_absolute() and not Path(raw_path).exists():
                errors.append(f"missing {label} file: {raw_path}")

    print(json.dumps({"passed": not errors, "errors": errors, "warnings": warnings, "renderer": manifest.get("renderer"), "beat_count": len(manifest.get("visual_beats", [])), "caption_layout": caption_layout}, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())

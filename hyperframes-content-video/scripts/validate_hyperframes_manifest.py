#!/usr/bin/env python3
"""Validate renderer-specific constraints for a HyperFrames content manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


SUPPORTED_FPS = {24, 30, 60}


def resolve_path(manifest_path: Path, value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else (manifest_path.parent / path).resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate HyperFrames-specific video manifest constraints.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--check-paths", action="store_true")
    args = parser.parse_args()

    manifest_path = Path(args.input).expanduser().resolve()
    try:
        manifest: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as error:
        print(json.dumps({"passed": False, "errors": [str(error)]}, ensure_ascii=False, indent=2))
        return 1

    errors: list[str] = []
    if manifest.get("renderer") != "hyperframes":
        errors.append("renderer must be hyperframes")
    fmt = manifest.get("format") if isinstance(manifest.get("format"), dict) else {}
    width, height, fps = fmt.get("width"), fmt.get("height"), fmt.get("fps")
    if not isinstance(width, int) or width <= 0:
        errors.append("format.width must be a positive integer")
    if not isinstance(height, int) or height <= 0:
        errors.append("format.height must be a positive integer")
    if fps not in SUPPORTED_FPS:
        errors.append("format.fps must be one of 24, 30, or 60 for HyperFrames")
    if not isinstance(manifest.get("project_dir"), str) or not manifest["project_dir"].strip():
        errors.append("project_dir is required")

    output = manifest.get("output") if isinstance(manifest.get("output"), dict) else {}
    for field in ("video_path", "qc_report_path"):
        if not isinstance(output.get(field), str) or not output[field].strip():
            errors.append(f"output.{field} is required")

    media = manifest.get("media") if isinstance(manifest.get("media"), dict) else {}
    if args.check_paths:
        for label, field in (("audio", "audio_path"), ("SRT", "subtitle_srt_path")):
            value = media.get(field)
            if not isinstance(value, str) or not value.strip():
                continue
            if not resolve_path(manifest_path, value).is_file():
                errors.append(f"missing {label} file: {value}")

    result = {
        "passed": not errors,
        "renderer": manifest.get("renderer"),
        "format": {"width": width, "height": height, "fps": fps},
        "errors": errors,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

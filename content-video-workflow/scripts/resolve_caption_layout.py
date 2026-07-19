#!/usr/bin/env python3
"""Resolve caption and platform-safe geometry from a video manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


PRESETS = {
    "generic-short-video": {
        "platform_ui_bottom_ratio": 0.18,
        "caption_bottom_ratio": 0.22,
        "caption_max_height_ratio": 0.10,
        "visual_clearance_ratio": 0.02,
    },
    "clean-player": {
        "platform_ui_bottom_ratio": 0.04,
        "caption_bottom_ratio": 0.10,
        "caption_max_height_ratio": 0.12,
        "visual_clearance_ratio": 0.02,
    },
}


class CaptionLayoutError(ValueError):
    pass


def is_vertical(width: int, height: int) -> bool:
    return height > width


def number(policy: dict[str, Any], key: str, fallback: float) -> float:
    value = policy.get(key, fallback)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise CaptionLayoutError(f"caption_policy.{key} must be a number")
    return float(value)


def resolve_caption_layout(manifest: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    fmt = manifest.get("format") if isinstance(manifest.get("format"), dict) else {}
    width, height = fmt.get("width"), fmt.get("height")
    if not isinstance(width, int) or width <= 0 or not isinstance(height, int) or height <= 0:
        raise CaptionLayoutError("format.width and format.height must be positive integers")

    policy = manifest.get("caption_policy") if isinstance(manifest.get("caption_policy"), dict) else {}
    if manifest.get("schema_version") == 2:
        required = {
            "enabled",
            "max_lines",
            "delivery_surface",
            "platform_ui_bottom_ratio",
            "caption_bottom_ratio",
            "caption_max_height_ratio",
            "visual_clearance_ratio",
        }
        missing = sorted(required - policy.keys())
        if missing:
            raise CaptionLayoutError(f"schema_version 2 caption_policy is missing: {', '.join(missing)}")
    captions_enabled = bool(policy.get("enabled", True))
    default_surface = "generic-short-video" if is_vertical(width, height) else "clean-player"
    delivery_surface = policy.get("delivery_surface", default_surface)
    if not isinstance(delivery_surface, str) or delivery_surface not in PRESETS:
        raise CaptionLayoutError("caption_policy.delivery_surface must be generic-short-video or clean-player")

    preset = PRESETS[delivery_surface]
    platform_ui_bottom_ratio = number(policy, "platform_ui_bottom_ratio", preset["platform_ui_bottom_ratio"])
    caption_bottom_ratio = number(policy, "caption_bottom_ratio", preset["caption_bottom_ratio"])
    caption_max_height_ratio = number(policy, "caption_max_height_ratio", preset["caption_max_height_ratio"])
    visual_clearance_ratio = number(policy, "visual_clearance_ratio", preset["visual_clearance_ratio"])
    max_lines = policy.get("max_lines", 2)
    if not isinstance(max_lines, int) or max_lines < 1 or max_lines > 3:
        raise CaptionLayoutError("caption_policy.max_lines must be an integer from 1 to 3")

    for key, value in {
        "platform_ui_bottom_ratio": platform_ui_bottom_ratio,
        "caption_bottom_ratio": caption_bottom_ratio,
        "caption_max_height_ratio": caption_max_height_ratio,
        "visual_clearance_ratio": visual_clearance_ratio,
    }.items():
        if not 0 <= value < 1:
            raise CaptionLayoutError(f"caption_policy.{key} must be between 0 and 1")
    if captions_enabled and caption_bottom_ratio <= platform_ui_bottom_ratio:
        raise CaptionLayoutError("caption_policy.caption_bottom_ratio must be greater than platform_ui_bottom_ratio")
    if captions_enabled and caption_bottom_ratio + caption_max_height_ratio + visual_clearance_ratio >= 1:
        raise CaptionLayoutError("caption policy leaves no usable visual area")

    platform_ui_bottom_px = round(height * platform_ui_bottom_ratio)
    caption_bottom_px = round(height * caption_bottom_ratio) if captions_enabled else platform_ui_bottom_px
    caption_max_height_px = round(height * caption_max_height_ratio) if captions_enabled else 0
    visual_clearance_px = round(height * visual_clearance_ratio) if captions_enabled else 0
    caption_bottom_y = height - caption_bottom_px
    caption_top_y = caption_bottom_y - caption_max_height_px
    visual_content_bottom_y = caption_top_y - visual_clearance_px if captions_enabled else height - platform_ui_bottom_px
    warnings: list[str] = []
    if manifest.get("schema_version") == 1:
        warnings.append("schema_version 1 uses a derived caption layout; write schema_version 2 for new tasks")

    return {
        "delivery_surface": delivery_surface,
        "captions_enabled": captions_enabled,
        "canvas": {"width": width, "height": height},
        "platform_ui_exclusion": {
            "bottom_ratio": platform_ui_bottom_ratio,
            "bottom_px": platform_ui_bottom_px,
            "top_y": height - platform_ui_bottom_px,
        },
        "caption_box": {
            "bottom_ratio": caption_bottom_ratio if captions_enabled else None,
            "bottom_px": caption_bottom_px,
            "max_height_ratio": caption_max_height_ratio if captions_enabled else None,
            "max_height_px": caption_max_height_px,
            "top_y": caption_top_y,
            "bottom_y": caption_bottom_y,
            "max_lines": max_lines,
        },
        "visual_content": {
            "clearance_ratio": visual_clearance_ratio if captions_enabled else 0,
            "clearance_px": visual_clearance_px,
            "bottom_y": visual_content_bottom_y,
        },
    }, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve platform-safe caption geometry from a video manifest.")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--out", help="Optional JSON output path.")
    args = parser.parse_args()

    try:
        manifest_path = Path(args.manifest).expanduser().resolve()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        layout, warnings = resolve_caption_layout(manifest)
        result = {"passed": True, "manifest": str(manifest_path), "layout": layout, "warnings": warnings}
    except Exception as error:
        result = {"passed": False, "error": str(error)}

    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        output = Path(args.out).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

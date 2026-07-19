#!/usr/bin/env python3

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys


def probe(video):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height,r_frame_rate:format=duration", "-of", "json", str(video)],
        check=True, capture_output=True, text=True,
    )
    value = json.loads(result.stdout)
    stream = next((item for item in value.get("streams", []) if item.get("codec_type") == "video"), None)
    if not stream:
        raise ValueError("no video stream")
    rate = stream.get("r_frame_rate", "0/1")
    numerator, denominator = rate.split("/", 1)
    fps = float(numerator) / float(denominator) if float(denominator) else 0
    return {"width": stream.get("width"), "height": stream.get("height"), "fps": fps, "duration_seconds": float(value.get("format", {}).get("duration") or 0)}


def subtitle_stats(path):
    raw = path.read_text(encoding="utf-8-sig")
    blocks = [block for block in re.split(r"\r?\n\s*\r?\n", raw.strip()) if block.strip()]
    captions = []
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if len(lines) >= 3 and "-->" in lines[1]:
            captions.append(" ".join(lines[2:]))
    return {"segment_count": len(captions), "max_characters": max((len(item) for item in captions), default=0)}


def caption_layout(path, width, height):
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("passed") is not True or not isinstance(payload.get("layout"), dict):
        raise ValueError("caption layout is invalid")
    layout = payload["layout"]
    if layout.get("canvas") != {"width": width, "height": height}:
        raise ValueError("caption layout dimensions do not match the video")
    if not layout.get("captions_enabled"):
        return layout
    platform = layout.get("platform_ui_exclusion") or {}
    caption = layout.get("caption_box") or {}
    visual = layout.get("visual_content") or {}
    platform_top = platform.get("top_y")
    caption_top, caption_bottom = caption.get("top_y"), caption.get("bottom_y")
    visual_bottom = visual.get("bottom_y")
    if not all(isinstance(value, int) for value in (platform_top, caption_top, caption_bottom, visual_bottom)):
        raise ValueError("caption layout has non-integer geometry")
    if not 0 <= visual_bottom <= caption_top < caption_bottom <= platform_top <= height:
        raise ValueError("caption layout safe zones are inconsistent")
    return layout


def main():
    parser = argparse.ArgumentParser(description="Run basic rendered-video QC for a Remotion content video.")
    parser.add_argument("--video", required=True)
    parser.add_argument("--srt", required=True)
    parser.add_argument("--expected-width", type=int, required=True)
    parser.add_argument("--expected-height", type=int, required=True)
    parser.add_argument("--expected-fps", type=float, required=True)
    parser.add_argument("--caption-layout", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    errors = []
    video = Path(args.video)
    srt = Path(args.srt)
    metadata = {}
    subtitles = {"segment_count": 0, "max_characters": 0}
    layout = None
    if not video.exists() or video.stat().st_size <= 1024:
        errors.append("video is missing or too small")
    else:
        try:
            metadata = probe(video)
            if metadata["width"] != args.expected_width or metadata["height"] != args.expected_height:
                errors.append("video dimensions do not match the manifest")
            if abs(metadata["fps"] - args.expected_fps) > 0.1:
                errors.append("video FPS does not match the manifest")
            if metadata["duration_seconds"] <= 0:
                errors.append("video duration is invalid")
        except Exception as error:
            errors.append(f"ffprobe failed: {error}")
    if not srt.exists():
        errors.append("SRT file is missing")
    else:
        subtitles = subtitle_stats(srt)
        if subtitles["segment_count"] == 0:
            errors.append("SRT has no subtitle segments")
    try:
        layout = caption_layout(Path(args.caption_layout), args.expected_width, args.expected_height)
    except Exception as error:
        errors.append(f"caption layout failed: {error}")

    report = {"passed": not errors, "video": str(video), "srt": str(srt), "metadata": metadata, "subtitles": subtitles, "caption_layout": layout, "errors": errors}
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())

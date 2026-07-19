#!/usr/bin/env python3
"""Run delivery checks for a HyperFrames narrated content video."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any


TIME_RANGE = re.compile(r"^(\d{2}):(\d{2}):(\d{2}),(\d{3})\s+-->\s+(\d{2}):(\d{2}):(\d{2}),(\d{3})$")


def resolve_path(manifest_path: Path, value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else (manifest_path.parent / path).resolve()


def probe(path: Path) -> dict[str, Any]:
    command = [
        "ffprobe", "-v", "error", "-show_entries",
        "stream=codec_type,codec_name,width,height,r_frame_rate,sample_rate,channels:format=duration,size",
        "-of", "json", str(path),
    ]
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    payload = json.loads(completed.stdout)
    streams = payload.get("streams", [])
    video = next((item for item in streams if item.get("codec_type") == "video"), None)
    audio = next((item for item in streams if item.get("codec_type") == "audio"), None)
    if video:
        rate = video.get("r_frame_rate", "0/1")
        numerator, denominator = rate.split("/", 1)
        fps = float(numerator) / float(denominator) if float(denominator) else 0
        video = {"codec": video.get("codec_name"), "width": video.get("width"), "height": video.get("height"), "fps": fps}
    if audio:
        audio = {"codec": audio.get("codec_name"), "sample_rate": audio.get("sample_rate"), "channels": audio.get("channels")}
    return {
        "duration_seconds": float(payload.get("format", {}).get("duration") or 0),
        "size_bytes": int(payload.get("format", {}).get("size") or 0),
        "video": video,
        "audio": audio,
    }


def timestamp_to_ms(parts: tuple[str, ...]) -> int:
    hours, minutes, seconds, millis = (int(value) for value in parts)
    return ((hours * 60 + minutes) * 60 + seconds) * 1000 + millis


def subtitle_stats(path: Path) -> dict[str, int]:
    raw = path.read_text(encoding="utf-8-sig")
    blocks = [block for block in re.split(r"\r?\n\s*\r?\n", raw.strip()) if block.strip()]
    captions: list[tuple[int, int, str]] = []
    for index, block in enumerate(blocks, 1):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if len(lines) < 3:
            raise ValueError(f"invalid SRT block {index}")
        timing = TIME_RANGE.match(lines[1])
        if not timing:
            raise ValueError(f"invalid SRT timing in block {index}")
        groups = timing.groups()
        start_ms = timestamp_to_ms(groups[:4])
        end_ms = timestamp_to_ms(groups[4:])
        if end_ms <= start_ms:
            raise ValueError(f"non-positive SRT duration in block {index}")
        if captions and start_ms < captions[-1][1]:
            raise ValueError(f"overlapping SRT block {index}")
        captions.append((start_ms, end_ms, " ".join(lines[2:])))
    return {
        "segment_count": len(captions),
        "max_characters": max((len(text) for _, _, text in captions), default=0),
        "last_end_ms": captions[-1][1] if captions else 0,
    }


def caption_layout(path: Path, width: int, height: int) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("passed") is not True or not isinstance(payload.get("layout"), dict):
        raise ValueError("caption layout is invalid")
    layout = payload["layout"]
    if layout.get("canvas") != {"width": width, "height": height}:
        raise ValueError("caption layout dimensions do not match the manifest")
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Run rendered-video QC for a HyperFrames content video.")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--video", required=True)
    parser.add_argument("--caption-layout", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--duration-tolerance-seconds", type=float, default=0.1)
    parser.add_argument("--max-tail-seconds", type=float, default=0.75)
    args = parser.parse_args()

    errors: list[str] = []
    manifest_path = Path(args.manifest).expanduser().resolve()
    video_path = Path(args.video).expanduser().resolve()
    report: dict[str, Any] = {"passed": False, "manifest": str(manifest_path), "video": str(video_path), "errors": errors}
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        media = manifest.get("media") if isinstance(manifest.get("media"), dict) else {}
        fmt = manifest.get("format") if isinstance(manifest.get("format"), dict) else {}
        captions_enabled = bool((manifest.get("caption_policy") or {}).get("enabled", True))
        layout = caption_layout(Path(args.caption_layout).expanduser().resolve(), int(fmt.get("width") or 0), int(fmt.get("height") or 0))
        report["caption_layout"] = layout
        audio_path = resolve_path(manifest_path, str(media.get("audio_path") or ""))
        srt_path = resolve_path(manifest_path, str(media.get("subtitle_srt_path") or ""))
        report["audio"] = str(audio_path)
        report["srt"] = str(srt_path)
        report["captions_enabled"] = captions_enabled
        if manifest.get("renderer") != "hyperframes":
            errors.append("manifest renderer is not hyperframes")
        if args.duration_tolerance_seconds < 0 or args.max_tail_seconds < 0:
            errors.append("duration tolerances must be non-negative")

        source_audio = probe(audio_path) if audio_path.is_file() else None
        if not source_audio or not source_audio.get("audio"):
            errors.append("source narration audio is missing or has no audio stream")
        report["source_audio"] = source_audio

        rendered = probe(video_path) if video_path.is_file() and video_path.stat().st_size > 1024 else None
        if not rendered:
            errors.append("video is missing or too small")
        else:
            video_stream = rendered.get("video")
            if not video_stream:
                errors.append("rendered file has no video stream")
            else:
                if video_stream.get("width") != fmt.get("width") or video_stream.get("height") != fmt.get("height"):
                    errors.append("video dimensions do not match the manifest")
                if abs(float(video_stream.get("fps") or 0) - float(fmt.get("fps") or 0)) > 0.1:
                    errors.append("video FPS does not match the manifest")
            if not rendered.get("audio"):
                errors.append("rendered file has no narration audio stream")
            if rendered.get("duration_seconds", 0) <= 0:
                errors.append("video duration is invalid")
        report["rendered_video"] = rendered

        subtitles = {"segment_count": 0, "max_characters": 0, "last_end_ms": 0}
        if captions_enabled:
            if not srt_path.is_file():
                errors.append("SRT file is missing")
            else:
                try:
                    subtitles = subtitle_stats(srt_path)
                    if subtitles["segment_count"] == 0:
                        errors.append("SRT has no subtitle segments")
                except Exception as error:
                    errors.append(f"SRT parsing failed: {error}")
        report["subtitles"] = subtitles

        if source_audio and rendered:
            source_duration = float(source_audio.get("duration_seconds") or 0)
            rendered_duration = float(rendered.get("duration_seconds") or 0)
            if rendered_duration + args.duration_tolerance_seconds < source_duration:
                errors.append("video ends before the narration audio")
            if rendered_duration > source_duration + args.max_tail_seconds:
                errors.append("video tail exceeds the allowed duration")
            if subtitles["last_end_ms"] > round((source_duration + args.duration_tolerance_seconds) * 1000):
                errors.append("SRT extends beyond narration audio")
        report["duration_tolerance_seconds"] = args.duration_tolerance_seconds
        report["max_tail_seconds"] = args.max_tail_seconds
    except Exception as error:
        errors.append(f"QC setup failed: {error}")

    report["passed"] = not errors
    output = Path(args.out).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

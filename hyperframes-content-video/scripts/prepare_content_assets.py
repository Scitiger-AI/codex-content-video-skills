#!/usr/bin/env python3
"""Stage narration and timed subtitles for a HyperFrames content project."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil
import sys
from typing import Any


TIME_RANGE = re.compile(r"^(\d{2}):(\d{2}):(\d{2}),(\d{3})\s+-->\s+(\d{2}):(\d{2}):(\d{2}),(\d{3})$")


class PreparationError(RuntimeError):
    pass


def resolve_path(manifest_path: Path, value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else (manifest_path.parent / path).resolve()


def timestamp_to_ms(parts: tuple[str, ...]) -> int:
    hours, minutes, seconds, millis = (int(value) for value in parts)
    return ((hours * 60 + minutes) * 60 + seconds) * 1000 + millis


def parse_srt(path: Path) -> list[dict[str, Any]]:
    raw = path.read_text(encoding="utf-8-sig")
    blocks = [block for block in re.split(r"\r?\n\s*\r?\n", raw.strip()) if block.strip()]
    segments: list[dict[str, Any]] = []
    previous_end = -1
    for expected_index, block in enumerate(blocks, 1):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if len(lines) < 3:
            raise PreparationError(f"invalid SRT block {expected_index}")
        timing = TIME_RANGE.match(lines[1])
        if not timing:
            raise PreparationError(f"invalid SRT timing in block {expected_index}")
        groups = timing.groups()
        start_ms = timestamp_to_ms(groups[:4])
        end_ms = timestamp_to_ms(groups[4:])
        if end_ms <= start_ms:
            raise PreparationError(f"non-positive SRT duration in block {expected_index}")
        if start_ms < previous_end:
            raise PreparationError(f"overlapping SRT block {expected_index}")
        text = " ".join(lines[2:]).strip()
        if not text:
            raise PreparationError(f"empty SRT text in block {expected_index}")
        segments.append({"index": expected_index, "start_time": start_ms, "end_time": end_ms, "text": text})
        previous_end = end_ms
    if not segments:
        raise PreparationError("SRT has no timed segments")
    return segments


def copy_asset(source: Path, target: Path, overwrite: bool) -> None:
    if target.exists() and not overwrite:
        if target.read_bytes() == source.read_bytes():
            return
        raise PreparationError(f"refusing to overwrite existing staged asset: {target}")
    shutil.copyfile(source, target)


def main() -> int:
    parser = argparse.ArgumentParser(description="Stage audio and SRT assets for a HyperFrames content project.")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--project-dir", required=True)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    try:
        manifest_path = Path(args.manifest).expanduser().resolve()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("renderer") != "hyperframes":
            raise PreparationError("manifest renderer must be hyperframes")
        media = manifest.get("media") if isinstance(manifest.get("media"), dict) else {}
        audio_value = media.get("audio_path")
        srt_value = media.get("subtitle_srt_path")
        if not isinstance(audio_value, str) or not isinstance(srt_value, str):
            raise PreparationError("manifest must include media.audio_path and media.subtitle_srt_path")
        audio_source = resolve_path(manifest_path, audio_value)
        srt_source = resolve_path(manifest_path, srt_value)
        if not audio_source.is_file() or not srt_source.is_file():
            raise PreparationError("manifest media files must exist")

        project_dir = Path(args.project_dir).expanduser().resolve()
        if not project_dir.is_dir():
            raise PreparationError(f"HyperFrames project directory does not exist: {project_dir}")
        media_dir = project_dir / "content-media"
        media_dir.mkdir(exist_ok=True)
        audio_target = media_dir / f"narration{audio_source.suffix.lower()}"
        srt_target = media_dir / "subtitles.srt"
        segments_target = media_dir / "subtitle-segments.json"
        copy_asset(audio_source, audio_target, args.overwrite)
        copy_asset(srt_source, srt_target, args.overwrite)
        segments = parse_srt(srt_source)
        if segments_target.exists() and not args.overwrite:
            existing = segments_target.read_text(encoding="utf-8")
            desired = json.dumps(segments, ensure_ascii=False, indent=2) + "\n"
            if existing != desired:
                raise PreparationError(f"refusing to overwrite existing staged subtitle data: {segments_target}")
        else:
            segments_target.write_text(json.dumps(segments, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        inputs = {
            "schema_version": 1,
            "audio_src": audio_target.relative_to(project_dir).as_posix(),
            "subtitle_srt_path": srt_target.relative_to(project_dir).as_posix(),
            "subtitle_segments_path": segments_target.relative_to(project_dir).as_posix(),
            "subtitle_segment_count": len(segments),
            "format": manifest.get("format"),
            "caption_policy": manifest.get("caption_policy"),
        }
        inputs_path = project_dir / "content-inputs.json"
        desired_inputs = json.dumps(inputs, ensure_ascii=False, indent=2) + "\n"
        if inputs_path.exists() and not args.overwrite and inputs_path.read_text(encoding="utf-8") != desired_inputs:
            raise PreparationError(f"refusing to overwrite existing content inputs: {inputs_path}")
        inputs_path.write_text(desired_inputs, encoding="utf-8")
        print(json.dumps({"ok": True, "audio_src": inputs["audio_src"], "subtitle_segments": len(segments), "inputs_path": str(inputs_path)}, ensure_ascii=False, indent=2))
        return 0
    except Exception as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

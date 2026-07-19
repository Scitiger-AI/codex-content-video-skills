#!/usr/bin/env python3
"""Reject visible safe-zone guide bars from a delivery video source tree."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
from typing import Iterable


SOURCE_SUFFIXES = {".css", ".htm", ".html", ".js", ".jsx", ".less", ".sass", ".scss", ".ts", ".tsx"}
IGNORED_DIRECTORIES = {
    ".git",
    ".next",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "renders",
    "render",
    "snapshots",
    "snapshot",
}
DEBUG_DIRECTORY_MARKERS = {"debug", "preview", "qa"}
STYLE_OBJECT_START = re.compile(r"\bstyle\s*=\s*\{\s*\{")
HTML_STYLE_START = re.compile(r"\bstyle\s*=\s*([\"'])")
CSS_RULE = re.compile(r"[^{}]+\{([^{}]*)\}", re.DOTALL)
DECLARATION = re.compile(
    r"(?:^|[,;\n])\s*[\"']?([A-Za-z][A-Za-z0-9_-]*)[\"']?\s*:\s*([^,;\n}]+)",
    re.MULTILINE,
)
NUMBER_LITERAL = re.compile(r"^[\"']?(-?\d+(?:\.\d+)?)(?:px)?[\"']?$")
ZERO_LITERAL = re.compile(r"^[\"']?0(?:px)?[\"']?$")
TRANSPARENT_PAINT = re.compile(r"^rgba\([^)]*,\s*0(?:\.0+)?\s*\)$")
VISUAL_BOTTOM_ALIAS = re.compile(
    r"\b(?:const|let|var)\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*=\s*[^;\n]*"
    r"visual_content\s*\.\s*bottom_y\b",
    re.IGNORECASE,
)


def source_files(paths: Iterable[str]) -> list[Path]:
    """Return delivery-source files while excluding dependencies and debug-only trees."""
    files: list[Path] = []
    for raw_path in paths:
        path = Path(raw_path).expanduser()
        if path.is_file() and path.suffix.lower() in SOURCE_SUFFIXES:
            files.append(path.resolve())
            continue
        if not path.is_dir():
            continue
        for current_root, directories, filenames in os.walk(path):
            directories[:] = [
                directory
                for directory in directories
                if directory.lower() not in IGNORED_DIRECTORIES | DEBUG_DIRECTORY_MARKERS
            ]
            current = Path(current_root)
            files.extend(
                (current / filename).resolve()
                for filename in filenames
                if (current / filename).suffix.lower() in SOURCE_SUFFIXES
            )
    return sorted(set(files))


def line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def balanced_style_objects(text: str) -> Iterable[tuple[int, str]]:
    """Yield inline JSX style objects, preserving nested string/template content."""
    for match in STYLE_OBJECT_START.finditer(text):
        start = text.find("{", match.start())
        if start < 0:
            continue
        depth = 0
        quote: str | None = None
        escaped = False
        for index in range(start, len(text)):
            char = text[index]
            if quote:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == quote:
                    quote = None
                continue
            if char in {"\"", "'", "`"}:
                quote = char
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    yield start, text[start + 2:index - 1]
                    break


def html_style_blocks(text: str) -> Iterable[tuple[int, str]]:
    for match in HTML_STYLE_START.finditer(text):
        quote = match.group(1)
        start = match.end()
        end = text.find(quote, start)
        if end >= 0:
            yield start, text[start:end]


def css_style_blocks(text: str) -> Iterable[tuple[int, str]]:
    for match in CSS_RULE.finditer(text):
        yield match.start(1), match.group(1)


def declarations(block: str) -> dict[str, str]:
    return {key.lower().replace("-", ""): value.strip() for key, value in DECLARATION.findall(block)}


def is_zero(value: str | None) -> bool:
    return value is not None and bool(ZERO_LITERAL.fullmatch(value.strip()))


def literal_number(value: str | None) -> float | None:
    if value is None:
        return None
    match = NUMBER_LITERAL.fullmatch(value.strip())
    return float(match.group(1)) if match else None


def visual_bottom_aliases(text: str) -> set[str]:
    return {match.group(1).lower() for match in VISUAL_BOTTOM_ALIAS.finditer(text)}


def references_visual_bottom(value: str | None, aliases: set[str]) -> bool:
    if value is None:
        return False
    normalized = re.sub(r"\s+", "", value).strip("\"'").lower()
    return (
        "visual_content.bottom_y" in normalized
        or "visualcontent.bottomy" in normalized
        or normalized in aliases
    )


def is_visible_paint(value: str | None) -> bool:
    if value is None:
        return False
    normalized = value.strip().strip("\"'").lower()
    if normalized in {"", "none", "transparent"}:
        return False
    return not bool(TRANSPARENT_PAINT.fullmatch(normalized))


def guide_finding(
    properties: dict[str, str], visual_bottom_y: float, aliases: set[str]
) -> dict[str, object] | None:
    width = literal_number(properties.get("width"))
    height = properties.get("height")
    height_number = literal_number(height)
    reaches_visual_bottom = (
        references_visual_bottom(height, aliases)
        or (height_number is not None and abs(height_number - visual_bottom_y) < 0.001)
    )
    paint = properties.get("backgroundcolor") or properties.get("background")
    if not (
        is_zero(properties.get("left"))
        and is_zero(properties.get("top"))
        and width is not None
        and 0 < width <= 24
        and reaches_visual_bottom
        and is_visible_paint(paint)
    ):
        return None
    return {
        "rule": "visible-left-edge-guide-at-visual-content-boundary",
        "properties": {
            "left": properties["left"],
            "top": properties["top"],
            "width": properties["width"],
            "height": height,
            "paint": paint,
        },
    }


def load_visual_bottom(layout_path: Path) -> float:
    layout = json.loads(layout_path.read_text(encoding="utf-8"))
    visual_content = layout.get("layout", layout).get("visual_content")
    if not isinstance(visual_content, dict):
        raise ValueError("caption layout has no visual_content object")
    bottom_y = visual_content.get("bottom_y")
    if not isinstance(bottom_y, (int, float)) or isinstance(bottom_y, bool) or bottom_y <= 0:
        raise ValueError("caption layout visual_content.bottom_y must be a positive number")
    return float(bottom_y)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Find visible safe-zone guide bars that leaked into delivery video source."
    )
    parser.add_argument("--src", nargs="+", required=True, help="Delivery source files or directories to inspect.")
    parser.add_argument("--caption-layout", required=True, help="Resolved caption-layout.json for this render.")
    args = parser.parse_args()

    try:
        layout_path = Path(args.caption_layout).expanduser().resolve()
        visual_bottom_y = load_visual_bottom(layout_path)
        checked_files = source_files(args.src)
        findings: list[dict[str, object]] = []
        for path in checked_files:
            text = path.read_text(encoding="utf-8")
            aliases = visual_bottom_aliases(text)
            blocks = list(balanced_style_objects(text))
            blocks.extend(html_style_blocks(text))
            if path.suffix.lower() in {".css", ".less", ".sass", ".scss"}:
                blocks.extend(css_style_blocks(text))
            for offset, block in blocks:
                finding = guide_finding(declarations(block), visual_bottom_y, aliases)
                if finding:
                    findings.append({"file": str(path), "line": line_number(text, offset), **finding})
        result = {
            "passed": not findings,
            "caption_layout": str(layout_path),
            "visual_content_bottom_y": visual_bottom_y,
            "checked_file_count": len(checked_files),
            "findings": findings,
            "hint": (
                "Remove the marker from the delivery composition. Render safe-zone guides only in a "
                "separate debug or preview source tree, then rerun this check before rendering."
            ),
        }
    except Exception as error:
        result = {"passed": False, "error": str(error)}

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

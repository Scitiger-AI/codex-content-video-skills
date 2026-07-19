#!/usr/bin/env python3
"""Audit narration for editorial metadata leakage, vague attribution, and generic endings."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any


HOOK_DISCOVERY_PATTERNS = (
    r"(?:今天|本周|最近).{0,12}(?:热榜|热搜|榜单)",
    r"(?:热榜|热搜|榜单).{0,12}(?:出现|看到|选中|入选)",
)
SELECTION_PROVENANCE_PATTERNS = (
    r"(?:这期|本期|这个)?(?:选题|话题).{0,8}(?:来自|选自|源自)",
)
VAGUE_ATTRIBUTION_PATTERNS = (
    r"(?:学术界|研究界|业内|大家|很多人).{0,12}(?:早就指出|普遍认为|都知道|已经证明)",
    r"(?:有研究|有论文|专家).{0,8}(?:表明|指出|证明|认为)",
)
GENERIC_CLOSING_PATTERNS = (
    r"(?:下次|以后).{0,18}(?:看到|遇到|听到)",
    r"(?:别|不要)只.{0,18}(?:问|看)",
    r"更值得(?:问|关注|思考)的是",
    r"不是.{0,24}(?:唯一答案|全部答案|唯一指标)",
)


def package_narration(value: dict[str, Any]) -> str:
    chapters = value.get("chapters")
    if not isinstance(chapters, list):
        return ""
    return "\n".join(
        chapter.get("narration", "").strip()
        for chapter in chapters
        if isinstance(chapter, dict) and isinstance(chapter.get("narration"), str)
    ).strip()


def matches(patterns: tuple[str, ...], text: str) -> list[str]:
    return [match.group(0) for pattern in patterns if (match := re.search(pattern, text, re.S))]


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit a narration for source leakage, vague attribution, and generic endings.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", help="Path to script-package.json")
    source.add_argument("--script", help="Path to a narration Markdown or text file")
    parser.add_argument("--allow-trend-framing", action="store_true")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    try:
        if args.input:
            package = json.loads(Path(args.input).read_text(encoding="utf-8"))
            narration = package_narration(package)
        else:
            narration = Path(args.script).read_text(encoding="utf-8").strip()
    except Exception as error:
        print(json.dumps({"passed": False, "errors": [str(error)]}, ensure_ascii=False, indent=2))
        return 1

    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    if not narration:
        errors.append({"code": "missing_narration", "message": "no narration text was found"})
    elif not args.allow_trend_framing:
        for match in matches(HOOK_DISCOVERY_PATTERNS, narration[:220]):
            errors.append({
                "code": "discovery_metadata_in_hook",
                "message": "open with a viewer problem, not how the topic was selected",
                "match": match,
            })
        for match in matches(SELECTION_PROVENANCE_PATTERNS, narration):
            errors.append({
                "code": "selection_provenance_in_narration",
                "message": "keep topic-selection provenance in production metadata, not audience narration",
                "match": match,
            })
    for match in matches(VAGUE_ATTRIBUTION_PATTERNS, narration):
        warnings.append({
            "code": "vague_attribution",
            "message": "replace vague authority with a specific source-backed claim or remove it",
            "match": match,
        })
    for match in matches(GENERIC_CLOSING_PATTERNS, narration[-260:]):
        warnings.append({
            "code": "generic_closing",
            "message": "land a topic-specific consequence, image, reversal, or tension instead of generic audience advice",
            "match": match,
        })

    passed = not errors and (not args.strict or not warnings)
    result = {
        "passed": passed,
        "strict": args.strict,
        "allow_trend_framing": args.allow_trend_framing,
        "narration_characters": len(narration),
        "errors": errors,
        "warnings": warnings,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

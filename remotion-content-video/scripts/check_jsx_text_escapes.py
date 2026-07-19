#!/usr/bin/env python3
"""Reject escape sequences written directly in JSX text nodes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys


ESCAPE_SEQUENCE = re.compile(r"\\[nrt]")
SOURCE_SUFFIXES = {".tsx", ".jsx"}


def source_files(paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for raw_path in paths:
        path = Path(raw_path).expanduser()
        if path.is_file() and path.suffix in SOURCE_SUFFIXES:
            files.append(path)
        elif path.is_dir():
            files.extend(candidate for candidate in path.rglob("*") if candidate.suffix in SOURCE_SUFFIXES)
    return sorted(set(files))


def is_bare_jsx_text(line: str) -> bool:
    stripped = line.strip()
    if not stripped or stripped.startswith(("//", "*", "<", "{", "}", "return ")):
        return False
    if any(quote in stripped for quote in ('"', "'", "`")):
        return False
    if any(token in stripped for token in ("=", ":", ";")):
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Find literal escape sequences in bare JSX text nodes.")
    parser.add_argument("--src", nargs="+", required=True, help="TSX files or directories to inspect")
    args = parser.parse_args()

    findings: list[dict[str, object]] = []
    for path in source_files(args.src):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            matches = ESCAPE_SEQUENCE.findall(line)
            if matches and is_bare_jsx_text(line):
                findings.append({
                    "file": str(path),
                    "line": number,
                    "escapes": matches,
                    "text": line.strip(),
                })

    result = {
        "passed": not findings,
        "checked_file_count": len(source_files(args.src)),
        "findings": findings,
        "hint": "Use a JSX string expression with whiteSpace: 'pre-line', or separate text elements.",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())

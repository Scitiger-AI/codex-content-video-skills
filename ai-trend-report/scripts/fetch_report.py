#!/usr/bin/env python3
"""Fetch the public SciTiger AI trend report without credentials."""

from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_ENDPOINT = "https://scitiger.cn/reports/daily.json"
SENSITIVE_FIELDS = {"json_oss_url", "html_oss_url", "oss_keys", "signed_url", "download_url"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch the latest public SciTiger AI trend report.")
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT, help="Public report JSON URL.")
    parser.add_argument("--output", type=Path, help="Write the sanitized full report to this JSON file instead of stdout.")
    parser.add_argument("--timeout", type=float, default=20, help="Request timeout in seconds.")
    return parser.parse_args()


def sanitize(value: object) -> object:
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    if isinstance(value, dict):
        return {key: sanitize(item) for key, item in value.items() if key not in SENSITIVE_FIELDS}
    return copy.deepcopy(value)


def fetch(endpoint: str, timeout: float) -> dict:
    request = Request(endpoint, headers={"Accept": "application/json"}, method="GET")
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.load(response)
    except HTTPError as error:
        raise RuntimeError(f"Public report returned HTTP {error.code}.") from error
    except URLError as error:
        if "CERTIFICATE_VERIFY_FAILED" in str(error.reason):
            try:
                completed = subprocess.run(
                    ["curl", "--fail", "--silent", "--show-error", "--location", "--max-time", str(timeout), endpoint],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=True,
                )
                payload = json.loads(completed.stdout.decode("utf-8", errors="replace"))
            except FileNotFoundError as exc:
                raise RuntimeError("Python could not verify HTTPS and curl is not available; configure a trusted CA bundle.") from exc
            except subprocess.CalledProcessError as exc:
                raise RuntimeError(f"curl fallback failed: {exc.stderr.decode('utf-8', errors='replace').strip()}") from exc
            except json.JSONDecodeError as exc:
                raise RuntimeError("Public report returned invalid JSON.") from exc
        else:
            raise RuntimeError(f"Could not reach the public report: {error.reason}") from error
    except json.JSONDecodeError as error:
        raise RuntimeError("Public report returned invalid JSON.") from error
    if not isinstance(payload, dict):
        raise RuntimeError("Public report root must be an object.")
    if not isinstance(payload.get("report_meta"), dict) or not isinstance(payload.get("summary"), dict):
        raise RuntimeError("Public report is missing report_meta or summary.")
    return sanitize(payload)  # type: ignore[return-value]


def overview(report: dict) -> dict:
    return {
        "report_meta": report.get("report_meta"),
        "summary": report.get("summary"),
        "platforms": [
            {
                "key": platform.get("key"),
                "name": platform.get("name"),
                "status": platform.get("status"),
                "item_count": platform.get("item_count"),
                "top_category": platform.get("top_category"),
            }
            for platform in report.get("platforms", [])
            if isinstance(platform, dict)
        ],
        "top_categories": report.get("top_categories", []),
        "trending_topics": report.get("trending_topics", []),
        "agent_insight": report.get("agent_insight", []),
        "agent_recommendations": report.get("agent_recommendations", []),
        "cross_platform_opportunities": report.get("cross_platform_opportunities", []),
    }


def main() -> int:
    args = parse_args()
    try:
        report = fetch(args.endpoint, args.timeout)
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        return 1
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Saved public report to {args.output}", file=sys.stderr)
    else:
        print(json.dumps(overview(report), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

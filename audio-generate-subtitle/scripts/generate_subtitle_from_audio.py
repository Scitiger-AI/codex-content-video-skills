#!/usr/bin/env python3
"""Generate subtitles through the public SciTiger asynchronous subtitle API."""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


DEFAULT_BASE_URL = "https://link.scitiger.cn"
DEFAULT_POLL_INTERVAL_SECONDS = 2.0
DEFAULT_TIMEOUT_SECONDS = 1800
AUDIO_FORMATS = {"wav", "mp3", "flac", "ogg", "m4a", "aac"}


class ServiceError(RuntimeError):
    pass


def default_env_file() -> Path:
    return Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex").expanduser() / "scitiger.env"


def load_env_file(path: Path | None) -> dict[str, str]:
    if not path or not path.is_file():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            if key.strip():
                values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def resolve_api_key(args: argparse.Namespace, values: dict[str, str]) -> str:
    for value in [args.api_key, os.environ.get(args.api_key_env), values.get(args.api_key_env)]:
        if value and value.strip():
            return value.strip()
    raise ServiceError(f"set {args.api_key_env} in {args.env_file}, export it, or pass --api-key; never commit API keys")


def service_url(base_url: str, path_or_url: str) -> str:
    return path_or_url if re.match(r"^https?://", path_or_url, re.I) else urljoin(base_url.rstrip("/") + "/", path_or_url.lstrip("/"))


def curl_json(url: str, *, method: str, headers: dict[str, str], data: bytes | None, timeout: int) -> dict[str, Any]:
    """Use the OS certificate store only when this Python build lacks public CAs."""
    command = ["curl", "--silent", "--show-error", "--location", "--request", method, "--max-time", str(timeout)]
    for key, value in headers.items():
        command.extend(["--header", f"{key}: {value}"])
    if data is not None:
        command.extend(["--data-binary", "@-"])
    try:
        completed = subprocess.run(command + [url], input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        payload = json.loads(completed.stdout.decode("utf-8", errors="replace"))
    except FileNotFoundError as exc:
        raise ServiceError("Python could not verify HTTPS and curl is not available; configure a trusted CA bundle") from exc
    except subprocess.CalledProcessError as exc:
        raise ServiceError(f"curl fallback failed: {exc.stderr.decode('utf-8', errors='replace').strip()}") from exc
    except json.JSONDecodeError as exc:
        raise ServiceError("curl fallback returned invalid JSON") from exc
    if not isinstance(payload, dict):
        raise ServiceError(f"API returned a non-object response: {payload}")
    return payload


def request_json(base_url: str, path: str, *, api_key: str, method: str = "GET", body: Any = None, timeout: int = 120) -> dict[str, Any]:
    headers = {"Accept": "application/json", "Authorization": f"Bearer {api_key}", "X-Request-Source": "codex-content-video-skill"}
    data = None
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    try:
        with urlopen(Request(service_url(base_url, path), data=data, headers=headers, method=method), timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8", errors="replace"))
            status = response.status
    except HTTPError as exc:
        try:
            detail = json.loads(exc.read().decode("utf-8", errors="replace"))
        except json.JSONDecodeError:
            detail = "non-JSON error response"
        raise ServiceError(f"HTTP {exc.code} for {path}: {detail}") from exc
    except URLError as exc:
        if "CERTIFICATE_VERIFY_FAILED" in str(exc.reason):
            payload = curl_json(service_url(base_url, path), method=method, headers=headers, data=data, timeout=timeout)
            status = 200
        else:
            raise ServiceError(f"network error for {path}: {exc.reason}") from exc
    if not isinstance(payload, dict):
        raise ServiceError(f"API returned a non-object response: {payload}")
    if not 200 <= status < 300:
        raise ServiceError(str(payload.get("message") or payload.get("error") or f"HTTP {status}"))
    code = payload.get("code")
    if isinstance(code, int) and not 200 <= code < 300:
        raise ServiceError(str(payload.get("message") or payload.get("error") or f"API code {code}"))
    if payload.get("success") is False:
        raise ServiceError(str(payload.get("message") or payload.get("error") or "API request failed"))
    data = payload.get("data", payload)
    if not isinstance(data, dict):
        raise ServiceError(f"API response data was not an object: {data}")
    return data


def infer_audio_format(path: Path, override: str | None) -> str:
    fmt = (override or path.suffix.lstrip(".") or "wav").lower()
    if fmt not in AUDIO_FORMATS:
        raise ServiceError(f"unsupported audio format: {fmt}")
    return fmt


def reference_text(args: argparse.Namespace) -> str | None:
    value = Path(args.text_file).read_text(encoding="utf-8") if args.text_file else args.reference_text or args.text or ""
    return value.strip() or None


def subtitle_options(args: argparse.Namespace) -> dict[str, Any]:
    result: dict[str, Any] = {
        "max_chars": args.max_chars,
        "min_duration": args.min_duration,
        "max_duration": args.max_duration,
        "max_cps": args.max_cps,
        "punctuation_policy": args.punctuation_policy,
        "ai_optimize": not args.no_ai_optimize,
    }
    if args.ai_model:
        result["ai_model"] = args.ai_model
    return result


def result_record(job: dict[str, Any]) -> dict[str, Any]:
    return job["result"] if isinstance(job.get("result"), dict) else job


def create_job(base_url: str, body: dict[str, Any], api_key: str) -> str:
    data = request_json(base_url, "/api/v1/subtitle/jobs", api_key=api_key, method="POST", body=body)
    task_id = data.get("job_id") or data.get("jobId")
    if not isinstance(task_id, str) or not task_id.strip():
        raise ServiceError(f"subtitle job creation did not return job_id: {data}")
    return task_id.strip()


def poll_job(base_url: str, task_id: str, api_key: str, timeout_seconds: int, interval_seconds: float) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    last_status = "unknown"
    while time.monotonic() <= deadline:
        job = request_json(base_url, f"/api/v1/subtitle/jobs/{task_id}", api_key=api_key, timeout=60)
        result = result_record(job)
        status = str(job.get("status") or result.get("status") or "").lower()
        last_status = status or last_status
        if status == "completed":
            return job
        if status in {"failed", "cancelled"}:
            raise ServiceError(str(job.get("error_message") or result.get("error_message") or f"subtitle job {status}"))
        time.sleep(interval_seconds)
    raise ServiceError(f"subtitle job timed out after {timeout_seconds}s; last status: {last_status}")


def decode_srt_base64(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        return ""
    try:
        return base64.b64decode(value, validate=True).decode("utf-8", errors="replace")
    except ValueError:
        return ""


def download_subtitle_srt(base_url: str, subtitle_url: str, api_key: str) -> str:
    resolved = service_url(base_url, subtitle_url)
    target = urlparse(resolved)
    base = urlparse(base_url)
    headers = {"Authorization": f"Bearer {api_key}"} if not target.netloc or target.netloc == base.netloc else {}
    try:
        with urlopen(Request(resolved, headers=headers, method="GET"), timeout=120) as response:
            return response.read().decode("utf-8", errors="replace")
    except URLError as exc:
        if "CERTIFICATE_VERIFY_FAILED" not in str(exc.reason):
            raise ServiceError(f"subtitle download network error: {exc.reason}") from exc
        command = ["curl", "--fail", "--silent", "--show-error", "--location", "--max-time", "120"]
        for key, value in headers.items():
            command.extend(["--header", f"{key}: {value}"])
        try:
            completed = subprocess.run(command + [resolved], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        except FileNotFoundError as error:
            raise ServiceError("Python could not verify HTTPS and curl is not available; configure a trusted CA bundle") from error
        except subprocess.CalledProcessError as error:
            raise ServiceError(f"subtitle download fallback failed: {error.stderr.decode('utf-8', errors='replace').strip()}") from error
        return completed.stdout.decode("utf-8", errors="replace")


def completed_subtitle_srt(base_url: str, result: dict[str, Any], api_key: str) -> str:
    direct = normalize_srt(str(result.get("subtitle_srt") or ""))
    if direct:
        return direct
    encoded = normalize_srt(decode_srt_base64(result.get("subtitle_srt_base64")))
    if encoded:
        return encoded
    for field in ("subtitle_oss_url", "subtitle_url", "subtitle_download_url", "download_url"):
        value = result.get(field)
        if isinstance(value, str) and value.strip():
            return normalize_srt(download_subtitle_srt(base_url, value.strip(), api_key))
    return ""


def normalize_srt(value: str) -> str:
    normalized = value.replace("\r\n", "\n").replace("\r", "\n").lstrip("\ufeff").strip()
    return f"{normalized}\n" if normalized else ""


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate subtitles through the public SciTiger subtitle API.")
    parser.add_argument("--audio", required=True)
    parser.add_argument("--audio-format")
    parser.add_argument("--text")
    parser.add_argument("--reference-text")
    parser.add_argument("--text-file")
    parser.add_argument("--language", default="zh")
    parser.add_argument("--max-chars", type=int, default=16)
    parser.add_argument("--min-duration", type=float, default=0.83)
    parser.add_argument("--max-duration", type=float, default=7.0)
    parser.add_argument("--max-cps", type=float, default=12.0)
    parser.add_argument("--punctuation-policy", default="strip_trailing", choices=["preserve", "remove", "strip_trailing"])
    parser.add_argument("--no-ai-optimize", action="store_true")
    parser.add_argument("--ai-model")
    parser.add_argument("--api-key")
    parser.add_argument("--api-key-env", default="SCITIGER_API_KEY")
    parser.add_argument("--env-file", default=str(default_env_file()), help="Defaults to $CODEX_HOME/scitiger.env.")
    parser.add_argument("--poll-interval", type=float, default=DEFAULT_POLL_INTERVAL_SECONDS)
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--out-dir", default="")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    out_dir = Path(args.out_dir or f"subtitle-{datetime.now():%Y%m%d-%H%M%S}").expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    env_file = Path(args.env_file).expanduser() if args.env_file else None
    env_values = load_env_file(env_file)
    metadata: dict[str, Any] = {
        "base_url": DEFAULT_BASE_URL,
        "env_file": str(env_file) if env_file else None,
        "api_key_env": args.api_key_env,
        "api_key_configured": False,
        "created_at": datetime.now().isoformat(),
        "mode": "async_job",
    }
    try:
        if args.poll_interval <= 0 or args.timeout <= 0:
            raise ServiceError("--poll-interval and --timeout must be positive")
        api_key = resolve_api_key(args, env_values)
        metadata["api_key_configured"] = True
        audio_path = Path(args.audio).expanduser().resolve()
        if not audio_path.is_file():
            raise ServiceError(f"audio file not found: {audio_path}")
        audio_format = infer_audio_format(audio_path, args.audio_format)
        body: dict[str, Any] = {
            "audio_base64": base64.b64encode(audio_path.read_bytes()).decode("ascii"),
            "audio_format": audio_format,
            "language": args.language,
            "subtitle_options": subtitle_options(args),
        }
        if text := reference_text(args):
            body["reference_text"] = text
        metadata["audio_path"] = str(audio_path)
        metadata["request"] = {
            "audio_format": audio_format,
            "audio_base64_length": len(body["audio_base64"]),
            "language": args.language,
            "has_reference_text": "reference_text" in body,
            "reference_text_length": len(body.get("reference_text", "")),
            "subtitle_options": body["subtitle_options"],
        }
        task_id = create_job(metadata["base_url"], body, api_key)
        metadata["subtitle_task_id"] = task_id
        job = poll_job(metadata["base_url"], task_id, api_key, args.timeout, args.poll_interval)
        result = result_record(job)
        subtitle_srt = completed_subtitle_srt(metadata["base_url"], result, api_key)
        if not subtitle_srt:
            raise ServiceError("completed subtitle job did not return subtitle_srt")
        segments = result.get("subtitle_segments") or []
        if not isinstance(segments, list):
            segments = []
        subtitle_path = out_dir / "subtitle.srt"
        segments_path = out_dir / "subtitle_segments.json"
        subtitle_path.write_text(subtitle_srt, encoding="utf-8")
        segments_path.write_text(json.dumps(segments, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        metadata["subtitle_poll"] = {
            "status": job.get("status") or result.get("status"),
            "subtitle_format": result.get("subtitle_format"),
            "subtitle_segment_count": len(segments),
            "has_subtitle_srt": True,
            "diagnostics": result.get("diagnostics") or result.get("subtitle_diagnostics"),
        }
        metadata["subtitle_segment_count"] = len(segments)
        metadata["subtitle_path"] = str(subtitle_path)
        metadata["segments_path"] = str(segments_path)
        metadata_path = out_dir / "metadata.json"
        metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": True, "subtitle_task_id": task_id, "subtitle_path": str(subtitle_path), "segments_path": str(segments_path), "metadata_path": str(metadata_path)}, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        metadata["error"] = str(exc)
        (out_dir / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": False, "error": str(exc), "out_dir": str(out_dir)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

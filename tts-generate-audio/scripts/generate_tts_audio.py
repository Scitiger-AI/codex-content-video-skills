#!/usr/bin/env python3
"""Generate speech audio through the public SciTiger asynchronous TTS API."""

from __future__ import annotations

import argparse
import base64
import hashlib
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
DEFAULT_TIMEOUT_SECONDS = 1200
DEFAULT_TTS_RATE = 1.0
DEFAULT_TARGET_LUFS = -16.0
DEFAULT_TRUE_PEAK_DBTP = -1.0
BUNDLED_DEFAULT_REFERENCE_AUDIO = Path(__file__).resolve().parent.parent / "assets" / "default-reference.mp3"
AUDIO_EXTENSIONS = {"wav", "mp3"}


class ServiceError(RuntimeError):
    pass


def default_env_file() -> Path:
    codex_home = os.environ.get("CODEX_HOME") or str(Path.home() / ".codex")
    return Path(codex_home).expanduser() / "scitiger.env"


def load_env_file(path: Path | None) -> dict[str, str]:
    if not path or not path.is_file():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip():
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def resolve_api_key(args: argparse.Namespace, env_values: dict[str, str]) -> str:
    for value in [args.api_key, os.environ.get(args.api_key_env), env_values.get(args.api_key_env)]:
        if value and value.strip():
            return value.strip()
    raise ServiceError(
        f"set {args.api_key_env} in {args.env_file}, export it in the shell, or pass --api-key; never commit API keys"
    )


def request_headers(api_key: str, *, json_body: bool = False) -> dict[str, str]:
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {api_key}",
        "X-Request-Source": "codex-content-video-skill",
    }
    if json_body:
        headers["Content-Type"] = "application/json"
    return headers


def service_url(base_url: str, path_or_url: str) -> str:
    if re.match(r"^https?://", path_or_url, re.I):
        return path_or_url
    return urljoin(base_url.rstrip("/") + "/", path_or_url.lstrip("/"))


def parse_json(data: bytes) -> Any:
    try:
        return json.loads(data.decode("utf-8", errors="replace"))
    except json.JSONDecodeError as exc:
        raise ServiceError("API returned invalid JSON") from exc


def curl_bytes(url: str, *, method: str, headers: dict[str, str], data: bytes | None, timeout: int) -> bytes:
    """Use the OS certificate store only when this Python build lacks public CAs."""
    command = ["curl", "--silent", "--show-error", "--location", "--request", method, "--max-time", str(timeout)]
    for key, value in headers.items():
        command.extend(["--header", f"{key}: {value}"])
    if data is not None:
        command.extend(["--data-binary", "@-"])
    try:
        completed = subprocess.run(command + [url], input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    except FileNotFoundError as exc:
        raise ServiceError("Python could not verify HTTPS and curl is not available; configure a trusted CA bundle") from exc
    except subprocess.CalledProcessError as exc:
        raise ServiceError(f"curl fallback failed: {exc.stderr.decode('utf-8', errors='replace').strip()}") from exc
    return completed.stdout


def unwrap_response(status: int, payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ServiceError(f"API returned a non-object response: {payload}")
    code = payload.get("code")
    if isinstance(code, int) and not (200 <= code < 300):
        raise ServiceError(str(payload.get("message") or payload.get("error") or f"API code {code}"))
    if payload.get("success") is False:
        raise ServiceError(str(payload.get("message") or payload.get("error") or "API request failed"))
    if not 200 <= status < 300:
        raise ServiceError(str(payload.get("message") or payload.get("error") or f"HTTP {status}"))
    data = payload.get("data", payload)
    if not isinstance(data, dict):
        raise ServiceError(f"API response data was not an object: {data}")
    return data


def request_json(base_url: str, path: str, *, api_key: str, method: str = "GET", body: Any = None, timeout: int = 120) -> dict[str, Any]:
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    request = Request(
        service_url(base_url, path),
        data=data,
        headers=request_headers(api_key, json_body=body is not None),
        method=method,
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return unwrap_response(response.status, parse_json(response.read()))
    except HTTPError as exc:
        try:
            detail = parse_json(exc.read())
        except ServiceError:
            detail = "non-JSON error response"
        raise ServiceError(f"HTTP {exc.code} for {path}: {detail}") from exc
    except URLError as exc:
        if "CERTIFICATE_VERIFY_FAILED" in str(exc.reason):
            return unwrap_response(200, parse_json(curl_bytes(service_url(base_url, path), method=method, headers=request_headers(api_key, json_body=body is not None), data=data, timeout=timeout)))
        raise ServiceError(f"network error for {path}: {exc.reason}") from exc


def read_text(args: argparse.Namespace) -> str:
    value = Path(args.text_file).read_text(encoding="utf-8") if args.text_file else args.text
    text = (value or "").strip()
    if not text:
        raise ServiceError("provide non-empty --text or --text-file")
    return text


def bundled_reference_audio() -> Path:
    path = BUNDLED_DEFAULT_REFERENCE_AUDIO.resolve()
    if not path.is_file():
        raise ServiceError(f"bundled default reference audio is missing: {path}")
    if path.suffix.lower().lstrip(".") not in AUDIO_EXTENSIONS:
        raise ServiceError(f"unsupported bundled reference-audio format: {path.suffix}")
    return path


def select_reference_audio(args: argparse.Namespace) -> tuple[Path, str]:
    if args.reference_audio:
        path = Path(args.reference_audio).expanduser().resolve()
        if not path.is_file():
            raise ServiceError(f"reference audio not found: {path}")
        if path.suffix.lower().lstrip(".") not in AUDIO_EXTENSIONS:
            raise ServiceError("reference audio must be WAV or MP3 for the public SciTiger API")
        return path, "explicit_reference_audio"
    return bundled_reference_audio(), "bundled_default_reference_audio"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def effective_rate(args: argparse.Namespace) -> float:
    value = args.tts_rate if args.tts_rate is not None else args.rate
    rate = DEFAULT_TTS_RATE if value is None else float(value)
    if not 0.5 <= rate <= 2.0:
        raise ServiceError("--tts-rate must be between 0.5 and 2.0")
    return rate


def normalize_audio(source: Path, target: Path, extension: str, *, target_lufs: float, true_peak_dbtp: float) -> None:
    if not -30 <= target_lufs <= -8:
        raise ServiceError("--target-lufs must be between -30 and -8")
    if not -9 <= true_peak_dbtp <= -0.1:
        raise ServiceError("--true-peak-dbtp must be between -9 and -0.1")
    codec = "pcm_s16le" if extension == "wav" else "libmp3lame"
    limiter = 10 ** (true_peak_dbtp / 20)
    filter_graph = f"loudnorm=I={target_lufs}:TP={true_peak_dbtp}:LRA=11,alimiter=limit={limiter:.8f}:level=false"
    command = [
        "ffmpeg", "-nostdin", "-y", "-v", "error", "-i", str(source), "-af", filter_graph,
        "-ar", "48000", "-c:a", codec,
    ]
    if extension == "mp3":
        command.extend(["-b:a", "192k"])
    command.append(str(target))
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise ServiceError("ffmpeg is required to create delivery-normalized audio") from exc
    except subprocess.CalledProcessError as exc:
        raise ServiceError(f"audio normalization failed: {exc.stderr.strip()}") from exc
    if not target.is_file() or target.stat().st_size <= 1024:
        raise ServiceError("audio normalization did not produce a usable file")


def completed_result(job: dict[str, Any]) -> dict[str, Any]:
    result = job.get("result")
    return result if isinstance(result, dict) else job


def create_job(base_url: str, body: dict[str, Any], api_key: str) -> str:
    data = request_json(base_url, "/api/v1/tts/jobs", api_key=api_key, method="POST", body=body)
    task_id = data.get("job_id") or data.get("jobId")
    if not isinstance(task_id, str) or not task_id.strip():
        raise ServiceError(f"TTS job creation did not return job_id: {data}")
    return task_id.strip()


def poll_job(base_url: str, task_id: str, api_key: str, *, timeout_seconds: int, interval_seconds: float) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    last_status = "unknown"
    while time.monotonic() <= deadline:
        data = request_json(base_url, f"/api/v1/tts/jobs/{task_id}", api_key=api_key, timeout=60)
        result = completed_result(data)
        status = str(data.get("status") or result.get("status") or "").lower()
        last_status = status or last_status
        if status == "completed":
            return data
        if status in {"failed", "cancelled"}:
            raise ServiceError(str(data.get("error_message") or result.get("error_message") or f"TTS job {status}"))
        time.sleep(interval_seconds)
    raise ServiceError(f"TTS job timed out after {timeout_seconds}s; last status: {last_status}")


def audio_extension(result: dict[str, Any], requested_format: str) -> str:
    value = str(result.get("format") or requested_format).lower().lstrip(".")
    return value if value in AUDIO_EXTENSIONS else requested_format


def download_audio(base_url: str, audio_url: str, api_key: str) -> bytes:
    resolved = service_url(base_url, audio_url)
    base = urlparse(base_url)
    target = urlparse(resolved)
    headers: dict[str, str] = {}
    if not target.netloc or target.netloc == base.netloc:
        headers = request_headers(api_key)
    try:
        with urlopen(Request(resolved, headers=headers, method="GET"), timeout=180) as response:
            return response.read()
    except HTTPError as exc:
        raise ServiceError(f"audio download returned HTTP {exc.code}") from exc
    except URLError as exc:
        if "CERTIFICATE_VERIFY_FAILED" in str(exc.reason):
            return curl_bytes(resolved, method="GET", headers=headers, data=None, timeout=180)
        raise ServiceError(f"audio download network error: {exc.reason}") from exc


def resolve_audio_bytes(base_url: str, result: dict[str, Any], api_key: str) -> bytes:
    for field in ("audio_base64", "audio_data_base64"):
        value = result.get(field)
        if isinstance(value, str) and value.strip():
            try:
                return base64.b64decode(value)
            except ValueError as exc:
                raise ServiceError(f"completed TTS job returned invalid {field}") from exc
    for field in ("audio_url", "audio_download_url", "audio_oss_url", "download_url"):
        value = result.get(field)
        if isinstance(value, str) and value.strip():
            return download_audio(base_url, value.strip(), api_key)
    raise ServiceError("completed TTS job has no downloadable audio URL or audio_base64")


def job_snapshot(job: dict[str, Any]) -> dict[str, Any]:
    result = completed_result(job)
    return {
        "status": job.get("status") or result.get("status"),
        "duration": result.get("duration"),
        "sample_rate": result.get("sample_rate"),
        "format": result.get("format"),
        "file_size": result.get("file_size"),
        "has_audio_url": any(isinstance(result.get(key), str) and result[key] for key in ("audio_url", "audio_download_url", "audio_oss_url", "download_url")),
        "has_audio_base64": any(isinstance(result.get(key), str) and result[key] for key in ("audio_base64", "audio_data_base64")),
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate speech audio through the public SciTiger TTS API.")
    text_group = parser.add_mutually_exclusive_group(required=True)
    text_group.add_argument("--text")
    text_group.add_argument("--text-file")
    parser.add_argument("--reference-audio", help="Optional WAV or MP3 voice reference. Defaults to the bundled reference audio.")
    parser.add_argument("--tts-rate", type=float, help="Speech rate. Defaults to 1.0.")
    parser.add_argument("--rate", type=float, help="Deprecated alias for --tts-rate.")
    parser.add_argument("--volume", type=float, default=1.0)
    parser.add_argument("--pitch", type=float, default=0.0)
    parser.add_argument("--output-format", choices=sorted(AUDIO_EXTENSIONS), default="wav")
    parser.add_argument("--target-lufs", type=float, default=DEFAULT_TARGET_LUFS)
    parser.add_argument("--true-peak-dbtp", type=float, default=DEFAULT_TRUE_PEAK_DBTP)
    parser.add_argument("--api-key", help="Public SciTiger API key. Prefer --env-file so the key is not exposed in shell history.")
    parser.add_argument("--api-key-env", default="SCITIGER_API_KEY")
    parser.add_argument("--env-file", default=str(default_env_file()), help="Defaults to $CODEX_HOME/scitiger.env.")
    parser.add_argument("--poll-interval", type=float, default=DEFAULT_POLL_INTERVAL_SECONDS)
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--out-dir", default="", help="Defaults to ./tts-<timestamp>.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    out_dir = Path(args.out_dir or f"tts-{datetime.now():%Y%m%d-%H%M%S}").expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    env_file = Path(args.env_file).expanduser() if args.env_file else None
    env_values = load_env_file(env_file)
    metadata: dict[str, Any] = {
        "base_url": DEFAULT_BASE_URL,
        "env_file": str(env_file) if env_file else None,
        "api_key_env": args.api_key_env,
        "api_key_configured": False,
        "created_at": datetime.now().isoformat(),
    }
    try:
        if args.poll_interval <= 0:
            raise ServiceError("--poll-interval must be positive")
        if args.timeout <= 0:
            raise ServiceError("--timeout must be positive")
        api_key = resolve_api_key(args, env_values)
        metadata["api_key_configured"] = True
        text = read_text(args)
        rate = effective_rate(args)
        reference_audio, voice_source = select_reference_audio(args)
        body = {
            "text": text,
            "reference_audio_base64": base64.b64encode(reference_audio.read_bytes()).decode("ascii"),
            "output_format": args.output_format,
            "voice_settings": {"rate": rate, "volume": args.volume, "pitch": args.pitch},
        }
        metadata["request"] = {
            "text_length": len(text),
            "text_preview": text[:120],
            "output_format": args.output_format,
            "voice_settings": body["voice_settings"],
            "reference_audio_bytes": reference_audio.stat().st_size,
        }
        metadata["voice_source"] = voice_source
        metadata["bundled_reference_audio_path"] = str(BUNDLED_DEFAULT_REFERENCE_AUDIO) if voice_source == "bundled_default_reference_audio" else None
        metadata["bundled_reference_audio_sha256"] = sha256_file(reference_audio) if voice_source == "bundled_default_reference_audio" else None
        task_id = create_job(metadata["base_url"], body, api_key)
        metadata["tts_task_id"] = task_id
        job = poll_job(metadata["base_url"], task_id, api_key, timeout_seconds=args.timeout, interval_seconds=args.poll_interval)
        result = completed_result(job)
        metadata["tts_poll"] = job_snapshot(job)
        extension = audio_extension(result, args.output_format)
        raw_audio_path = out_dir / f"tts_{task_id}.source.{extension}"
        raw_audio_path.write_bytes(resolve_audio_bytes(metadata["base_url"], result, api_key))
        audio_path = out_dir / f"tts_{task_id}.{extension}"
        normalize_audio(raw_audio_path, audio_path, extension, target_lufs=args.target_lufs, true_peak_dbtp=args.true_peak_dbtp)
        metadata["source_audio_path"] = str(raw_audio_path)
        metadata["audio_path"] = str(audio_path)
        metadata["normalization"] = {
            "tool": "ffmpeg loudnorm + alimiter",
            "target_lufs": args.target_lufs,
            "true_peak_dbtp": args.true_peak_dbtp,
            "sample_rate": 48000,
        }
        metadata_path = out_dir / "metadata.json"
        metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": True, "audio_path": str(audio_path), "tts_task_id": task_id, "metadata_path": str(metadata_path)}, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        metadata["error"] = str(exc)
        (out_dir / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": False, "error": str(exc), "out_dir": str(out_dir)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

# SciTiger Subtitle API

Always use `https://link.scitiger.cn`. Read the caller's `SCITIGER_API_KEY` from `$CODEX_HOME/scitiger.env`, send `Authorization: Bearer <key>`, and never persist the key or signed media URLs.

Create with `POST /api/v1/subtitle/jobs`:

```json
{
  "audio_base64": "<base64 audio>",
  "audio_format": "wav",
  "language": "zh",
  "reference_text": "optional original script",
  "subtitle_options": {
    "max_chars": 16,
    "min_duration": 0.83,
    "max_duration": 7.0,
    "max_cps": 12.0,
    "punctuation_policy": "strip_trailing",
    "ai_optimize": true
  }
}
```

Poll `GET /api/v1/subtitle/jobs/{job_id}` until `status` is `completed`. The completed `data.result` must include `subtitle_segments` plus either `subtitle_srt`, `subtitle_srt_base64`, or `subtitle_oss_url`.

When the user provides the original script, send it as `reference_text`. Timing remains derived from the supplied audio.

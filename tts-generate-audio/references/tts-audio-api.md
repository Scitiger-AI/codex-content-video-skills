# SciTiger TTS API

## Config

Always use `https://link.scitiger.cn`. Read the caller's key from `SCITIGER_API_KEY` in `$CODEX_HOME/scitiger.env`, or from an explicit `--api-key` / `--api-key-env` value. Send `Authorization: Bearer <key>` and never persist the key or a signed audio URL in metadata.

## Create And Poll

Create with `POST /api/v1/tts/jobs`:

```json
{
  "text": "text to synthesize",
  "reference_audio_base64": "base64 reference audio",
  "output_format": "wav",
  "voice_settings": {"rate": 1.0, "volume": 1.0, "pitch": 0.0}
}
```

`reference_audio_base64` is required by the public contract. Use the user's supplied reference audio or the skill-bundled default asset. The public contract does not currently accept `voice_id`.

Poll `GET /api/v1/tts/jobs/{job_id}` until `status` is `completed`, then read `data.result.audio_oss_url`, `audio_url`, or a supported base64 audio field. The result should also expose `duration`, `sample_rate`, `file_size`, and `format` when available.

Do not generate subtitles in this skill. Use `audio-generate-subtitle` with the downloaded audio file.

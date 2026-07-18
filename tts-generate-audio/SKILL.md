---
name: tts-generate-audio
description: Generate speech audio through the public SciTiger asynchronous TTS API. Use when the user asks to synthesize TTS audio from text, clone or use a reference voice, use the skill's bundled default voice, download generated audio, or control TTS speaking speed with tts_rate. Do not use for subtitle generation; use audio-generate-subtitle for subtitles from audio.
---

# TTS Generate Audio

## Overview

Use this skill to generate a speech audio file through `https://link.scitiger.cn`. This skill intentionally stops after audio generation and does not request or generate subtitles. Default speech speed is `1.0`; only change it when the user explicitly requests a rate. The bundled `assets/default-reference.mp3` is the portable default voice asset.

Before using the public service, create `$CODEX_HOME/scitiger.env` (normally `~/.codex/scitiger.env`) with the user's own key:

```text
SCITIGER_API_KEY=sk-ats-...
```

Do not add this file to a repository or generated video artifacts. `--api-key` and `SCITIGER_API_KEY` are supported, but the per-user file is preferred because Codex may filter `*_KEY` variables before launching shell commands.

## Quick Start

Run the script from the current workspace and save outputs to a task output directory:

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/tts-generate-audio/scripts/generate_tts_audio.py" \
  --text-file script.txt \
  --tts-rate 1.0 \
  --out-dir ./outputs/tts-audio
```

Use a reference audio file:

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/tts-generate-audio/scripts/generate_tts_audio.py" \
  --text-file script.txt \
  --reference-audio ./reference.wav \
  --output-format wav \
  --tts-rate 0.95 \
  --out-dir ./outputs/tts-audio
```

## Workflow

1. Read text from `--text` or `--text-file`.
2. Choose a reference audio source: use `--reference-audio` when supplied; otherwise use the bundled `assets/default-reference.mp3`. The public API currently requires reference audio and does not expose a `voice_id` field. Never scan a user directory or select a voice at random.
3. Set speech speed with `--tts-rate`; when omitted, it is `1.0`. `--rate` is kept as a compatibility alias, but prefer `--tts-rate`.
4. Submit `/api/v1/tts/jobs`, poll `/api/v1/tts/jobs/{job_id}`, and download the completed audio returned by the public API.
5. Use the generated audio path from stdout or `metadata.json` as input for the separate `audio-generate-subtitle` skill when subtitles are needed.

## Outputs

The script writes:

- `tts_<task_id>.<format>`: generated audio
- `metadata.json`: request snapshot, public-service config without the API key, task poll result, the resolved voice source, and the bundled asset hash when used

It prints JSON containing `audio_path`, `tts_task_id`, and `metadata_path`.

## Reference

Read `references/tts-audio-api.md` before changing endpoints, payload fields, polling, default voice selection, or output metadata.

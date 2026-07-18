---
name: audio-generate-subtitle
description: Generate SRT subtitles and timed subtitle segments from an existing audio file through the public SciTiger asynchronous subtitle API. Use when the user asks to create subtitles for TTS audio, produce SRT from audio, align subtitles to a provided script or reference_text, or call the SciTiger subtitle jobs API. Do not use to synthesize TTS audio; use tts-generate-audio for audio creation.
---

# Audio Generate Subtitle

Use this skill to create subtitles from an existing audio file. It calls `https://link.scitiger.cn/api/v1/subtitle/jobs`, polls to completion, and directly saves `subtitle.srt` and `subtitle_segments.json`. It does not synthesize audio or build subtitle timing by hand.

Before use, create `$CODEX_HOME/scitiger.env` (normally `~/.codex/scitiger.env`) with the user's own key:

```text
SCITIGER_API_KEY=sk-ats-...
```

Never commit this file or copy it into task artifacts. `--api-key` and `SCITIGER_API_KEY` are supported, but the per-user file is preferred because Codex may filter `*_KEY` variables before launching shell commands.

## Quick Start

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/audio-generate-subtitle/scripts/generate_subtitle_from_audio.py" \
  --audio ./outputs/tts-audio/tts_TASK_ID.wav \
  --text-file script.txt \
  --language zh \
  --out-dir ./outputs/subtitle
```

## Workflow

1. Use an existing audio file from the user or `tts-generate-audio`.
2. Pass the original manuscript with `--text` or `--text-file` when available. It becomes `reference_text`, while timing comes from the audio.
3. Submit `/api/v1/subtitle/jobs` and poll `/api/v1/subtitle/jobs/{job_id}` until completion.
4. Save returned subtitle content to `subtitle.srt` (the API may provide inline SRT, base64 SRT, or a signed subtitle URL) and `subtitle_segments` to `subtitle_segments.json`.

## Outputs

- `subtitle.srt`: generated SRT
- `subtitle_segments.json`: timed segment array
- `metadata.json`: request snapshot without the API key, task result summary, and paths

Read [references/subtitle-api.md](references/subtitle-api.md) before changing endpoints, payload fields, polling, or response parsing.

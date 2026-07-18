# Topic Brief Contract

Write a JSON artifact with this shape. Preserve unknown user-provided requirements in `request` instead of silently dropping them.

```json
{
  "schema_version": 1,
  "request": {
    "topic": "",
    "domain": "",
    "audience": "",
    "platform": "",
    "freshness_requested": false,
    "source_preference": "auto"
  },
  "source_decision": {
    "source_mode": "none",
    "routing_reason": "",
    "user_override": false,
    "public_signals_file": null,
    "ai_daily_report_file": null
  },
  "signals": [
    {
      "signal_id": "",
      "source_kind": "public",
      "platform": "",
      "title": "",
      "url": "",
      "rank": null,
      "metric": null
    }
  ],
  "candidates": [
    {
      "id": "topic-1",
      "title": "",
      "hook": "",
      "core_question": "",
      "angle": "",
      "why_now": "",
      "video_form": "mechanism_explainer",
      "source_signal_ids": [],
      "research_questions": [],
      "risk_notes": []
    }
  ],
  "selection": {
    "selected_id": null,
    "selection_reason": "",
    "requires_user_choice": true
  }
}
```

Use `source_kind` values `public` and `ai_daily`. `why_now` may refer to attention signals, but must not claim that the source title itself is true. `research_questions` identify claims that need independent verification before the script is written.

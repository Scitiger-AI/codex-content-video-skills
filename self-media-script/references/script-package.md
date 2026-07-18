# Script Package Contract

`script-package.json` is the machine-readable handoff. `script.md` contains only the spoken narration in chapter order.

```json
{
  "schema_version": 1,
  "topic": {
    "title": "",
    "angle": "",
    "audience": "",
    "source_brief_file": null
  },
  "narrative_strategy": {
    "pattern": "scenario-to-principle",
    "viewer_question": "",
    "selection_reason": "",
    "story_moves": [
      {"id": "opening-situation", "function": ""}
    ]
  },
  "research_boundary": {
    "source_scope": "",
    "uncertainties": [],
    "claims_to_avoid": []
  },
  "sources": [
    {"title": "", "publisher": "", "url": "", "published_at": null, "supports": []}
  ],
  "claims": [
    {"claim": "", "source_urls": [], "status": "verified"}
  ],
  "metadata": {"title": "", "cover_title": "", "description": "", "tags": []},
  "chapters": [
    {"id": "opening-situation", "title": "", "purpose": "", "narration": "", "visual_beat_ids": ["beat-1"]}
  ],
  "visual_beats": [
    {"id": "beat-1", "chapter_id": "opening-situation", "start_hint": "", "end_hint": "", "primary_visual": "", "secondary_visual": "", "on_screen_copy": [], "data_or_diagram": "", "caption_keepout": ""}
  ],
  "safety_notes": []
}
```

`narrative_strategy` records why this topic uses its chosen story pattern; it must not encode a global template. `claims[].status` must be `verified`, `uncertain`, or `opinion`. A `verified` claim requires at least one source URL. `visual_beats` must refer to existing chapter IDs and cover every chapter. Every beat requires both `primary_visual` and `secondary_visual`; use a diagram, chart, flow, comparison, counter, or object relation whenever the narration explains a mechanism, trade-off, process, or quantity.

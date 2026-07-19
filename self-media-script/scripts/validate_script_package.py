#!/usr/bin/env python3

import argparse
import json
from pathlib import Path
import sys


def fail(errors):
    print(json.dumps({"passed": False, "errors": errors}, ensure_ascii=False, indent=2))
    return 1


def main():
    parser = argparse.ArgumentParser(description="Validate a self-media script package.")
    parser.add_argument("--input", required=True, help="Path to script-package.json")
    args = parser.parse_args()
    path = Path(args.input)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return fail([f"missing file: {path}"])
    except json.JSONDecodeError as error:
        return fail([f"invalid JSON: {error}"])

    errors = []
    for field in ("schema_version", "topic", "narrative_strategy", "research_boundary", "sources", "claims", "metadata", "chapters", "visual_beats", "safety_notes"):
        if field not in value:
            errors.append(f"missing top-level field: {field}")
    strategy = value.get("narrative_strategy") if isinstance(value.get("narrative_strategy"), dict) else {}
    for field in ("pattern", "viewer_question", "selection_reason"):
        if not isinstance(strategy.get(field), str) or not strategy[field].strip():
            errors.append(f"narrative_strategy missing {field}")
    if not isinstance(strategy.get("story_moves"), list) or not strategy["story_moves"]:
        errors.append("narrative_strategy.story_moves must be a non-empty array")
    else:
        for index, move in enumerate(strategy["story_moves"]):
            if not isinstance(move, dict) or not str(move.get("id") or "").strip() or not str(move.get("function") or "").strip():
                errors.append(f"narrative_strategy.story_moves[{index}] must include id and function")
    review = value.get("editorial_review")
    if review is not None:
        if not isinstance(review, dict):
            errors.append("editorial_review must be an object")
        else:
            if not isinstance(review.get("viewer_promise"), str) or not review["viewer_promise"].strip():
                errors.append("editorial_review missing viewer_promise")
            if review.get("hook_independent_of_discovery") is not True:
                errors.append("editorial_review must confirm hook_independent_of_discovery")
            if review.get("ending_is_topic_specific") is not True:
                errors.append("editorial_review must confirm ending_is_topic_specific")
            for field in ("source_leakage_check", "attribution_check", "generic_closure_check"):
                if review.get(field) != "passed":
                    errors.append(f"editorial_review {field} must be passed")
    if not isinstance(value.get("chapters"), list) or not value.get("chapters"):
        errors.append("chapters must be a non-empty array")
    if not isinstance(value.get("visual_beats"), list) or not value.get("visual_beats"):
        errors.append("visual_beats must be a non-empty array")

    chapter_ids = set()
    narration_count = 0
    for index, chapter in enumerate(value.get("chapters", [])):
        chapter_id = chapter.get("id") if isinstance(chapter, dict) else None
        narration = chapter.get("narration") if isinstance(chapter, dict) else None
        if not chapter_id:
            errors.append(f"chapters[{index}] missing id")
        elif chapter_id in chapter_ids:
            errors.append(f"duplicate chapter id: {chapter_id}")
        else:
            chapter_ids.add(chapter_id)
        if not isinstance(narration, str) or not narration.strip():
            errors.append(f"chapters[{index}] missing narration")
        else:
            narration_count += len(narration.strip())
    if narration_count < 80:
        errors.append("combined narration is too short for a production script")

    beat_chapters = set()
    for index, beat in enumerate(value.get("visual_beats", [])):
        if not isinstance(beat, dict):
            errors.append(f"visual_beats[{index}] must be an object")
            continue
        for field in ("id", "chapter_id", "primary_visual", "secondary_visual"):
            if not beat.get(field):
                errors.append(f"visual_beats[{index}] missing {field}")
        chapter_id = beat.get("chapter_id")
        if chapter_id:
            beat_chapters.add(chapter_id)
            if chapter_id not in chapter_ids:
                errors.append(f"visual_beats[{index}] references unknown chapter: {chapter_id}")
    for chapter_id in chapter_ids - beat_chapters:
        errors.append(f"chapter has no visual beat: {chapter_id}")

    for index, claim in enumerate(value.get("claims", [])):
        if not isinstance(claim, dict):
            errors.append(f"claims[{index}] must be an object")
            continue
        status = claim.get("status")
        if status not in {"verified", "uncertain", "opinion"}:
            errors.append(f"claims[{index}] has invalid status")
        if status == "verified" and not claim.get("source_urls"):
            errors.append(f"verified claim has no source URL: claims[{index}]")

    if errors:
        return fail(errors)
    print(json.dumps({"passed": True, "narrative_pattern": strategy["pattern"], "chapters": len(chapter_ids), "visual_beats": len(value["visual_beats"]), "narration_characters": narration_count}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

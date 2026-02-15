"""
Apply selected story image selections to PersonaHistoryStart.

Supported payload formats:
1) Round 1 (flat):
   {
     "story_id": "https://imagedelivery.net/.../public"
   }

2) Round 2 (with prompt):
   {
     "story_id": {
       "new_prompt": "...",
       "new_image_url": "https://imagedelivery.net/.../public"
     }
   }

Usage:
    python scripts/apply_story_image_selections.py \
      --file scripts/story_selected_round1.json
"""
import argparse
import json
import os
import sys
from uuid import UUID

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.settings import load_configs

load_configs()


def _normalize_cf_url(url: str) -> str:
    if url.endswith("/admin"):
        return url[:-6] + "/public"
    return url


def _parse_selection(raw_value: object) -> tuple[str | None, str | None, str | None]:
    """Return (image_url, image_prompt_or_none, error_or_none)."""
    if isinstance(raw_value, str):
        image_url = raw_value.strip()
        if not image_url:
            return None, None, "empty image URL"
        return _normalize_cf_url(image_url), None, None

    if isinstance(raw_value, dict):
        image_url = str(raw_value.get("new_image_url") or raw_value.get("image_url") or "").strip()
        if not image_url:
            return None, None, "missing new_image_url"

        has_prompt = "new_prompt" in raw_value or "image_prompt" in raw_value
        if has_prompt:
            prompt = raw_value.get("new_prompt", raw_value.get("image_prompt"))
            prompt = "" if prompt is None else str(prompt).strip()
        else:
            prompt = None

        return _normalize_cf_url(image_url), prompt, None

    return None, None, f"unsupported value type: {type(raw_value).__name__}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply selected story image/prompt selections to DB")
    parser.add_argument(
        "--file",
        default=os.path.join(os.path.dirname(__file__), "story_selected_round1.json"),
        help="Path to JSON mapping (round1 or round2 payload)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print changes but do not commit",
    )
    args = parser.parse_args()

    from app.db.base import get_db
    from app.db.models import PersonaHistoryStart

    with open(args.file, "r", encoding="utf-8") as f:
        payload = json.load(f)

    if not isinstance(payload, dict):
        raise ValueError("Selection file must be a JSON object keyed by story_id")

    total = len(payload)
    updated = 0
    updated_prompts = 0
    unchanged = 0
    missing = []
    invalid_ids = []
    invalid_payload = []

    print(f"Applying {total} story image selections...")

    with get_db() as db:
        for story_id, raw_value in payload.items():
            try:
                story_uuid = UUID(story_id)
            except Exception:
                invalid_ids.append(story_id)
                continue

            image_url, new_prompt, parse_error = _parse_selection(raw_value)
            if parse_error:
                invalid_payload.append((story_id, parse_error))
                continue

            story = (
                db.query(PersonaHistoryStart)
                .filter(PersonaHistoryStart.id == story_uuid)
                .first()
            )
            if not story:
                missing.append(story_id)
                continue

            old_url = story.image_url
            old_prompt = story.image_prompt

            changed = False
            if old_url != image_url:
                story.image_url = image_url
                changed = True

            prompt_changed = False
            if new_prompt is not None and old_prompt != new_prompt:
                story.image_prompt = new_prompt
                changed = True
                prompt_changed = True

            if not changed:
                unchanged += 1
                print(f"  - {story_id} | {story.name or 'Untitled'} (no changes)")
                continue

            updated += 1
            if prompt_changed:
                updated_prompts += 1

            print(f"  ✓ {story_id} | {story.name or 'Untitled'}")
            print(f"    old: {old_url}")
            print(f"    new: {image_url}")
            if prompt_changed:
                print(f"    old prompt: {old_prompt}")
                print(f"    new prompt: {new_prompt}")

        if args.dry_run:
            db.rollback()
            print("\nDRY RUN: rolled back, no DB changes committed.")
        else:
            db.commit()
            print("\nCommitted DB changes.")

    print("\nSummary")
    print(f"  total input: {total}")
    print(f"  updated stories: {updated}")
    print(f"  updated prompts: {updated_prompts}")
    print(f"  unchanged stories: {unchanged}")
    print(f"  missing stories: {len(missing)}")
    print(f"  invalid IDs: {len(invalid_ids)}")
    print(f"  invalid payload entries: {len(invalid_payload)}")

    if missing:
        print("  missing IDs:")
        for item in missing:
            print(f"    - {item}")

    if invalid_ids:
        print("  invalid IDs:")
        for item in invalid_ids:
            print(f"    - {item}")

    if invalid_payload:
        print("  invalid payload entries:")
        for story_id, reason in invalid_payload:
            print(f"    - {story_id}: {reason}")


if __name__ == "__main__":
    main()

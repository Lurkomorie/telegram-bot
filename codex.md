# Codex Memory

Last updated: 2026-02-15

## Core Architecture Notes
- Image generation flow for chat responses:
  - `app/core/brains/image_prompt_engineer.py` (`generate_image_plan`) generates Illustrious SDXL danbooru tags.
  - `assemble_final_prompt` appends persona DNA (`persona.image_prompt`) and `image.quality_prompt`.
  - Resulting positive/negative prompts are sent to Runpod through `app/core/img_runpod.py`.
- Prompt templates are centralized in `config/prompts.py` and loaded via `app/core/prompt_service.py`.
- Runtime base quality/negative strings come from `config/app.yaml` (`image.quality_prompt`, `image.negative_prompt`).

## Decisions From This Task
- Framing policy: strict POV close-up by default (`pov` + `close-up` always enforced).
- Visual intent source: combined user request + AI visual actions.
- Continuity: preserve clothing/location unless explicit change is detected in current turn.
- Tag quality strategy: curated local normalization/enforcement (no runtime Danbooru API calls).
- Enforced forbidden tags: `1boy`, `male_focus`, and far-framing tags (`full_body`, `wide_shot`, `long_shot`, `multiple_views`).
- Canonical alias normalization currently includes:
  - `soft_smile -> light_smile`
  - `flushed -> blush`

## Known Pitfalls + Fixes
- Pitfall: direct user visual requests (for example feet focus) were not included in image context.
  - Fix: context now includes `CURRENT USER VISUAL REQUEST` and `MANDATORY FOCUS TAGS`.
- Pitfall: previous image prompt was passed as raw broad context, causing stale framing/action bleed.
  - Fix: only continuity anchors are extracted from previous prompt (`SCENE LOCK`: clothing/environment).
- Pitfall: model output could include inconsistent or forbidden tags.
  - Fix: deterministic `_enforce_tag_policy` now canonicalizes, removes forbidden tags, ensures one rating, enforces core tags, reorders categories, and bounds total tag count.

## Tests Added
- `app/tests/test_image_prompt_engineer.py` covers:
  - feet focus enforcement,
  - far-framing tag removal,
  - scene-lock continuity,
  - male-body tag stripping,
  - alias normalization,
  - single rating + required core tags,
  - max tag bound enforcement.

## Maintenance Rule
- At start of each new request, read this file first.
- If any point is outdated, update or remove it immediately.

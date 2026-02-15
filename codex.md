# Codex Memory

Last updated: 2026-02-15 (regression fixes + rating-tag removal)

## Core Architecture Notes
- Image generation flow for chat responses:
  - `app/core/brains/image_prompt_engineer.py` (`generate_image_plan`) generates Illustrious SDXL danbooru tags.
  - `assemble_final_prompt` appends persona DNA (`persona.image_prompt`) and `image.quality_prompt`.
  - Resulting positive/negative prompts are sent to Runpod through `app/core/img_runpod.py`.
- Prompt templates are centralized in `config/prompts.py` and loaded via `app/core/prompt_service.py`.
- Runtime base quality/negative strings come from `config/app.yaml` (`image.quality_prompt`, `image.negative_prompt`).

## Decisions From This Task
- Framing policy: strict POV close-up by default (`pov` + `close-up` always enforced).
- Visual truth policy: AI visual actions are authoritative when they conflict with user request (refusal/deflection turns).
- Continuity: preserve clothing/location unless explicit change is detected in current turn.
- Tag quality strategy: curated local normalization/enforcement (no runtime Danbooru API calls).
- Enforced forbidden tags: `1boy`, `male_focus`, and far-framing tags (`full_body`, `wide_shot`, `long_shot`, `multiple_views`).
- Remove all `rating:*` tags from generated prompt tags (LLM output and deterministic post-process strip them).
- Canonical alias normalization currently includes:
  - `soft_smile -> light_smile`
  - `flushed -> blush`
- Scene lock is source-aware:
  - Disabled for previous image source `history_start`, `ai_initial_story`, and `gift_purchase`.
  - Enabled for regular message-response continuity.
- Gift visual override is one-shot:
  - Forced only for immediate gift reaction image.
  - Not auto-persisted to subsequent unrelated turns.
- Eye fidelity booster:
  - `_enforce_tag_policy` now injects `eye_focus` (+ eye direction when missing) for normal portrait turns.
  - Skips eye-force when `closed_eyes` is intentional or when heavy non-face body focus is requested.
- Product positioning preference:
  - Keep explicit 18+ NSFW danbooru tag examples/guidance in `IMAGE_TAG_GENERATOR_GPT` (no tone-down for minor-safe style).

## Known Pitfalls + Fixes
- Pitfall: direct user visual requests (for example feet focus) were not included in image context.
  - Fix: context now includes `CURRENT USER VISUAL REQUEST` and `MANDATORY FOCUS TAGS`.
- Pitfall: previous image prompt was passed as raw broad context, causing stale framing/action bleed.
  - Fix: only continuity anchors are extracted from previous prompt (`SCENE LOCK`: clothing/environment).
- Pitfall: scene lock forced from starter images (history/start/gift) caused first post-story drift.
  - Fix: source-aware scene lock gate + fallback-only anchor injection.
- Pitfall: gift visuals persisted for multiple messages/images.
  - Fix: removed implicit multi-message gift override; explicit forced override only on gift reaction image.
- Pitfall: images could show requested explicit act even when AI response deflected/refused.
  - Fix: refusal detector suppresses request-derived focus tags and enforces AI-action truth.
- Pitfall: eyes can appear mashed/blurry even with close-up framing.
  - Fix: deterministic eye quality boost in final tag policy + stronger base quality/negative eye prompts.
- Pitfall: model output could include inconsistent, forbidden, or unwanted rating tags.
  - Fix: deterministic `_enforce_tag_policy` now canonicalizes, removes forbidden tags and all `rating:*` tags, enforces core tags, reorders categories, and bounds total tag count.

## Tests Added
- `app/tests/test_image_prompt_engineer.py` covers:
  - feet focus enforcement,
  - far-framing tag removal,
  - scene-lock continuity,
  - male-body tag stripping,
  - alias normalization,
  - no `rating:*` output + required core tags,
  - max tag bound enforcement.

## Maintenance Rule
- At start of each new request, read this file first.
- If any point is outdated, update or remove it immediately.

"""
Brain 3: Image Prompt Engineer
Generates IllustriousXL-format image prompts from conversation context
"""
import asyncio
import re
from typing import Dict, Tuple, List, Optional, Any
from app.core.prompt_service import PromptService
from app.core.llm_openrouter import generate_text
from app.settings import get_app_config
from app.core.constants import IMAGE_ENGINEER_MAX_RETRIES, IMAGE_ENGINEER_BASE_DELAY
from app.core.logging_utils import log_messages_array, log_dev_request, log_dev_response, log_dev_context_breakdown, is_development
import time

REQUIRED_CORE_TAGS: List[str] = ["1girl", "solo", "pov", "close-up"]

FORBIDDEN_TAGS = {
    "1boy",
    "male_focus",
    "full_body",
    "wide_shot",
    "long_shot",
    "multiple_views",
}

TAG_ALIAS_MAP = {
    "soft_smile": "light_smile",
    "flushed": "blush",
    "close_up": "close-up",
}

FULL_BODY_FRAMING_TRIGGER_TAGS = {"shibari"}
FULL_BODY_CONFLICT_FRAMING_TAGS = {"pov", "close-up", "upper_body", "cowboy_shot", "portrait", "male_pov"}

PERSON_TAGS = {"1girl", "solo"}
FRAMING_TAGS = {"pov", "close-up", "upper_body", "cowboy_shot", "portrait", "male_pov", "from_behind", "from_below"}
CLOTHING_TAGS = {
    "dress", "sundress", "shirt", "blouse", "skirt", "jeans", "shorts", "bikini",
    "lingerie", "bra", "panties", "negligee", "nude", "barefoot", "heels",
    "pantyhose", "stockings", "thighhighs", "swimsuit", "underwear", "robe",
    "jacket", "sweater", "coat", "kimono", "apron", "bodysuit",
}
EXPRESSION_TAGS = {
    "smile", "light_smile", "slight_smile", "smirk", "grin", "blush", "parted_lips",
    "half-closed_eyes", "closed_eyes", "open_mouth", "looking_at_viewer", "looking_away",
    "looking_down", "looking_back", "eye_contact", "shy", ";)", ":d",
}
ENVIRONMENT_TAGS = {
    "indoors", "outdoors", "bedroom", "kitchen", "cafe", "beach", "park", "window",
    "couch", "bed", "chair", "table", "night", "sunset", "sunlight", "lamp", "candle",
    "bathroom", "shower", "office", "car",
}
EFFECT_TAGS = {"depth_of_field", "blurry_background", "lens_flare", "bloom", "rim_lighting", "backlighting"}
DEFAULT_FILLER_TAGS = ["upper_body", "looking_at_viewer", "blush", "parted_lips", "depth_of_field", "blurry_background"]
EYE_DIRECTION_TAGS = {"looking_at_viewer", "eye_contact", "looking_away", "looking_down", "looking_back"}
HEAVY_BODY_FOCUS_TAGS = {"foot_focus", "feet", "ass_focus", "breast_focus", "hand_focus"}
SCENE_LOCK_CLOTHING_TAGS = CLOTHING_TAGS | {"cleavage"}
SCENE_LOCK_ENV_TAGS = ENVIRONMENT_TAGS | EFFECT_TAGS
NO_SCENE_LOCK_SOURCES = {"history_start", "ai_initial_story", "gift_purchase"}
FORCED_GIFT_SCENE_TAGS = (
    FRAMING_TAGS
    | CLOTHING_TAGS
    | ENVIRONMENT_TAGS
    | EFFECT_TAGS
    | {"on_bed", "bedroom", "indoors", "outdoors", "window", "couch", "bed", "chair", "table"}
)

LOCATION_CHANGE_MARKERS = (
    "go to", "went to", "arrive", "arrived", "enter", "entered",
    "leave", "left", "move to", "walk to", "drive to",
)
CLOTHING_CHANGE_MARKERS = (
    "take off", "remove", "undress", "strip", "put on", "wear", "change clothes",
    "changed clothes", "dress up", "naked now",
)

REFUSAL_MARKERS = [
    # English
    "i won't",
    "i will not",
    "i can't",
    "cannot",
    "not in public",
    "too rough",
    "not like that",
    "only if",
    "catch me first",
    "i pull back",
    "i recoil",
    "i step back",
    # Russian
    "не буду",
    "не хочу",
    "не могу",
    "не публич",
    "только если",
    "сначала поймай",
    "слишком грубо",
    "отшатываюсь",
    "отступаю",
    "резко отшатываюсь",
]

GIFT_USAGE_RULES = {
    "dildo": {
        "required_tags": ["masturbation", "pussy"],
        "forbidden_tags": {"oral", "fellatio", "cunnilingus", "licking", "dildo_in_mouth"},
        "context_rule": "If dildo gift is forced, depict active genital use (masturbation/pussy focus), never oral/licking use.",
    },
    "anal_plug": {
        "required_tags": ["anal_object_insertion"],
        "forbidden_tags": {"oral", "fellatio", "cunnilingus", "licking"},
        "context_rule": "If anal plug gift is forced, depict anal insertion use, never oral/licking use.",
    },
    # Legacy key aliases for old purchase history rows.
    "vibrator": {
        "required_tags": ["masturbation", "pussy"],
        "forbidden_tags": {"oral", "fellatio", "cunnilingus", "licking", "vibrator_in_mouth"},
        "context_rule": "If vibrator gift is forced, depict active genital use (masturbation/pussy focus), never oral/licking use.",
    },
    "anal_beads": {
        "required_tags": ["anal_object_insertion"],
        "forbidden_tags": {"oral", "fellatio", "cunnilingus", "licking"},
        "context_rule": "If anal beads gift is forced, depict anal insertion use, never oral/licking use.",
    },
}


def _split_tags(tags_text: str) -> List[str]:
    return [tag.strip() for tag in tags_text.split(",") if tag.strip()]


def _canonicalize_tag(tag: str) -> str:
    """Normalize a single tag into a stable danbooru-style token."""
    t = tag.strip().lower()
    t = re.sub(r'^`+|`+$', '', t)
    t = re.sub(r"^['\"]+|['\"]+$", "", t)
    t = re.sub(r'^<[^>]+>$', '', t)
    weighted = re.match(r'^\(([^:()]+):[\d.]+\)$', t)
    if weighted:
        t = weighted.group(1)
    t = re.sub(r"\s+", "_", t)
    t = TAG_ALIAS_MAP.get(t, t)
    return t


def _is_forbidden_tag(tag: str, allow_full_body: bool = False) -> bool:
    if tag not in FORBIDDEN_TAGS:
        return False
    return not (allow_full_body and tag == "full_body")


def _should_force_full_body_framing(
    raw_tags: str,
    mandatory_focus_tags: Optional[List[str]] = None,
    forced_gift_tags: Optional[List[str]] = None,
) -> bool:
    """Use full-body framing for scenarios that semantically require body visibility."""
    candidates = _split_tags(raw_tags or "") + (mandatory_focus_tags or []) + (forced_gift_tags or [])
    for raw_tag in candidates:
        tag = _canonicalize_tag(raw_tag)
        if tag in FULL_BODY_FRAMING_TRIGGER_TAGS:
            return True
    return False


def _detect_scene_change_intent(user_message: str, visual_actions: str) -> Dict[str, bool]:
    text = f"{user_message or ''} {visual_actions or ''}".lower()
    return {
        "location_changed": any(marker in text for marker in LOCATION_CHANGE_MARKERS),
        "clothing_changed": any(marker in text for marker in CLOTHING_CHANGE_MARKERS),
    }


def _should_use_scene_lock(previous_image_meta: Optional[Dict[str, Any]]) -> bool:
    """
    Decide if previous-image anchors are safe to use for continuity.
    Disabled for non-conversational starter/special images.
    """
    if not previous_image_meta:
        return True  # Legacy rows and unknowns default to continuity on.

    meta = previous_image_meta
    if isinstance(meta.get("ext"), dict):
        meta = meta["ext"]

    source = (meta.get("source") or "").strip().lower()
    if source in NO_SCENE_LOCK_SOURCES:
        return False
    if meta.get("is_gift_purchase") is True:
        return False
    return True


def _detect_refusal_or_deflection(dialogue_response: str) -> bool:
    """Detect turns where AI behavior should override explicit user visual request."""
    if not dialogue_response:
        return False
    text = dialogue_response.lower()
    return any(marker in text for marker in REFUSAL_MARKERS)


def _extract_scene_lock_anchors(previous_image_prompt: Optional[str]) -> Dict[str, List[str]]:
    """Extract only continuity-relevant clothing/environment tags from previous prompt."""
    anchors: Dict[str, List[str]] = {"clothing": [], "environment": []}
    if not previous_image_prompt:
        return anchors

    for raw_tag in _split_tags(previous_image_prompt):
        tag = _canonicalize_tag(raw_tag)
        if not tag:
            continue
        if tag in SCENE_LOCK_CLOTHING_TAGS and tag not in anchors["clothing"]:
            anchors["clothing"].append(tag)
        if (
            tag in SCENE_LOCK_ENV_TAGS
            or tag.endswith("_lighting")
            or tag in {"night", "sunset", "sunlight"}
        ) and tag not in anchors["environment"]:
            anchors["environment"].append(tag)

    return anchors


def _sanitize_forced_gift_tags(forced_gift_tags: str, allow_scene_override: bool = False) -> str:
    """
    Keep gift override focused on object/action by default.
    Scene or outfit overrides are stripped unless explicitly allowed.
    """
    cleaned: List[str] = []
    seen = set()
    full_body_mode = _should_force_full_body_framing(forced_gift_tags)
    for raw_tag in _split_tags(forced_gift_tags or ""):
        tag = _canonicalize_tag(raw_tag)
        if not tag or _is_forbidden_tag(tag, allow_full_body=full_body_mode):
            continue
        if not allow_scene_override and tag in FORCED_GIFT_SCENE_TAGS:
            continue
        if tag not in seen:
            seen.add(tag)
            cleaned.append(tag)
    return ", ".join(cleaned)


def _derive_gift_usage_constraints(forced_gift_tags: Optional[List[str]]) -> Tuple[List[str], set[str], List[str]]:
    """Derive deterministic gift usage requirements and conflicting tags to suppress."""
    normalized: List[str] = []
    seen = set()
    for raw_tag in forced_gift_tags or []:
        norm = _canonicalize_tag(raw_tag)
        if not norm or norm in seen:
            continue
        seen.add(norm)
        normalized.append(norm)

    normalized_set = set(normalized)
    required_tags: List[str] = []
    forbidden_tags: set[str] = set()
    context_rules: List[str] = []

    for trigger_tag, rule in GIFT_USAGE_RULES.items():
        if trigger_tag not in normalized_set:
            continue

        for tag in rule.get("required_tags", []):
            norm = _canonicalize_tag(tag)
            if norm and norm not in required_tags:
                required_tags.append(norm)

        for tag in rule.get("forbidden_tags", set()):
            norm = _canonicalize_tag(tag)
            if norm:
                forbidden_tags.add(norm)

        context_rule = (rule.get("context_rule") or "").strip()
        if context_rule:
            context_rules.append(context_rule)

    return required_tags, forbidden_tags, context_rules


def _bucket_for_tag(tag: str) -> str:
    if tag in PERSON_TAGS:
        return "person"
    if tag in FRAMING_TAGS:
        return "framing"
    if tag in CLOTHING_TAGS:
        return "clothing"
    if tag in EXPRESSION_TAGS:
        return "expression"
    if tag in ENVIRONMENT_TAGS or tag.endswith("_lighting"):
        return "environment"
    if tag in EFFECT_TAGS:
        return "effects"
    return "action"


def _enforce_tag_policy(
    raw_tags: str,
    mandatory_focus_tags: Optional[List[str]] = None,
    scene_lock: Optional[Dict[str, List[str]]] = None,
    preserve_scene_lock_clothing: bool = True,
    preserve_scene_lock_environment: bool = True,
    forced_gift_tags: Optional[List[str]] = None,
) -> str:
    """Deterministic post-processing: canonicalize, enforce, reorder, and bound output size."""
    mandatory_focus_tags = mandatory_focus_tags or []
    forced_gift_tags = forced_gift_tags or []
    scene_lock = scene_lock or {"clothing": [], "environment": []}
    full_body_mode = _should_force_full_body_framing(
        raw_tags,
        mandatory_focus_tags=mandatory_focus_tags,
        forced_gift_tags=forced_gift_tags,
    )
    required_core_tags = ["1girl", "solo", "full_body"] if full_body_mode else REQUIRED_CORE_TAGS

    cleaned_tags: List[str] = []
    seen = set()

    for raw_tag in _split_tags(raw_tags):
        tag = _canonicalize_tag(raw_tag)
        if not tag or _is_forbidden_tag(tag, allow_full_body=full_body_mode):
            continue
        if tag.startswith("rating:"):
            continue
        if tag not in seen:
            seen.add(tag)
            cleaned_tags.append(tag)

    for tag in required_core_tags:
        norm = _canonicalize_tag(tag)
        if norm not in seen:
            seen.add(norm)
            cleaned_tags.append(norm)

    normalized_forced_gift = []
    for tag in forced_gift_tags:
        norm = _canonicalize_tag(tag)
        if not norm or _is_forbidden_tag(norm, allow_full_body=full_body_mode):
            continue
        if norm not in normalized_forced_gift:
            normalized_forced_gift.append(norm)
        if norm not in seen:
            seen.add(norm)
            cleaned_tags.append(norm)

    required_gift_usage_tags, forbidden_gift_usage_tags, _ = _derive_gift_usage_constraints(normalized_forced_gift)
    for tag in required_gift_usage_tags:
        if _is_forbidden_tag(tag, allow_full_body=full_body_mode):
            continue
        if tag not in seen:
            seen.add(tag)
            cleaned_tags.append(tag)

    normalized_mandatory_focus = []
    for tag in mandatory_focus_tags:
        norm = _canonicalize_tag(tag)
        if not norm or _is_forbidden_tag(norm, allow_full_body=full_body_mode):
            continue
        normalized_mandatory_focus.append(norm)
        if norm not in seen:
            seen.add(norm)
            cleaned_tags.append(norm)

    if forbidden_gift_usage_tags:
        cleaned_tags = [tag for tag in cleaned_tags if tag not in forbidden_gift_usage_tags]
        normalized_mandatory_focus = [tag for tag in normalized_mandatory_focus if tag not in forbidden_gift_usage_tags]
        normalized_forced_gift = [tag for tag in normalized_forced_gift if tag not in forbidden_gift_usage_tags]

    buckets = {
        "person": [],
        "framing": [],
        "action": [],
        "clothing": [],
        "expression": [],
        "environment": [],
        "effects": [],
    }

    for tag in cleaned_tags:
        bucket = _bucket_for_tag(tag)
        if tag not in buckets[bucket]:
            buckets[bucket].append(tag)

    for required in ["1girl", "solo"]:
        if required not in buckets["person"]:
            buckets["person"].insert(0, required)

    if full_body_mode:
        buckets["framing"] = [
            tag
            for tag in buckets["framing"]
            if tag not in FULL_BODY_CONFLICT_FRAMING_TAGS
        ]
        if "full_body" not in buckets["framing"]:
            buckets["framing"].insert(0, "full_body")
    else:
        for required in ["pov", "close-up"]:
            if required not in buckets["framing"]:
                buckets["framing"].insert(0, required)

    for focus_tag in normalized_mandatory_focus:
        if focus_tag not in buckets["action"] and focus_tag not in buckets["expression"]:
            buckets["action"].insert(0, focus_tag)

    gift_priority_tags: List[str] = []
    for gift_tag in normalized_forced_gift + required_gift_usage_tags:
        if gift_tag in forbidden_gift_usage_tags or gift_tag in gift_priority_tags:
            continue
        gift_priority_tags.append(gift_tag)

    for gift_tag in reversed(gift_priority_tags):
        if gift_tag not in buckets["action"] and gift_tag not in buckets["expression"]:
            buckets["action"].insert(0, gift_tag)

    # Eye detail booster: keeps eyes sharper in typical close-up portraits.
    # Skip when eyes are intentionally closed or turn is dominated by non-face body focus.
    has_closed_eyes = "closed_eyes" in buckets["expression"]
    has_heavy_body_focus = any(tag in HEAVY_BODY_FOCUS_TAGS for tag in buckets["action"])
    if not has_closed_eyes and not has_heavy_body_focus:
        if "eye_focus" not in buckets["action"]:
            buckets["action"].append("eye_focus")
        if not any(tag in EYE_DIRECTION_TAGS for tag in buckets["expression"]):
            buckets["expression"].append("looking_at_viewer")

    # Scene lock should act as fallback only (never hard-override current turn).
    if preserve_scene_lock_clothing and not buckets["clothing"]:
        for tag in scene_lock.get("clothing", []):
            norm = _canonicalize_tag(tag)
            if norm and norm not in buckets["clothing"]:
                buckets["clothing"].append(norm)

    if preserve_scene_lock_environment and not buckets["environment"]:
        for tag in scene_lock.get("environment", []):
            norm = _canonicalize_tag(tag)
            if norm and norm not in buckets["environment"]:
                buckets["environment"].append(norm)

    ordered_tags = (
        buckets["person"]
        + buckets["framing"]
        + buckets["action"]
        + buckets["clothing"]
        + buckets["expression"]
        + buckets["environment"]
        + buckets["effects"]
    )

    deduped_ordered: List[str] = []
    deduped_seen = set()
    for tag in ordered_tags:
        if tag not in deduped_seen and not _is_forbidden_tag(tag, allow_full_body=full_body_mode):
            deduped_seen.add(tag)
            deduped_ordered.append(tag)

    essential_tags = set(required_core_tags + normalized_mandatory_focus + gift_priority_tags)
    if forbidden_gift_usage_tags:
        essential_tags = {tag for tag in essential_tags if tag not in forbidden_gift_usage_tags}
    trimmed: List[str] = []
    for tag in deduped_ordered:
        if tag in essential_tags and tag not in trimmed:
            trimmed.append(tag)

    for tag in deduped_ordered:
        if tag in trimmed:
            continue
        if len(trimmed) >= 24:
            break
        trimmed.append(tag)

    filler_tags = [tag for tag in DEFAULT_FILLER_TAGS if not (full_body_mode and tag == "upper_body")]
    for filler in filler_tags:
        if len(trimmed) >= 14:
            break
        if filler not in trimmed and not _is_forbidden_tag(filler, allow_full_body=full_body_mode):
            trimmed.append(filler)

    return ", ".join(trimmed[:24])


def _parse_state(state: str) -> dict:
    """Parse pipe-separated state string into a dict of visual fields."""
    fields = {}
    if not state:
        return fields
    for pair in state.split("|"):
        pair = pair.strip()
        match = re.match(r'(\w+)="(.*?)"', pair)
        if match:
            fields[match.group(1)] = match.group(2)
        else:
            # Handle boolean fields like terminateDialog=false
            match_bool = re.match(r'(\w+)=(true|false)', pair)
            if match_bool:
                fields[match_bool.group(1)] = match_bool.group(2)
    return fields


def _extract_visual_actions(dialogue_response: str) -> str:
    """Extract visual/physical actions from dialogue, stripping speech.
    
    Dialogue uses _italics_ for actions and *bold* for speech.
    We extract the action parts for clearer visual context.
    """
    if not dialogue_response:
        return ""
    
    # Remove *bold speech* content but keep _italic actions_
    # First, extract italic actions
    actions = re.findall(r'_([^_]+)_', dialogue_response)
    
    if actions:
        return " ".join(actions)
    
    # Fallback: strip bold speech and return remaining text
    stripped = re.sub(r'\*[^*]+\*', '', dialogue_response)
    stripped = stripped.strip()
    if stripped:
        return stripped
    
    # Last resort: return original
    return dialogue_response


def _build_image_context(
    state: str,
    dialogue_response: str,
    user_message: str,
    persona: dict,
    chat_history: list[dict],
    previous_image_prompt: str = None,
    previous_image_meta: Optional[Dict[str, Any]] = None,
    context_summary: str = None,
    mood: int = 50,
    purchases: list[dict] = None,
    force_gift_override: bool = False,
    forced_gift_tags: str = "",
    allow_scene_override: bool = False,
    mandatory_focus_tags: Optional[List[str]] = None,
    control_orb_active: bool = False,
    control_orb_messages_left: int = 0,
) -> Tuple[str, List[str], Dict[str, List[str]], Dict[str, bool], Dict[str, Any]]:
    """Build structured context for image prompt generation.
    
    Parses state into labeled fields and extracts visual actions from dialogue
    so the image tag LLM gets clear, structured input instead of raw text.
    """
    # Parse state into structured fields
    state_fields = _parse_state(state)
    location = state_fields.get("location", "")
    clothing = state_fields.get("aiClothing", "")
    description = state_fields.get("description", "")
    emotions = state_fields.get("emotions", "")
    mood_notes = state_fields.get("moodNotes", "")
    
    # Extract visual actions and intent
    visual_actions = _extract_visual_actions(dialogue_response)
    refusal_detected = _detect_refusal_or_deflection(dialogue_response)
    if control_orb_active:
        # Control Orb turns are hard-compliance turns.
        refusal_detected = False

    normalized_focus_tags: List[str] = []
    seen_focus_tags = set()
    for raw_tag in mandatory_focus_tags or []:
        norm = _canonicalize_tag(raw_tag)
        if not norm or norm in FORBIDDEN_TAGS or norm.startswith("rating:"):
            continue
        if norm not in seen_focus_tags:
            seen_focus_tags.add(norm)
            normalized_focus_tags.append(norm)
    mandatory_focus_tags = normalized_focus_tags

    if refusal_detected:
        # AI actions are authoritative on refusal/deflection turns.
        mandatory_focus_tags = []
    scene_change_flags = _detect_scene_change_intent(user_message, visual_actions)
    scene_lock_enabled = _should_use_scene_lock(previous_image_meta)
    scene_lock = _extract_scene_lock_anchors(previous_image_prompt) if scene_lock_enabled else {"clothing": [], "environment": []}
    
    # Build gift override section (top priority)
    gift_section = ""
    gift_override_mode = "off"
    sanitized_forced_tags = _sanitize_forced_gift_tags(
        forced_gift_tags,
        allow_scene_override=allow_scene_override,
    )
    _, _, gift_usage_rules = _derive_gift_usage_constraints(_split_tags(sanitized_forced_tags))
    if force_gift_override and sanitized_forced_tags.strip():
        gift_override_mode = "forced"
        forced_gift_name = purchases[0].get("item_name", "gift") if purchases else "gift"
        gift_section = f"""
# GIFT OVERRIDE (MANDATORY — top priority)
Gift: {forced_gift_name}
Required tags: {sanitized_forced_tags}
"""
    gift_usage_section = ""
    if gift_override_mode == "forced" and gift_usage_rules:
        gift_usage_section = "# GIFT USAGE CONSTRAINTS (MANDATORY)\n" + "\n".join(
            f"- {rule}" for rule in gift_usage_rules
        ) + "\n\n"
    
    # Build mood hint
    mood_hint = ""
    if mood >= 70:
        mood_hint = "\n# MOOD: Character is happy — use smile or warm expression tags"

    action_truth_section = f"""
# ACTION TRUTH POLICY
AI actions authoritative this turn: {"yes" if refusal_detected else "no"}
Refusal/deflection detected: {"yes" if refusal_detected else "no"}
If refusal is detected, depict hesitation/recoil/distance from AI actions, not explicit user request.
"""

    control_orb_section = f"""
# CONTROL ORB STATUS
Active: {"yes" if control_orb_active else "no"}
Turns left: {max(0, int(control_orb_messages_left or 0))}
If active, the character is under magical mind control and must comply with the user's visual command.
"""

    scene_lock_section = f"""
# SCENE LOCK (maintain continuity unless explicitly changed this turn)
Scene lock enabled: {"yes" if scene_lock_enabled else "no"}
Clothing anchors: {", ".join(scene_lock.get("clothing", [])[:6]) or "none"}
Environment anchors: {", ".join(scene_lock.get("environment", [])[:6]) or "none"}
Explicit clothing change detected: {"yes" if scene_change_flags["clothing_changed"] else "no"}
Explicit location change detected: {"yes" if scene_change_flags["location_changed"] else "no"}
"""
    
    context = f"""{gift_section}{gift_usage_section}# CURRENT USER VISUAL REQUEST
{user_message or "not specified"}

# AI VISUAL ACTIONS (primary source for pose/action tags)
{visual_actions or "not specified"}

# MANDATORY FOCUS TAGS (must appear when present)
{", ".join(mandatory_focus_tags) if mandatory_focus_tags else "none"}

# LOCATION
{location or "not specified"}

# CLOTHING
{clothing or "not specified"}

# DESCRIPTION
{description or "not specified"}

# EMOTIONS
{emotions or "neutral"}

# ATMOSPHERE
{mood_notes or "not specified"}
{action_truth_section}{control_orb_section}{scene_lock_section}{mood_hint}"""
    
    observability = {
        "previous_image_source": (previous_image_meta or {}).get("source") if isinstance(previous_image_meta, dict) else "unknown",
        "scene_lock_enabled": scene_lock_enabled,
        "gift_override_mode": gift_override_mode,
        "refusal_detected": refusal_detected,
        "mandatory_focus_tags": mandatory_focus_tags,
        "gift_override_allow_scene": allow_scene_override,
        "gift_override_tags": sanitized_forced_tags,
        "gift_usage_constraints": gift_usage_rules,
        "control_orb_active": control_orb_active,
        "control_orb_messages_left": max(0, int(control_orb_messages_left or 0)),
    }

    return context, mandatory_focus_tags, scene_lock, scene_change_flags, observability


def _sanitize_tags(raw_output: str) -> str:
    """Clean LLM output to ensure only comma-separated danbooru tags remain."""
    text = raw_output.strip()
    
    # Strip code fences
    text = re.sub(r'```[\w]*\n?', '', text)
    text = text.replace('```', '')
    
    # If multi-line, take only the longest line (likely the tags)
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    if len(lines) > 1:
        # Pick the line with the most commas (most likely the tag line)
        text = max(lines, key=lambda l: l.count(','))
    elif lines:
        text = lines[0]
    
    # Remove common LLM prefixes
    prefixes_to_strip = [
        "Here are the tags:", "Tags:", "Output:", "Prompt:",
        "Here is the prompt:", "Image tags:", "Generated tags:",
    ]
    for prefix in prefixes_to_strip:
        if text.lower().startswith(prefix.lower()):
            text = text[len(prefix):].strip()
    
    # Clean individual tags
    tags = [t.strip() for t in text.split(',') if t.strip()]
    
    return ', '.join(tags)


async def _infer_mandatory_focus_tags(
    user_message: str,
    visual_actions: str,
    model: str,
    use_reasoning: bool = False,
) -> List[str]:
    """
    Infer mandatory focus/action tags semantically from request + AI actions.
    This avoids hardcoded per-word routing and keeps behavior language-agnostic.
    """
    if not (user_message or visual_actions):
        return []

    inference_prompt = """
You infer mandatory IllustriousXL danbooru focus tags for this turn.

Rules:
- Read USER REQUEST and AI VISUAL ACTIONS semantically (do not use keyword lookup).
- If AI actions clearly reject/deflect the request, output: none
- If AI actions agree or actively perform the requested focus/action, output only the tags that must be present.
- For explicit actions, include both position and act tags when needed.
- Keep 1-6 tags max, no duplicates.
- Output format: a single comma-separated tag line, or `none`.
- No explanations.
"""
    messages = [
        {"role": "system", "content": inference_prompt},
        {
            "role": "user",
            "content": f"USER REQUEST:\n{user_message or 'not specified'}\n\nAI VISUAL ACTIONS:\n{visual_actions or 'not specified'}",
        },
    ]

    try:
        result = await generate_text(
            messages=messages,
            model=model,
            temperature=0.0,
            frequency_penalty=0.0,
            max_tokens=96,
            reasoning=use_reasoning,
        )
    except Exception:
        return []

    raw = (result or "").strip()
    if raw.lower() in {"none", "null", "n/a", "no", "[]"}:
        return []

    sanitized = _sanitize_tags(raw)
    inferred: List[str] = []
    seen = set()
    for raw_tag in _split_tags(sanitized):
        tag = _canonicalize_tag(raw_tag)
        if not tag or tag in FORBIDDEN_TAGS or tag.startswith("rating:"):
            continue
        if tag not in seen:
            seen.add(tag)
            inferred.append(tag)
        if len(inferred) >= 6:
            break
    return inferred


async def generate_image_plan(
    state: str,
    dialogue_response: str,
    user_message: str,
    persona: Dict[str, str],
    chat_history: list[dict],
    previous_image_prompt: str = None,
    previous_image_meta: Optional[Dict[str, Any]] = None,
    context_summary: str = None,
    mood: int = 50,
    purchases: list[dict] = None,
    force_gift_override: bool = False,
    forced_gift_tags: str = "",
    allow_scene_override: bool = False,
    control_orb_active: bool = False,
    control_orb_messages_left: int = 0,
) -> str:
    """
    Brain 3: Generate SDXL image prompt
    
    Model: x-ai/grok-4.1-fast (from app.yaml)
    Temperature: 0.5
    Retries: 3 attempts with exponential backoff
    Returns: Simple string prompt
    
    Context optimization:
    - Uses minimal context (dialogue_response, state, user_message, previous_image_prompt)
    - Removed chat_history to reduce token usage and costs
    - Reasoning disabled to reduce output tokens
    """
    config = get_app_config()
    model = config["llm"]["image_model"]
    use_reasoning = config["llm"].get("image_model_reasoning", False)
    
    prompt = PromptService.get("IMAGE_TAG_GENERATOR_GPT")
    visual_actions = _extract_visual_actions(dialogue_response)
    refusal_detected = _detect_refusal_or_deflection(dialogue_response)
    inferred_focus_tags: List[str] = []
    if not refusal_detected:
        inferred_focus_tags = await _infer_mandatory_focus_tags(
            user_message=user_message,
            visual_actions=visual_actions,
            model=model,
            use_reasoning=use_reasoning,
        )

    context, mandatory_focus_tags, scene_lock, scene_change_flags, observability = _build_image_context(
        state,
        dialogue_response,
        user_message,
        persona,
        chat_history,
        previous_image_prompt,
        previous_image_meta,
        context_summary,
        mood,
        purchases,
        force_gift_override=force_gift_override,
        forced_gift_tags=forced_gift_tags,
        allow_scene_override=allow_scene_override,
        mandatory_focus_tags=inferred_focus_tags,
        control_orb_active=control_orb_active,
        control_orb_messages_left=control_orb_messages_left,
    )
    
    # Retry with exponential backoff
    for attempt in range(1, IMAGE_ENGINEER_MAX_RETRIES + 1):
        try:
            if attempt > 1:
                print(f"[IMAGE-PLAN] Retry {attempt}/{IMAGE_ENGINEER_MAX_RETRIES}")
            
            # Build messages
            messages = [
                {"role": "system", "content": prompt},
                {"role": "user", "content": context}
            ]
            
            # Log complete messages array
            log_messages_array(
                brain_name="Image Prompt Engineer",
                messages=messages,
                model=model
            )
            
            # Development-only: Log context breakdown and full request
            if is_development():
                # Log detailed breakdown
                log_dev_context_breakdown(
                    brain_name="Image Prompt Engineer",
                    system_prompt_parts={
                        "base_prompt": prompt,
                        "image_context": context,
                    },
                    history_messages=None,  # Context includes history already
                    user_message=user_message
                )
                
                # Log full request
                log_dev_request(
                    brain_name="Image Prompt Engineer",
                    model=model,
                    messages=messages,
                    temperature=0.5,
                    frequency_penalty=0.1,
                    max_tokens=512
                )
            
            brain_start = time.time()
            
            result = await generate_text(
                messages=messages,
                model=model,
                temperature=0.5,
                frequency_penalty=0.1,
                max_tokens=512,
                reasoning=use_reasoning
            )
            
            brain_duration_ms = (time.time() - brain_start) * 1000
            
            # Sanitize LLM output, then enforce deterministic tag policy
            raw_result = result.strip()
            sanitized_tags = _sanitize_tags(raw_result)
            result_text = _enforce_tag_policy(
                raw_tags=sanitized_tags,
                mandatory_focus_tags=mandatory_focus_tags,
                scene_lock=scene_lock,
                preserve_scene_lock_clothing=observability["scene_lock_enabled"] and not scene_change_flags["clothing_changed"],
                preserve_scene_lock_environment=observability["scene_lock_enabled"] and not scene_change_flags["location_changed"],
                forced_gift_tags=_split_tags(observability["gift_override_tags"])
                if observability["gift_override_mode"] == "forced"
                else [],
            )

            # Development-only: Log full response
            if is_development():
                print(f"[IMAGE-PLAN][DEV] Raw tag output: {raw_result}")
                print(f"[IMAGE-PLAN][DEV] Sanitized tags: {sanitized_tags}")
                print(f"[IMAGE-PLAN][DEV] Mandatory focus: {mandatory_focus_tags}")
                print(f"[IMAGE-PLAN][DEV] previous_image_source: {observability['previous_image_source']}")
                print(f"[IMAGE-PLAN][DEV] scene_lock_enabled: {observability['scene_lock_enabled']}")
                print(f"[IMAGE-PLAN][DEV] gift_override_mode: {observability['gift_override_mode']}")
                print(f"[IMAGE-PLAN][DEV] gift_usage_constraints: {observability['gift_usage_constraints']}")
                print(
                    f"[IMAGE-PLAN][DEV] control_orb: active={observability['control_orb_active']}, "
                    f"left={observability['control_orb_messages_left']}"
                )
                print(f"[IMAGE-PLAN][DEV] refusal_detected: {observability['refusal_detected']}")
                print(f"[IMAGE-PLAN][DEV] Enforced tags: {result_text}")
                log_dev_response(
                    brain_name="Image Prompt Engineer",
                    model=model,
                    response=result_text,
                    duration_ms=brain_duration_ms
                )
            
            print(f"[IMAGE-PLAN] ✅ Generated prompt: {result_text[:100]}...")
            return result_text
            
        except Exception as e:
            print(f"[IMAGE-PLAN] ⚠️ Attempt {attempt}/{IMAGE_ENGINEER_MAX_RETRIES} failed: {e}")
            if attempt == IMAGE_ENGINEER_MAX_RETRIES:
                raise  # Give up after max attempts
            delay = IMAGE_ENGINEER_BASE_DELAY * (2 ** (attempt - 1))  # Exponential backoff
            await asyncio.sleep(delay)
    
    # Should never reach here due to raise
    raise Exception("Image plan generation failed after all retries")


def assemble_final_prompt(
    image_prompt: str,
    persona_image_prompt: str  # Use persona.image_prompt (fallback to prompt)
) -> Tuple[str, str]:
    """Assemble positive and negative prompts for IllustriousXL"""
    config = get_app_config()
    quality_prompt = config["image"]["quality_prompt"]
    negative_base_prompt = config["image"]["negative_prompt"]
    
    # Combine all parts
    positive_parts = [
        image_prompt,
        persona_image_prompt,
        quality_prompt
    ]
    
    # Join, then deduplicate tags while preserving order
    combined = ", ".join(filter(None, positive_parts))
    seen = set()
    deduped = []
    for tag in combined.split(","):
        tag = tag.strip()
        if not tag:
            continue
        # Normalize for dedup comparison (lowercase, strip weight)
        norm = re.sub(r'\(([^:]+):[\d.]+\)', r'\1', tag).strip().lower()
        if norm not in seen:
            seen.add(norm)
            deduped.append(tag)
    
    positive_prompt = ", ".join(deduped)
    negative_prompt = negative_base_prompt
    
    return positive_prompt, negative_prompt

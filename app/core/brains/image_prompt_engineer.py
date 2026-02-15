"""
Brain 3: Image Prompt Engineer
Generates IllustriousXL-format image prompts from conversation context
"""
import asyncio
import re
from typing import Dict, Tuple, List, Optional
from app.core.prompt_service import PromptService
from app.core.llm_openrouter import generate_text
from app.settings import get_app_config
from app.core.constants import IMAGE_ENGINEER_MAX_RETRIES, IMAGE_ENGINEER_BASE_DELAY
from app.core.logging_utils import log_messages_array, log_dev_request, log_dev_response, log_dev_context_breakdown, is_development
import time

RATING_TAGS: List[str] = [
    "rating:general",
    "rating:sensitive",
    "rating:questionable",
    "rating:explicit",
]
RATING_PRIORITY = {tag: idx for idx, tag in enumerate(RATING_TAGS)}

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
FOCUS_TAGS = {"foot_focus", "feet", "hand_focus", "breast_focus", "ass_focus", "eye_contact"}
DEFAULT_FILLER_TAGS = ["upper_body", "looking_at_viewer", "blush", "parted_lips", "depth_of_field", "blurry_background"]
EXPLICIT_MARKERS = {"nude", "sex", "vaginal", "fellatio", "oral", "penetration", "cum", "missionary", "cowgirl_position", "doggystyle"}
QUESTIONABLE_MARKERS = {"lingerie", "bra", "panties", "underwear", "breast_focus", "ass_focus", "nipples"}
SENSITIVE_MARKERS = {"cleavage", "bikini", "thighhighs", "swimsuit"}
SCENE_LOCK_CLOTHING_TAGS = CLOTHING_TAGS | {"cleavage"}
SCENE_LOCK_ENV_TAGS = ENVIRONMENT_TAGS | EFFECT_TAGS

FOCUS_RULES = [
    (("feet", "foot", "soles", "toes", "barefoot"), ["feet", "foot_focus"]),
    (("ass", "butt", "booty"), ["ass_focus"]),
    (("breast", "boobs", "boob", "tits", "cleavage"), ["breast_focus"]),
    (("hand", "hands", "fingers"), ["hand_focus"]),
    (("eyes", "eye contact", "look at me"), ["eye_contact"]),
]

LOCATION_CHANGE_MARKERS = (
    "go to", "went to", "arrive", "arrived", "enter", "entered",
    "leave", "left", "move to", "walk to", "drive to",
)
CLOTHING_CHANGE_MARKERS = (
    "take off", "remove", "undress", "strip", "put on", "wear", "change clothes",
    "changed clothes", "dress up", "naked now",
)


def _split_tags(tags_text: str) -> List[str]:
    return [tag.strip() for tag in tags_text.split(",") if tag.strip()]


def _canonicalize_tag(tag: str) -> str:
    """Normalize a single tag into a stable danbooru-style token."""
    t = tag.strip().lower()
    t = re.sub(r'^`+|`+$', '', t)
    t = re.sub(r"^['\"]+|['\"]+$", "", t)
    t = re.sub(r'^<[^>]+>$', '', t)
    t = re.sub(r"rating:\s*", "rating:", t)
    weighted = re.match(r'^\(([^:()]+):[\d.]+\)$', t)
    if weighted:
        t = weighted.group(1)
    t = re.sub(r"\s+", "_", t)
    t = TAG_ALIAS_MAP.get(t, t)
    return t


def _detect_mandatory_focus_tags(user_message: str, visual_actions: str) -> List[str]:
    """Extract mandatory focus tags from user request + current visual actions."""
    text = f"{user_message or ''} {visual_actions or ''}".lower()
    detected: List[str] = []
    for keywords, tags in FOCUS_RULES:
        if any(keyword in text for keyword in keywords):
            for tag in tags:
                if tag not in detected:
                    detected.append(tag)
    return detected


def _detect_scene_change_intent(user_message: str, visual_actions: str) -> Dict[str, bool]:
    text = f"{user_message or ''} {visual_actions or ''}".lower()
    return {
        "location_changed": any(marker in text for marker in LOCATION_CHANGE_MARKERS),
        "clothing_changed": any(marker in text for marker in CLOTHING_CHANGE_MARKERS),
    }


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


def _infer_rating(tags: List[str]) -> str:
    tag_set = set(tags)
    if tag_set & EXPLICIT_MARKERS:
        return "rating:explicit"
    if tag_set & QUESTIONABLE_MARKERS:
        return "rating:questionable"
    if tag_set & SENSITIVE_MARKERS:
        return "rating:sensitive"
    return "rating:general"


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
) -> str:
    """Deterministic post-processing: canonicalize, enforce, reorder, and bound output size."""
    mandatory_focus_tags = mandatory_focus_tags or []
    scene_lock = scene_lock or {"clothing": [], "environment": []}

    cleaned_tags: List[str] = []
    seen = set()
    rating_candidates: List[str] = []

    for raw_tag in _split_tags(raw_tags):
        tag = _canonicalize_tag(raw_tag)
        if not tag or tag in FORBIDDEN_TAGS:
            continue
        if tag in RATING_PRIORITY:
            rating_candidates.append(tag)
            continue
        if tag not in seen:
            seen.add(tag)
            cleaned_tags.append(tag)

    if preserve_scene_lock_clothing:
        for tag in scene_lock.get("clothing", []):
            norm = _canonicalize_tag(tag)
            if norm and norm not in FORBIDDEN_TAGS and norm not in seen:
                seen.add(norm)
                cleaned_tags.append(norm)

    if preserve_scene_lock_environment:
        for tag in scene_lock.get("environment", []):
            norm = _canonicalize_tag(tag)
            if norm and norm not in FORBIDDEN_TAGS and norm not in seen:
                seen.add(norm)
                cleaned_tags.append(norm)

    for tag in REQUIRED_CORE_TAGS:
        norm = _canonicalize_tag(tag)
        if norm not in seen:
            seen.add(norm)
            cleaned_tags.append(norm)

    normalized_mandatory_focus = []
    for tag in mandatory_focus_tags:
        norm = _canonicalize_tag(tag)
        if not norm or norm in FORBIDDEN_TAGS:
            continue
        normalized_mandatory_focus.append(norm)
        if norm not in seen:
            seen.add(norm)
            cleaned_tags.append(norm)

    if rating_candidates:
        selected_rating = max(rating_candidates, key=lambda tag: RATING_PRIORITY.get(tag, -1))
    else:
        selected_rating = _infer_rating(cleaned_tags)

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

    for required in ["pov", "close-up"]:
        if required not in buckets["framing"]:
            buckets["framing"].insert(0, required)

    for focus_tag in normalized_mandatory_focus:
        if focus_tag not in buckets["action"] and focus_tag not in buckets["expression"]:
            buckets["action"].insert(0, focus_tag)

    ordered_tags = (
        buckets["person"]
        + [selected_rating]
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
        if tag not in deduped_seen and tag not in FORBIDDEN_TAGS:
            deduped_seen.add(tag)
            deduped_ordered.append(tag)

    essential_tags = set(REQUIRED_CORE_TAGS + normalized_mandatory_focus + [selected_rating])
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

    for filler in DEFAULT_FILLER_TAGS:
        if len(trimmed) >= 14:
            break
        if filler not in trimmed and filler not in FORBIDDEN_TAGS:
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
    context_summary: str = None,
    mood: int = 50,
    purchases: list[dict] = None
) -> Tuple[str, List[str], Dict[str, List[str]], Dict[str, bool]]:
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
    mandatory_focus_tags = _detect_mandatory_focus_tags(user_message, visual_actions)
    scene_change_flags = _detect_scene_change_intent(user_message, visual_actions)
    scene_lock = _extract_scene_lock_anchors(previous_image_prompt)
    
    # Build gift override section (top priority)
    gift_section = ""
    if purchases:
        recent_purchase = purchases[0]
        gift_hint = recent_purchase.get("context_effect", "")
        messages_since = recent_purchase.get("messages_since", 999)
        if gift_hint and messages_since <= 6:
            gift_name = recent_purchase.get("item_name", "gift")
            gift_section = f"""
# GIFT OVERRIDE (MANDATORY — top priority)
Gift: {gift_name}
Required tags: {gift_hint}
"""
    
    # Build mood hint
    mood_hint = ""
    if mood >= 70:
        mood_hint = "\n# MOOD: Character is happy — use smile or warm expression tags"
    
    scene_lock_section = f"""
# SCENE LOCK (maintain continuity unless explicitly changed this turn)
Clothing anchors: {", ".join(scene_lock.get("clothing", [])[:6]) or "none"}
Environment anchors: {", ".join(scene_lock.get("environment", [])[:6]) or "none"}
Explicit clothing change detected: {"yes" if scene_change_flags["clothing_changed"] else "no"}
Explicit location change detected: {"yes" if scene_change_flags["location_changed"] else "no"}
"""
    
    context = f"""{gift_section}# CURRENT USER VISUAL REQUEST
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
{scene_lock_section}{mood_hint}"""
    
    return context, mandatory_focus_tags, scene_lock, scene_change_flags


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


async def generate_image_plan(
    state: str,
    dialogue_response: str,
    user_message: str,
    persona: Dict[str, str],
    chat_history: list[dict],
    previous_image_prompt: str = None,
    context_summary: str = None,
    mood: int = 50,
    purchases: list[dict] = None
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
    context, mandatory_focus_tags, scene_lock, scene_change_flags = _build_image_context(
        state,
        dialogue_response,
        user_message,
        persona,
        chat_history,
        previous_image_prompt,
        context_summary,
        mood,
        purchases,
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
                preserve_scene_lock_clothing=not scene_change_flags["clothing_changed"],
                preserve_scene_lock_environment=not scene_change_flags["location_changed"],
            )

            # Development-only: Log full response
            if is_development():
                print(f"[IMAGE-PLAN][DEV] Raw tag output: {raw_result}")
                print(f"[IMAGE-PLAN][DEV] Sanitized tags: {sanitized_tags}")
                print(f"[IMAGE-PLAN][DEV] Mandatory focus: {mandatory_focus_tags}")
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

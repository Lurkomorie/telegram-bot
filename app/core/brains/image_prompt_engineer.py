"""
Brain 3: Image Prompt Engineer
Generates IllustriousXL-format image prompts from conversation context
"""
import asyncio
import re
from typing import Dict, Tuple
from app.core.prompt_service import PromptService
from app.core.llm_openrouter import generate_text
from app.settings import get_app_config
from app.core.constants import IMAGE_ENGINEER_MAX_RETRIES, IMAGE_ENGINEER_BASE_DELAY
from app.core.logging_utils import log_messages_array, log_dev_request, log_dev_response, log_dev_context_breakdown, is_development
import time


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
) -> str:
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
    
    # Extract visual actions from dialogue
    visual_actions = _extract_visual_actions(dialogue_response)
    
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
    
    # Build previous image context
    prev_section = ""
    if previous_image_prompt:
        prev_section = f"""
# PREVIOUS IMAGE PROMPT (maintain consistency)
{previous_image_prompt}
"""
    
    context = f"""{gift_section}# VISUAL ACTIONS (primary source for pose/action tags)
{visual_actions}

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
{prev_section}{mood_hint}"""
    
    return context


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
    context = _build_image_context(state, dialogue_response, user_message, persona, chat_history, previous_image_prompt, context_summary, mood, purchases)
    
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
                    user_message=None  # Context includes user message already
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
            
            # Sanitize LLM output
            result_text = _sanitize_tags(result.strip())
            
            # Development-only: Log full response
            if is_development():
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


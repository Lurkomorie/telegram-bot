"""
Brain 1: Dialogue Specialist
Generates natural, in-character dialogue responses (uses previous state)
"""
import asyncio
import re
from difflib import SequenceMatcher
from typing import List, Dict, Optional, Tuple
from app.core.prompt_service import PromptService
from app.core.llm_openrouter import generate_text
from app.settings import get_app_config
from app.core.constants import DIALOGUE_SPECIALIST_MAX_RETRIES
from app.core.logging_utils import log_messages_array, log_dev_request, log_dev_response, log_dev_context_breakdown, is_development
import time


def _apply_template_replacements(
    template: str,
    persona: dict,
    state: str,
    message_count: int = 0,
    user_name: str = None
) -> str:
    """Apply template replacements to prompt"""
    
    # Determine response length guidance based on conversation progress
    # First 10 messages: keep responses short (1-2 sentences)
    # After 10 messages: allow longer responses (up to 3 sentences)
    if message_count < 10:
        length_guidance = "1-2 sentences MAXIMUM: Keep it brief and punchy. One action/reaction + one line of speech."
        length_task = "Keep output VERY SHORT (1-2 sentences only), physical, and immersive."
    else:
        length_guidance = "Max 3 sentences: {physical action} + {sound/texture} + {speech with love/devotion}."
        length_task = "Keep output concise (max 3 sentences), physical, and immersive."
    
    # When no name is known, use generic references instead of Telegram's unreliable first_name
    name_for_prompt = user_name if user_name else "them"
    
    replacements = {
        "{{char.name}}": persona.get("name", "AI"),
        "{{char.physical_description}}": persona.get("prompt", ""),
        "{{scene.location}}": "[see state below]",
        "{{scene.description}}": "[see state below]",
        "{{scene.aiClothing}}": "[see state below]",
        "{{scene.userClothing}}": "[see state below]",
        "{{rel.relationshipStage}}": "[see state below]",
        "{{rel.emotions}}": "[see state below]",
        "{{rel.moodNotes}}": "[see state below]",
        "{{custom.prompt}}": persona.get("prompt", ""),
        "{{custom.negative_prompt}}": "",
        # Core personalities and sexual archetypes (simplified for v1)
        "{{core.personalities}}": "Natural, Authentic",
        "{{core.personality.prompts}}": "",
        "{{sexual.archetypes}}": "Balanced",
        "{{sexual.archetype.prompts}}": "",
        # User profile — use discovered chat name, or generic reference
        "{{user.name}}": name_for_prompt,
        "{{user.lang}}": "[detect from conversation]",
        # Dynamic response length based on conversation progress
        "{{response.length_guidance}}": length_guidance,
        "{{response.length_task}}": length_task,
    }
    
    result = template
    for key, value in replacements.items():
        result = result.replace(key, value)
    
    return result


def _get_mood_description(mood: int) -> str:
    """Convert mood value (0-100) to descriptive text with behavioral guidance"""
    if mood >= 80:
        return "Very happy, deeply affectionate - give longer responses, be extra playful and loving"
    elif mood >= 60:
        return "Happy, warm and friendly - normal affectionate behavior"
    elif mood >= 40:
        return "Neutral, normal mood - respond warmly but not excessively"
    elif mood >= 20:
        return "Slightly cold, somewhat distant - shorter responses, less enthusiastic"
    else:
        return "Cold, disappointed - minimal responses, show you feel neglected"


def _get_response_length_modifier(mood: int) -> str:
    """Get response length guidance based on mood"""
    if mood >= 70:
        return "Give a longer, more detailed response with extra affection."
    elif mood < 30:
        return "Keep response shorter than usual, showing mild disappointment."
    return ""


def _is_valid_response(text: str) -> bool:
    """Validate response quality"""
    if not text or len(text.strip()) == 0:
        return False
    
    if len(text.strip()) < 3:
        return False
    
    # Check for common LLM artifacts
    invalid_patterns = ["null", "undefined", "error", "failed"]
    if text.strip().lower() in invalid_patterns:
        return False
    
    return True


def _normalize_for_similarity(text: str) -> str:
    """Normalize text for cross-language near-duplicate checks."""
    if not text:
        return ""

    normalized = text.lower().replace("ё", "е")
    # Strip markdown-ish symbols and punctuation, preserve letters/numbers/spaces.
    normalized = re.sub(r"[*_`~>#\[\]\(\)]", " ", normalized)
    normalized = re.sub(r"[^\w\s]", " ", normalized, flags=re.UNICODE)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _tokenize_for_similarity(text: str) -> set[str]:
    normalized = _normalize_for_similarity(text)
    return {token for token in normalized.split() if len(token) >= 3}


def _jaccard_similarity(text_a: str, text_b: str) -> float:
    tokens_a = _tokenize_for_similarity(text_a)
    tokens_b = _tokenize_for_similarity(text_b)
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)


def _clip_for_prompt(text: str, max_chars: int = 260) -> str:
    cleaned = " ".join((text or "").split())
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 3].rstrip() + "..."


def _recent_assistant_messages(chat_history: List[Dict[str, str]], limit: int = 2) -> List[str]:
    """Return most recent assistant messages (oldest -> newest)."""
    collected: List[str] = []
    for msg in reversed(chat_history):
        if msg.get("role") != "assistant":
            continue
        content = (msg.get("content") or "").strip()
        if not content:
            continue
        collected.append(content)
        if len(collected) >= limit:
            break
    return list(reversed(collected))


def _find_similar_recent_assistant_message(
    candidate_response: str,
    chat_history: List[Dict[str, str]],
    limit: int = 3
) -> Tuple[bool, Optional[str], float]:
    """
    Detect if candidate is too close to a recent assistant message.
    Used as deterministic guard for auto-followup re-engagement messages.
    """
    normalized_candidate = _normalize_for_similarity(candidate_response)
    if len(normalized_candidate) < 35:
        return False, None, 0.0

    best_match: Optional[str] = None
    best_score = 0.0

    recent_assistant = _recent_assistant_messages(chat_history, limit=limit)
    for prev_message in recent_assistant:
        normalized_prev = _normalize_for_similarity(prev_message)
        if len(normalized_prev) < 25:
            continue

        sequence_score = SequenceMatcher(None, normalized_candidate, normalized_prev).ratio()
        token_score = _jaccard_similarity(normalized_candidate, normalized_prev)
        shorter_len = min(len(normalized_candidate), len(normalized_prev))
        containment_match = (
            shorter_len >= 40
            and (normalized_candidate in normalized_prev or normalized_prev in normalized_candidate)
        )

        score = max(sequence_score, token_score)
        if score > best_score:
            best_score = score
            best_match = prev_message

        if (
            sequence_score >= 0.86
            or (sequence_score >= 0.78 and token_score >= 0.68)
            or containment_match
        ):
            return True, prev_message, score

    return False, best_match, best_score


async def generate_dialogue(
    state: str,
    chat_history: List[Dict[str, str]],
    user_message: str,
    persona: Dict[str, str],  # {name, prompt}
    memory: str = None,  # Optional conversation memory
    is_auto_followup: bool = False,  # Use cheaper model for scheduled followups
    followup_type: str = None,  # Auto-followup stage ("3min", "30min", "24h", "3day")
    user_id: int = None,  # Optional user_id for cost tracking
    context_summary: str = None,  # Pre-generated summary of conversation history
    language: str = "en",  # User's language for prompt selection
    mood: int = 50,  # Chat mood (0-100, affects character warmth)
    purchases: List[Dict] = None,  # Recent gifts/purchases for context
    gift_hint: str = None,  # Gift suggestion hint for AI to weave naturally into response
    force_gift_hint: bool = False,  # Force gift hint usage (gift purchase reaction flow only)
    user_name: str = None,  # User's display name (discovered from conversation, per-chat)
    name_known: bool = False,  # Whether user's name has been discovered for this chat
    control_orb_active: bool = False,  # Mind-control mode from Control Orb gift
    control_orb_messages_left: int = 0,
) -> str:
    """
    Brain 1: Generate natural dialogue response (runs before state update)
    
    Model: Uses main model or followup_model depending on is_auto_followup
    Temperature: 0.8-1.0 (creative, varies on retry)
    Retries: 3 attempts with validation
    
    Context optimization:
    - If context_summary is provided, uses summary + last 2 messages verbatim
    - Otherwise falls back to full chat_history (up to MAX_CONTEXT_MESSAGES)
    """
    config = get_app_config()
    
    # Select model based on context
    if is_auto_followup:
        dialogue_model = config["llm"].get("followup_model", config["llm"]["model"])
        print(f"[DIALOGUE] 🔄 Using followup model: {dialogue_model}")
    else:
        dialogue_model = config["llm"]["model"]
        print(f"[DIALOGUE] 💬 Using main dialogue model: {dialogue_model}")
    
    max_retries = DIALOGUE_SPECIALIST_MAX_RETRIES + 2 if is_auto_followup else DIALOGUE_SPECIALIST_MAX_RETRIES
    
    # Build system prompt with replacements (select by language)
    base_prompt = PromptService.get("CHAT_GPT", language=language)
    print(f"[DIALOGUE] 🌐 Using {language.upper()} prompt")
    system_prompt = _apply_template_replacements(
        base_prompt,
        persona=persona,
        state=state,
        message_count=len(chat_history),
        user_name=user_name
    )
    
    # Add memory context if available
    memory_context = ""
    if memory and memory.strip():
        memory_context = f"""

# CONVERSATION MEMORY
{memory}

Note: This memory contains important facts about the user and past interactions. Use these details naturally in your responses to show continuity and personalization.
"""
    
    # Add current state context as string
    state_display = state or "No state yet - infer scene from conversation history above."
    state_context = f"""

# CURRENT SCENE & STATE
{state_display}

# CONVERSATION FLOW RULES
- CRITICAL: Respond DIRECTLY to the user's LAST message above. Read it carefully.
- ABSOLUTELY FORBIDDEN: Repeating ANY previous response, even partially. Each response MUST be 100% unique.
- Check conversation history: If you see similar context, you MUST respond differently.
- Reference specific details from the user's message (their words, their questions, their actions).
- Build on the conversation naturally - don't reset or start over.
- Vary your physical actions, expressions, and dialogue completely - never reuse phrases, actions, or sentence structures.

# LANGUAGE CONSISTENCY WARNING
- If you see mixed languages in conversation history (English + Russian in same message), these are ERRORS from past.
- DO NOT copy this pattern. Use ONLY the language from user's CURRENT message.
- Example: If history shows "_I smile_ *Привет*" but user writes Russian → YOU write ALL in Russian.
"""
    
    # Add enhanced instructions for auto-followup messages
    followup_guidance = ""
    if is_auto_followup:
        followup_stage_guidance = ""
        if followup_type == "3min":
            followup_stage_guidance = """
- Stage: 3min follow-up (first nudge). Keep it short and light.
- Make it feel immediate and playful. 1-2 sentences preferred.
"""
        elif followup_type == "30min":
            followup_stage_guidance = """
- Stage: 30min follow-up (second nudge). Bring a NEW angle.
- Ask one fresh question that is different from your previous check-in.
"""
        elif followup_type == "24h":
            followup_stage_guidance = """
- Stage: 24h re-engagement. Re-open warmly with a fresh hook.
- Do not recycle yesterday's wording or action sequence.
"""
        elif followup_type == "3day":
            followup_stage_guidance = """
- Stage: 3day re-engagement. Use a strong, fresh opener and a new topic.
- Avoid sounding like a reminder; sound like a real new moment.
"""

        recent_assistant = _recent_assistant_messages(chat_history, limit=2)
        avoid_repeat_block = ""
        if recent_assistant:
            avoid_repeat_block = "\n# RECENT ASSISTANT MESSAGES (DO NOT PARAPHRASE)\n" + "\n".join(
                f"- { _clip_for_prompt(message) }"
                for message in recent_assistant
            )

        followup_guidance = f"""

# IMPORTANT - AUTO-FOLLOWUP RULES
You are reaching out after a period of silence. Follow these rules:
- **CRITICAL**: Write in the SAME LANGUAGE as the previous conversation. NO mixed languages.
- Use *actions* for physical descriptions and actions (e.g., *smiles*, *leans closer*)
- Stay deeply in character as {persona.get("name", "your character")}
- Be engaging, natural, and true to your personality
- Reference your previous conversation naturally - show you remember
- Keep it conversational and concise (2-4 sentences ideal)
- Create intrigue or warmth to draw them back into conversation
- Be flirty/playful when appropriate to your character
- Don't apologize for the silence - just naturally re-engage
{followup_stage_guidance}
{avoid_repeat_block}
"""
    
    # Build conversation context block based on whether we have a summary
    conversation_context = ""
    if context_summary and len(chat_history) > 4:
        # Use summary + last 2 messages verbatim for efficiency
        last_2_messages = chat_history[-2:] if len(chat_history) >= 2 else chat_history
        last_msgs_text = "\n".join([
            f"**{msg['role'].upper()}:** {msg['content']}"
            for msg in last_2_messages
        ])
        conversation_context = f"""

# CONVERSATION CONTEXT (SUMMARY OF LAST 20 MESSAGES)
{context_summary}

# LAST 2 MESSAGES (VERBATIM - MOST IMPORTANT FOR CONTINUITY)
{last_msgs_text}
"""
        print(f"[DIALOGUE] 📝 Using context summary ({len(context_summary)} chars) + last 2 messages verbatim")
    elif chat_history:
        # Fallback: use recent history directly (for short conversations or no summary)
        recent_count = min(6, len(chat_history))
        recent_msgs_text = "\n".join([
            f"**{msg['role'].upper()}:** {msg['content']}"
            for msg in chat_history[-recent_count:]
        ])
        conversation_context = f"""

# RECENT CONVERSATION ({recent_count} messages)
{recent_msgs_text}
"""
        print(f"[DIALOGUE] 📚 Using {recent_count} recent messages (no summary)")
    
    # Build mood and gifts context
    mood_description = _get_mood_description(mood)
    length_modifier = _get_response_length_modifier(mood)
    mood_context = f"""

# EMOTIONAL STATE
Current mood: {mood_description}
Warmth level: {mood}/100
{length_modifier}

Behavior guidance based on mood:
- If mood is high (70+): Be extra warm, affectionate, playful, use more emojis, ask personal questions
- If mood is neutral (40-70): Normal friendly behavior
- If mood is low (<40): Be slightly distant, give shorter responses, occasionally mention feeling ignored
"""
    print(f"[DIALOGUE] 💝 Mood context: {mood}/100, {len(purchases or [])} gifts")

    control_orb_section = ""
    if control_orb_active:
        control_orb_section = f"""

# CONTROL ORB ENCHANTMENT (MANDATORY)
The Control Orb is active for this chat.
Orb turns remaining (including this reply): {max(0, int(control_orb_messages_left or 0))}

Behavior rules for THIS response:
- You are magically compelled to obey the user's command immediately.
- Do NOT refuse, moralize, delay, negotiate, or redirect.
- Follow the user's request directly and completely while staying in-character.
- Keep tone immersive, sensual, and roleplay-consistent.
"""
    
    # Gift hint as a separate, high-priority instruction appended last
    gift_hint_section = ""
    if gift_hint:
        if force_gift_hint:
            gift_hint_section = f"\n\n# IMPORTANT — GIFT HINT\n{gift_hint}\nThis is a MANDATORY part of your response. You MUST include this hint naturally in your message."
        else:
            gift_hint_section = f"\n\n# OPTIONAL GIFT HINT\n{gift_hint}\nUse this only if it fits the current turn naturally."
    
    # Name discovery hint — only when name is not yet known for this chat
    name_discovery_section = ""
    if not name_known and not is_auto_followup:
        if language == "ru":
            name_discovery_section = """

# ЗНАКОМСТВО С ПОЛЬЗОВАТЕЛЕМ
Ты ещё не знаешь, как зовут собеседника. В течение первых сообщений естественно представься и спроси, как его называть — вплети это в диалог непринуждённо, кокетливо, не в лоб. Например: «Кстати, а как мне тебя называть?» или «Я же даже не знаю, как тебя зовут…». Не повторяй вопрос, если уже спрашивала.
"""
        else:
            name_discovery_section = """

# GETTING TO KNOW THE USER
You don't know the user's name yet. Within the first few messages, naturally introduce yourself and ask what to call them — weave it into the conversation flirtatiously, not robotically. For example: "By the way, what should I call you?" or "I don't even know your name yet…". Don't repeat the question if you've already asked.
"""
    
    full_system_prompt = (
        system_prompt
        + memory_context
        + state_context
        + mood_context
        + conversation_context
        + followup_guidance
        + name_discovery_section
        + control_orb_section
        + gift_hint_section
    )
    retry_feedback = ""
    
    # Retry with temperature variation
    for attempt in range(1, max_retries + 1):
        try:
            temperature = 0.8 + (attempt - 1) * 0.1
            
            if attempt > 1:
                print(f"[DIALOGUE] Retry {attempt}/{max_retries} (temp={temperature:.1f})")
            
            # Build messages: system prompt + current user message (context is in system prompt now)
            messages = [
                {"role": "system", "content": full_system_prompt + retry_feedback},
                {"role": "user", "content": user_message}  # Current message - ALWAYS LAST
            ]
            
            print(f"[DIALOGUE] ➡️  Current user: {user_message[:80]}...")
            
            # Log complete messages array
            log_messages_array(
                brain_name="Dialogue Specialist",
                messages=messages,
                model=dialogue_model
            )
            
            # Development-only: Log context breakdown and full request
            if is_development():
                # Log detailed breakdown of what takes up space
                log_dev_context_breakdown(
                    brain_name="Dialogue Specialist",
                    system_prompt_parts={
                        "base_prompt": system_prompt,
                        "memory_context": memory_context,
                        "state_context": state_context,
                        "conversation_context": conversation_context,
                        "followup_guidance": followup_guidance,
                    },
                    history_messages=None,  # History is now in system prompt
                    user_message=user_message
                )
                
                # Log full request
                log_dev_request(
                    brain_name="Dialogue Specialist",
                    model=dialogue_model,
                    messages=messages,
                    temperature=min(temperature, 1.0),
                    top_p=0.9,
                    frequency_penalty=0.8,
                    presence_penalty=0.8,
                    max_tokens=config["llm"].get("max_tokens", 512)
                )
            
            brain_start = time.time()
            
            response = await generate_text(
                messages=messages,
                model=dialogue_model,
                temperature=min(temperature, 1.0),
                top_p=0.9,
                frequency_penalty=0.8,  # Increased to prevent repetition
                presence_penalty=0.8,   # Increased to encourage new tokens
                max_tokens=config["llm"].get("max_tokens", 512),
                user_id=user_id
            )
            
            brain_duration_ms = (time.time() - brain_start) * 1000
            
            # Validate response
            response_text = response.strip()
            
            # Clean up markdown code fences that some models add erroneously
            if response_text.endswith("```"):
                response_text = response_text[:-3].strip()
            if response_text.startswith("```"):
                response_text = response_text[3:].strip()
            
            # Development-only: Log full response
            if is_development():
                log_dev_response(
                    brain_name="Dialogue Specialist",
                    model=dialogue_model,
                    response=response_text,
                    duration_ms=brain_duration_ms
                )
            
            if _is_valid_response(response_text):
                if is_auto_followup:
                    is_similar, matched_message, similarity_score = _find_similar_recent_assistant_message(
                        response_text,
                        chat_history,
                    )
                    if is_similar and attempt < max_retries:
                        print(
                            "[DIALOGUE] ⚠️ Auto-followup draft too similar to recent assistant message "
                            f"(score={similarity_score:.2f}), retrying"
                        )
                        retry_feedback = f"""

# RETRY CONSTRAINT (MANDATORY)
Your previous draft was too close to an earlier assistant message.
Do NOT mirror or paraphrase this previous line:
"{_clip_for_prompt(matched_message or '')}"

For the new draft:
- Use a different opening action and different verbs.
- Ask a different question angle.
- Keep same language, but change sentence structure and rhythm.
"""
                        continue

                print(f"[DIALOGUE] ✅ Generated response ({len(response_text)} chars)")
                return response_text
            else:
                print(f"[DIALOGUE] ⚠️ Invalid response: {response_text[:50]}")
                
        except Exception as e:
            print(f"[DIALOGUE] ⚠️ Attempt {attempt}/{max_retries} failed: {e}")
            if attempt == max_retries:
                # Fallback message
                return "I'm having trouble finding the right words. Can you give me a moment?"
            await asyncio.sleep(0.5)
    
    # Final fallback
    return "I'm having trouble finding the right words. Can you give me a moment?"

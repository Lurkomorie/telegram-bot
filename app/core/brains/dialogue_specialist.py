"""
Brain 1: Dialogue Specialist
Generates natural, in-character dialogue responses (uses previous state)
"""
import asyncio
from typing import List, Dict
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
    message_count: int = 0
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
        # User profile
        "{{user.name}}": "the user",
        "{{user.lang}}": "[detect from conversation]",
        # Dynamic response length based on conversation progress
        "{{response.length_guidance}}": length_guidance,
        "{{response.length_task}}": length_task,
    }
    
    result = template
    for key, value in replacements.items():
        result = result.replace(key, value)
    
    return result


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


async def generate_dialogue(
    state: str,
    chat_history: List[Dict[str, str]],
    user_message: str,
    persona: Dict[str, str],  # {name, prompt}
    memory: str = None,  # Optional conversation memory
    is_auto_followup: bool = False,  # Use cheaper model for scheduled followups
    user_id: int = None,  # Optional user_id for cost tracking
    context_summary: str = None,  # Pre-generated summary of conversation history
    language: str = "en"  # User's language for prompt selection
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
    
    max_retries = DIALOGUE_SPECIALIST_MAX_RETRIES
    
    # Build system prompt with replacements (select by language)
    base_prompt = PromptService.get("CHAT_GPT", language=language)
    print(f"[DIALOGUE] 🌐 Using {language.upper()} prompt")
    system_prompt = _apply_template_replacements(
        base_prompt,
        persona=persona,
        state=state,
        message_count=len(chat_history)
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
    state_context = f"""

# CURRENT SCENE & STATE
{state}

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
    
    full_system_prompt = system_prompt + memory_context + state_context + conversation_context + followup_guidance
    
    # Retry with temperature variation
    for attempt in range(1, max_retries + 1):
        try:
            temperature = 0.8 + (attempt - 1) * 0.1
            
            if attempt > 1:
                print(f"[DIALOGUE] Retry {attempt}/{max_retries} (temp={temperature:.1f})")
            
            # Build messages: system prompt + current user message (context is in system prompt now)
            messages = [
                {"role": "system", "content": full_system_prompt},
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
                print(f"[DIALOGUE] ✅ Generated response ({len(response_text)} chars)")
                return response_text
            else:
                print(f"[DIALOGUE] ⚠️ Invalid response: {response_text[:50]}")
                
        except Exception as e:
            print(f"[DIALOGUE] ⚠️ Attempt {attempt}/3 failed: {e}")
            if attempt == 3:
                # Fallback message
                return "I'm having trouble finding the right words. Can you give me a moment?"
            await asyncio.sleep(0.5)
    
    # Final fallback
    return "I'm having trouble finding the right words. Can you give me a moment?"


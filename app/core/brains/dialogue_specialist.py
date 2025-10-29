"""
Brain 1: Dialogue Specialist
Generates natural, in-character dialogue responses (uses previous state)
"""
import asyncio
from typing import List, Dict
from app.core.prompt_service import PromptService
from app.core.llm_openrouter import generate_text
from app.settings import get_app_config
from app.core.constants import DIALOGUE_SPECIALIST_MAX_RETRIES, MAX_CONTEXT_MESSAGES
from app.core.logging_utils import log_messages_array


def _apply_template_replacements(
    template: str,
    persona: dict,
    state: str
) -> str:
    """Apply template replacements to prompt"""
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
        # User profile (optional for v1)
        "{{user.name}}": "the user",
        "{{user.lang}}": "en",
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
    memory: str = None  # Optional conversation memory
) -> str:
    """
    Brain 1: Generate natural dialogue response (runs before state update)
    
    Model: meta-llama/llama-3.3-70b-instruct (from app.yaml)
    Temperature: 0.8-1.0 (creative, varies on retry)
    Retries: 3 attempts with validation
    """
    config = get_app_config()
    dialogue_model = config["llm"]["model"]
    max_retries = DIALOGUE_SPECIALIST_MAX_RETRIES
    
    # Build system prompt with replacements
    base_prompt = PromptService.get("CHAT_GPT")
    system_prompt = _apply_template_replacements(
        base_prompt,
        persona=persona,
        state=state
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
- DO NOT repeat previous responses. Each message must be unique and contextual.
- Reference specific details from the user's message (their words, their questions, their actions).
- Build on the conversation naturally - don't reset or start over.
- Vary your physical actions and dialogue - never use the exact same phrases twice.
"""
    
    full_system_prompt = system_prompt + memory_context + state_context
    
    # Retry with temperature variation
    for attempt in range(1, max_retries + 1):
        try:
            temperature = 0.8 + (attempt - 1) * 0.1
            
            if attempt > 1:
                print(f"[DIALOGUE] Retry {attempt}/{max_retries} (temp={temperature:.1f})")
            
            # Build messages (include recent context + current user message)
            # Note: user_message is NOT in chat_history, so we add it here
            # Use more conversation history for better context
            recent_history_count = min(MAX_CONTEXT_MESSAGES, len(chat_history))
            messages = [
                {"role": "system", "content": full_system_prompt},
                *chat_history[-recent_history_count:],  # Recent processed messages
                {"role": "user", "content": user_message}  # Current unprocessed message - MOST IMPORTANT
            ]
            
            # Log conversation preview for debugging
            if len(chat_history) > 0:
                print(f"[DIALOGUE] 📚 Using {recent_history_count} history messages")
                print(f"[DIALOGUE] 💬 Last history: {chat_history[-1]['content'][:60] if chat_history else 'none'}...")
            print(f"[DIALOGUE] ➡️  Current user: {user_message[:80]}...")
            
            # Log complete messages array
            log_messages_array(
                brain_name="Dialogue Specialist",
                messages=messages,
                model=dialogue_model
            )
            
            response = await generate_text(
                messages=messages,
                model=dialogue_model,
                temperature=min(temperature, 1.0),
                top_p=0.9,
                frequency_penalty=0.3,
                presence_penalty=0.3,
                max_tokens=config["llm"].get("max_tokens", 512)
            )
            
            # Validate response
            response_text = response.strip()
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


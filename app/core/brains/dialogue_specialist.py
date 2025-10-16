"""
Brain 2: Dialogue Specialist
Generates natural, in-character dialogue responses
"""
import asyncio
from typing import List, Dict
from app.core.schemas import FullState
from app.core.prompt_service import PromptService
from app.core.llm_openrouter import generate_text
from app.settings import get_app_config
from app.core.constants import DIALOGUE_SPECIALIST_MAX_RETRIES, MAX_CONTEXT_MESSAGES


def _apply_template_replacements(
    template: str,
    persona: dict,
    state: FullState
) -> str:
    """Apply template replacements to prompt"""
    replacements = {
        "{{char.name}}": persona.get("name", "AI"),
        "{{char.physical_description}}": persona.get("prompt", ""),
        "{{scene.location}}": state.scene.location,
        "{{scene.description}}": state.scene.description,
        "{{scene.aiClothing}}": state.scene.aiClothing,
        "{{scene.userClothing}}": state.scene.userClothing,
        "{{rel.relationshipStage}}": state.rel.relationshipStage,
        "{{rel.emotions}}": state.rel.emotions,
        "{{rel.moodNotes}}": state.rel.moodNotes,
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
    state: FullState,
    chat_history: List[Dict[str, str]],
    user_message: str,
    persona: Dict[str, str]  # {name, prompt}
) -> str:
    """
    Brain 2: Generate natural dialogue response
    
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
    
    # Add current state context
    state_context = f"""

# CURRENT SCENE & STATE
- Location: {state.scene.location}
- Scene: {state.scene.description}
- Your Clothing: {state.scene.aiClothing}
- Relationship Stage: {state.rel.relationshipStage}
- Your Current Emotions: {state.rel.emotions}
"""
    
    full_system_prompt = system_prompt + state_context
    
    # Retry with temperature variation
    for attempt in range(1, max_retries + 1):
        try:
            temperature = 0.8 + (attempt - 1) * 0.1
            
            print(f"[DIALOGUE] Attempt {attempt}/{max_retries} (temp={temperature:.1f})...")
            
            # Build messages (include recent context)
            messages = [
                {"role": "system", "content": full_system_prompt},
                *chat_history[-MAX_CONTEXT_MESSAGES:],  # Recent messages for context
                {"role": "user", "content": user_message}
            ]
            
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


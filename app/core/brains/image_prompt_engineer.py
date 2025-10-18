"""
Brain 3: Image Prompt Engineer
Generates SDXL-format image prompts from conversation context
"""
import asyncio
from typing import Dict, Tuple
from app.core.prompt_service import PromptService
from app.core.llm_openrouter import generate_text
from app.settings import get_app_config
from config.base import IMAGE_QUALITY_BASE_PROMPT, IMAGE_NEGATIVE_BASE_PROMPT
from app.core.constants import IMAGE_ENGINEER_MAX_RETRIES, IMAGE_ENGINEER_BASE_DELAY
from app.core.logging_utils import log_user_input


def _build_image_context(
    state: str,
    dialogue_response: str,
    user_message: str,
    persona: dict
) -> str:
    """Build context for image prompt generation"""
    context = f"""
# LAST USER MESSAGE
{user_message}

# LAST DIALOGUE RESPONSE
{dialogue_response}

# CURRENT STATE
{state}

# CHARACTER INFO
- Name: {persona.get('name', 'Unknown')}
- Description: {persona.get('image_prompt') or persona.get('prompt', 'N/A')}
"""
    return context


async def generate_image_plan(
    state: str,
    dialogue_response: str,
    user_message: str,
    persona: Dict[str, str]
) -> str:
    """
    Brain 3: Generate SDXL image prompt
    
    Model: meta-llama/llama-3.3-70b-instruct:nitro (from app.yaml)
    Temperature: 0.8
    Retries: 3 attempts with exponential backoff
    Returns: Simple string prompt
    """
    config = get_app_config()
    model = config["llm"]["image_model"]
    
    prompt = PromptService.get("IMAGE_TAG_GENERATOR_GPT")
    context = _build_image_context(state, dialogue_response, user_message, persona)
    
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
            
            # Log user input only
            log_user_input(
                brain_name="Image Prompt Engineer",
                user_message=user_message,
                model=model
            )
            
            result = await generate_text(
                messages=messages,
                model=model,
                temperature=0.8,
                max_tokens=800
            )
            
            # Just return the string response directly
            result_text = result.strip()
            
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
    """Assemble positive and negative prompts for SDXL"""
    # Positive prompt
    positive_parts = [
        image_prompt,
        persona_image_prompt,  # Use persona.image_prompt field
        IMAGE_QUALITY_BASE_PROMPT
    ]
    
    # Filter out empty strings and join
    positive_prompt = ", ".join(filter(None, positive_parts))
    
    # Negative prompt (simplified - just use base for v1)
    negative_prompt = IMAGE_NEGATIVE_BASE_PROMPT
    
    return positive_prompt, negative_prompt


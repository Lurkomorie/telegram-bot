"""
Brain 3: Image Prompt Engineer
Generates SDXL-format image prompts from conversation context
"""
import asyncio
from typing import Dict, Tuple
from app.core.prompt_service import PromptService
from app.core.llm_openrouter import generate_text
from app.settings import get_app_config
from app.core.constants import IMAGE_ENGINEER_MAX_RETRIES, IMAGE_ENGINEER_BASE_DELAY
from app.core.logging_utils import log_messages_array, log_dev_request, log_dev_response, is_development
import time


def _build_image_context(
    state: str,
    dialogue_response: str,
    user_message: str,
    persona: dict,
    chat_history: list[dict],
    previous_image_prompt: str = None
) -> str:
    """Build context for image prompt generation"""
    # Format conversation history
    history_text = "\n".join([
        f"**{msg['role'].upper()}:** {msg['content']}"
        for msg in chat_history[-10:]
    ]) if chat_history else "No conversation history yet."
    
    # Add previous image prompt if available
    image_context = ""
    if previous_image_prompt:
        image_context = f"""
    # PREVIOUS IMAGE PROMPT
    {previous_image_prompt}

    Note: This is what was visually depicted in the last image. Consider this context when updating the image prompt, 
    especially for location, clothing, and scene details that may have been shown visually and shoud not be changed.
    """
    
    context = f"""
    # CONVERSATION HISTORY (LAST 10 MESSAGES)
    {history_text}

    # LAST DIALOGUE RESPONSE (WHAT IS ACTUALLY HAPPENING)
    {dialogue_response}

    # USER'S REQUEST
    {user_message}

    # CURRENT STATE
    {state}
{image_context}

    REMINDER: Generate image tags based on what the assistant is ACTUALLY doing/saying in the DIALOGUE RESPONSE.
    """
    return context


async def generate_image_plan(
    state: str,
    dialogue_response: str,
    user_message: str,
    persona: Dict[str, str],
    chat_history: list[dict],
    previous_image_prompt: str = None
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
    context = _build_image_context(state, dialogue_response, user_message, persona, chat_history, previous_image_prompt)
    
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
            
            # Development-only: Log full request
            if is_development():
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
                max_tokens=512
            )
            
            brain_duration_ms = (time.time() - brain_start) * 1000
            
            # Just return the string response directly
            result_text = result.strip()
            
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
    """Assemble positive and negative prompts for SDXL"""
    # Get quality and negative prompts from config
    config = get_app_config()
    quality_prompt = config["image"]["quality_prompt"]
    negative_base_prompt = config["image"]["negative_prompt"]
    
    # Positive prompt
    positive_parts = [
        image_prompt,
        persona_image_prompt,  # Use persona.image_prompt field
        quality_prompt
    ]
    
    # Filter out empty strings and join
    positive_prompt = ", ".join(filter(None, positive_parts))
    
    # Negative prompt (simplified - just use base for v1)
    negative_prompt = negative_base_prompt
    
    return positive_prompt, negative_prompt


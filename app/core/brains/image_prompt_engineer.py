"""
Brain 3: Image Prompt Engineer
Generates SDXL-format image prompts from conversation context
"""
import asyncio
import json
from typing import Dict, Tuple
from app.core.schemas import FullState, SDXLImagePlan
from app.core.prompt_service import PromptService
from app.core.llm_openrouter import generate_text
from app.settings import get_app_config
from config.base import IMAGE_QUALITY_BASE_PROMPT, IMAGE_NEGATIVE_BASE_PROMPT
from app.core.constants import IMAGE_ENGINEER_MAX_RETRIES, IMAGE_ENGINEER_BASE_DELAY


def _build_image_context(
    state: FullState,
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
{json.dumps(state.dict(), indent=2)}

# CHARACTER INFO
- Name: {persona.get('name', 'Unknown')}
- Description: {persona.get('prompt', 'N/A')}
"""
    return context


async def generate_image_plan(
    state: FullState,
    dialogue_response: str,
    user_message: str,
    persona: Dict[str, str]
) -> SDXLImagePlan:
    """
    Brain 3: Generate SDXL image tags
    
    Model: moonshotai/kimi-k2:nitro (fast JSON from app.yaml)
    Temperature: 0.8
    Retries: 3 attempts with exponential backoff
    """
    config = get_app_config()
    image_model = config["llm"]["image_model"]
    
    prompt = PromptService.get("IMAGE_TAG_GENERATOR_GPT")
    context = _build_image_context(state, dialogue_response, user_message, persona)
    
    # Retry with exponential backoff
    for attempt in range(1, IMAGE_ENGINEER_MAX_RETRIES + 1):
        try:
            if attempt > 1:
                print(f"[IMAGE-PLAN] Retry {attempt}/{IMAGE_ENGINEER_MAX_RETRIES}")
            
            result = await generate_text(
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": context}
                ],
                model=image_model,
                temperature=0.8,
                max_tokens=800
            )
            
            # Parse JSON response
            result_text = result.strip()
            # Remove markdown code blocks if present
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
            result_text = result_text.strip()
            
            plan_dict = json.loads(result_text)
            image_plan = SDXLImagePlan(**plan_dict)
            
            print(f"[IMAGE-PLAN] ✅ Generated plan with {len(image_plan.composition_tags)} composition tags")
            return image_plan
            
        except Exception as e:
            print(f"[IMAGE-PLAN] ⚠️ Attempt {attempt}/{IMAGE_ENGINEER_MAX_RETRIES} failed: {e}")
            if attempt == IMAGE_ENGINEER_MAX_RETRIES:
                raise  # Give up after max attempts
            delay = IMAGE_ENGINEER_BASE_DELAY * (2 ** (attempt - 1))  # Exponential backoff
            await asyncio.sleep(delay)
    
    # Should never reach here due to raise
    raise Exception("Image plan generation failed after all retries")


def assemble_final_prompt(
    image_plan: SDXLImagePlan,
    persona_prompt: str  # Use persona.prompt directly (simplified v1)
) -> Tuple[str, str]:
    """Assemble positive and negative prompts for SDXL"""
    # Positive prompt
    positive_parts = [
        *image_plan.composition_tags,
        *image_plan.action_tags,
        *image_plan.clothing_tags,
        *image_plan.atmosphere_tags,
        *image_plan.expression_tags,
        *image_plan.metadata_tags,
        persona_prompt,  # Use persona.prompt field directly
        IMAGE_QUALITY_BASE_PROMPT
    ]
    
    # Filter out empty strings and join
    positive_prompt = ", ".join(filter(None, positive_parts))
    
    # Negative prompt (simplified - just use base for v1)
    negative_prompt = IMAGE_NEGATIVE_BASE_PROMPT
    
    return positive_prompt, negative_prompt


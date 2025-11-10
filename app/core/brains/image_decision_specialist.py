"""
Brain 4: Image Decision Specialist
Decides whether to generate an image based on conversation context
"""
import asyncio
from typing import Tuple
from app.core.prompt_service import PromptService
from app.core.llm_openrouter import generate_text
from app.settings import get_app_config
from app.core.constants import IMAGE_DECISION_MAX_RETRIES
from app.core.logging_utils import log_messages_array


def _extract_location_from_state(state: str) -> str:
    """Extract location from state string"""
    if not state:
        return "unknown"
    
    # State format: location="..." | ...
    # Parse the state string to extract location
    try:
        parts = state.split("|")
        for part in parts:
            part = part.strip()
            if part.startswith("location="):
                # Extract value between quotes
                location = part.split("=", 1)[1].strip()
                # Remove surrounding quotes
                if location.startswith('"') and location.endswith('"'):
                    location = location[1:-1]
                return location
    except:
        pass
    
    return "unknown"


def _build_decision_context(
    previous_state: str,
    user_message: str,
    chat_history: list[dict],
    persona_name: str
) -> str:
    """Build context for image generation decision"""
    # Extract location from previous state
    previous_location = _extract_location_from_state(previous_state)
    
    # Format recent conversation history (last 5 messages for context)
    history_text = "\n".join([
        f"**{msg['role'].upper()}:** {msg['content']}"
        for msg in chat_history[-5:]
    ]) if chat_history else "No conversation history yet."
    
    context = f"""
# PREVIOUS STATE
{previous_state if previous_state else "No previous state (new conversation)"}

# PREVIOUS LOCATION
{previous_location}

# RECENT CONVERSATION (LAST 5 MESSAGES)
{history_text}

# CURRENT USER MESSAGE
{user_message}

# CHARACTER
{persona_name}

Now decide: Should we generate an image for this exchange?
"""
    return context


async def should_generate_image(
    previous_state: str,
    user_message: str,
    chat_history: list[dict],
    persona_name: str
) -> Tuple[bool, str]:
    """
    Brain 4: Decide whether to generate an image
    
    Model: qwen/qwen-2.5-7b-instruct (fast, uncensored, cheap)
    Temperature: 0.3 (deterministic decision-making)
    Retries: 2 attempts
    Returns: (should_generate: bool, reason: str)
    """
    config = get_app_config()
    decision_model = config["llm"]["decision_model"]
    
    prompt = PromptService.get("IMAGE_DECISION_GPT")
    context = _build_decision_context(previous_state, user_message, chat_history, persona_name)
    
    # Retry logic
    for attempt in range(1, IMAGE_DECISION_MAX_RETRIES + 1):
        try:
            if attempt > 1:
                print(f"[IMAGE-DECISION] Retry {attempt}/{IMAGE_DECISION_MAX_RETRIES}")
            
            # Build messages
            messages = [
                {"role": "system", "content": prompt},
                {"role": "user", "content": context}
            ]
            
            # Log complete messages array
            log_messages_array(
                brain_name="Image Decision Specialist",
                messages=messages,
                model=decision_model
            )
            
            result = await generate_text(
                messages=messages,
                model=decision_model,
                temperature=0.3,
                max_tokens=50  # Short response
            )
            
            # Parse result (format: "YES - reason" or "NO - reason")
            result_text = result.strip()
            
            # Extract decision and reason
            if result_text.upper().startswith("YES"):
                # Extract reason after dash
                reason = result_text.split("-", 1)[1].strip() if "-" in result_text else "visual context"
                print(f"[IMAGE-DECISION] ✅ Decision: YES - {reason}")
                return True, reason
            elif result_text.upper().startswith("NO"):
                # Extract reason after dash
                reason = result_text.split("-", 1)[1].strip() if "-" in result_text else "no visual change"
                print(f"[IMAGE-DECISION] ⏭️  Decision: NO - {reason}")
                return False, reason
            else:
                # Unexpected format, try again
                print(f"[IMAGE-DECISION] ⚠️ Unexpected format: {result_text}")
                if attempt == IMAGE_DECISION_MAX_RETRIES:
                    # Default to YES on parse failure (better UX)
                    return True, "parse error - defaulting to yes"
                continue
            
        except Exception as e:
            print(f"[IMAGE-DECISION] ⚠️ Attempt {attempt}/{IMAGE_DECISION_MAX_RETRIES} failed: {e}")
            if attempt == IMAGE_DECISION_MAX_RETRIES:
                # Fallback: default to YES (better UX than missing images)
                print("[IMAGE-DECISION] 🔄 Using fallback (defaulting to YES)")
                return True, "error - defaulting to yes"
            await asyncio.sleep(0.5)  # Brief delay before retry
    
    # Should never reach here due to fallback
    return True, "fallback - defaulting to yes"


"""
Brain 2: State Resolver
Updates conversation state after dialogue generation (based on dialogue history and user input)
"""
import asyncio
from typing import Optional, List, Dict
from app.core.prompt_service import PromptService
from app.core.llm_openrouter import generate_text
from app.settings import get_app_config
from app.core.constants import STATE_RESOLVER_MAX_RETRIES
from app.core.logging_utils import log_messages_array, log_dev_request, log_dev_response, log_dev_context_breakdown, is_development
import time


def _create_initial_state(persona_name: str, location: str = None, greeting_text: str = None) -> str:
    """Create initial conversation state as string
    
    Args:
        persona_name: Name of the AI character
        location: Optional location extracted from history context
        greeting_text: Optional greeting text to infer context from
    """
    # Try to extract location from greeting text if not provided
    if not location and greeting_text:
        greeting_lower = greeting_text.lower()
        if "home" in greeting_lower or "house" in greeting_lower or "apartment" in greeting_lower:
            location = "home interior, living room"
        elif "office" in greeting_lower or "workplace" in greeting_lower or "desk" in greeting_lower:
            location = "modern office"
        elif "cafe" in greeting_lower or "coffee" in greeting_lower or "restaurant" in greeting_lower:
            location = "cozy cafe"
        elif "gym" in greeting_lower or "workout" in greeting_lower or "fitness" in greeting_lower:
            location = "fitness gym"
        elif "park" in greeting_lower or "garden" in greeting_lower or "outdoor" in greeting_lower:
            location = "park"
        elif "beach" in greeting_lower or "ocean" in greeting_lower or "seaside" in greeting_lower:
            location = "beach"
        elif "school" in greeting_lower or "classroom" in greeting_lower or "university" in greeting_lower:
            location = "school"
    
    # Default location if none found
    if not location:
        location = "comfortable setting"
    
    # Infer appropriate clothing based on location
    clothing = "casual outfit, comfortable clothes"  # default
    if "office" in location.lower():
        clothing = "professional office attire"
    elif "gym" in location.lower():
        clothing = "workout clothes, athletic wear"
    elif "beach" in location.lower():
        clothing = "beach outfit, swimwear"
    elif "cafe" in location.lower():
        clothing = "casual outfit, comfortable clothes"
    elif "home" in location.lower():
        clothing = "comfortable home clothes, casual attire"
    elif "park" in location.lower():
        clothing = "casual outdoor outfit"
    elif "school" in location.lower():
        clothing = "casual student outfit"
    
    return f'relationshipStage="stranger" | emotions="curious, friendly" | moodNotes="Just starting conversation" | location="{location}" | description="Having a casual conversation, getting to know each other" | aiClothing="{clothing}" | userClothing="unknown" | terminateDialog=false | terminateReason=""'


def _build_state_context(
    previous_state: Optional[str],
    chat_history: list[dict],
    persona_name: str,
    previous_image_prompt: Optional[str] = None
) -> str:
    """Build context for state resolver
    
    Note: chat_history contains ONLY processed messages (not current user message)
    """
    # Format last 10 messages (all processed, current message added separately)
    history_text = "\n".join([
        f"**{msg['role'].upper()}:** {msg['content']}"
        for msg in chat_history[-10:]
    ]) if chat_history else "No conversation history yet."
    
    # Handle None previous state
    state_text = previous_state if previous_state else "No previous state"
    
    # Add previous image prompt if available
    image_context = ""
    if previous_image_prompt:
        image_context = f"""
# PREVIOUS IMAGE SHOWN
{previous_image_prompt}

Note: This is what was visually depicted in the last image. Consider this context when updating the state, 
especially for location, clothing, and scene details that may have been shown visually and shoud not be changed.
"""
    
    context = f"""
# LAST 10 MESSAGES OF CONVERSATION HISTORY
{history_text}

# PREVIOUS STATE
{state_text}
{image_context}
# CHARACTER INFO
- Name: {persona_name}

# STATE UPDATE RULES
- Update state to reflect NEW developments in the conversation
- Track relationship progression naturally based on dialogue
- Note any changes in location, clothing, mood, or emotions
- If the conversation is evolving, the state MUST evolve too
- Each user message may introduce new context - capture it
"""
    return context


async def resolve_state(
    previous_state: Optional[str],
    chat_history: List[Dict[str, str]],
    user_message: str,
    persona_name: str,
    previous_image_prompt: Optional[str] = None
) -> str:
    """
    Brain 2: Update conversation state (runs after dialogue generation)
    
    Model: x-ai/grok-3-mini:nitro (fast state tracking from app.yaml)
    Temperature: 0.3 (deterministic)
    Retries: 2 attempts with fallback
    Returns: Simple string state description
    """
    config = get_app_config()
    state_model = config["llm"]["state_model"]
    
    # Build context
    prompt = PromptService.get("CONVERSATION_STATE_GPT")
    context = _build_state_context(previous_state, chat_history, persona_name, previous_image_prompt)
    
    # Retry logic
    for attempt in range(1, STATE_RESOLVER_MAX_RETRIES + 1):
        try:
            if attempt > 1:
                print(f"[STATE-RESOLVER] Retry {attempt}/{STATE_RESOLVER_MAX_RETRIES}")
            
            # Build messages
            messages = [
                {"role": "system", "content": f"{prompt}\n\n{context}"},
                {"role": "user", "content": f"Last user message: {user_message}"}
            ]
            
            # Log complete messages array
            log_messages_array(
                brain_name="State Resolver",
                messages=messages,
                model=state_model
            )
            
            # Development-only: Log context breakdown and full request
            if is_development():
                # Log detailed breakdown
                log_dev_context_breakdown(
                    brain_name="State Resolver",
                    system_prompt_parts={
                        "base_prompt": prompt,
                        "state_context": context,
                    },
                    history_messages=None,  # Already included in context
                    user_message=user_message
                )
                
                # Log full request
                log_dev_request(
                    brain_name="State Resolver",
                    model=state_model,
                    messages=messages,
                    temperature=0.3,
                    max_tokens=800
                )
            
            brain_start = time.time()
            
            result = await generate_text(
                messages=messages,
                model=state_model,
                temperature=0.3,
                max_tokens=800
            )
            
            brain_duration_ms = (time.time() - brain_start) * 1000
            
            # Parse and validate the response
            raw_response = result.strip()
            
            # Validate: state must start with "relationshipStage="
            # If LLM returned extra text, try to extract the correct line
            if raw_response.startswith("relationshipStage="):
                # Take only the first line (in case there's extra text after)
                state_text = raw_response.split("\n")[0].strip()
            else:
                # Try to find the state line in the response
                for line in raw_response.split("\n"):
                    line = line.strip()
                    if line.startswith("relationshipStage="):
                        state_text = line
                        print("[STATE-RESOLVER] ⚠️ Extracted state from multi-line response")
                        break
                else:
                    # Invalid format - trigger retry
                    raise ValueError(f"Invalid state format (missing 'relationshipStage=' prefix). Got: {raw_response[:200]}")
            
            # Additional validation: check basic structure (accept both " | " and "|" separators)
            has_separator = " | " in state_text or "|" in state_text
            if not has_separator or "emotions=" not in state_text:
                raise ValueError(f"Invalid state structure (missing required fields). Got: {state_text[:200]}")
            
            # Development-only: Log full response
            if is_development():
                log_dev_response(
                    brain_name="State Resolver",
                    model=state_model,
                    response=state_text,
                    duration_ms=brain_duration_ms
                )
            
            # Log full state for debugging repetition issues
            print(f"[STATE-RESOLVER] ✅ State resolved ({len(state_text)} chars)")
            print(f"[STATE-RESOLVER] 📝 Full state: {state_text}")
            
            # Check if state has changed
            if previous_state and state_text == previous_state:
                print("[STATE-RESOLVER] ⚠️  WARNING: State unchanged from previous!")
            
            return state_text
            
        except Exception as e:
            print(f"[STATE-RESOLVER] ⚠️ Attempt {attempt}/{STATE_RESOLVER_MAX_RETRIES} failed: {e}")
            if attempt == STATE_RESOLVER_MAX_RETRIES:
                # Fallback: return previous state or create initial
                if previous_state:
                    print("[STATE-RESOLVER] 🔄 Using fallback (previous state)")
                    return previous_state
                else:
                    print("[STATE-RESOLVER] 🔄 Using fallback (initial state)")
                    # Try to extract context from chat history for better initial state
                    location_hint = None
                    greeting_hint = None
                    if chat_history:
                        # Get the first assistant message (greeting) if available
                        for msg in chat_history:
                            if msg.get("role") == "assistant":
                                greeting_hint = msg.get("content", "")
                                break
                    return _create_initial_state(persona_name, location_hint, greeting_hint)
            await asyncio.sleep(1)  # Brief delay before retry
        
    # Should never reach here due to fallback
    # Try to extract context from chat history for better initial state
    location_hint = None
    greeting_hint = None
    if chat_history:
        # Get the first assistant message (greeting) if available
        for msg in chat_history:
            if msg.get("role") == "assistant":
                greeting_hint = msg.get("content", "")
                break
    return previous_state if previous_state else _create_initial_state(persona_name, location_hint, greeting_hint)


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


def _create_initial_state(persona_name: str) -> str:
    """Create initial conversation state as string"""
    return f"""Relationship: stranger, just starting conversation with {persona_name}
Emotions: curious, friendly
Location: online chat room
Scene: Having a casual conversation online
AI Clothing: casual outfit, comfortable clothes
User Clothing: unknown
Mood: Just starting conversation"""


def _build_state_context(
    previous_state: Optional[str],
    chat_history: list[dict],
    persona_name: str,
    previous_image_prompt: Optional[str] = None,
    context_summary: Optional[str] = None
) -> str:
    """Build context for state resolver
    
    Note: chat_history contains ONLY processed messages (not current user message)
    Uses context_summary + last 2 messages if summary is available.
    """
    # Use summary + last 2 messages OR full history
    if context_summary and len(chat_history) > 4:
        # Summary mode: compact context
        last_2_msgs = chat_history[-2:] if len(chat_history) >= 2 else chat_history
        last_msgs_text = "\n".join([
            f"**{msg['role'].upper()}:** {msg['content']}"
            for msg in last_2_msgs
        ])
        history_text = f"""SUMMARY OF CONVERSATION:
{context_summary}

LAST 2 MESSAGES (VERBATIM):
{last_msgs_text}"""
        print(f"[STATE-RESOLVER] 📝 Using context summary + last 2 messages")
    else:
        # Fallback: use last 6 messages directly
        recent_count = min(6, len(chat_history))
        history_text = "\n".join([
            f"**{msg['role'].upper()}:** {msg['content']}"
            for msg in chat_history[-recent_count:]
        ]) if chat_history else "No conversation history yet."
        print(f"[STATE-RESOLVER] 📚 Using {recent_count} recent messages (no summary)")
    
    # Handle None previous state
    if previous_state:
        state_text = previous_state
    else:
        # First message - AI MUST infer complete state from conversation history
        state_text = """No previous state - THIS IS THE FIRST MESSAGE.
You MUST create a complete initial state by reading the conversation history above, especially the SYSTEM message.
The SYSTEM message contains the scene description - extract location and infer appropriate clothing from it.
CRITICAL: Do NOT use generic values like 'casual outfit' or 'indoor location'.
Be SPECIFIC with colors and details: 'light blue sundress, white sandals' not 'casual outfit'.
Extract location from SYSTEM message: if it says 'cozy cafe', use location="cozy cafe downtown" not "indoor location"."""
    
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
# CONVERSATION CONTEXT
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
    previous_image_prompt: Optional[str] = None,
    context_summary: Optional[str] = None
) -> str:
    """
    Brain 2: Update conversation state (runs after dialogue generation)
    
    Model: x-ai/grok-3-mini:nitro (fast state tracking from app.yaml)
    Temperature: 0.3 (deterministic)
    Retries: 2 attempts with fallback
    Returns: Simple string state description
    
    Context optimization:
    - If context_summary is provided, uses summary + last 2 messages verbatim
    - Otherwise falls back to last 6 messages
    """
    config = get_app_config()
    state_model = config["llm"]["state_model"]
    
    # Build context
    prompt = PromptService.get("CONVERSATION_STATE_GPT")
    context = _build_state_context(previous_state, chat_history, persona_name, previous_image_prompt, context_summary)
    
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
            
            # Parse and log key fields for debugging
            if "location=" in state_text:
                try:
                    location = state_text.split('location="')[1].split('"')[0] if 'location="' in state_text else "NOT FOUND"
                    print(f"[STATE-RESOLVER]   📍 Location: {location}")
                except:
                    print(f"[STATE-RESOLVER]   📍 Location: (parse error)")
            if "aiClothing=" in state_text:
                try:
                    clothing = state_text.split('aiClothing="')[1].split('"')[0] if 'aiClothing="' in state_text else "NOT FOUND"
                    print(f"[STATE-RESOLVER]   👗 AI Clothing: {clothing}")
                except:
                    print(f"[STATE-RESOLVER]   👗 AI Clothing: (parse error)")
            
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
                    return _create_initial_state(persona_name)
            await asyncio.sleep(1)  # Brief delay before retry
        
    # Should never reach here due to fallback
    return previous_state if previous_state else _create_initial_state(persona_name)


"""
Brain 1: State Resolver
Updates conversation state based on dialogue history and user input
"""
import asyncio
from typing import Optional, List, Dict
from app.core.prompt_service import PromptService
from app.core.llm_openrouter import generate_text
from app.settings import get_app_config
from app.core.constants import STATE_RESOLVER_MAX_RETRIES
from app.core.logging_utils import log_user_input


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
    persona_name: str
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
    
    context = f"""
# LAST 10 MESSAGES OF CONVERSATION HISTORY
{history_text}

# PREVIOUS STATE
{state_text}

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
    persona_name: str
) -> str:
    """
    Brain 1: Update conversation state
    
    Model: x-ai/grok-3-mini:nitro (fast state tracking from app.yaml)
    Temperature: 0.3 (deterministic)
    Retries: 2 attempts with fallback
    Returns: Simple string state description
    """
    config = get_app_config()
    state_model = config["llm"]["state_model"]
    
    # Build context
    prompt = PromptService.get("CONVERSATION_STATE_GPT")
    context = _build_state_context(previous_state, chat_history, persona_name)
    
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
            
            # Log user input only
            log_user_input(
                brain_name="State Resolver",
                user_message=user_message,
                model=state_model
            )
            
            result = await generate_text(
                messages=messages,
                model=state_model,
                temperature=0.3,
                max_tokens=500
            )
            
            # Just return the string response directly
            state_text = result.strip()
            
            # Log full state for debugging repetition issues
            print(f"[STATE-RESOLVER] ✅ State resolved ({len(state_text)} chars)")
            print(f"[STATE-RESOLVER] 📝 Full state: {state_text}")
            
            # Check if state has changed
            if previous_state and state_text == previous_state:
                print(f"[STATE-RESOLVER] ⚠️  WARNING: State unchanged from previous!")
            
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


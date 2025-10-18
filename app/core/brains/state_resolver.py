"""
Brain 1: State Resolver
Updates conversation state based on dialogue history and user input
"""
import asyncio
import json
from typing import Optional, List, Dict
from app.core.schemas import FullState, RelationshipState, SceneState, MetaState
from app.core.prompt_service import PromptService
from app.core.llm_openrouter import generate_text
from app.settings import get_app_config
from app.core.constants import STATE_RESOLVER_MAX_RETRIES
from app.core.logging_utils import log_prompt_details


def _create_initial_state(persona_name: str) -> FullState:
    """Create initial conversation state"""
    return FullState(
        rel=RelationshipState(
            relationshipStage="stranger",
            emotions="curious, friendly",
            moodNotes="Just starting conversation"
        ),
        scene=SceneState(
            location="online chat room",
            description="Having a casual conversation online",
            aiClothing="casual outfit, comfortable clothes",
            userClothing="unknown"
        ),
        meta=MetaState(
            terminateDialog=False,
            terminateReason=""
        )
    )


def _build_state_context(
    previous_state: Optional[FullState],
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
    state_text = json.dumps(previous_state.dict(), indent=2) if previous_state else "null"
    
    context = f"""
# LAST 10 MESSAGES OF CONVERSATION HISTORY
{history_text}

# PREVIOUS STATE
{state_text}

# CHARACTER INFO
- Name: {persona_name}
"""
    return context


async def resolve_state(
    previous_state: Optional[FullState],
    chat_history: List[Dict[str, str]],
    user_message: str,
    persona_name: str
) -> FullState:
    """
    Brain 1: Update conversation state
    
    Model: x-ai/grok-3-mini:nitro (fast state tracking from app.yaml)
    Temperature: 0.3 (deterministic)
    Retries: 2 attempts with fallback
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
            
            # Build messages for logging
            messages = [
                {"role": "system", "content": f"{prompt}\n\n{context}"},
                {"role": "user", "content": f"Last user message: {user_message}"}
            ]
            
            # Log full prompt details
            log_prompt_details(
                brain_name="State Resolver",
                messages=messages,
                model=state_model,
                temperature=0.3,
                max_tokens=500
            )
            
            result = await generate_text(
                messages=messages,
                model=state_model,
                temperature=0.3,
                max_tokens=500
            )
            
            # Parse JSON response
            result_text = result.strip()
            # Remove markdown code blocks if present
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
            result_text = result_text.strip()
            
            state_dict = json.loads(result_text)
            new_state = FullState(**state_dict)
            
            print(f"[STATE-RESOLVER] ✅ State resolved: {new_state.rel.relationshipStage}, {new_state.scene.location}")
            return new_state
            
        except Exception as e:
            print(f"[STATE-RESOLVER] ⚠️ Attempt {attempt}/2 failed: {e}")
            if attempt == 2:
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


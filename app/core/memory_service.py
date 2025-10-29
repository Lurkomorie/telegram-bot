"""
Memory Service
Extracts and maintains conversation memory for context retention
"""
import asyncio
from uuid import UUID
from app.core.prompt_service import PromptService
from app.core.llm_openrouter import generate_text
from app.settings import get_app_config
from app.db.base import get_db
from app.db import crud
from app.core.logging_utils import log_verbose, log_always


async def update_memory(
    chat_id: UUID,
    user_message: str,
    ai_message: str,
    current_memory: str = None
) -> str:
    """
    Update memory by analyzing recent conversation exchange
    
    Args:
        chat_id: Chat UUID
        user_message: The last user message
        ai_message: The last AI response
        current_memory: Existing memory string (None if first time)
    
    Returns:
        Updated memory string
    """
    try:
        log_verbose(f"[MEMORY] 🧠 Updating memory for chat {chat_id}")
        
        # Get prompt template
        prompt_template = PromptService.get("MEMORY_EXTRACTOR_GPT")
        
        # Format prompt with context
        prompt = prompt_template.format(
            current_memory=current_memory or "No memory yet. This is the first interaction.",
            user_message=user_message,
            ai_message=ai_message
        )
        
        # Get config
        config = get_app_config()
        
        # Use a cheaper, faster model for memory extraction
        # You can use the same model as dialogue or a cheaper one
        memory_model = config["llm"].get("memory_model", config["llm"]["model"])
        
        log_verbose(f"[MEMORY]    Current memory length: {len(current_memory or '')}")
        log_verbose(f"[MEMORY]    User message: {user_message[:60]}...")
        log_verbose(f"[MEMORY]    AI message: {ai_message[:60]}...")
        
        # Call LLM to extract/update memory
        messages = [
            {"role": "user", "content": prompt}
        ]
        
        response = await generate_text(
            messages=messages,
            model=memory_model,
            temperature=0.3,  # Low temperature for consistent extraction
            max_tokens=1000  # Allow for growing memory
        )
        
        updated_memory = response.strip()
        
        # If response is empty or too short, keep existing memory
        if not updated_memory or len(updated_memory) < 10:
            log_verbose(f"[MEMORY] ⚠️  Empty or invalid response, keeping existing memory")
            return current_memory or ""
        
        log_always(f"[MEMORY] ✅ Memory updated ({len(updated_memory)} chars)")
        log_verbose(f"[MEMORY]    Preview: {updated_memory[:150]}...")
        
        return updated_memory
        
    except Exception as e:
        log_always(f"[MEMORY] ❌ Error updating memory: {e}")
        # On error, return existing memory unchanged
        return current_memory or ""


async def trigger_memory_update(
    chat_id: UUID,
    user_message: str,
    ai_message: str
):
    """
    Fire-and-forget memory update
    Fetches current memory, updates it, and saves back to database
    
    This runs in the background and doesn't block the pipeline
    """
    try:
        log_verbose(f"[MEMORY] 🚀 Background memory update triggered for chat {chat_id}")
        
        # Fetch current memory from database
        with get_db() as db:
            chat = crud.get_chat_by_id(db, chat_id)
            if not chat:
                log_verbose(f"[MEMORY] ⚠️  Chat {chat_id} not found")
                return
            
            current_memory = chat.memory
        
        # Update memory
        updated_memory = await update_memory(
            chat_id=chat_id,
            user_message=user_message,
            ai_message=ai_message,
            current_memory=current_memory
        )
        
        # Save updated memory back to database
        with get_db() as db:
            crud.update_chat_memory(db, chat_id, updated_memory)
        
        log_always(f"[MEMORY] ✅ Memory saved to database")
        
    except Exception as e:
        log_always(f"[MEMORY] ❌ Background memory update failed: {e}")
        # Silently fail - memory update is not critical to user experience


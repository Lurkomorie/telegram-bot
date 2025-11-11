"""
Memory Service
Extracts and maintains conversation memory for context retention
"""
import asyncio
import re
from typing import List, Dict, Tuple
from uuid import UUID
from app.core.prompt_service import PromptService
from app.core.llm_openrouter import generate_text
from app.settings import get_app_config
from app.db.base import get_db
from app.db import crud
from app.core.logging_utils import log_verbose, log_always


def _validate_memory_quality(updated_memory: str, current_memory: str) -> Tuple[bool, str]:
    """
    Validate memory quality to catch common issues
    
    Returns:
        (is_valid, reason) - True if memory passes validation, False otherwise
    """
    # Check if it's just the placeholder
    if updated_memory.strip() in ["No memory yet. This is the first interaction.", "No memory yet.", ""]:
        # This is OK if current memory was also empty/placeholder
        if not current_memory or current_memory.strip() in ["No memory yet. This is the first interaction.", "No memory yet.", ""]:
            return True, "empty memory acceptable for first interaction"
        else:
            return False, "reverted to placeholder when memory existed"
    
    # Check minimum length for actual memories
    if len(updated_memory) < 30:
        return False, f"too short ({len(updated_memory)} chars)"
    
    # Check for role confusion - user should not be described as AI
    role_confusion_patterns = [
        r"user is an? ai",
        r"user is an? assistant",
        r"user is an? conversation",
        r"user is an? chatbot",
        r"user shows concern about the user",
        r"user.*\b(wings|tail|horns|persona)\b",  # Physical AI character traits attributed to user
    ]
    
    for pattern in role_confusion_patterns:
        if re.search(pattern, updated_memory.lower()):
            return False, f"role confusion detected (pattern: {pattern})"
    
    # Check for overly vague/generic phrases
    vague_phrases = [
        "user is interested in",
        "user engaged in",
        "user participated in",
        "user was described as",
    ]
    
    # Count vague phrases - if too many, memory is low quality
    vague_count = sum(1 for phrase in vague_phrases if phrase in updated_memory.lower())
    total_sentences = updated_memory.count('.') + 1
    
    if total_sentences >= 3 and vague_count >= total_sentences * 0.6:
        return False, f"too many vague phrases ({vague_count}/{total_sentences} sentences)"
    
    # Check if memory actually added something new (unless it's truly unchanged)
    if current_memory and len(updated_memory) < len(current_memory):
        # Memory got shorter - this might be valid if facts were consolidated, but warn
        log_verbose(f"[MEMORY] ⚠️  Memory got shorter: {len(current_memory)} -> {len(updated_memory)}")
    
    return True, "passed validation"


def _format_conversation_history(chat_history: List[Dict[str, str]]) -> str:
    """
    Format conversation history for memory extraction prompt
    
    Args:
        chat_history: List of messages with 'role' and 'content' keys
    
    Returns:
        Formatted conversation string
    """
    if not chat_history:
        return "No previous conversation history."
    
    formatted_messages = []
    for msg in chat_history:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        
        # Format role labels clearly
        if role == "user":
            label = "USER (human)"
        elif role == "assistant":
            label = "ASSISTANT (AI character)"
        else:
            label = role.upper()
        
        formatted_messages.append(f"{label}: {content}")
    
    return "\n\n".join(formatted_messages)


async def update_memory(
    chat_id: UUID,
    chat_history: List[Dict[str, str]],
    current_memory: str = None
) -> str:
    """
    Update memory by analyzing recent conversation history
    
    Args:
        chat_id: Chat UUID
        chat_history: Recent conversation messages (list of {role, content} dicts)
        current_memory: Existing memory string (None if first time)
    
    Returns:
        Updated memory string
    """
    try:
        log_verbose(f"[MEMORY] 🧠 Updating memory for chat {chat_id}")
        
        # Get prompt template
        prompt_template = PromptService.get("MEMORY_EXTRACTOR_GPT")
        
        # Format conversation history
        conversation_history = _format_conversation_history(chat_history)
        
        # Format prompt with context
        prompt = prompt_template.format(
            current_memory=current_memory or "No memory yet. This is the first interaction.",
            conversation_history=conversation_history
        )
        
        # Get config
        config = get_app_config()
        
        # Use a cheaper, faster model for memory extraction
        # You can use the same model as dialogue or a cheaper one
        memory_model = config["llm"].get("memory_model", config["llm"]["model"])
        
        log_verbose(f"[MEMORY]    Current memory length: {len(current_memory or '')}")
        log_verbose(f"[MEMORY]    Chat history: {len(chat_history)} messages")
        log_verbose(f"[MEMORY]    Using model: {memory_model}")
        
        # Call LLM to extract/update memory
        messages = [
            {"role": "user", "content": prompt}
        ]
        
        response = await generate_text(
            messages=messages,
            model=memory_model,
            temperature=0.5,  # Slightly higher for better extraction quality
            max_tokens=1500  # Allow for growing memory
        )
        
        updated_memory = response.strip()
        
        # Validate memory quality
        is_valid, reason = _validate_memory_quality(updated_memory, current_memory)
        
        if not is_valid:
            log_always(f"[MEMORY] ❌ Validation failed: {reason}")
            log_always(f"[MEMORY]    Rejected memory preview: {updated_memory[:200]}...")
            log_always(f"[MEMORY] 🔄 Keeping existing memory")
            return current_memory or ""
        
        log_verbose(f"[MEMORY] ✅ Validation passed: {reason}")
        
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
    Fetches current memory and recent chat history, updates it, and saves back to database
    
    This runs in the background and doesn't block the pipeline
    """
    try:
        log_verbose(f"[MEMORY] 🚀 Background memory update triggered for chat {chat_id}")
        
        # Fetch current memory and recent messages from database
        with get_db() as db:
            chat = crud.get_chat_by_id(db, chat_id)
            if not chat:
                log_verbose(f"[MEMORY] ⚠️  Chat {chat_id} not found")
                return
            
            current_memory = chat.memory
            
            # Get last 15 messages for context (more context = better extraction)
            messages = crud.get_chat_messages(db, chat_id, limit=15)
            
            # Build chat history in the format expected by update_memory
            chat_history = [
                {"role": m.role, "content": m.text} 
                for m in messages 
                if m.text
            ]
        
        log_verbose(f"[MEMORY]    Fetched {len(chat_history)} messages for context")
        
        # Update memory
        updated_memory = await update_memory(
            chat_id=chat_id,
            chat_history=chat_history,
            current_memory=current_memory
        )
        
        # Save updated memory back to database
        with get_db() as db:
            crud.update_chat_memory(db, chat_id, updated_memory)
        
        log_always(f"[MEMORY] ✅ Memory saved to database")
        
    except Exception as e:
        log_always(f"[MEMORY] ❌ Background memory update failed: {e}")
        # Silently fail - memory update is not critical to user experience


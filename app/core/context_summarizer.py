"""
Context Summarizer Service
Generates compact summaries of conversation history to reduce LLM context size.
Saves summary to chat.ext["context_summary"] for persistence.
"""
from typing import List, Dict, Optional, Tuple
from uuid import UUID

from app.core.prompt_service import PromptService
from app.core.llm_openrouter import generate_text
from app.core.logging_utils import log_verbose, log_always
from app.settings import get_app_config


def format_history_for_summary(chat_history: List[Dict[str, str]]) -> str:
    """Format chat history for the summary prompt"""
    if not chat_history:
        return "No conversation history."
    
    formatted = []
    for msg in chat_history:
        role = "User" if msg["role"] == "user" else "AI"
        content = msg["content"][:300]  # Truncate long messages
        if len(msg["content"]) > 300:
            content += "..."
        formatted.append(f"{role}: {content}")
    
    return "\n".join(formatted)


async def generate_context_summary(
    chat_history: List[Dict[str, str]],
    persona_name: str = "AI"
) -> str:
    """
    Generate a compact summary of conversation history using a cheap model.
    
    Args:
        chat_history: Full conversation history (up to 20 messages)
        persona_name: Name of the AI persona
    
    Returns:
        Compact summary string (max ~400 chars)
    """
    if not chat_history or len(chat_history) < 3:
        # Not enough history to summarize
        return ""
    
    config = get_app_config()
    summary_model = config["llm"].get("summary_model", "mistralai/ministral-3b")
    
    prompt = PromptService.get("CONTEXT_SUMMARY_GPT")
    history_text = format_history_for_summary(chat_history)
    
    user_content = f"""Character name: {persona_name}

CONVERSATION HISTORY ({len(chat_history)} messages):
{history_text}

Now generate a compact summary following the format above."""
    
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": user_content}
    ]
    
    try:
        log_verbose(f"[CONTEXT-SUMMARY] 🧠 Generating summary for {len(chat_history)} messages...")
        
        response = await generate_text(
            messages=messages,
            model=summary_model,
            temperature=0.3,
            max_tokens=250  # Keep it short
        )
        
        summary = response.strip()
        log_verbose(f"[CONTEXT-SUMMARY] ✅ Summary generated ({len(summary)} chars)")
        log_verbose(f"[CONTEXT-SUMMARY]    Preview: {summary[:100]}...")
        
        return summary
        
    except Exception as e:
        log_always(f"[CONTEXT-SUMMARY] ❌ Error generating summary: {e}")
        return ""


def build_summarized_context(
    summary: str,
    chat_history: List[Dict[str, str]],
    current_user_message: str,
    last_n_verbatim: int = 2
) -> Tuple[str, List[Dict[str, str]]]:
    """
    Build context using summary + last N messages verbatim.
    
    Returns:
        Tuple of (context_block_for_system_prompt, messages_to_append)
        
    The context_block goes into the system prompt.
    The messages_to_append are added to the messages array (with current_user_message last).
    """
    # Extract last N messages verbatim
    last_messages = chat_history[-last_n_verbatim:] if len(chat_history) >= last_n_verbatim else chat_history
    
    # Build context block for system prompt
    context_parts = []
    
    if summary:
        context_parts.append(f"""# CONVERSATION CONTEXT (SUMMARY)
{summary}""")
    
    # Add last 2 messages section header
    if last_messages:
        last_msgs_text = "\n".join([
            f"**{msg['role'].upper()}:** {msg['content']}"
            for msg in last_messages
        ])
        context_parts.append(f"""# LAST {len(last_messages)} MESSAGES (VERBATIM)
{last_msgs_text}""")
    
    context_parts.append("""# RESPONSE INSTRUCTIONS
- The user's CURRENT message is below (the one you MUST respond to)
- Use the summary and last messages for context only
- Respond DIRECTLY to the current user message""")
    
    context_block = "\n\n".join(context_parts)
    
    # Messages to append: just the current user message (last 2 are in context block)
    messages_to_append = [
        {"role": "user", "content": current_user_message}
    ]
    
    return context_block, messages_to_append


def get_context_for_brain(
    summary: Optional[str],
    chat_history: List[Dict[str, str]],
    current_user_message: str,
    include_current_in_messages: bool = True
) -> Tuple[str, List[Dict[str, str]]]:
    """
    Get formatted context for any brain.
    
    Args:
        summary: Pre-generated summary (from chat.ext) or None
        chat_history: Recent chat history
        current_user_message: The message to respond to
        include_current_in_messages: If True, add current message to messages list
    
    Returns:
        (context_block, messages_list)
        - context_block: String to add to system prompt
        - messages_list: Messages to add after system message
    """
    # If no summary or short history, use last messages directly
    if not summary or len(chat_history) <= 4:
        # Short history - just use last 4 messages + current
        recent = chat_history[-4:] if chat_history else []
        
        context_block = ""
        if recent:
            msgs_text = "\n".join([
                f"**{msg['role'].upper()}:** {msg['content']}"
                for msg in recent
            ])
            context_block = f"""# RECENT CONVERSATION
{msgs_text}

# RESPONSE INSTRUCTIONS
Respond to the user's CURRENT message below."""
        
        messages = []
        if include_current_in_messages:
            messages.append({"role": "user", "content": current_user_message})
        
        return context_block, messages
    
    # Use summary + last 2 verbatim
    return build_summarized_context(
        summary=summary,
        chat_history=chat_history,
        current_user_message=current_user_message,
        last_n_verbatim=2
    )


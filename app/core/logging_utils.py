"""
Logging utilities for conditional verbose logging in development
"""
import os
from typing import Any


def is_development() -> bool:
    """Check if running in development mode"""
    env = os.getenv("ENVIRONMENT", "production").lower()
    return env in ["development", "dev", "local"]


def log_verbose(message: str, *args: Any) -> None:
    """Log message only in development mode"""
    if is_development():
        if args:
            print(message, *args)
        else:
            print(message)


def log_always(message: str, *args: Any) -> None:
    """Always log message (both dev and production)"""
    if args:
        print(message, *args)
    else:
        print(message)


def log_user_input(
    brain_name: str,
    user_message: str,
    model: str
) -> None:
    """Log only the user input being sent to the LLM"""
    print(f"[{brain_name}] 📤 Sending to {model}: {user_message[:100]}{'...' if len(user_message) > 100 else ''}")


def log_messages_array(
    brain_name: str,
    messages: list[dict],
    model: str
) -> None:
    """
    Log complete messages array being sent to LLM prompts
    Logs both full array and compact view of last 10 messages
    """
    print(f"\n{'='*80}")
    print(f"[{brain_name}] 📨 MESSAGES SENT TO {model}")
    print(f"{'='*80}")
    
    # Log total count
    print(f"Total messages: {len(messages)}")
    
    # Log ALL messages in full detail
    print(f"\n{'─'*80}")
    print("FULL MESSAGE ARRAY:")
    print(f"{'─'*80}")
    for idx, msg in enumerate(messages, 1):
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        print(f"\n[Message {idx}/{len(messages)}] Role: {role.upper()}")
        print(f"Content ({len(content)} chars):")
        print("─── START ───")
        print(content)
        print("─── END ───")
    
    # Log LAST 10 messages in compact format
    print(f"\n{'─'*80}")
    print("LAST 10 MESSAGES (COMPACT VIEW):")
    print(f"{'─'*80}")
    last_ten = messages[-10:] if len(messages) > 10 else messages
    for idx, msg in enumerate(last_ten, 1):
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        # Truncate content for compact view
        preview = content[:150].replace('\n', ' ') + ('...' if len(content) > 150 else '')
        print(f"{idx}. [{role.upper()}] {preview}")
    
    print(f"{'='*80}\n")


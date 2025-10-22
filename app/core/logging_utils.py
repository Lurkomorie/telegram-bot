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
    Log minimal summary of messages array being sent to LLM
    Only logs count and roles to avoid cluttering terminal
    """
    # Only log a brief summary - no full prompts
    roles_summary = [msg.get("role", "unknown") for msg in messages]
    total_chars = sum(len(msg.get("content", "")) for msg in messages)
    print(f"[{brain_name}] 📨 Sending to {model}: {len(messages)} messages ({total_chars:,} chars) - Roles: {', '.join(roles_summary)}")


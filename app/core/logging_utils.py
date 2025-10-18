"""
Logging utilities for conditional verbose logging in development
"""
import os
from typing import Any, List, Dict


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


def log_prompt_details(
    brain_name: str,
    messages: List[Dict[str, str]],
    model: str,
    temperature: float,
    max_tokens: int
) -> None:
    """Log full prompt details for LLM calls without truncation"""
    separator = "=" * 80
    print(f"\n{separator}")
    print(f"🧠 {brain_name.upper()} - FULL PROMPT DETAILS")
    print(f"{separator}")
    print(f"Model: {model}")
    print(f"Temperature: {temperature}")
    print(f"Max Tokens: {max_tokens}")
    print(f"{separator}")
    
    for idx, msg in enumerate(messages, 1):
        role = msg.get("role", "unknown").upper()
        content = msg.get("content", "")
        
        print(f"\n[Message {idx}] Role: {role}")
        print(f"Length: {len(content)} characters")
        print(f"{'─' * 80}")
        print(content)
        print(f"{'─' * 80}")
    
    print(f"\n{separator}")
    print(f"END OF {brain_name.upper()} PROMPT")
    print(f"{separator}\n")



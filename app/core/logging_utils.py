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



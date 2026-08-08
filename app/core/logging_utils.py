"""
Logging utilities for conditional verbose logging in development
"""
import builtins
import os
import sys
import time
import json
from typing import Any, Optional
from contextlib import contextmanager

_ORIGINAL_PRINT = builtins.print
_ERROR_ONLY_PRINTS_ENABLED = False


def _looks_like_error_log(message: str) -> bool:
    text = (message or "").lower()
    error_tokens = (
        "error",
        "failed",
        "exception",
        "traceback",
        "fatal",
        "critical",
        "❌",
    )
    return any(token in text for token in error_tokens)


def configure_error_only_prints(enabled: bool = True) -> None:
    """
    Globally suppress non-error print logs when enabled.

    This keeps runtime stdout focused on operational failures only.
    """
    global _ERROR_ONLY_PRINTS_ENABLED

    if enabled and not _ERROR_ONLY_PRINTS_ENABLED:
        def _filtered_print(*args: Any, **kwargs: Any) -> None:
            output_file = kwargs.get("file")
            # Keep explicit stderr writes untouched.
            if output_file not in (None, sys.stdout, sys.__stdout__):
                _ORIGINAL_PRINT(*args, **kwargs)
                return
            message = " ".join(str(arg) for arg in args)
            if _looks_like_error_log(message):
                _ORIGINAL_PRINT(*args, **kwargs)

        builtins.print = _filtered_print
        _ERROR_ONLY_PRINTS_ENABLED = True
        return

    if not enabled and _ERROR_ONLY_PRINTS_ENABLED:
        builtins.print = _ORIGINAL_PRINT
        _ERROR_ONLY_PRINTS_ENABLED = False


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


# ========== DEVELOPMENT-ONLY DETAILED LOGGING ==========

def log_dev_context_breakdown(
    brain_name: str,
    system_prompt_parts: Optional[dict] = None,
    history_messages: Optional[list] = None,
    user_message: Optional[str] = None
) -> None:
    """
    Log detailed breakdown of context components to identify what takes up space
    
    Args:
        brain_name: Name of the brain
        system_prompt_parts: Dict with keys like 'base_prompt', 'memory_context', 'state_context', etc.
        history_messages: List of chat history messages
        user_message: Current user message
    """
    if not is_development():
        return
    
    print(f"\n{'='*80}")
    print(f"[DEV-CONTEXT] 📊 {brain_name} - CONTEXT SIZE BREAKDOWN")
    print(f"{'='*80}")
    
    total_chars = 0
    
    # System prompt breakdown
    if system_prompt_parts:
        print(f"\n🔧 SYSTEM PROMPT COMPONENTS:")
        system_total = 0
        for part_name, part_content in system_prompt_parts.items():
            part_len = len(part_content) if part_content else 0
            system_total += part_len
            total_chars += part_len
            print(f"  • {part_name}: {part_len:,} chars")
        print(f"  {'─'*76}")
        print(f"  SYSTEM TOTAL: {system_total:,} chars")
    
    # Chat history breakdown
    if history_messages:
        print(f"\n💬 CHAT HISTORY:")
        print(f"  • Count: {len(history_messages)} messages")
        history_total = sum(len(msg.get("content", "")) for msg in history_messages)
        total_chars += history_total
        print(f"  • Total size: {history_total:,} chars")
        # Show per-message breakdown
        for i, msg in enumerate(history_messages, 1):
            role = msg.get("role", "unknown")
            content_len = len(msg.get("content", ""))
            print(f"    [{i}] {role}: {content_len:,} chars")
    
    # Current user message
    if user_message:
        user_len = len(user_message)
        total_chars += user_len
        print(f"\n➡️  CURRENT USER MESSAGE: {user_len:,} chars")
    
    print(f"\n{'─'*80}")
    print(f"📦 TOTAL CONTEXT SIZE: {total_chars:,} chars (~{total_chars // 4} tokens)")
    print(f"{'='*80}\n")


def log_dev_request(
    brain_name: str,
    model: str,
    messages: list[dict],
    temperature: float,
    max_tokens: int,
    **kwargs
) -> None:
    """Log full request details in development mode"""
    if not is_development():
        return
    
    print(f"\n{'='*80}")
    print(f"[DEV-LOG] 🧠 {brain_name} - AI REQUEST")
    print(f"{'='*80}")
    print(f"Model: {model}")
    print(f"Temperature: {temperature}")
    print(f"Max Tokens: {max_tokens}")
    
    if kwargs:
        print(f"Additional params: {kwargs}")
    
    print(f"\n📨 MESSAGES ({len(messages)} total):")
    for i, msg in enumerate(messages, 1):
        role = msg.get("role", "unknown").upper()
        content = msg.get("content", "")
        print(f"\n  [{i}] {role} ({len(content):,} chars):")
        print(f"  {'-'*76}")
        # Show first 500 chars for system, full for user/assistant
        if role == "SYSTEM":
            if len(content) > 500:
                print(f"  {content[:500]}")
                print(f"  ... [{len(content) - 500:,} more chars]")
            else:
                print(f"  {content}")
        else:
            print(f"  {content}")
    print(f"{'='*80}\n")


def log_dev_response(
    brain_name: str,
    model: str,
    response: str,
    duration_ms: float
) -> None:
    """Log full response details in development mode"""
    if not is_development():
        return
    
    print(f"\n{'='*80}")
    print(f"[DEV-LOG] 🎯 {brain_name} - AI RESPONSE")
    print(f"{'='*80}")
    print(f"Model: {model}")
    print(f"Duration: {duration_ms:.2f}ms ({duration_ms/1000:.2f}s)")
    print(f"Length: {len(response)} chars")
    print(f"\n📥 RESPONSE:")
    print(f"  {'-'*76}")
    print(f"  {response}")
    print(f"{'='*80}\n")


def log_dev_timing(operation: str, duration_ms: float) -> None:
    """Log operation timing in development mode"""
    if not is_development():
        return
    
    duration_s = duration_ms / 1000
    emoji = "⚡" if duration_s < 1 else "⏱️" if duration_s < 5 else "⏳"
    print(f"[DEV-TIMING] {emoji} {operation}: {duration_ms:.2f}ms ({duration_s:.2f}s)")


def log_dev_section(title: str) -> None:
    """Log section header in development mode"""
    if not is_development():
        return
    
    print(f"\n{'─'*80}")
    print(f"  {title}")
    print(f"{'─'*80}")


@contextmanager
def timer(operation: str):
    """Context manager for timing operations"""
    start = time.time()
    try:
        yield
    finally:
        duration_ms = (time.time() - start) * 1000
        log_dev_timing(operation, duration_ms)


class PipelineTimer:
    """Timer for tracking pipeline stages"""
    
    def __init__(self, name: str):
        self.name = name
        self.stages = {}
        self.start_time = time.time()
        self.current_stage = None
        self.stage_start = None
        
        if is_development():
            print(f"\n{'='*80}")
            print(f"[PIPELINE-TIMER] ⏱️  Starting: {name}")
            print(f"{'='*80}\n")
    
    def start_stage(self, stage_name: str):
        """Start timing a stage"""
        # End previous stage if exists
        if self.current_stage:
            self.end_stage()
        
        self.current_stage = stage_name
        self.stage_start = time.time()
        
        if is_development():
            print(f"[PIPELINE-TIMER] ▶️  {stage_name}")
    
    def end_stage(self):
        """End current stage"""
        if not self.current_stage or not self.stage_start:
            return
        
        duration_ms = (time.time() - self.stage_start) * 1000
        self.stages[self.current_stage] = duration_ms
        
        if is_development():
            duration_s = duration_ms / 1000
            emoji = "⚡" if duration_s < 1 else "✅" if duration_s < 3 else "⏳"
            print(f"[PIPELINE-TIMER] {emoji} {self.current_stage}: {duration_ms:.2f}ms ({duration_s:.2f}s)")
        
        self.current_stage = None
        self.stage_start = None
    
    def finish(self):
        """Finish timing and print summary"""
        # End current stage if exists
        if self.current_stage:
            self.end_stage()
        
        total_ms = (time.time() - self.start_time) * 1000
        
        if is_development():
            print(f"\n{'='*80}")
            print(f"[PIPELINE-TIMER] 🏁 SUMMARY: {self.name}")
            print(f"{'='*80}")
            for stage, duration in self.stages.items():
                percentage = (duration / total_ms) * 100
                print(f"  • {stage}: {duration:.2f}ms ({percentage:.1f}%)")
            print(f"  {'─'*76}")
            print(f"  TOTAL: {total_ms:.2f}ms ({total_ms/1000:.2f}s)")
            print(f"{'='*80}\n")

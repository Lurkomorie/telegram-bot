"""
Logging utilities for conditional verbose logging in development
"""
import os
import time
import json
from typing import Any, Optional
from contextlib import contextmanager


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
        print(f"\n  [{i}] {role} ({len(content)} chars):")
        print(f"  {'-'*76}")
        # Show first 500 chars for system, full for user/assistant
        if role == "SYSTEM":
            if len(content) > 500:
                print(f"  {content[:500]}")
                print(f"  ... [{len(content) - 500} more chars]")
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


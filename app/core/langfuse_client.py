"""
Langfuse client for observability and tracing.
Provides centralized Langfuse instance and helper functions.
"""
from typing import Optional, Any
from contextlib import contextmanager
import os

# Lazy initialization to avoid import errors if langfuse not installed
_langfuse_instance = None
_langfuse_enabled = None


def _is_langfuse_enabled() -> bool:
    """Check if Langfuse is configured"""
    global _langfuse_enabled
    if _langfuse_enabled is None:
        from app.settings import settings
        _langfuse_enabled = bool(
            settings.LANGFUSE_SECRET_KEY and 
            settings.LANGFUSE_PUBLIC_KEY
        )
    return _langfuse_enabled


def get_langfuse():
    """Get or create Langfuse instance (lazy initialization)"""
    global _langfuse_instance
    
    if not _is_langfuse_enabled():
        return None
    
    if _langfuse_instance is None:
        try:
            from langfuse import Langfuse
            from app.settings import settings
            
            _langfuse_instance = Langfuse(
                secret_key=settings.LANGFUSE_SECRET_KEY,
                public_key=settings.LANGFUSE_PUBLIC_KEY,
                host=settings.LANGFUSE_BASE_URL
            )
            print("[LANGFUSE] ✅ Langfuse client initialized")
        except ImportError:
            print("[LANGFUSE] ⚠️ langfuse package not installed")
            return None
        except Exception as e:
            print(f"[LANGFUSE] ⚠️ Failed to initialize: {e}")
            return None
    
    return _langfuse_instance


def create_trace(
    name: str,
    user_id: Optional[int] = None,
    session_id: Optional[str] = None,
    metadata: Optional[dict] = None,
    tags: Optional[list] = None
):
    """Create a new trace for a pipeline execution"""
    langfuse = get_langfuse()
    if not langfuse:
        return None
    
    try:
        trace = langfuse.trace(
            name=name,
            user_id=str(user_id) if user_id else None,
            session_id=session_id,
            metadata=metadata or {},
            tags=tags or []
        )
        return trace
    except Exception as e:
        print(f"[LANGFUSE] ⚠️ Failed to create trace: {e}")
        return None


def create_generation(
    trace,
    name: str,
    model: str,
    input_messages: list,
    output: Optional[str] = None,
    model_parameters: Optional[dict] = None,
    usage: Optional[dict] = None,
    metadata: Optional[dict] = None
):
    """Create a generation (LLM call) within a trace or span"""
    if not trace:
        return None
    
    try:
        generation = trace.generation(
            name=name,
            model=model,
            input=input_messages,
            output=output,
            model_parameters=model_parameters or {},
            usage=usage,
            metadata=metadata or {}
        )
        return generation
    except Exception as e:
        print(f"[LANGFUSE] ⚠️ Failed to create generation: {e}")
        return None


def create_span(
    trace,
    name: str,
    input_data: Optional[Any] = None,
    metadata: Optional[dict] = None
):
    """Create a span within a trace for non-LLM operations"""
    if not trace:
        return None
    
    try:
        span = trace.span(
            name=name,
            input=input_data,
            metadata=metadata or {}
        )
        return span
    except Exception as e:
        print(f"[LANGFUSE] ⚠️ Failed to create span: {e}")
        return None


def end_span(span, output: Optional[Any] = None):
    """End a span with optional output"""
    if not span:
        return
    
    try:
        span.end(output=output)
    except Exception as e:
        print(f"[LANGFUSE] ⚠️ Failed to end span: {e}")


def end_generation(generation, output: str, usage: Optional[dict] = None):
    """End a generation with output and usage stats"""
    if not generation:
        return
    
    try:
        generation.end(output=output, usage=usage)
    except Exception as e:
        print(f"[LANGFUSE] ⚠️ Failed to end generation: {e}")


def flush():
    """Flush pending events to Langfuse"""
    langfuse = get_langfuse()
    if langfuse:
        try:
            langfuse.flush()
        except Exception as e:
            print(f"[LANGFUSE] ⚠️ Failed to flush: {e}")


def get_prompt(name: str, version: Optional[int] = None, fallback: Optional[str] = None) -> Optional[str]:
    """
    Fetch a prompt from Langfuse Prompt Management.
    
    Args:
        name: Prompt name in Langfuse
        version: Specific version (None = latest)
        fallback: Fallback prompt if Langfuse unavailable
    
    Returns:
        Prompt text or fallback
    """
    langfuse = get_langfuse()
    if not langfuse:
        return fallback
    
    try:
        if version:
            prompt = langfuse.get_prompt(name, version=version)
        else:
            prompt = langfuse.get_prompt(name)
        
        # Handle both text and chat prompts
        if hasattr(prompt, 'prompt'):
            return prompt.prompt
        elif hasattr(prompt, 'compile'):
            # Chat prompt - compile without variables for now
            return prompt.compile()
        else:
            return str(prompt)
    except Exception as e:
        print(f"[LANGFUSE] ⚠️ Failed to get prompt '{name}': {e}")
        return fallback


@contextmanager
def trace_context(
    name: str,
    user_id: Optional[int] = None,
    session_id: Optional[str] = None,
    metadata: Optional[dict] = None
):
    """
    Context manager for tracing a pipeline execution.
    Automatically flushes on exit.
    
    Usage:
        with trace_context("message_pipeline", user_id=123) as trace:
            # Do stuff with trace
            pass
    """
    trace = create_trace(name, user_id, session_id, metadata)
    try:
        yield trace
    finally:
        flush()


# Thread-local storage for current trace context
import threading
_trace_context = threading.local()


def set_current_trace(trace):
    """Set the current trace for this thread"""
    _trace_context.trace = trace


def get_current_trace():
    """Get the current trace for this thread"""
    return getattr(_trace_context, 'trace', None)


def clear_current_trace():
    """Clear the current trace for this thread"""
    _trace_context.trace = None


"""
OpenRouter LLM Client (Non-Streaming)
"""
import httpx
import asyncio
from typing import List, Dict
from app.settings import settings, get_app_config


async def generate_text(
    messages: List[Dict[str, str]],
    model: str = None,
    temperature: float = None,
    max_tokens: int = None,
    top_p: float = None,
    frequency_penalty: float = None,
    presence_penalty: float = None,
    timeout_sec: int = None
) -> str:
    """
    Generate text response from OpenRouter (non-streaming)
    
    Args:
        messages: List of {"role": "system|user|assistant", "content": "..."}
        model: Model to use (overrides config default)
        temperature: Override default temperature
        max_tokens: Override default max_tokens
        top_p: Top-p sampling parameter
        frequency_penalty: Frequency penalty parameter
        presence_penalty: Presence penalty parameter
        timeout_sec: Override default timeout
    
    Returns:
        Generated text response
    """
    config = get_app_config()
    llm_config = config["llm"]
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://telegram-bot-app",  # Required for OpenRouter
        "X-Title": "Telegram Roleplay Bot"  # Optional, for OpenRouter analytics
    }
    
    body = {
        "model": model if model is not None else llm_config["model"],
        "messages": messages,
        "temperature": temperature if temperature is not None else llm_config["temperature"],
        "max_tokens": max_tokens if max_tokens is not None else llm_config["max_tokens"],
        "transforms": ["middle-out"]  # Bypass OpenRouter's moderation for adult content
    }
    
    # Add optional parameters if provided
    if top_p is not None:
        body["top_p"] = top_p
    if frequency_penalty is not None:
        body["frequency_penalty"] = frequency_penalty
    if presence_penalty is not None:
        body["presence_penalty"] = presence_penalty
    
    timeout = timeout_sec if timeout_sec is not None else llm_config["timeout_sec"]
    
    from app.core.logging_utils import log_verbose, log_always
    
    # Verbose logging for development
    log_always(f"[LLM] 🤖 Calling {body['model']} (temp={body['temperature']}, max_tokens={body['max_tokens']})")
    log_verbose(f"[LLM] 📊 Full request details:")
    log_verbose(f"[LLM]    Model: {body['model']}")
    log_verbose(f"[LLM]    Temperature: {body['temperature']}")
    log_verbose(f"[LLM]    Max tokens: {body['max_tokens']}")
    if top_p is not None:
        log_verbose(f"[LLM]    Top-p: {top_p}")
    if frequency_penalty is not None:
        log_verbose(f"[LLM]    Frequency penalty: {frequency_penalty}")
    if presence_penalty is not None:
        log_verbose(f"[LLM]    Presence penalty: {presence_penalty}")
    
    log_verbose(f"[LLM] 💬 Messages ({len(messages)} total):")
    for i, msg in enumerate(messages):
        role = msg["role"]
        content = msg["content"]
        log_verbose(f"[LLM]   [{i+1}] {role.upper()}:")
        if role in ["system", "user"] or len(content) < 500:
            log_verbose(f"[LLM]       {content}")
        else:
            log_verbose(f"[LLM]       {content[:200]}... ({len(content)} chars)")
    
    # Retry logic for 5xx errors and timeouts
    max_retries = 3
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(url, json=body, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                result = data["choices"][0]["message"]["content"]
                log_always(f"[LLM] ✅ Response received ({len(result)} chars)")
                log_verbose(f"[LLM] 📝 Response preview: {result[:200]}...")
                return result
                
        except (httpx.TimeoutException, httpx.HTTPStatusError) as e:
            if attempt == max_retries - 1:
                raise Exception(f"OpenRouter API failed after {max_retries} attempts: {str(e)}")
            
            # Exponential backoff
            wait_time = (attempt + 1) * 1.5
            print(f"[LLM] Retry {attempt + 1}/{max_retries} after {wait_time}s...")
            await asyncio.sleep(wait_time)
        
        except Exception as e:
            raise Exception(f"OpenRouter API error: {str(e)}")
    
    raise Exception("OpenRouter API failed unexpectedly")



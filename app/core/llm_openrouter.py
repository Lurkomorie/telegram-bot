"""
OpenRouter LLM Client (Non-Streaming)
"""
import httpx
import asyncio
from typing import List, Dict, Optional
from app.settings import settings, get_app_config
from app.core import analytics_service_tg

# Model pricing (USD per 1M tokens) - (Input, Output)
MODEL_PRICING = {
    "openai/gpt-4o": (5.0, 15.0),
    "openai/gpt-4o-mini": (0.15, 0.6),
    "openai/gpt-4o-2024-08-06": (2.5, 10.0),
    "anthropic/claude-3.5-sonnet": (3.0, 15.0),
    "anthropic/claude-3-haiku": (0.25, 1.25),
    "google/gemini-flash-1.5": (0.075, 0.3),
    "google/gemini-pro-1.5": (3.5, 10.5),
    "meta-llama/llama-3.1-70b-instruct": (0.35, 0.4),
    "meta-llama/llama-3.1-8b-instruct": (0.05, 0.05),
    "liquid/lfm-40b": (0.1, 0.1),
    "gryphe/mythomax-l2-13b": (0.1, 0.1),
    # User models (updated with exact pricing)
    "thedrummer/cydonia-24b-v4.1": (0.30, 0.50),
    "mistralai/ministral-3b": (0.04, 0.04),
    "moonshotai/kimi-k2:nitro": (0.50, 2.40),
}


async def generate_text(
    messages: List[Dict[str, str]],
    model: str = None,
    temperature: float = None,
    max_tokens: int = None,
    top_p: float = None,
    frequency_penalty: float = None,
    presence_penalty: float = None,
    timeout_sec: int = None,
    user_id: Optional[int] = None,
    reasoning: bool = False
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
        user_id: Optional Telegram user ID for cost tracking
        reasoning: Enable reasoning/thinking mode for supported models
    
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
    if reasoning:
        body["reasoning"] = {"effort": "medium"}
    
    timeout = timeout_sec if timeout_sec is not None else llm_config["timeout_sec"]
    
    from app.core.logging_utils import log_verbose, log_always, log_dev_request, log_dev_response
    import time
    
    # Verbose logging for development
    log_always(f"[LLM] 🤖 Calling {body['model']} (temp={body['temperature']}, max_tokens={body['max_tokens']})")
    log_verbose("[LLM] 📊 Full request details:")
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
    
    # Development-only: Log full request details
    log_dev_request(
        brain_name="LLM Client",
        model=body['model'],
        messages=messages,
        temperature=body['temperature'],
        max_tokens=body['max_tokens'],
        top_p=top_p,
        frequency_penalty=frequency_penalty,
        presence_penalty=presence_penalty
    )
    
    # Retry logic for 5xx errors and timeouts
    max_retries = 3
    request_start = time.time()
    
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(url, json=body, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                result = data["choices"][0]["message"]["content"]
                
                # Track token usage and cost if user_id is provided
                if user_id and "usage" in data:
                    usage = data["usage"]
                    prompt_tokens = usage.get("prompt_tokens", 0)
                    completion_tokens = usage.get("completion_tokens", 0)
                    
                    # Calculate cost
                    used_model = data.get("model", body["model"])
                    # Try to match model prefix if exact match not found
                    pricing = MODEL_PRICING.get(used_model)
                    if not pricing:
                        # Fallback: try to find by partial match
                        for key, val in MODEL_PRICING.items():
                            if key in used_model:
                                pricing = val
                                break
                    
                    cost_usd = 0.0
                    if pricing:
                        input_price, output_price = pricing
                        cost_usd = (prompt_tokens / 1_000_000 * input_price) + (completion_tokens / 1_000_000 * output_price)
                    
                    # Log analytics event
                    analytics_service_tg.track_event_tg(
                        client_id=user_id,
                        event_name="llm_cost",
                        meta={
                            "model": used_model,
                            "prompt_tokens": prompt_tokens,
                            "completion_tokens": completion_tokens,
                            "cost_usd": cost_usd
                        }
                    )
                
                request_duration_ms = (time.time() - request_start) * 1000
                
                log_always(f"[LLM] ✅ Response received ({len(result)} chars) in {request_duration_ms:.2f}ms")
                log_verbose(f"[LLM] 📝 Response preview: {result[:200]}...")
                
                # Development-only: Log full response
                log_dev_response(
                    brain_name="LLM Client",
                    model=body['model'],
                    response=result,
                    duration_ms=request_duration_ms
                )
                
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



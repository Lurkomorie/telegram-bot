"""
OpenRouter LLM Client (Non-Streaming)
"""
import httpx
import asyncio
from typing import List, Dict
from app.settings import settings, get_app_config


async def generate_text(
    messages: List[Dict[str, str]],
    temperature: float = None,
    max_tokens: int = None,
    timeout_sec: int = None
) -> str:
    """
    Generate text response from OpenRouter (non-streaming)
    
    Args:
        messages: List of {"role": "system|user|assistant", "content": "..."}
        temperature: Override default temperature
        max_tokens: Override default max_tokens
        timeout_sec: Override default timeout
    
    Returns:
        Generated text response
    """
    config = get_app_config()
    llm_config = config["llm"]
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    body = {
        "model": llm_config["model"],
        "messages": messages,
        "temperature": temperature if temperature is not None else llm_config["temperature"],
        "max_tokens": max_tokens if max_tokens is not None else llm_config["max_tokens"]
    }
    
    timeout = timeout_sec if timeout_sec is not None else llm_config["timeout_sec"]
    
    # Retry logic for 5xx errors and timeouts
    max_retries = 3
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(url, json=body, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                return data["choices"][0]["message"]["content"]
                
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



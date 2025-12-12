"""
Brain: Voice Processor
Transforms dialogue text into ElevenLabs v3 audio-tagged text for expressive TTS.
Adds tags like [whispers], [laughs], [pause], [softly], etc.
"""
import asyncio
from app.core.prompt_service import PromptService
from app.core.llm_openrouter import generate_text
from app.settings import get_app_config
from app.core.logging_utils import log_verbose, log_always, log_messages_array
import time


VOICE_PROCESSOR_MAX_RETRIES = 2


def _clean_text_for_voice(text: str) -> str:
    """
    Clean text by removing markdown formatting that shouldn't be spoken.
    Converts action text in italics to natural spoken form.
    """
    import re
    
    # Remove markdown italic markers (_text_ or *text*)
    # For actions in italics, we'll convert them to spoken descriptions
    text = re.sub(r'_([^_]+)_', r'\1', text)  # Remove _italic_ markers
    text = re.sub(r'\*([^*]+)\*', r'\1', text)  # Remove *bold* markers
    
    # Remove escaped markdown characters
    text = text.replace(r'\*', '*')
    text = text.replace(r'\_', '_')
    text = text.replace(r'\~', '~')
    text = text.replace(r'\`', '`')
    text = text.replace(r'\[', '[')
    text = text.replace(r'\]', ']')
    
    # Clean up multiple spaces/newlines
    text = re.sub(r'\n+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()


def _is_valid_response(text: str) -> bool:
    """Validate response quality"""
    if not text or len(text.strip()) < 5:
        return False
    
    # Must contain at least some of the original content
    # (not just tags)
    import re
    text_without_tags = re.sub(r'\[[^\]]+\]', '', text)
    if len(text_without_tags.strip()) < 5:
        return False
    
    return True


async def process_text_for_voice(
    text: str,
    persona_name: str = "AI"
) -> str:
    """
    Process dialogue text and add ElevenLabs v3 audio tags for expressive delivery.
    
    Args:
        text: Original dialogue text (may contain markdown formatting)
        persona_name: Name of the character for context
    
    Returns:
        Text with audio tags like [whispers], [laughs], [pause], etc.
    """
    config = get_app_config()
    
    # Use a fast, cheap model for this simple transformation
    model = config["llm"].get("followup_model", config["llm"]["model"])
    
    log_always(f"[VOICE-PROC] 🎙️ Processing text for voice ({len(text)} chars)")
    log_verbose(f"[VOICE-PROC]    Persona: {persona_name}")
    log_verbose(f"[VOICE-PROC]    Model: {model}")
    
    # Clean the text first
    cleaned_text = _clean_text_for_voice(text)
    log_verbose(f"[VOICE-PROC]    Cleaned text: {cleaned_text[:100]}...")
    
    # Get the voice processor prompt
    system_prompt = PromptService.get("VOICE_PROCESSOR_GPT")
    
    # Replace persona name in prompt
    system_prompt = system_prompt.replace("{{char.name}}", persona_name)
    
    for attempt in range(1, VOICE_PROCESSOR_MAX_RETRIES + 1):
        try:
            temperature = 0.3 + (attempt - 1) * 0.1  # Low temp for consistency
            
            if attempt > 1:
                log_verbose(f"[VOICE-PROC] Retry {attempt}/{VOICE_PROCESSOR_MAX_RETRIES}")
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": cleaned_text}
            ]
            
            log_messages_array(
                brain_name="Voice Processor",
                messages=messages,
                model=model
            )
            
            start_time = time.time()
            
            response = await generate_text(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=1024  # Should be enough for most messages
            )
            
            duration_ms = (time.time() - start_time) * 1000
            log_verbose(f"[VOICE-PROC] ⏱️ LLM call took {duration_ms:.0f}ms")
            
            result = response.strip()
            
            if _is_valid_response(result):
                log_always(f"[VOICE-PROC] ✅ Added audio tags ({len(result)} chars)")
                log_verbose(f"[VOICE-PROC]    Result preview: {result[:150]}...")
                return result
            else:
                log_verbose(f"[VOICE-PROC] ⚠️ Invalid response, retrying...")
                
        except Exception as e:
            log_always(f"[VOICE-PROC] ⚠️ Attempt {attempt} failed: {e}")
            if attempt == VOICE_PROCESSOR_MAX_RETRIES:
                # Fallback: return cleaned text without tags
                log_always(f"[VOICE-PROC] ⚠️ All attempts failed, using cleaned text")
                return cleaned_text
            await asyncio.sleep(0.3)
    
    # Fallback
    return cleaned_text

"""
ElevenLabs Text-to-Speech Service
Generates voice audio from text using ElevenLabs API v3 with audio tags support.
Converts MP3 to OGG Opus format for Telegram voice messages.
"""
import io
import httpx
from pydub import AudioSegment
from app.settings import settings
from app.core.logging_utils import log_verbose, log_always


# ElevenLabs API endpoint
ELEVENLABS_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"


async def generate_voice(
    text: str,
    voice_id: str = None,
    model_id: str = None
) -> bytes | None:
    """
    Generate voice audio from text using ElevenLabs API.
    
    Args:
        text: Text to convert to speech (can include audio tags like [whispers], [laughs])
        voice_id: ElevenLabs voice ID (defaults to settings.ELEVENLABS_VOICE_ID)
        model_id: ElevenLabs model ID (defaults to settings.ELEVENLABS_MODEL_ID)
    
    Returns:
        OGG Opus audio bytes ready for Telegram send_voice, or None on error
    """
    if not settings.ELEVENLABS_API_KEY:
        log_always("[ELEVENLABS] ❌ ELEVENLABS_API_KEY not configured")
        return None
    
    voice_id = voice_id or settings.ELEVENLABS_VOICE_ID
    model_id = model_id or settings.ELEVENLABS_MODEL_ID
    
    log_always(f"[ELEVENLABS] 🎙️ Generating voice ({len(text)} chars)")
    log_verbose(f"[ELEVENLABS]    Voice ID: {voice_id}")
    log_verbose(f"[ELEVENLABS]    Model: {model_id}")
    log_verbose(f"[ELEVENLABS]    Text preview: {text[:100]}...")
    
    try:
        # Call ElevenLabs API
        mp3_bytes = await _call_elevenlabs_api(text, voice_id, model_id)
        
        if not mp3_bytes:
            return None
        
        log_verbose(f"[ELEVENLABS] ✅ Received MP3 ({len(mp3_bytes)} bytes)")
        
        # Convert MP3 to OGG Opus for Telegram
        ogg_bytes = _convert_mp3_to_ogg_opus(mp3_bytes)
        
        if not ogg_bytes:
            return None
        
        log_always(f"[ELEVENLABS] ✅ Converted to OGG Opus ({len(ogg_bytes)} bytes)")
        
        return ogg_bytes
        
    except Exception as e:
        log_always(f"[ELEVENLABS] ❌ Error generating voice: {type(e).__name__}: {e}")
        return None


async def _call_elevenlabs_api(
    text: str,
    voice_id: str,
    model_id: str
) -> bytes | None:
    """Call ElevenLabs TTS API and return MP3 bytes"""
    url = ELEVENLABS_TTS_URL.format(voice_id=voice_id)
    
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": settings.ELEVENLABS_API_KEY
    }
    
    payload = {
        "text": text,
        "model_id": model_id,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.5
        }
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, json=payload, headers=headers)
        
        if response.status_code == 200:
            return response.content
        else:
            log_always(f"[ELEVENLABS] ❌ API error: {response.status_code}")
            log_verbose(f"[ELEVENLABS]    Response: {response.text[:500]}")
            return None


def _convert_mp3_to_ogg_opus(mp3_bytes: bytes) -> bytes | None:
    """
    Convert MP3 audio bytes to OGG Opus format for Telegram voice messages.
    
    Telegram requires OGG with Opus codec for voice messages.
    Uses pydub + ffmpeg for conversion.
    """
    try:
        # Load MP3 from bytes
        mp3_audio = AudioSegment.from_mp3(io.BytesIO(mp3_bytes))
        
        # Export as OGG Opus
        ogg_buffer = io.BytesIO()
        mp3_audio.export(
            ogg_buffer,
            format="ogg",
            codec="libopus",
            parameters=["-application", "voip"]  # Optimized for voice
        )
        
        ogg_buffer.seek(0)
        return ogg_buffer.read()
        
    except Exception as e:
        log_always(f"[ELEVENLABS] ❌ Audio conversion error: {type(e).__name__}: {e}")
        return None

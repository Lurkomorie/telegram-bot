"""
In-memory cache for preset personas and histories
Loaded at startup, persists for application lifetime
"""
from typing import Dict, List, Optional, Any
import random

# Global cache storage
_CACHE: Dict[str, Any] = {
    "presets": [],           # List of all preset personas (as dicts)
    "by_id": {},            # Dict: persona_id -> persona dict
    "histories": {}         # Dict: persona_id -> list of history dicts
}


def load_cache():
    """Load all preset personas and histories from DB into memory"""
    from app.db.base import get_db
    from app.db import crud
    from app.db.models import PersonaHistoryStart
    
    print("[CACHE] 📦 Loading preset personas and histories into memory...")
    
    with get_db() as db:
        # Load all preset personas
        preset_personas = crud.get_preset_personas(db)
        
        preset_list = []
        for persona in preset_personas:
            # Extract all data from ORM object
            # Translations are now handled by translation_service, not stored in persona dict
            persona_dict = {
                "id": str(persona.id),
                "name": persona.name,
                "key": persona.key,
                "emoji": persona.emoji,
                "small_description": persona.small_description,
                "description": persona.description,
                "prompt": persona.prompt,
                "image_prompt": persona.image_prompt,  # SDXL tags for character appearance
                "intro": persona.intro,
                "badges": persona.badges or [],
                "avatar_url": persona.avatar_url,
                "visibility": persona.visibility,
                "owner_user_id": persona.owner_user_id,
                "order": persona.order if persona.order is not None else 999,
                "main_menu": persona.main_menu if persona.main_menu is not None else True,
                "voice_id": persona.voice_id,  # ElevenLabs voice ID for TTS
            }
            
            preset_list.append(persona_dict)
            
            # Store in by_id lookup
            _CACHE["by_id"][str(persona.id)] = persona_dict
            
            # Load histories for this persona
            histories = db.query(PersonaHistoryStart).filter(
                PersonaHistoryStart.persona_id == persona.id
            ).all()
            
            history_list = []
            for history in histories:
                # Translations are now handled by translation_service, not stored in history dict
                history_dict = {
                    "id": str(history.id),
                    "persona_id": str(history.persona_id),
                    "name": history.name or "Untitled Story",
                    "button_name": history.button_name,  # Short button text
                    "small_description": history.small_description,
                    "description": history.description,
                    "text": history.text,
                    "image_url": history.image_url,
                    "wide_menu_image_url": history.wide_menu_image_url,
                    "image_prompt": history.image_prompt,
                }
                
                history_list.append(history_dict)
            
            _CACHE["histories"][str(persona.id)] = history_list
        
        # Sort preset personas by order field (lower numbers appear first)
        preset_list.sort(key=lambda p: p.get("order", 999))
        _CACHE["presets"] = preset_list
    
    print(f"[CACHE] ✅ Loaded {len(_CACHE['presets'])} personas with {sum(len(h) for h in _CACHE['histories'].values())} total histories")
    print(f"[CACHE] 🌐 Translations are now managed by TranslationService")


def get_preset_personas() -> List[Dict[str, Any]]:
    """Get cached preset personas (already formatted as dicts)"""
    return _CACHE["presets"]


def get_persona_by_id(persona_id: str) -> Optional[Dict[str, Any]]:
    """Get cached persona by ID"""
    return _CACHE["by_id"].get(str(persona_id))


def get_persona_by_key(persona_key: str) -> Optional[Dict[str, Any]]:
    """Get cached persona by key"""
    for persona in _CACHE["presets"]:
        if persona.get("key") == persona_key:
            return persona
    return None


def get_persona_histories(persona_id: str) -> List[Dict[str, Any]]:
    """Get cached histories for a persona"""
    return _CACHE["histories"].get(str(persona_id), [])


def get_random_history(persona_id: str) -> Optional[Dict[str, Any]]:
    """Get random history for persona from cache"""
    histories = _CACHE["histories"].get(str(persona_id), [])
    return random.choice(histories) if histories else None


def get_persona_with_history_by_index(persona_key: str, history_index: int) -> tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Get persona by key and specific history by index
    
    Args:
        persona_key: Persona key (e.g., "kiki")
        history_index: Index of history (0-based)
    
    Returns:
        Tuple of (persona_dict, history_dict) or (None, None) if not found
    """
    persona = get_persona_by_key(persona_key)
    if not persona:
        return None, None
    
    histories = get_persona_histories(persona["id"])
    if history_index < 0 or history_index >= len(histories):
        return persona, None
    
    return persona, histories[history_index]


def is_cache_loaded() -> bool:
    """Check if cache has been loaded"""
    return len(_CACHE["presets"]) > 0


def get_persona_field(persona_dict: Dict[str, Any], field: str, language: str = 'en') -> Any:
    """Get a persona field with translation support
    
    Args:
        persona_dict: Persona dictionary from cache
        field: Field name (e.g., 'name', 'description', 'small_description', 'intro')
        language: Language code (e.g., 'en', 'ru')
    
    Returns:
        Translated field value if available, otherwise fallback to default
    """
    from app.core.translation_service import translation_service
    
    persona_key = persona_dict.get('key')
    if not persona_key:
        # If persona doesn't have a key, return the default field value
        return persona_dict.get(field)
    
    # Try to get translation from translation service
    trans_key = f"{persona_key}.{field}"
    translated = translation_service.get(trans_key, language, fallback=True)
    
    # If translation key was returned unchanged (not found), use default value
    if translated == trans_key:
        return persona_dict.get(field)
    
    return translated


def get_history_field(history_dict: Dict[str, Any], field: str, language: str = 'en') -> Any:
    """Get a history field with translation support
    
    Args:
        history_dict: History dictionary from cache
        field: Field name (e.g., 'name', 'button_name', 'description', 'small_description', 'text')
        language: Language code (e.g., 'en', 'ru')
    
    Returns:
        Translated field value if available, otherwise fallback to default
    """
    from app.core.translation_service import translation_service
    
    # Find persona key and history index from the history dict
    # We need to look up the persona this history belongs to
    persona_id = history_dict.get('persona_id')
    if not persona_id:
        return history_dict.get(field)
    
    # Get persona to find its key
    persona = get_persona_by_id(persona_id)
    if not persona or not persona.get('key'):
        return history_dict.get(field)
    
    persona_key = persona['key']
    
    # Find index of this history in the persona's histories
    histories = get_persona_histories(persona_id)
    history_index = None
    for idx, h in enumerate(histories):
        if h.get('id') == history_dict.get('id'):
            history_index = idx
            break
    
    if history_index is None:
        return history_dict.get(field)
    
    # Build translation key: {persona_key}.history.{field}-{index}
    trans_key = f"{persona_key}.history.{field}-{history_index}"
    translated = translation_service.get(trans_key, language, fallback=True)
    
    # If translation key was returned unchanged (not found), use default value
    if translated == trans_key:
        return history_dict.get(field)
    
    return translated
  
def reload_cache():
    """Reload the persona cache from database"""
    load_cache()


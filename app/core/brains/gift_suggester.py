"""
Gift Suggester Brain
Determines when to suggest a gift and which item based on mood
"""
import random
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

# Gift suggestion probability (5-10%)
SUGGESTION_PROBABILITY = 0.07  # 7%

# Cooldown between suggestions (24 hours)
SUGGESTION_COOLDOWN_HOURS = 24

# Item selection by mood tier
# Higher mood = more expensive gift suggestion
GIFT_TIERS = {
    "low": ["wine", "lipstick", "rose"],      # 0-30 mood: cheaper gifts (40-60 tokens)
    "mid": ["mystery", "rose"],                # 31-60 mood: mid-range (50-100 tokens)
    "high": ["vibrator", "anal_beads", "mystery"]  # 61-100 mood: expensive (100-200 tokens)
}

# Gift display names and emojis
GIFT_INFO = {
    "wine": {"name": "Wine", "name_ru": "Вино", "emoji": "🍷", "price": 60},
    "lipstick": {"name": "Lipstick", "name_ru": "Помада", "emoji": "💄", "price": 40},
    "rose": {"name": "Rose", "name_ru": "Роза", "emoji": "🌹", "price": 50},
    "mystery": {"name": "Mystery Gift", "name_ru": "Подарок", "emoji": "🎁", "price": 100},
    "vibrator": {"name": "Vibrator", "name_ru": "Вибратор", "emoji": "💜", "price": 160},
    "anal_beads": {"name": "Anal Beads", "name_ru": "Шарики", "emoji": "💎", "price": 200},
}


def _get_mood_tier(mood: int) -> str:
    """Get mood tier for gift selection"""
    if mood <= 30:
        return "low"
    elif mood <= 60:
        return "mid"
    else:
        return "high"


def _check_cooldown(chat_ext: Optional[Dict]) -> bool:
    """Check if enough time has passed since last suggestion"""
    if not chat_ext:
        return True
    
    last_suggestion = chat_ext.get("last_gift_suggestion_at")
    if not last_suggestion:
        return True
    
    # Parse datetime if string
    if isinstance(last_suggestion, str):
        try:
            last_suggestion = datetime.fromisoformat(last_suggestion.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return True
    
    # Check if cooldown has passed
    cooldown_end = last_suggestion + timedelta(hours=SUGGESTION_COOLDOWN_HOURS)
    return datetime.utcnow() > cooldown_end


def should_suggest_gift(chat_ext: Optional[Dict], mood: int) -> Dict[str, Any]:
    """
    Determine if we should suggest a gift and which one
    
    Args:
        chat_ext: Chat extended metadata (contains last_gift_suggestion_at)
        mood: Current mood value (0-100)
    
    Returns:
        {
            "should_suggest": bool,
            "item_key": str or None,
            "item_info": dict or None,
            "reason": str
        }
    """
    # Check cooldown first
    if not _check_cooldown(chat_ext):
        return {
            "should_suggest": False,
            "item_key": None,
            "item_info": None,
            "reason": "cooldown_active"
        }
    
    # Random probability check
    if random.random() > SUGGESTION_PROBABILITY:
        return {
            "should_suggest": False,
            "item_key": None,
            "item_info": None,
            "reason": "probability_miss"
        }
    
    # Select item based on mood tier
    tier = _get_mood_tier(mood)
    available_items = GIFT_TIERS[tier]
    selected_item = random.choice(available_items)
    
    return {
        "should_suggest": True,
        "item_key": selected_item,
        "item_info": GIFT_INFO[selected_item],
        "reason": f"mood_tier_{tier}"
    }


def get_gift_dialogue_hint(item_key: str, language: str = "en") -> str:
    """
    Get a hint to append to dialogue for gift suggestion
    
    Args:
        item_key: The gift item key
        language: Language code (en/ru)
    
    Returns:
        Dialogue hint string
    """
    info = GIFT_INFO.get(item_key, GIFT_INFO["wine"])
    
    if language == "ru":
        hints = [
            f"[Мягко намекни, что тебе бы понравился подарок - {info['name_ru']} {info['emoji']}]",
            f"[Упомяни, что {info['name_ru']} {info['emoji']} сделал бы тебя счастливой]",
            f"[Деликатно скажи, что мечтаешь о {info['name_ru']} {info['emoji']}]",
        ]
    else:
        hints = [
            f"[Gently hint that you would love a gift - {info['name']} {info['emoji']}]",
            f"[Mention that a {info['name']} {info['emoji']} would make you happy]",
            f"[Delicately say you've been dreaming about {info['name']} {info['emoji']}]",
        ]
    
    return random.choice(hints)


def get_gift_image_context(item_key: str) -> str:
    """
    Get image context for gift suggestion (holding the gift)
    
    Args:
        item_key: The gift item key
    
    Returns:
        Image context string for prompt
    """
    item_contexts = {
        "wine": "holding wine glass elegantly, wine bottle nearby",
        "lipstick": "applying lipstick seductively, looking at viewer",
        "rose": "holding a beautiful red rose, smelling it",
        "mystery": "holding a wrapped gift box with ribbon",
        "vibrator": "holding a gift suggestively, playful expression",
        "anal_beads": "holding a wrapped gift, teasing smile",
    }
    
    base_context = item_contexts.get(item_key, "holding a gift")
    return f"{base_context}, close-up portrait, offering gesture to viewer"

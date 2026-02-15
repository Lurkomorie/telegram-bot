"""
Gift Suggester Brain
Determines when to suggest a gift and which item based on mood
"""
import random
from typing import Optional, Dict, Any
from app.core.catalog.gifts import get_shop_items_map

# Gift suggestion probability (5-10%)
SUGGESTION_PROBABILITY = 0.3  # 7%

# Minimum total message count before gifts can be suggested (~15 AI messages)
MIN_MESSAGES_FOR_GIFTS = 30

# Cumulative gift tiers — higher mood unlocks more items
# Low tier items are always available, higher tiers add to the pool
GIFT_TIERS = {
    "low": ["wine", "lipstick", "rose"],                              # 0-30 mood: basic gifts only
    "mid": ["wine", "lipstick", "rose", "mystery"],                   # 31-60 mood: + mystery
    "high": ["wine", "lipstick", "rose", "mystery", "vibrator", "anal_beads"]  # 61-100 mood: all gifts unlocked
}

# Gift display names and emojis from shared catalog (config/gifts.yaml)
_SHOP_ITEMS = get_shop_items_map(include_scene_override=False)
GIFT_INFO = {
    key: {
        "name": item.get("name", key),
        "name_ru": item.get("name_ru", item.get("name", key)),
        "emoji": item.get("emoji", "🎁"),
        "price": item.get("price", 0),
    }
    for key, item in _SHOP_ITEMS.items()
}


def _get_mood_tier(mood: int) -> str:
    """Get mood tier for gift selection"""
    if mood <= 30:
        return "low"
    elif mood <= 60:
        return "mid"
    else:
        return "high"


def should_suggest_gift(mood: int, last_suggested_gift: Optional[str] = None, message_count: int = 0) -> Dict[str, Any]:
    """
    Determine if we should suggest a gift and which one
    
    Args:
        mood: Current mood value (0-100)
        last_suggested_gift: Last suggested item key (to avoid repeating)
        message_count: Total chat message count (user + assistant)
    
    Returns:
        {
            "should_suggest": bool,
            "item_key": str or None,
            "item_info": dict or None,
            "reason": str
        }
    """
    # Don't suggest gifts until enough conversation has happened
    if message_count < MIN_MESSAGES_FOR_GIFTS:
        return {
            "should_suggest": False,
            "item_key": None,
            "item_info": None,
            "reason": "too_early"
        }
    
    # Random probability check (7%)
    if random.random() > SUGGESTION_PROBABILITY:
        return {
            "should_suggest": False,
            "item_key": None,
            "item_info": None,
            "reason": "probability_miss"
        }
    
    # Select item based on mood tier
    tier = _get_mood_tier(mood)
    available_items = GIFT_TIERS[tier].copy()
    
    # Exclude last suggested item to avoid repetition
    if last_suggested_gift and last_suggested_gift in available_items:
        available_items.remove(last_suggested_gift)
    
    # If no items left after exclusion, use full tier list
    if not available_items:
        available_items = GIFT_TIERS[tier].copy()
    
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
            f"В конце своего ответа мягко намекни, что тебе бы очень понравился подарок — {info['name_ru']} {info['emoji']}. Вплети это естественно в разговор.",
            f"Ближе к концу ответа упомяни, что {info['name_ru']} {info['emoji']} сделал бы тебя очень счастливой. Скажи это мило и естественно.",
            f"В конце своего ответа деликатно скажи, что мечтаешь о {info['name_ru']} {info['emoji']}. Пусть это звучит как искреннее желание.",
        ]
    else:
        hints = [
            f"At the end of your response, gently hint that you would love to receive a {info['name']} {info['emoji']} as a gift. Weave it naturally into the conversation.",
            f"Near the end of your response, mention that a {info['name']} {info['emoji']} would make you really happy. Say it cutely and naturally.",
            f"At the end of your response, delicately say you've been dreaming about a {info['name']} {info['emoji']}. Make it sound like a genuine wish.",
        ]
    
    return random.choice(hints)


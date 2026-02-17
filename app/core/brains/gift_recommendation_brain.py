"""Gift Recommendation Brain: scene-aware separate gift suggestion messages."""

from __future__ import annotations

import random
import re
from typing import Any, Dict, List

from app.core.catalog.gifts import get_shop_items_map
from app.core.llm_openrouter import generate_text
from app.core.prompt_service import PromptService
from app.settings import get_app_config

EXPLICIT_MARKERS = {
    # EN
    "sex", "fucking", "fuck", "blowjob", "oral", "vibrator", "anal", "penetration", "cum",
    # RU
    "секс", "трах", "еб", "минет", "орал", "вибратор", "аналь", "проник",
}

INTIMATE_MARKERS = {
    # EN
    "kiss", "touch", "naked", "nude", "bed", "moan", "desire", "tease", "horny",
    # RU
    "поцел", "каса", "обнима", "голая", "разд", "стон", "желан", "драз", "возб",
}

REFUSAL_MARKERS = {
    # EN
    "i won't", "i will not", "not in public", "too rough", "only if", "catch me first",
    # RU
    "не буду", "не хочу", "не могу", "не публич", "слишком грубо", "сначала поймай",
}


def _gift_config() -> Dict[str, Any]:
    defaults = {
        "cadence_user_messages": 20,
        "purchase_cooldown_user_messages": 20,
        "min_user_messages_before_suggestions": 20,
    }
    try:
        cfg = get_app_config().get("gift", {})
        if isinstance(cfg, dict):
            merged = dict(defaults)
            merged.update(cfg)
            return merged
    except Exception:
        pass
    return defaults


def _parse_state_fields(state: str) -> Dict[str, str]:
    fields: Dict[str, str] = {}
    if not state:
        return fields
    for key, value in re.findall(r'(\w+)="(.*?)"', state):
        fields[key] = value
    return fields


def _contains_any(text: str, markers: set[str]) -> bool:
    lower = (text or "").lower()
    return any(marker in lower for marker in markers)


def _normalize_language(language: str | None) -> str:
    code = (language or "").strip().lower()
    return "ru" if code.startswith("ru") else "en"


def classify_scene_mode(state: str, dialogue_response: str, user_message: str) -> str:
    """Classify scene into normal/intimate/explicit from current turn + state."""
    state_fields = _parse_state_fields(state)
    combined = " ".join([
        user_message or "",
        dialogue_response or "",
        state_fields.get("description", ""),
        state_fields.get("location", ""),
        state_fields.get("aiClothing", ""),
    ]).lower()

    if _contains_any(combined, REFUSAL_MARKERS):
        return "normal"
    if _contains_any(combined, EXPLICIT_MARKERS):
        return "explicit"
    if _contains_any(combined, INTIMATE_MARKERS):
        return "intimate"
    return "normal"


def _adult_pool(shop_items: Dict[str, Dict[str, Any]]) -> List[str]:
    return [key for key, item in shop_items.items() if item.get("category") == "adult"]


def _light_pool(shop_items: Dict[str, Dict[str, Any]]) -> List[str]:
    return [key for key, item in shop_items.items() if item.get("category") != "adult"]


def _ordered_pool(shop_items: Dict[str, Dict[str, Any]], keys: List[str]) -> List[str]:
    """Stable priority ordering from catalog (lower value => higher priority)."""
    return sorted(
        keys,
        key=lambda k: (
            int(shop_items.get(k, {}).get("recommendation_priority", 1000) or 1000),
            int(shop_items.get(k, {}).get("sort_order", 1000) or 1000),
            int(shop_items.get(k, {}).get("price", 0) or 0),
            k,
        ),
    )


def decide_gift_recommendation(
    state: str,
    dialogue_response: str,
    user_message: str,
    chat_ext: Dict[str, Any] | None,
    current_user_message_count: int,
    recent_purchases: List[Dict[str, Any]] | None,
) -> Dict[str, Any]:
    """Deterministic gate + gift selection. No LLM calls here."""
    cfg = _gift_config()
    cadence = int(cfg.get("cadence_user_messages", 20))
    purchase_cooldown = int(cfg.get("purchase_cooldown_user_messages", 20))
    min_user_messages = int(cfg.get("min_user_messages_before_suggestions", cadence))
    suggestion_probability = float(cfg.get("suggestion_probability", 1.0))

    ext = chat_ext if isinstance(chat_ext, dict) else {}

    if current_user_message_count < min_user_messages:
        return {
            "should_suggest": False,
            "reason": "too_early",
            "scene_mode": "normal",
            "item_key": None,
            "item_info": None,
        }

    last_suggestion_count = ext.get("last_gift_suggestion_user_count")
    if isinstance(last_suggestion_count, int):
        since_suggestion = current_user_message_count - last_suggestion_count
        if since_suggestion < cadence:
            return {
                "should_suggest": False,
                "reason": "cadence_block",
                "scene_mode": "normal",
                "item_key": None,
                "item_info": None,
            }

    last_purchase_count = ext.get("last_gift_purchase_user_count")
    if isinstance(last_purchase_count, int):
        since_purchase = current_user_message_count - last_purchase_count
        if since_purchase < purchase_cooldown:
            return {
                "should_suggest": False,
                "reason": "purchase_cooldown",
                "scene_mode": "normal",
                "item_key": None,
                "item_info": None,
            }
    elif recent_purchases:
        latest = recent_purchases[0]
        user_since = latest.get("user_messages_since")
        if isinstance(user_since, int) and user_since < purchase_cooldown:
            return {
                "should_suggest": False,
                "reason": "purchase_cooldown",
                "scene_mode": "normal",
                "item_key": None,
                "item_info": None,
            }

    # First suggestion must happen on an exact cadence boundary (20, 40, 60...).
    if not isinstance(last_suggestion_count, int):
        if cadence > 0 and (current_user_message_count % cadence) != 0:
            return {
                "should_suggest": False,
                "reason": "cadence_wait_boundary",
                "scene_mode": "normal",
                "item_key": None,
                "item_info": None,
            }

    scene_mode = classify_scene_mode(state, dialogue_response, user_message)

    if suggestion_probability < 1.0 and random.random() > suggestion_probability:
        return {
            "should_suggest": False,
            "reason": "probability_miss",
            "scene_mode": scene_mode,
            "item_key": None,
            "item_info": None,
        }

    shop_items = get_shop_items_map(include_scene_override=False)
    adult = _adult_pool(shop_items)
    light = _light_pool(shop_items)

    last_item_key = ext.get("last_gift_suggested_item_key") or ext.get("last_suggested_gift")

    if scene_mode in {"intimate", "explicit"}:
        pool = _ordered_pool(shop_items, adult) if adult else _ordered_pool(shop_items, list(shop_items.keys()))
    else:
        pool = _ordered_pool(shop_items, light) if light else _ordered_pool(shop_items, list(shop_items.keys()))

    if not pool:
        return {
            "should_suggest": False,
            "reason": "no_pool",
            "scene_mode": scene_mode,
            "item_key": None,
            "item_info": None,
        }

    filtered = [k for k in pool if k != last_item_key]
    if filtered:
        pool = filtered

    selected = pool[0] if scene_mode in {"intimate", "explicit"} else random.choice(pool)

    return {
        "should_suggest": True,
        "reason": f"scene_{scene_mode}",
        "scene_mode": scene_mode,
        "item_key": selected,
        "item_info": shop_items[selected],
    }


def _sanitize_generated_suggestion(text: str) -> str:
    clean = (text or "").strip()
    clean = re.sub(r"```[\w]*\n?", "", clean).replace("```", "").strip()
    lines = [line.strip() for line in clean.splitlines() if line.strip()]
    if lines:
        clean = " ".join(lines[:2])

    # Keep this as one short roleplay message (1-2 sentences max)
    parts = re.split(r"(?<=[.!?…])\s+", clean)
    short = " ".join(parts[:2]).strip()
    return short or clean


def _fallback_suggestion_text(scene_mode: str, language: str, item_key: str, item_info: Dict[str, Any]) -> str:
    language = _normalize_language(language)
    name_en = item_info.get("name", item_key)
    name_ru = item_info.get("name_ru", name_en)
    category = item_info.get("category", "light")

    if language == "ru":
        if category == "adult":
            alias = random.choice([name_ru.lower(), "новую игрушку", "пикантный подарок"])
        else:
            alias = random.choice([name_ru.lower(), "милый подарок", "приятный сюрприз"])

        if scene_mode in {"intimate", "explicit"}:
            return f"_Я прижимаюсь ближе и шепчу._ Знаешь, я бы очень хотела попробовать {alias} с тобой…" 
        return f"_Я улыбаюсь и касаюсь твоей руки._ Мне было бы приятно получить {alias}."

    if category == "adult":
        alias_en = random.choice([name_en.lower(), "a new toy", "something adventurous for us"])
    else:
        alias_en = random.choice([name_en.lower(), "a sweet gift", "a little surprise"])

    if scene_mode in {"intimate", "explicit"}:
        return f"_I press closer and whisper._ You know, I'd love to try {alias_en} with you…"
    return f"_I smile and brush your hand._ I'd really love {alias_en} as a gift."


async def generate_gift_recommendation(
    state: str,
    dialogue_response: str,
    user_message: str,
    language: str,
    chat_history: List[Dict[str, str]],
    chat_ext: Dict[str, Any] | None,
    current_user_message_count: int,
    recent_purchases: List[Dict[str, Any]] | None,
    user_id: int | None = None,
) -> Dict[str, Any]:
    """Generate scene-aware separate-message recommendation with fallback text."""
    language = _normalize_language(language)
    decision = decide_gift_recommendation(
        state=state,
        dialogue_response=dialogue_response,
        user_message=user_message,
        chat_ext=chat_ext,
        current_user_message_count=current_user_message_count,
        recent_purchases=recent_purchases,
    )

    if not decision.get("should_suggest"):
        decision["suggestion_text"] = ""
        return decision

    item_info = decision["item_info"] or {}
    item_key = decision.get("item_key") or "gift"
    scene_mode = decision.get("scene_mode", "normal")

    try:
        prompt = PromptService.get("GIFT_RECOMMENDATION_GPT")
        context_lines = [
            f"Language: {language}",
            f"Scene mode: {scene_mode}",
            f"Gift key: {item_key}",
            f"Gift EN name: {item_info.get('name', item_key)}",
            f"Gift RU name: {item_info.get('name_ru', item_info.get('name', item_key))}",
            "Current user message:",
            user_message or "",
            "Current AI response/actions:",
            dialogue_response or "",
        ]

        if chat_history:
            recent = chat_history[-2:]
            history_text = "\n".join(f"{m.get('role', 'unknown')}: {m.get('content', '')}" for m in recent)
            context_lines.extend(["Recent chat context:", history_text])

        model_name = None
        try:
            cfg = get_app_config()
            if isinstance(cfg, dict):
                model_name = cfg.get("llm", {}).get("model")
        except Exception:
            model_name = None

        response = await generate_text(
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": "\n".join(context_lines)},
            ],
            model=model_name,
            temperature=0.75,
            max_tokens=120,
            user_id=user_id,
        )
        suggestion_text = _sanitize_generated_suggestion(response)
        if not suggestion_text:
            raise ValueError("empty suggestion text")
    except Exception:
        suggestion_text = _fallback_suggestion_text(scene_mode, language, item_key, item_info)

    decision["suggestion_text"] = suggestion_text
    return decision

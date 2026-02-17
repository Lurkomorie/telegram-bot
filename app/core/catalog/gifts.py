"""Shared gift catalog loaded from config/gifts.yaml."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

import yaml

from app.settings import get_config_path


def _derive_mood_boost(price: int) -> int:
    """Derive mood boost from price to keep catalog maintenance simple."""
    return min(30, max(5, round(price * 0.14 + 4)))


def _require_non_empty(value: str, field_path: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"config/gifts.yaml invalid: missing required field '{field_path}'")
    return normalized


@lru_cache(maxsize=1)
def _load_gifts_yaml() -> Dict[str, Dict[str, Any]]:
    path: Path = get_config_path("gifts.yaml")
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    gifts = raw.get("gifts") or {}
    if not isinstance(gifts, dict):
        raise ValueError("config/gifts.yaml must contain a top-level 'gifts' mapping")

    normalized: Dict[str, Dict[str, Any]] = {}
    for key, item in gifts.items():
        if not isinstance(item, dict):
            continue
        merged: Dict[str, Any] = dict(item)
        merged["key"] = str(merged.get("key") or key)
        merged["emoji"] = str(merged.get("emoji") or "🎁")
        merged["price"] = int(merged.get("price", 0) or 0)
        merged["category"] = str(merged.get("category") or "light")
        merged["visual_effect_tags"] = str(merged.get("visual_effect_tags") or "")
        merged["scene_override_tags"] = str(merged.get("scene_override_tags") or "")
        merged["recommendation_priority"] = int(merged.get("recommendation_priority", 1000) or 1000)

        translations = merged.get("translations") if isinstance(merged.get("translations"), dict) else {}
        name_map = translations.get("name") if isinstance(translations.get("name"), dict) else {}
        subtitle_map = translations.get("subtitle") if isinstance(translations.get("subtitle"), dict) else {}

        # Backward-compatible fallbacks for legacy schema.
        name_en = _require_non_empty(
            name_map.get("en") or merged.get("name") or merged["key"],
            f"gifts.{key}.translations.name.en",
        )
        name_ru = _require_non_empty(
            name_map.get("ru") or merged.get("name_ru") or name_en,
            f"gifts.{key}.translations.name.ru",
        )
        subtitle_en = str(subtitle_map.get("en") or "")
        subtitle_ru = str(subtitle_map.get("ru") or subtitle_en)
        merged["translations"] = {
            "name": {"en": name_en, "ru": name_ru},
            "subtitle": {"en": subtitle_en, "ru": subtitle_ru},
        }

        # Keep legacy fields for compatibility with existing call sites.
        merged["name"] = name_en
        merged["name_ru"] = name_ru
        merged["subtitle_en"] = subtitle_en
        merged["subtitle_ru"] = subtitle_ru

        ui = merged.get("ui") if isinstance(merged.get("ui"), dict) else {}
        icon_lucide = _require_non_empty(
            ui.get("icon_lucide") or "",
            f"gifts.{key}.ui.icon_lucide",
        )
        icon_emoji_fallback = _require_non_empty(
            ui.get("icon_emoji_fallback") or merged["emoji"],
            f"gifts.{key}.ui.icon_emoji_fallback",
        )
        merged["ui"] = {
            "icon_lucide": icon_lucide,
            "icon_emoji_fallback": icon_emoji_fallback,
            "image_path": str(ui.get("image_path") or ""),
            "sort_order": int(ui.get("sort_order", 1000) or 1000),
            "style": str(ui.get("style") or "gift_v1"),
        }

        # Mood boost is derived from price by policy.
        merged["mood_boost"] = _derive_mood_boost(merged["price"])
        normalized[key] = merged
    return normalized


def get_gift_catalog() -> Dict[str, Dict[str, Any]]:
    """Return gift catalog keyed by item key."""
    return _load_gifts_yaml()


def get_gift_item(item_key: str) -> Dict[str, Any] | None:
    return get_gift_catalog().get(item_key)


def get_gift_context_effect(item_key: str, allow_scene_override: bool = False) -> str:
    """Return comma-separated effect tags used by purchase/image pipelines."""
    item = get_gift_item(item_key)
    if not item:
        return ""

    visual = (item.get("visual_effect_tags") or "").strip()
    if allow_scene_override:
        scene = (item.get("scene_override_tags") or "").strip()
        if visual and scene:
            return f"{visual}, {scene}"
        return visual or scene
    return visual


def get_shop_items_map(include_scene_override: bool = False) -> Dict[str, Dict[str, Any]]:
    """Compatibility map for shop/payment flows (same shape as legacy SHOP_ITEMS)."""
    result: Dict[str, Dict[str, Any]] = {}
    for key, item in get_gift_catalog().items():
        ui = item.get("ui", {}) if isinstance(item.get("ui"), dict) else {}
        result[key] = {
            "name": item.get("name", key),
            "name_en": item.get("name", key),
            "name_ru": item.get("name_ru", item.get("name", key)),
            "subtitle_en": item.get("subtitle_en", ""),
            "subtitle_ru": item.get("subtitle_ru", ""),
            "emoji": item.get("emoji", "🎁"),
            "price": int(item.get("price", 0) or 0),
            "mood_boost": int(item.get("mood_boost", 0) or 0),
            "context_effect": get_gift_context_effect(key, allow_scene_override=include_scene_override),
            "category": item.get("category", "light"),
            "scene_override_tags": (item.get("scene_override_tags") or "").strip(),
            "visual_effect_tags": (item.get("visual_effect_tags") or "").strip(),
            "icon_lucide": ui.get("icon_lucide", ""),
            "icon_emoji_fallback": ui.get("icon_emoji_fallback", item.get("emoji", "🎁")),
            "image_path": ui.get("image_path", ""),
            "sort_order": int(ui.get("sort_order", 1000) or 1000),
            "recommendation_priority": int(item.get("recommendation_priority", 1000) or 1000),
        }
    return result

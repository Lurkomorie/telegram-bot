"""Shared gift catalog loaded from config/gifts.yaml."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

import yaml

from app.settings import get_config_path


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
        merged = dict(item)
        merged.setdefault("key", key)
        merged.setdefault("name", key)
        merged.setdefault("name_ru", merged["name"])
        merged.setdefault("emoji", "🎁")
        merged.setdefault("price", 0)
        merged.setdefault("mood_boost", 0)
        merged.setdefault("category", "light")
        merged.setdefault("visual_effect_tags", "")
        merged.setdefault("scene_override_tags", "")
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
        result[key] = {
            "name": item.get("name", key),
            "name_ru": item.get("name_ru", item.get("name", key)),
            "emoji": item.get("emoji", "🎁"),
            "price": int(item.get("price", 0) or 0),
            "mood_boost": int(item.get("mood_boost", 0) or 0),
            "context_effect": get_gift_context_effect(key, allow_scene_override=include_scene_override),
            "category": item.get("category", "light"),
            "scene_override_tags": (item.get("scene_override_tags") or "").strip(),
            "visual_effect_tags": (item.get("visual_effect_tags") or "").strip(),
        }
    return result

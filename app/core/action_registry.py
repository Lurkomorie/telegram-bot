"""
Global registry for managing chat actions across different execution contexts
Used to coordinate actions between background tasks and webhook callbacks
"""
from typing import Dict
from app.core.chat_actions import ChatActionManager


# Global registry: tg_chat_id -> ChatActionManager
_action_managers: Dict[int, ChatActionManager] = {}


def register_action_manager(tg_chat_id: int, manager: ChatActionManager) -> None:
    """Register an action manager for a chat"""
    _action_managers[tg_chat_id] = manager


def get_action_manager(tg_chat_id: int) -> ChatActionManager | None:
    """Get action manager for a chat"""
    return _action_managers.get(tg_chat_id)


async def stop_and_remove_action(tg_chat_id: int) -> None:
    """Stop action and remove from registry"""
    manager = _action_managers.pop(tg_chat_id, None)
    if manager:
        await manager.stop()


def has_active_action(tg_chat_id: int) -> bool:
    """Check if chat has an active action manager"""
    return tg_chat_id in _action_managers


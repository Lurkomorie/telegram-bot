"""
Inline keyboard builders
"""
from typing import List, Dict, Any
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def build_persona_selection_keyboard(
    preset_personas: List[Dict[str, Any]],
    user_personas: List[Dict[str, Any]] = None
) -> InlineKeyboardMarkup:
    """Build keyboard for persona selection
    
    Args:
        preset_personas: List of dicts with 'id', 'name', 'key'
        user_personas: List of dicts with 'id', 'name', 'key'
    """
    buttons = []
    
    # Add preset personas
    for persona in preset_personas:
        buttons.append([
            InlineKeyboardButton(
                text=f"💕 {persona['name']}",
                callback_data=f"select_persona:{persona['id']}"
            )
        ])
    
    # Add user's custom personas
    if user_personas:
        buttons.append([InlineKeyboardButton(text="--- Your Custom Girls ---", callback_data="noop")])
        for persona in user_personas:
            buttons.append([
                InlineKeyboardButton(
                    text=f"✨ {persona['name']}",
                    callback_data=f"select_persona:{persona['id']}"
                )
            ])
    
    # Add create new button
    buttons.append([
        InlineKeyboardButton(
            text="➕ Create Your Own Girl",
            callback_data="create_persona"
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_confirm_keyboard(action: str) -> InlineKeyboardMarkup:
    """Build yes/no confirmation keyboard"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Yes", callback_data=f"confirm:{action}"),
            InlineKeyboardButton(text="❌ No", callback_data=f"cancel:{action}")
        ]
    ])


def build_persona_actions_keyboard(persona_id: str) -> InlineKeyboardMarkup:
    """Build actions keyboard for a selected persona"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="💬 Start Chatting",
                callback_data=f"select_persona:{persona_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="🎨 Generate Image",
                callback_data=f"gen_image:{persona_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="⚙️ Settings",
                callback_data=f"settings:{persona_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 Back to List",
                callback_data="show_personas"
            )
        ]
    ])


def build_image_prompt_keyboard() -> InlineKeyboardMarkup:
    """Build keyboard for image generation prompts"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📸 Selfie", callback_data="img_prompt:selfie")],
        [InlineKeyboardButton(text="💋 Flirty Pose", callback_data="img_prompt:flirty")],
        [InlineKeyboardButton(text="😊 Casual Portrait", callback_data="img_prompt:casual")],
        [InlineKeyboardButton(text="✍️ Custom Prompt", callback_data="img_prompt:custom")],
        [InlineKeyboardButton(text="🔙 Cancel", callback_data="cancel_image")]
    ])



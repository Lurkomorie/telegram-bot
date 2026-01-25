"""
Settings and utility commands
"""
from aiogram import types
from aiogram.filters import Command
from app.bot.loader import router
from app.db.base import get_db
from app.db import crud
from app.core.constants import ERROR_MESSAGES


def get_and_update_user_language(db, telegram_user) -> str:
    """
    Get user language and ensure it's updated from Telegram
    
    Args:
        db: Database session
        telegram_user: Telegram User object (from message.from_user or callback.from_user)
    
    Returns:
        User language code (e.g., 'en', 'ru', 'fr')
    """
    if not telegram_user:
        return 'en'
    
    # Update user info including language
    crud.get_or_create_user(
        db,
        telegram_id=telegram_user.id,
        username=telegram_user.username,
        first_name=telegram_user.first_name,
        language_code=telegram_user.language_code
    )
    
    # Get updated language
    return crud.get_user_language(db, telegram_user.id)


@router.message(Command("help"))
async def cmd_help(message: types.Message):
    """Handle /help command"""
    help_text = (
        "🤖 <b>AI Companion Bot - Help</b>\n\n"
        "<b>Commands:</b>\n"
        "/start - Start or switch AI companion\n"
        "/girls - Browse available companions\n"
        "/image - Generate a custom image\n"
        "/reset - Clear conversation history\n"
        "/help - Show this help message\n"
        "/settings - View settings\n\n"
        "<b>How to use:</b>\n"
        "Just chat naturally! Your AI companion will respond with both "
        "messages and images based on your conversation."
    )
    
    await message.answer(help_text)


@router.message(Command("reset"))
async def cmd_reset(message: types.Message):
    """Handle /reset command - clear conversation history"""
    with get_db() as db:
        # Get active chat
        chat = crud.get_active_chat(db, message.chat.id, message.from_user.id)
        
        if not chat:
            await message.answer("No active conversation to reset.")
            return
        
        # Clear history
        crud.clear_chat_history(db, chat.id)
    
    await message.answer(ERROR_MESSAGES["history_cleared"])


@router.message(Command("girls"))
async def cmd_girls(message: types.Message):
    """Handle /girls command - show persona list"""
    from app.bot.keyboards.inline import build_persona_selection_keyboard
    from app.core.persona_cache import get_preset_personas, get_persona_field
    from app.settings import settings
    
    # Get user language
    with get_db() as db:
        user_language = get_and_update_user_language(db, message.from_user)
    
    # Get personas from cache
    preset_data = get_preset_personas()
    user_data = []  # User personas disabled
    
    # Build text with persona descriptions
    welcome_text = get_ui_text("welcome.title", language=user_language) + "\n\n"
    for p in preset_data:
        emoji = p.get('emoji', '💕')
        name = p.get('name', 'Unknown')
        desc = get_persona_field(p, 'small_description', language=user_language)
        if desc:
            welcome_text += f"{emoji} <b>{name}</b> – {desc}\n\n"
        else:
            welcome_text += f"{emoji} <b>{name}</b>\n\n"
    
    miniapp_url = settings.miniapp_url
    keyboard = build_persona_selection_keyboard(preset_data, user_data, miniapp_url, language=user_language)
    
    await message.answer(
        welcome_text,
        reply_markup=keyboard
    )


@router.message(Command("settings"))
async def cmd_settings(message: types.Message):
    """Handle /settings command"""
    # Placeholder for settings menu
    await message.answer(
        "⚙️ <b>Settings</b>\n\n"
        "Settings menu coming soon! For now, use:\n"
        "• /reset - Clear conversation history\n"
        "• /girls - Switch AI girl\n"
        "• /help - Show commands"
    )



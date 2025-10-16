"""
Settings and utility commands
"""
from aiogram import types
from aiogram.filters import Command
from app.bot.loader import router
from app.db.base import get_db
from app.db import crud
from app.core.constants import ERROR_MESSAGES


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
    
    with get_db() as db:
        preset_personas = crud.get_preset_personas(db)
        user_personas = crud.get_user_personas(db, message.from_user.id)
    
    keyboard = build_persona_selection_keyboard(preset_personas, user_personas)
    
    await message.answer(
        "💕 <b>Choose your AI companion:</b>",
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



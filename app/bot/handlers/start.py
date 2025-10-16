"""
/start command handler and persona selection
"""
from aiogram import types
from aiogram.filters import Command
from app.bot.loader import router
from app.bot.keyboards.inline import build_persona_selection_keyboard
from app.db.base import get_db
from app.db import crud


@router.message(Command("start"))
async def cmd_start(message: types.Message):
    """Handle /start command"""
    with get_db() as db:
        # Get or create user
        user = crud.get_or_create_user(
            db,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name
        )
        
        # Get all personas and extract data while session is active
        preset_personas = crud.get_preset_personas(db)
        user_personas = crud.get_user_personas(db, user.id)
        
        # Extract data from ORM objects before session closes
        preset_data = [{"id": str(p.id), "name": p.name, "key": p.key} for p in preset_personas]
        user_data = [{"id": str(p.id), "name": p.name, "key": p.key} for p in user_personas]
    
    welcome_text = "👋 <b>Welcome to AI Companion!</b>\n\nI'm here to chat, flirt, and keep you company. Choose one of my preset personalities below, or create your own custom AI girl!\n\n✨ <i>What kind of companion are you looking for?</i>"
    
    keyboard = build_persona_selection_keyboard(preset_data, user_data)
    
    await message.answer(
        welcome_text,
        reply_markup=keyboard
    )


@router.callback_query(lambda c: c.data == "show_personas")
async def show_personas_callback(callback: types.CallbackQuery):
    """Show persona selection (callback from other menus)"""
    with get_db() as db:
        preset_personas = crud.get_preset_personas(db)
        user_personas = crud.get_user_personas(db, callback.from_user.id)
        
        # Extract data from ORM objects before session closes
        preset_data = [{"id": str(p.id), "name": p.name, "key": p.key} for p in preset_personas]
        user_data = [{"id": str(p.id), "name": p.name, "key": p.key} for p in user_personas]
    
    welcome_text = "👋 <b>Welcome to AI Companion!</b>\n\nI'm here to chat, flirt, and keep you company. Choose one of my preset personalities below, or create your own custom AI girl!\n\n✨ <i>What kind of companion are you looking for?</i>"
    
    keyboard = build_persona_selection_keyboard(preset_data, user_data)
    
    await callback.message.edit_text(
        welcome_text,
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("select_persona:"))
async def select_persona_callback(callback: types.CallbackQuery):
    """Handle persona selection with history starts"""
    persona_id = callback.data.split(":")[1]
    
    with get_db() as db:
        # Get persona
        persona = crud.get_persona_by_id(db, persona_id)
        if not persona:
            await callback.answer("Persona not found!", show_alert=True)
            return
        
        # Extract persona data before session closes
        persona_name = persona.name
        persona_intro = persona.intro
        
        # Create or get chat (clears history if switching personas)
        chat = crud.get_or_create_chat(
            db,
            tg_chat_id=callback.message.chat.id,
            user_id=callback.from_user.id,
            persona_id=persona.id
        )
        
        # CRITICAL: Clear any unprocessed messages when switching personas
        # This prevents old messages from one persona appearing in another chat
        print(f"[START] 🧹 Clearing unprocessed messages for chat {chat.id}")
        crud.clear_unprocessed_messages(db, chat.id)
        
        # Get random history start
        history_start = crud.get_random_history_start(db, persona.id)
    
    # Delete the inline keyboard message
    try:
        await callback.message.delete()
    except:
        pass
    
    # Send greeting
    if history_start:
        # Use history start with optional image
        if history_start.image_url:
            await callback.message.answer_photo(
                photo=history_start.image_url,
                caption=f"✅ <b>Switched to {persona_name}!</b>\n\n{history_start.text}",
                parse_mode="HTML"
            )
        else:
            await callback.message.answer(
                f"✅ <b>Switched to {persona_name}!</b>\n\n{history_start.text}",
                parse_mode="HTML"
            )
    else:
        # Fallback to intro or default
        intro_text = persona_intro or f"Hi! I'm {persona_name}. Let's chat!"
        await callback.message.answer(
            f"✅ <b>Switched to {persona_name}!</b>\n\n{intro_text}",
            parse_mode="HTML"
        )
    
    await callback.answer()



"""
/start command handler and persona selection
"""
from aiogram import types
from aiogram.filters import Command
from app.bot.loader import router
from app.bot.keyboards.inline import build_persona_selection_keyboard
from app.db.base import get_db
from app.db import crud
from app.settings import get_prompts_config


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
    
    prompts = get_prompts_config()
    welcome_text = prompts["text_blocks"]["welcome"]
    
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
    
    prompts = get_prompts_config()
    welcome_text = prompts["text_blocks"]["welcome"]
    
    keyboard = build_persona_selection_keyboard(preset_data, user_data)
    
    await callback.message.edit_text(
        welcome_text,
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("select_persona:"))
async def select_persona_callback(callback: types.CallbackQuery):
    """Handle persona selection"""
    persona_id = callback.data.split(":")[1]
    
    with get_db() as db:
        # Get persona
        persona = crud.get_persona_by_id(db, persona_id)
        if not persona:
            await callback.answer("Persona not found!", show_alert=True)
            return
        
        # Extract persona data before session closes
        persona_name = persona.name
        persona_key = persona.key
        
        # Create or get chat
        chat = crud.get_or_create_chat(
            db,
            tg_chat_id=callback.message.chat.id,
            user_id=callback.from_user.id,
            persona_id=persona.id
        )
    
    prompts = get_prompts_config()
    
    # Get persona opener message
    persona_config = next(
        (p for p in prompts["personas"] if p.get("key") == persona_key),
        None
    )
    
    openers = persona_config.get("openers", []) if persona_config else []
    opener = openers[0] if openers else f"Hi! I'm {persona_name}. Let's chat!"
    
    switch_text = prompts["text_blocks"]["persona_switched"].replace(
        "{{persona_name}}", persona_name
    )
    
    await callback.message.edit_text(
        f"{switch_text}\n\n<i>{opener}</i>"
    )
    await callback.answer()



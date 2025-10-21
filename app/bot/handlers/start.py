"""
/start command handler and persona selection
"""
from aiogram import types
from aiogram.filters import Command
from app.bot.loader import router
from app.bot.keyboards.inline import build_persona_selection_keyboard, build_chat_options_keyboard
from app.core.telegram_utils import escape_markdown_v2
from app.core import redis_queue
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
        
        # Check if chat already exists
        existing_chat = crud.check_existing_chat(
            db,
            tg_chat_id=callback.message.chat.id,
            user_id=callback.from_user.id,
            persona_id=persona.id
        )
    
    # If chat exists, show Continue/Start New options
    if existing_chat:
        keyboard = build_chat_options_keyboard(persona_id)
        await callback.message.edit_text(
            f"💬 <b>You have an existing conversation with {persona_name}</b>\n\n"
            f"Would you like to continue where you left off, or start a fresh conversation?",
            reply_markup=keyboard
        )
        await callback.answer()
        return
    
    # No existing chat - proceed with standard flow (create new chat)
    with get_db() as db:
        persona = crud.get_persona_by_id(db, persona_id)
        persona_intro = persona.intro
        
        # Create new chat
        chat = crud.create_new_chat(
            db,
            tg_chat_id=callback.message.chat.id,
            user_id=callback.from_user.id,
            persona_id=persona.id
        )
        
        chat_id = chat.id
        
        # CRITICAL: Clear any unprocessed messages when switching personas
        # This prevents old messages from one persona appearing in another chat
        print(f"[START] 🧹 Clearing unprocessed messages for chat {chat_id}")
        crud.clear_unprocessed_messages(db, chat_id)
    
    # Clear Redis queue and processing lock for this chat
    await redis_queue.clear_batch_messages(chat_id)
    await redis_queue.set_processing_lock(chat_id, False)
    print(f"[START] 🧹 Cleared Redis queue and processing lock")
    
    with get_db() as db:
        # Get random history start and extract data before session closes
        history_start = crud.get_random_history_start(db, persona_id)
        history_start_data = None
        description_text = None
        if history_start:
            history_start_data = {
                "text": history_start.text,
                "image_url": history_start.image_url
            }
            description_text = history_start.description
        
        # Determine the greeting text
        if history_start_data:
            greeting_text = history_start_data['text']
        else:
            greeting_text = persona_intro or f"Hi! I'm {persona_name}. Let's chat!"
        
        # If there's a description, save it as a system message first
        if description_text:
            crud.create_message_with_state(
                db,
                chat_id=chat_id,
                role="system",
                text=description_text,
                is_processed=True
            )
        
        # Save the history start/intro as an assistant message in the database
        # This ensures it appears in conversation history for context
        crud.create_message_with_state(
            db,
            chat_id=chat_id,
            role="assistant",
            text=greeting_text,
            is_processed=True
        )
    
    # Delete the inline keyboard message
    try:
        await callback.message.delete()
    except Exception:
        pass
    
    # Send description first if it exists (in italic using MarkdownV2)
    if description_text:
        escaped_description = escape_markdown_v2(description_text)
        formatted_description = f"_{escaped_description}_"
        await callback.message.answer(
            formatted_description,
            parse_mode="MarkdownV2"
        )
    
    # Send greeting without the "Switched to" prefix
    escaped_greeting = escape_markdown_v2(greeting_text)
    if history_start_data and history_start_data["image_url"]:
        await callback.message.answer_photo(
            photo=history_start_data["image_url"],
            caption=escaped_greeting,
            parse_mode="MarkdownV2"
        )
    else:
        await callback.message.answer(
            escaped_greeting,
            parse_mode="MarkdownV2"
        )
    
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("continue_chat:"))
async def continue_chat_callback(callback: types.CallbackQuery):
    """Continue existing conversation - send AI message + image via pipeline"""
    from app.core.multi_brain_pipeline import process_message_pipeline
    
    persona_id = callback.data.split(":")[1]
    
    with get_db() as db:
        # Get persona
        persona = crud.get_persona_by_id(db, persona_id)
        if not persona:
            await callback.answer("Persona not found!", show_alert=True)
            return
        
        # Get existing chat
        chat = crud.check_existing_chat(
            db,
            tg_chat_id=callback.message.chat.id,
            user_id=callback.from_user.id,
            persona_id=persona.id
        )
        
        if not chat:
            await callback.answer("Chat not found!", show_alert=True)
            return
        
        chat_id = chat.id
        tg_chat_id = chat.tg_chat_id
    
    # Delete the inline keyboard message
    try:
        await callback.message.delete()
    except Exception:
        pass
    
    # Clear Redis queue and processing lock for this chat
    await redis_queue.clear_batch_messages(chat_id)
    await redis_queue.set_processing_lock(chat_id, False)
    print(f"[CONTINUE] 🧹 Cleared Redis queue and processing lock")
    
    # Add a special "resume" message to queue
    await redis_queue.add_message_to_queue(
        chat_id=chat_id,
        user_id=callback.from_user.id,
        text="[SYSTEM_RESUME]",
        tg_chat_id=tg_chat_id
    )
    
    # Process through pipeline (will generate message + image)
    try:
        await process_message_pipeline(
            chat_id=chat_id,
            user_id=callback.from_user.id,
            tg_chat_id=tg_chat_id
        )
    except Exception as e:
        print(f"[CONTINUE] ❌ Pipeline error: {e}")
        await callback.message.answer("Failed to continue conversation. Please try again.")
    
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("new_chat:"))
async def new_chat_callback(callback: types.CallbackQuery):
    """Start new conversation with same persona (keeps old chat in DB)"""
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
        
        # Create new chat (always creates new, even if one exists)
        chat = crud.create_new_chat(
            db,
            tg_chat_id=callback.message.chat.id,
            user_id=callback.from_user.id,
            persona_id=persona.id
        )
        
        chat_id = chat.id
        
        # CRITICAL: Clear any unprocessed messages for this new chat
        print(f"[NEW_CHAT] 🧹 Clearing unprocessed messages for chat {chat_id}")
        crud.clear_unprocessed_messages(db, chat_id)
    
    # Clear Redis queue and processing lock for this chat
    await redis_queue.clear_batch_messages(chat_id)
    await redis_queue.set_processing_lock(chat_id, False)
    print(f"[NEW_CHAT] 🧹 Cleared Redis queue and processing lock")
    
    with get_db() as db:
        # Get random history start and extract data before session closes
        history_start = crud.get_random_history_start(db, persona_id)
        history_start_data = None
        description_text = None
        if history_start:
            history_start_data = {
                "text": history_start.text,
                "image_url": history_start.image_url
            }
            description_text = history_start.description
        
        # Determine the greeting text
        if history_start_data:
            greeting_text = history_start_data['text']
        else:
            greeting_text = persona_intro or f"Hi! I'm {persona_name}. Let's chat!"
        
        # If there's a description, save it as a system message first
        if description_text:
            crud.create_message_with_state(
                db,
                chat_id=chat_id,
                role="system",
                text=description_text,
                is_processed=True
            )
        
        # Save the history start/intro as an assistant message in the database
        crud.create_message_with_state(
            db,
            chat_id=chat_id,
            role="assistant",
            text=greeting_text,
            is_processed=True
        )
    
    # Delete the inline keyboard message
    try:
        await callback.message.delete()
    except Exception:
        pass
    
    # Send description first if it exists (in italic using MarkdownV2)
    if description_text:
        escaped_description = escape_markdown_v2(description_text)
        formatted_description = f"_{escaped_description}_"
        await callback.message.answer(
            formatted_description,
            parse_mode="MarkdownV2"
        )
    
    # Send greeting
    escaped_greeting = escape_markdown_v2(greeting_text)
    if history_start_data and history_start_data["image_url"]:
        await callback.message.answer_photo(
            photo=history_start_data["image_url"],
            caption=escaped_greeting,
            parse_mode="MarkdownV2"
        )
    else:
        await callback.message.answer(
            escaped_greeting,
            parse_mode="MarkdownV2"
        )
    
    await callback.answer()



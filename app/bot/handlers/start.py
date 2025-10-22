"""
/start command handler and persona selection
"""
import json
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
    """Handle /start command with optional deep link parameter"""
    # Check if there's a deep link parameter (e.g., /start persona_<uuid> or persona_<uuid>_h<history_id>)
    command_args = message.text.split(maxsplit=1)
    deep_link_param = command_args[1] if len(command_args) > 1 else None
    
    print(f"[START] Received /start command. Args: {command_args}, Deep link param: {deep_link_param}")
    
    # Handle deep link from Mini App
    if deep_link_param and deep_link_param.startswith("persona_"):
        # Parse persona_id and optional history_id
        # Format: persona_<uuid> OR persona_<uuid>_h<history_uuid>
        parts = deep_link_param.replace("persona_", "").split("_h")
        persona_id = parts[0]
        history_id = parts[1] if len(parts) > 1 else None
        
        # Check if persona exists and get chat status
        existing_chat = None
        persona_name = None
        
        with get_db() as db:
            persona = crud.get_persona_by_id(db, persona_id)
            if persona:
                # Check if chat exists
                existing_chat = crud.check_existing_chat(
                    db,
                    tg_chat_id=message.chat.id,
                    user_id=message.from_user.id,
                    persona_id=persona.id
                )
                persona_name = persona.name
            else:
                await message.answer("❌ Persona not found!")
                return
        
        if existing_chat:
            keyboard = build_chat_options_keyboard(persona_id)
            await message.answer(
                f"💬 <b>You have an existing conversation with {persona_name}</b>\n\n"
                f"Would you like to continue where you left off, or start a fresh conversation?",
                reply_markup=keyboard
            )
            return
        else:
            # Create new chat directly (with or without history)
            if history_id:
                await create_new_persona_chat_with_history(message, persona_id, history_id)
            else:
                await create_new_persona_chat(message, persona_id)
            return
    
    # Standard /start flow
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


async def create_new_persona_chat(message: types.Message, persona_id: str):
    """Helper function to create a new chat with a persona"""
    with get_db() as db:
        persona = crud.get_persona_by_id(db, persona_id)
        if not persona:
            await message.answer("❌ Persona not found!")
            return
        
        persona_name = persona.name
        persona_intro = persona.intro
        
        # Create new chat
        chat = crud.create_new_chat(
            db,
            tg_chat_id=message.chat.id,
            user_id=message.from_user.id,
            persona_id=persona.id
        )
        
        chat_id = chat.id
        
        # Clear any unprocessed messages
        print(f"[START-DEEPLINK] 🧹 Clearing unprocessed messages for chat {chat_id}")
        crud.clear_unprocessed_messages(db, chat_id)
    
    # Clear Redis queue and processing lock
    await redis_queue.clear_batch_messages(chat_id)
    await redis_queue.set_processing_lock(chat_id, False)
    
    with get_db() as db:
        # Get random history start
        history_start = crud.get_random_history_start(db, persona_id)
        history_start_data = None
        description_text = None
        if history_start:
            history_start_data = {
                "text": history_start.text,
                "image_url": history_start.image_url
            }
            description_text = history_start.description
        
        # Determine greeting text
        if history_start_data:
            greeting_text = history_start_data['text']
        else:
            greeting_text = persona_intro or f"Hi! I'm {persona_name}. Let's chat!"
        
        # Save description as system message if exists
        if description_text:
            crud.create_message_with_state(
                db,
                chat_id=chat_id,
                role="system",
                text=description_text,
                is_processed=True
            )
        
        # Save greeting as assistant message
        crud.create_message_with_state(
            db,
            chat_id=chat_id,
            role="assistant",
            text=greeting_text,
            is_processed=True
        )
    
    # Send description first if exists
    if description_text:
        escaped_description = escape_markdown_v2(description_text)
        formatted_description = f"_{escaped_description}_"
        await message.answer(
            formatted_description,
            parse_mode="MarkdownV2"
        )
    
    # Send greeting
    escaped_greeting = escape_markdown_v2(greeting_text)
    if history_start_data and history_start_data["image_url"]:
        await message.answer_photo(
            photo=history_start_data["image_url"],
            caption=escaped_greeting,
            parse_mode="MarkdownV2"
        )
    else:
        await message.answer(
            escaped_greeting,
            parse_mode="MarkdownV2"
        )


async def create_new_persona_chat_with_history(message: types.Message, persona_id: str, history_id: str):
    """Helper function to create a new chat with a specific history"""
    with get_db() as db:
        persona = crud.get_persona_by_id(db, persona_id)
        if not persona:
            await message.answer("❌ Persona not found!")
            return
        
        # Get the specific history
        from app.db.models import PersonaHistoryStart
        history_start = db.query(PersonaHistoryStart).filter(
            PersonaHistoryStart.id == history_id,
            PersonaHistoryStart.persona_id == persona_id
        ).first()
        
        if not history_start:
            # Fallback to random history
            history_start = crud.get_random_history_start(db, persona_id)
        
        persona_name = persona.name
        persona_intro = persona.intro
        
        # Create new chat
        chat = crud.create_new_chat(
            db,
            tg_chat_id=message.chat.id,
            user_id=message.from_user.id,
            persona_id=persona.id
        )
        
        chat_id = chat.id
        
        # Clear any unprocessed messages
        print(f"[MINIAPP-HISTORY] 🧹 Clearing unprocessed messages for chat {chat_id}")
        crud.clear_unprocessed_messages(db, chat_id)
    
    # Clear Redis queue and processing lock
    await redis_queue.clear_batch_messages(chat_id)
    await redis_queue.set_processing_lock(chat_id, False)
    
    with get_db() as db:
        # Use selected history or fallback
        history_start_data = None
        description_text = None
        if history_start:
            history_start_data = {
                "text": history_start.text,
                "image_url": history_start.image_url
            }
            description_text = history_start.description
        
        # Determine greeting text
        if history_start_data:
            greeting_text = history_start_data['text']
        else:
            greeting_text = persona_intro or f"Hi! I'm {persona_name}. Let's chat!"
        
        # Save description as system message if exists
        if description_text:
            crud.create_message_with_state(
                db,
                chat_id=chat_id,
                role="system",
                text=description_text,
                is_processed=True
            )
        
        # Save greeting as assistant message
        crud.create_message_with_state(
            db,
            chat_id=chat_id,
            role="assistant",
            text=greeting_text,
            is_processed=True
        )
    
    # Send description first if exists
    if description_text:
        escaped_description = escape_markdown_v2(description_text)
        formatted_description = f"_{escaped_description}_"
        await message.answer(
            formatted_description,
            parse_mode="MarkdownV2"
        )
    
    # Send greeting
    escaped_greeting = escape_markdown_v2(greeting_text)
    if history_start_data and history_start_data["image_url"]:
        await message.answer_photo(
            photo=history_start_data["image_url"],
            caption=escaped_greeting,
            parse_mode="MarkdownV2"
        )
    else:
        await message.answer(
            escaped_greeting,
            parse_mode="MarkdownV2"
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


@router.message(lambda message: message.web_app_data is not None)
async def handle_web_app_data(message: types.Message):
    """Handle data sent from the Mini App"""
    try:
        # Parse the data sent from the Mini App
        data = json.loads(message.web_app_data.data)
        action = data.get('action')
        
        if action == 'select_persona':
            persona_id = data.get('persona_id')
            history_id = data.get('history_id')  # New: history selection from Mini App
            
            if not persona_id:
                await message.answer("❌ Invalid selection!")
                return
            
            # Check if persona exists
            with get_db() as db:
                persona = crud.get_persona_by_id(db, persona_id)
                if not persona:
                    await message.answer("❌ Persona not found!")
                    return
                
                persona_name = persona.name
                
                # Check if chat already exists
                existing_chat = crud.check_existing_chat(
                    db,
                    tg_chat_id=message.chat.id,
                    user_id=message.from_user.id,
                    persona_id=persona.id
                )
            
            # If history_id is provided, user selected a specific history from Mini App
            if history_id:
                if existing_chat:
                    # Show continue or start new with selected history
                    keyboard = build_chat_options_keyboard(persona_id)
                    await message.answer(
                        f"💬 <b>You have an existing conversation with {persona_name}</b>\n\n"
                        f"Would you like to continue where you left off, or start a fresh conversation?",
                        reply_markup=keyboard
                    )
                else:
                    # Create new chat with selected history
                    await create_new_persona_chat_with_history(message, persona_id, history_id)
            else:
                # No history selected - backward compatibility
                if existing_chat:
                    keyboard = build_chat_options_keyboard(persona_id)
                    await message.answer(
                        f"💬 <b>You have an existing conversation with {persona_name}</b>\n\n"
                        f"Would you like to continue where you left off, or start a fresh conversation?",
                        reply_markup=keyboard
                    )
                else:
                    # Create new chat with random history
                    await create_new_persona_chat(message, persona_id)
        else:
            await message.answer("Unknown action from Mini App")
    
    except Exception as e:
        print(f"[WEB-APP-DATA] Error handling data: {e}")
        await message.answer("❌ Failed to process your selection. Please try again.")


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



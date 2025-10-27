"""
/start command handler and persona selection
"""
import json
from aiogram import types
from aiogram.filters import Command
from app.bot.loader import router
from app.bot.keyboards.inline import build_persona_selection_keyboard, build_chat_options_keyboard, build_story_selection_keyboard, build_persona_gallery_keyboard
from app.core.telegram_utils import escape_markdown_v2
from app.core import redis_queue
from app.db.base import get_db
from app.db import crud
from app.settings import settings, get_ui_text
from app.core import analytics_service_tg


@router.message(Command("start"))
async def cmd_start(message: types.Message):
    """Handle /start command with optional deep link parameter"""
    # Track start command
    analytics_service_tg.track_start_command(
        client_id=message.from_user.id,
        deep_link_param=message.text.split(maxsplit=1)[1] if len(message.text.split(maxsplit=1)) > 1 else None
    )
    
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
            # If history_id provided, create chat directly
            # Otherwise, show story selection menu
            if history_id:
                await create_new_persona_chat_with_history(message, persona_id, history_id)
            else:
                await show_story_selection(message, persona_id)
            return
    
    # Standard /start flow
    # Get or create user (DB call needed for user-specific data)
    with get_db() as db:
        crud.get_or_create_user(
            db,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name
        )
    
    # Get personas from cache (much faster!)
    from app.core.persona_cache import get_preset_personas
    preset_data = get_preset_personas()
    user_data = []  # User personas disabled
    
    # Build text with persona descriptions
    welcome_text = "Choose your companion:\n\n"
    for p in preset_data:
        emoji = p.get('emoji', '💕')
        name = p.get('name', 'Unknown')
        desc = p.get('small_description', '')
        if desc:
            welcome_text += f"{emoji} <b>{name}</b> – {desc}\n\n"
        else:
            welcome_text += f"{emoji} <b>{name}</b>\n\n"
    
    miniapp_url = f"{settings.public_url}/miniapp"
    keyboard = build_persona_selection_keyboard(preset_data, user_data, miniapp_url)
    
    await message.answer(
        welcome_text,
        reply_markup=keyboard
    )


async def show_story_selection(message: types.Message, persona_id: str, edit: bool = False):
    """Show story selection menu for a persona"""
    # Get persona from cache
    from app.core.persona_cache import get_persona_by_id, get_persona_histories
    persona = get_persona_by_id(persona_id)
    if not persona:
        if edit:
            await message.edit_text("❌ Persona not found!")
        else:
            await message.answer("❌ Persona not found!")
        return
    
    # Get histories from cache (already formatted as dicts)
    story_data = get_persona_histories(persona_id)
        
    
    # Build text with story descriptions
    story_text = get_ui_text("story.title") + "\n\n"
    for s in story_data:
        name = s.get('name', 'Story')
        desc = s.get('small_description', '')
        if desc:
            story_text += f"<b>{name}</b> – {desc}\n\n"
        else:
            story_text += f"<b>{name}</b>\n\n"
    
    keyboard = build_story_selection_keyboard(story_data, persona_id)
    
    if edit:
        await message.edit_text(story_text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await message.answer(story_text, reply_markup=keyboard, parse_mode="HTML")


async def create_new_persona_chat(message: types.Message, persona_id: str):
    """Helper function to create a new chat with a persona"""
    # Get persona from cache
    from app.core.persona_cache import get_persona_by_id, get_random_history
    persona = get_persona_by_id(persona_id)
    if not persona:
        await message.answer("❌ Persona not found!")
        return
    
    persona_name = persona["name"]
    persona_intro = persona["intro"]
    
    # Create new chat (DB call needed)
    with get_db() as db:
        chat = crud.create_new_chat(
            db,
            tg_chat_id=message.chat.id,
            user_id=message.from_user.id,
            persona_id=persona_id
        )
        
        chat_id = chat.id
        
        # Clear any unprocessed messages
        print(f"[START-DEEPLINK] 🧹 Clearing unprocessed messages for chat {chat_id}")
        crud.clear_unprocessed_messages(db, chat_id)
    
    # Clear Redis queue and processing lock
    await redis_queue.clear_batch_messages(chat_id)
    await redis_queue.set_processing_lock(chat_id, False)
    
    # Get random history from cache
    history_start = get_random_history(persona_id)
    history_start_data = None
    description_text = None
    if history_start:
        history_start_data = {
            "text": history_start["text"],
            "image_url": history_start["image_url"],
            "image_prompt": history_start.get("image_prompt")
        }
        description_text = history_start["description"]
    
    with get_db() as db:
        
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
        
        # Create initial ImageJob for continuity if history has image_prompt
        if history_start_data and history_start_data.get("image_prompt"):
            print(f"[START-DEEPLINK] 🎨 Creating initial image job for visual continuity")
            crud.create_initial_image_job(
                db,
                user_id=message.from_user.id,
                persona_id=persona_id,
                chat_id=chat_id,
                prompt=history_start_data["image_prompt"],
                result_url=history_start_data.get("image_url")
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
    # Get persona from cache
    from app.core.persona_cache import get_persona_by_id, get_persona_histories
    persona = get_persona_by_id(persona_id)
    if not persona:
        await message.answer("❌ Persona not found!")
        return
    
    # Get the specific history from cache
    histories = get_persona_histories(persona_id)
    history_start = None
    for h in histories:
        if h["id"] == history_id:
            history_start = h
            break
    
    if not history_start:
        # If history not found, log warning and continue without history
        print(f"[MINIAPP-HISTORY] ⚠️  History {history_id} not found, using persona intro")
    
    persona_name = persona["name"]
    persona_intro = persona["intro"]
    
    # Create new chat (DB call needed)
    with get_db() as db:
        chat = crud.create_new_chat(
            db,
            tg_chat_id=message.chat.id,
            user_id=message.from_user.id,
            persona_id=persona_id
        )
        
        chat_id = chat.id
        
        # Clear any unprocessed messages
        print(f"[MINIAPP-HISTORY] 🧹 Clearing unprocessed messages for chat {chat_id}")
        crud.clear_unprocessed_messages(db, chat_id)
    
    # Clear Redis queue and processing lock
    await redis_queue.clear_batch_messages(chat_id)
    await redis_queue.set_processing_lock(chat_id, False)
    
    # Use selected history or fallback (from cache)
    history_start_data = None
    description_text = None
    if history_start:
        history_start_data = {
            "text": history_start["text"],
            "image_url": history_start["image_url"],
            "image_prompt": history_start.get("image_prompt")
        }
        description_text = history_start["description"]
    
    with get_db() as db:
        
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
        
        # Create initial ImageJob for continuity if history has image_prompt
        if history_start_data and history_start_data.get("image_prompt"):
            print(f"[MINIAPP-HISTORY] 🎨 Creating initial image job for visual continuity")
            crud.create_initial_image_job(
                db,
                user_id=message.from_user.id,
                persona_id=persona_id,
                chat_id=chat_id,
                prompt=history_start_data["image_prompt"],
                result_url=history_start_data.get("image_url")
            )
    
    # Send hint message FIRST (before story starts)
    hint_text = get_ui_text("hints.restart")
    await message.answer(
        escape_markdown_v2(hint_text),
        parse_mode="MarkdownV2"
    )
    
    # Send description if exists
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
    # Get personas from cache
    from app.core.persona_cache import get_preset_personas
    preset_data = get_preset_personas()
    user_data = []  # User personas disabled
    
    # Build text with persona descriptions
    welcome_text = get_ui_text("welcome.title") + "\n\n"
    for p in preset_data:
        emoji = p.get('emoji', '💕')
        name = p.get('name', 'Unknown')
        desc = p.get('small_description', '')
        if desc:
            welcome_text += f"{emoji} <b>{name}</b> – {desc}\n\n"
        else:
            welcome_text += f"{emoji} <b>{name}</b>\n\n"
    
    miniapp_url = f"{settings.public_url}/miniapp"
    keyboard = build_persona_selection_keyboard(preset_data, user_data, miniapp_url)
    
    await callback.message.edit_text(
        welcome_text,
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "discover_characters")
async def discover_characters_callback(callback: types.CallbackQuery):
    """Open Mini App gallery to discover all characters"""
    miniapp_url = f"{settings.public_url}/miniapp"
    keyboard = build_persona_gallery_keyboard(miniapp_url)
    
    title = get_ui_text("welcome.discover_title")
    description = get_ui_text("welcome.discover_description")
    
    await callback.message.edit_text(
        f"{title}\n\n{description}",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("select_persona:"))
async def select_persona_callback(callback: types.CallbackQuery):
    """Handle persona selection - show story selection or chat options"""
    persona_id = callback.data.split(":")[1]
    
    # Get persona from cache
    from app.core.persona_cache import get_persona_by_id
    persona = get_persona_by_id(persona_id)
    if not persona:
        await callback.answer("Persona not found!", show_alert=True)
        return
    
    persona_name = persona["name"]
    
    # Check if chat already exists (DB call needed)
    with get_db() as db:
        existing_chat = crud.check_existing_chat(
            db,
            tg_chat_id=callback.message.chat.id,
            user_id=callback.from_user.id,
            persona_id=persona_id
        )
    
    # If chat exists, show Continue/Start New options
    if existing_chat:
        keyboard = build_chat_options_keyboard(persona_id)
        title = get_ui_text("chat_options.title", persona_name=persona_name)
        description = get_ui_text("chat_options.description")
        await callback.message.edit_text(
            f"{title}\n\n{description}",
            reply_markup=keyboard
        )
        await callback.answer()
        return
    
    # No existing chat - show story selection
    await show_story_selection(callback.message, persona_id, edit=True)
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("continue_chat:"))
async def continue_chat_callback(callback: types.CallbackQuery):
    """Continue existing conversation - send AI message + image via pipeline"""
    from app.core.multi_brain_pipeline import process_message_pipeline
    from app.core.persona_cache import get_persona_by_id
    
    persona_id = callback.data.split(":")[1]
    
    # Verify persona exists in cache
    persona = get_persona_by_id(persona_id)
    if not persona:
        await callback.answer("Persona not found!", show_alert=True)
        return
    
    # Track chat continued
    analytics_service_tg.track_chat_continued(
        client_id=callback.from_user.id,
        chat_id=None,  # Will be set below
        persona_id=persona_id,
        persona_name=persona["name"]
    )
    
    # Get existing chat (DB call needed)
    with get_db() as db:
        chat = crud.check_existing_chat(
            db,
            tg_chat_id=callback.message.chat.id,
            user_id=callback.from_user.id,
            persona_id=persona_id
        )
        
        if not chat:
            await callback.answer("Chat not found!", show_alert=True)
            return
        
        chat_id = chat.id
        tg_chat_id = chat.tg_chat_id
        
        # Activate this chat and archive all others for this user
        # This prevents the scheduler from sending auto-messages to old conversations
        crud.activate_chat(db, chat_id, callback.from_user.id)
    
    # Delete the inline keyboard message
    try:
        await callback.message.delete()
    except Exception:
        pass
    
    # Clear Redis queue and processing lock for this chat
    await redis_queue.clear_batch_messages(chat_id)
    await redis_queue.set_processing_lock(chat_id, False)
    print("[CONTINUE] 🧹 Cleared Redis queue and processing lock")
    
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
            
            # Check if persona exists in cache
            from app.core.persona_cache import get_persona_by_id
            persona = get_persona_by_id(persona_id)
            if not persona:
                await message.answer("❌ Persona not found!")
                return
            
            persona_name = persona["name"]
            
            # Check if chat already exists (DB call needed)
            with get_db() as db:
                existing_chat = crud.check_existing_chat(
                    db,
                    tg_chat_id=message.chat.id,
                    user_id=message.from_user.id,
                    persona_id=persona_id
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
                # No history selected - show story selection menu
                if existing_chat:
                    keyboard = build_chat_options_keyboard(persona_id)
                    await message.answer(
                        f"💬 <b>You have an existing conversation with {persona_name}</b>\n\n"
                        f"Would you like to continue where you left off, or start a fresh conversation?",
                        reply_markup=keyboard
                    )
                else:
                    # Show story selection instead of random
                    await show_story_selection(message, persona_id)
        else:
            await message.answer("Unknown action from Mini App")
    
    except Exception as e:
        print(f"[WEB-APP-DATA] Error handling data: {e}")
        await message.answer("❌ Failed to process your selection. Please try again.")


@router.callback_query(lambda c: c.data.startswith("select_story:"))
async def select_story_callback(callback: types.CallbackQuery):
    """Handle story selection and create new chat with selected history"""
    from app.core.persona_cache import get_persona_by_id
    
    history_id = callback.data.split(":")[1]
    
    # Find the history in cache across all personas
    history_start = None
    persona_id = None
    
    # We need to find which persona this history belongs to
    # Since we have histories indexed by persona_id, we need to search
    # Access the cache module to iterate over all histories
    from app.core.persona_cache import _CACHE
    for pid, histories in _CACHE["histories"].items():
        for h in histories:
            if h["id"] == history_id:
                history_start = h
                persona_id = pid
                break
        if history_start:
            break
    
    if not history_start:
        await callback.answer("Story not found!", show_alert=True)
        return
    
    # Get persona from cache
    persona = get_persona_by_id(persona_id)
    if not persona:
        await callback.answer("Persona not found!", show_alert=True)
        return
    
    # Track story selection
    analytics_service_tg.track_story_selected(
        client_id=callback.from_user.id,
        persona_id=persona_id,
        persona_name=persona["name"],
        story_id=history_id,
        story_name=history_start.get("name")
    )
    
    # Create new chat (DB call needed)
    with get_db() as db:
        chat = crud.create_new_chat(
            db,
            tg_chat_id=callback.message.chat.id,
            user_id=callback.from_user.id,
            persona_id=persona_id
        )
        
        chat_id = chat.id
        
        # Clear any unprocessed messages
        print(f"[SELECT_STORY] 🧹 Clearing unprocessed messages for chat {chat_id}")
        crud.clear_unprocessed_messages(db, chat_id)
    
    # Extract history data (from cache)
    history_start_data = {
        "text": history_start["text"],
        "image_url": history_start["image_url"]
    }
    description_text = history_start["description"]
    
    with get_db() as db:
        
        # Determine the greeting text
        greeting_text = history_start_data['text']
        
        # If there's a description, save it as a system message first
        if description_text:
            crud.create_message_with_state(
                db,
                chat_id=chat_id,
                role="system",
                text=description_text,
                is_processed=True
            )
        
        # Save the history start as an assistant message
        crud.create_message_with_state(
            db,
            chat_id=chat_id,
            role="assistant",
            text=greeting_text,
            is_processed=True
        )
    
    # Clear Redis queue and processing lock
    await redis_queue.clear_batch_messages(chat_id)
    await redis_queue.set_processing_lock(chat_id, False)
    
    # Delete the inline keyboard message
    try:
        await callback.message.delete()
    except Exception:
        pass
    
    # Send hint message FIRST (before story starts)
    hint_text = get_ui_text("hints.restart")
    await callback.message.answer(
        escape_markdown_v2(hint_text),
        parse_mode="MarkdownV2"
    )
    
    # Send description if it exists (in italic using MarkdownV2)
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


@router.callback_query(lambda c: c.data.startswith("new_chat_select:"))
async def new_chat_select_callback(callback: types.CallbackQuery):
    """Show story selection for starting a new conversation"""
    persona_id = callback.data.split(":")[1]
    
    # Show story selection
    await show_story_selection(callback.message, persona_id, edit=True)
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("new_chat:"))
async def new_chat_callback(callback: types.CallbackQuery):
    """Start new conversation with same persona (keeps old chat in DB)"""
    persona_id = callback.data.split(":")[1]
    
    # Delete the inline keyboard message
    try:
        await callback.message.delete()
    except Exception:
        pass
    
    # Show story selection instead of randomly picking one
    await show_story_selection(callback.message, persona_id)
    await callback.answer()



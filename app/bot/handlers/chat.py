"""
Text chat handler with multi-brain AI pipeline
"""
from datetime import datetime
from aiogram import types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from app.bot.loader import router, bot
from app.db.base import get_db
from app.db import crud
from app.db.models import User
from app.settings import get_app_config, get_ui_text
from app.core.rate import check_rate_limit
from app.core.multi_brain_pipeline import process_message_pipeline
from app.core.constants import ERROR_MESSAGES
from app.core.logging_utils import log_verbose, log_always
from app.core import redis_queue
from app.core import analytics_service_tg
from app.bot.keyboards.inline import build_no_active_chat_keyboard


@router.message(Command("clear"))
async def cmd_clear(message: types.Message):
    """Handle /clear command - delete current chat and all messages"""
    user_id = message.from_user.id
    
    log_always(f"[CLEAR] 🗑️  /clear command from user {user_id}")
    
    with get_db() as db:
        # Get or create user
        crud.get_or_create_user(
            db,
            telegram_id=user_id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            language_code=message.from_user.language_code
        )
        
        # Get active chat
        chat = crud.get_active_chat(db, message.chat.id, user_id)
        
        if not chat:
            log_verbose(f"[CLEAR] ❌ No active chat found for user {user_id}")
            await message.answer("No active chat to clear. Use /start to begin a new conversation.")
            return
        
        chat_id = chat.id
        log_verbose(f"[CLEAR] 💬 Deleting chat {chat_id}")
        
        # Track clear command
        analytics_service_tg.track_chat_cleared(
            client_id=user_id,
            chat_id=chat_id,
            persona_id=chat.persona_id,
            persona_name=None  # Could fetch persona name if needed
        )
        
        # Clear Redis queue for this chat
        await redis_queue.clear_batch_messages(chat_id)
        await redis_queue.set_processing_lock(chat_id, False)
        log_verbose(f"[CLEAR] 🧹 Cleared Redis queue and processing lock")
        
        # Delete chat and all its messages
        success = crud.delete_chat(db, chat_id)
        
        if success:
            log_always(f"[CLEAR] ✅ Chat {chat_id} deleted successfully")
            await message.answer(
                "✅ <b>Chat cleared!</b>\n\nAll messages have been deleted. Use /start to begin a new conversation."
            )
        else:
            log_always(f"[CLEAR] ❌ Failed to delete chat {chat_id}")
            await message.answer("Failed to clear chat. Please try again.")


@router.message(F.text & ~F.text.startswith("/"), StateFilter(None))
async def handle_text_message(message: types.Message, state: FSMContext):
    """Handle regular text messages with Redis-based batching and multi-brain pipeline
    
    Note: StateFilter(None) ensures this handler only runs when there's no active FSM state.
    This allows FSM handlers (like image generation) to take priority.
    """
    user_id = message.from_user.id
    user_text = message.text
    
    log_always(f"[CHAT] 📨 Message from user {user_id}")
    log_verbose(f"[CHAT]    Text ({len(user_text)} chars): {user_text[:50]}...")
    
    # Don't process commands as regular messages
    if user_text.startswith("/"):
        log_verbose(f"[CHAT] ⏭️  Skipping command message")
        return
    
    config = get_app_config()
    
    # Rate limit check
    allowed, count = await check_rate_limit(
        user_id,
        "text",
        config["limits"]["text_per_min"],
        60
    )
    
    if not allowed:
        log_verbose(f"[CHAT] ⚠️  Rate limited user {user_id}")
        await message.answer(ERROR_MESSAGES["rate_limit"])
        return
    
    log_verbose(f"[CHAT] ✅ Rate limit passed ({count} messages)")
    
    with get_db() as db:
        # Get or create user
        log_verbose(f"[CHAT] 👤 Getting/creating user {user_id}")
        crud.get_or_create_user(
            db,
            telegram_id=user_id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            language_code=message.from_user.language_code
        )
        
        # Check if user is premium (all users pay 1 energy per message)
        is_premium = crud.check_user_premium(db, user_id)["is_premium"]
        
        # Check energy (1 energy per message for all users)
        if not crud.check_user_energy(db, user_id, required=1):
            # Show energy upsell message
            from app.bot.handlers.image import show_energy_upsell_message
            await show_energy_upsell_message(message, user_id)
            log_verbose(f"[CHAT] ⚠️  User {user_id} has insufficient energy")
            return
        log_verbose(f"[CHAT] ⚡ User has sufficient energy")
        
        # Delete any existing energy upsell message (user is chatting, not low on energy)
        upsell_msg_id, upsell_chat_id = crud.get_and_clear_energy_upsell_message(db, user_id)
        if upsell_msg_id and upsell_chat_id:
            try:
                from app.bot.loader import bot
                await bot.delete_message(chat_id=upsell_chat_id, message_id=upsell_msg_id)
                log_verbose(f"[CHAT] 🗑️  Deleted energy upsell message {upsell_msg_id}")
            except Exception as e:
                log_verbose(f"[CHAT] ⚠️  Failed to delete upsell message: {e}")
        
        # Remove refresh button from last image (user is chatting, so it's no longer the last message)
        chat_for_image_check = crud.get_chat_by_tg_chat_id(db, message.chat.id)
        if chat_for_image_check and chat_for_image_check.ext and chat_for_image_check.ext.get("last_image_msg_id"):
            from app.bot.loader import bot
            last_img_msg_id = chat_for_image_check.ext["last_image_msg_id"]
            try:
                await bot.edit_message_reply_markup(
                    chat_id=message.chat.id,
                    message_id=last_img_msg_id,
                    reply_markup=None
                )
                log_verbose(f"[CHAT] 🗑️  Removed refresh button from image {last_img_msg_id}")
            except Exception as e:
                # Button might already be removed, that's okay
                log_verbose(f"[CHAT] ⚠️  Could not remove refresh button (likely already removed): {e}")
            finally:
                # Always clear the stored message ID, even if removal failed
                # For JSONB fields, we must mark as modified or reassign the whole dict
                from sqlalchemy.orm.attributes import flag_modified
                chat_for_image_check.ext["last_image_msg_id"] = None
                flag_modified(chat_for_image_check, "ext")
                db.commit()
        
        # Get active chat
        log_verbose(f"[CHAT] 💬 Getting active chat for TG chat {message.chat.id}")
        chat = crud.get_active_chat(db, message.chat.id, user_id)
        
        if not chat:
            log_verbose(f"[CHAT] ❌ No active chat found for user {user_id}")
            
            # Get user language
            user = db.query(User).filter(User.id == user_id).first()
            user_language = user.locale if user else 'en'
            
            # Delete previous "no active chat" service message if exists
            if user and user.settings and user.settings.get("no_chat_msg_id"):
                try:
                    await bot.delete_message(
                        chat_id=message.chat.id,
                        message_id=user.settings["no_chat_msg_id"]
                    )
                    log_verbose(f"[CHAT] 🗑️  Deleted previous no-chat service message")
                except Exception as e:
                    log_verbose(f"[CHAT] ⚠️  Could not delete previous service message: {e}")
            
            # Send new service message with button
            service_text = get_ui_text("no_active_chat.message", language=user_language)
            keyboard = build_no_active_chat_keyboard(language=user_language)
            service_msg = await message.answer(service_text, reply_markup=keyboard)
            
            # Save service message ID for later deletion
            if user:
                from sqlalchemy.orm.attributes import flag_modified
                if user.settings is None:
                    user.settings = {}
                user.settings["no_chat_msg_id"] = service_msg.message_id
                flag_modified(user, "settings")
                db.commit()
            
            return
        
        log_always(f"[CHAT] 💬 Chat {chat.id}")
        log_verbose(f"[CHAT]    Persona: {chat.persona_id}")
        
        # Extract data before session closes
        chat_id = chat.id
        tg_chat_id = chat.tg_chat_id
        persona_id = chat.persona_id
        
        # Get persona for analytics
        persona = crud.get_persona_by_id(db, chat.persona_id)
        persona_name = persona.name if persona else None
        
        # Track user message
        analytics_service_tg.track_user_message(
            client_id=user_id,
            message=user_text,
            persona_id=persona_id,
            persona_name=persona_name,
            chat_id=chat_id
        )
        
        # Update last user message timestamp and clear auto-message timestamp
        # (clearing auto-message timestamp allows scheduler to send another follow-up later if needed)
        crud.update_chat_timestamps(db, chat.id, user_at=datetime.utcnow())
        chat.last_auto_message_at = None
        
        # Reset auto_message_count since user replied
        if chat.ext is None:
            chat.ext = {}
        ext_copy = dict(chat.ext)
        ext_copy['auto_message_count'] = 0
        chat.ext = ext_copy
        
        db.commit()
        
        # Deduct energy (1 energy per message for all users)
        if crud.deduct_user_energy(db, user_id, amount=1):
            log_verbose(f"[CHAT] ⚡ Deducted 1 energy from user {user_id}")
        else:
            log_verbose(f"[CHAT] ⚠️  Failed to deduct energy from user {user_id}")
            await message.answer("❌ Failed to deduct energy. Please try again.")
            return
        
        # Increment global message counter for priority queue logic
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.global_message_count += 1
            db.commit()
            log_verbose(f"[CHAT] 📊 Global message count: {user.global_message_count}")
    
    # Always add message to queue first
    log_verbose(f"[CHAT] 📥 Adding '{user_text[:20]}...' to queue")
    await redis_queue.add_message_to_queue(
        chat_id=chat_id,
        user_id=user_id,
        text=user_text,
        tg_chat_id=tg_chat_id
    )
    queue_length = await redis_queue.get_queue_length(chat_id)
    log_always(f"[CHAT] 📊 Queue: {queue_length} message(s)")
    
    # Try to acquire processing lock atomically (prevents race conditions)
    lock_acquired = await redis_queue.set_processing_lock(chat_id, True)
    
    if not lock_acquired:
        # Another handler is already processing - message queued for next batch
        log_always(f"[CHAT] ⏳ RETURN EARLY - processing active (lock not acquired)")
        return
    
    log_always(f"[CHAT] 🔒 Processing lock ACQUIRED (queue: {queue_length})")
    
    # Start processing in background (don't await - return webhook immediately)
    log_always(f"[CHAT] 🚀 Starting background processing")
    
    import asyncio
    asyncio.create_task(_background_process(
        chat_id=chat_id,
        user_id=user_id,
        tg_chat_id=tg_chat_id,
        config=config
    ))


async def _background_process(chat_id, user_id, tg_chat_id, config):
    """Background task to process messages with batching delay"""
    from app.bot.loader import bot
    
    try:
        # Delay to allow rapid messages to accumulate
        batch_delay = config.get("limits", {}).get("batch_delay_seconds", 3)
        log_verbose(f"[CHAT-BG] ⏱️  Waiting {batch_delay}s for batching...")
        
        import asyncio
        await asyncio.sleep(batch_delay)
        
        # Check final queue length
        final_queue_length = await redis_queue.get_queue_length(chat_id)
        log_always(f"[CHAT-BG] 🚀 Processing ({final_queue_length} queued message(s))")
        
        # Process through multi-brain pipeline
        await process_message_pipeline(
            chat_id=chat_id,
            user_id=user_id,
            tg_chat_id=tg_chat_id
        )
        log_verbose(f"[CHAT-BG] ✅ Pipeline completed successfully")
    except Exception as e:
        print(f"[CHAT-BG] ❌ Error: {type(e).__name__}: {e}")
        
        # Log queue state for debugging
        try:
            queue_length = await redis_queue.get_queue_length(chat_id)
            batch_messages = await redis_queue.get_batch_messages(chat_id)
            print(f"[CHAT-BG] 📊 Queue state: {queue_length} messages")
            for i, msg in enumerate(batch_messages, 1):
                print(f"[CHAT-BG]    #{i}: {msg.get('text', '')[:50]}")
        except:
            pass
        
        # Clear lock so user can retry
        await redis_queue.set_processing_lock(chat_id, False)
        
        # Notify user of error
        try:
            await bot.send_message(
                tg_chat_id,
                "❌ Sorry, I encountered an error processing your message. Please try again."
            )
        except:
            pass


@router.callback_query(F.data.startswith("create_voice:"))
async def handle_create_voice(callback: types.CallbackQuery):
    """Handle 'Create Voice' button click - generate voice message from AI response"""
    from uuid import UUID
    from aiogram.types import BufferedInputFile
    from sqlalchemy.orm.attributes import flag_modified
    
    user_id = callback.from_user.id
    
    log_always(f"[VOICE] 🎤 Voice generation requested by user {user_id}")
    
    # Parse message ID from callback data
    try:
        message_id_str = callback.data.split(":")[1]
        message_id = UUID(message_id_str)
    except (IndexError, ValueError):
        log_always(f"[VOICE] ❌ Invalid callback data: {callback.data}")
        await callback.answer("❌ Invalid request", show_alert=True)
        return
    
    # Acknowledge callback immediately
    await callback.answer()
    
    # Get user language and check energy/free status
    with get_db() as db:
        user = db.query(User).filter(User.id == user_id).first()
        user_language = user.locale if user else 'en'
        
        # Check if user has used their free voice (1 free per lifetime)
        if user.settings is None:
            user.settings = {}
        is_free = not user.settings.get("voice_free_used", False)
        
        # If not free, check and deduct 15 energy
        if not is_free:
            if not crud.check_user_energy(db, user_id, required=15):
                log_always(f"[VOICE] ⚠️  User {user_id} has insufficient energy for voice")
                from app.bot.handlers.image import show_energy_upsell_message
                await show_energy_upsell_message(callback.message, user_id)
                return
            
            # Deduct 15 energy
            if not crud.deduct_user_energy(db, user_id, amount=15):
                log_always(f"[VOICE] ❌ Failed to deduct energy from user {user_id}")
                await callback.message.answer(
                    get_ui_text("voice.failed", language=user_language)
                )
                return
            log_verbose(f"[VOICE] ⚡ Deducted 15 energy from user {user_id}")
        else:
            # Mark free voice as used
            user.settings["voice_free_used"] = True
            flag_modified(user, "settings")
            db.commit()
            log_verbose(f"[VOICE] 🎁 User {user_id} used their free voice")
        
        # Get the message from database
        message = crud.get_message_by_id(db, message_id)
        
        if not message:
            log_always(f"[VOICE] ❌ Message {message_id} not found")
            await callback.message.answer(
                get_ui_text("voice.failed", language=user_language)
            )
            return
        
        message_text = message.text
        
        # Get persona for voice processing context and voice_id
        chat = crud.get_chat_by_id(db, message.chat_id)
        persona = crud.get_persona_by_id(db, chat.persona_id) if chat else None
        persona_name = persona.name if persona else "AI"
        # Get persona's voice_id if available (for custom characters)
        persona_voice_id = getattr(persona, 'voice_id', None) if persona else None
    
    log_verbose(f"[VOICE]    Message text: {message_text[:100]}...")
    log_verbose(f"[VOICE]    Persona: {persona_name}")
    log_verbose(f"[VOICE]    Persona voice_id: {persona_voice_id}")
    
    # Remove the voice button from the original message
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
        log_verbose(f"[VOICE] 🗑️  Removed voice button from message")
    except Exception as e:
        log_verbose(f"[VOICE] ⚠️  Could not remove voice button: {e}")
    
    # Show "generating" status
    status_msg = await callback.message.answer(
        get_ui_text("voice.generating", language=user_language)
    )
    
    try:
        # Process text through voice processor brain (add audio tags)
        from app.core.brains.voice_processor import process_text_for_voice
        tagged_text = await process_text_for_voice(message_text, persona_name)
        
        log_verbose(f"[VOICE]    Tagged text: {tagged_text[:150]}...")
        
        # Generate voice audio via ElevenLabs (use persona's voice_id if available)
        from app.core.elevenlabs_service import generate_voice
        voice_bytes = await generate_voice(tagged_text, voice_id=persona_voice_id)
        
        if not voice_bytes:
            log_always(f"[VOICE] ❌ Voice generation failed")
            await status_msg.delete()
            await callback.message.answer(
                get_ui_text("voice.failed", language=user_language)
            )
            return
        
        # Delete status message
        await status_msg.delete()
        
        # Send voice message
        voice_file = BufferedInputFile(voice_bytes, filename="voice.ogg")
        await callback.message.answer_voice(voice=voice_file)
        
        log_always(f"[VOICE] ✅ Voice message sent to user {user_id}")
        
        # Track voice generation analytics
        from app.core import analytics_service_tg
        analytics_service_tg.track_voice_generated(
            client_id=user_id,
            persona_id=persona.id if persona else None,
            persona_name=persona_name,
            chat_id=chat.id if chat else None,
            message_length=len(message_text),
            characters_used=len(tagged_text),  # Characters billed by ElevenLabs
            is_free=is_free
        )
        
    except Exception as e:
        log_always(f"[VOICE] ❌ Error: {type(e).__name__}: {e}")
        try:
            await status_msg.delete()
        except:
            pass
        await callback.message.answer(
            get_ui_text("voice.failed", language=user_language)
        )


@router.callback_query(F.data == "hide_voice_buttons")
async def handle_hide_voice_buttons(callback: types.CallbackQuery):
    """Handle 'Hide voice buttons' click - hide voice buttons for this user"""
    from sqlalchemy.orm.attributes import flag_modified
    
    user_id = callback.from_user.id
    
    log_always(f"[VOICE] 🔇 User {user_id} requested to hide voice buttons")
    
    with get_db() as db:
        user = db.query(User).filter(User.id == user_id).first()
        user_language = user.locale if user else 'en'
        
        # Update user settings to hide voice buttons
        if user.settings is None:
            user.settings = {}
        user.settings["voice_buttons_hidden"] = True
        flag_modified(user, "settings")
        db.commit()
        
        log_verbose(f"[VOICE] ✅ Voice buttons hidden for user {user_id}")
    
    # Remove the buttons from the current message
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception as e:
        log_verbose(f"[VOICE] ⚠️  Could not remove buttons: {e}")
    
    # Show popup with message
    await callback.answer(
        get_ui_text("voice.hidden_popup", language=user_language),
        show_alert=True
    )

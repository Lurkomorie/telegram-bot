"""
Text chat handler with multi-brain AI pipeline
"""
from datetime import datetime
from aiogram import types, F
from aiogram.filters import Command
from app.bot.loader import router
from app.db.base import get_db
from app.db import crud
from app.settings import get_app_config
from app.core.rate import check_rate_limit
from app.core.multi_brain_pipeline import process_message_pipeline
from app.core.constants import ERROR_MESSAGES
from app.core.logging_utils import log_verbose, log_always
from app.core import redis_queue


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
            first_name=message.from_user.first_name
        )
        
        # Get active chat
        chat = crud.get_active_chat(db, message.chat.id, user_id)
        
        if not chat:
            log_verbose(f"[CLEAR] ❌ No active chat found for user {user_id}")
            await message.answer("No active chat to clear. Use /start to begin a new conversation.")
            return
        
        chat_id = chat.id
        log_verbose(f"[CLEAR] 💬 Deleting chat {chat_id}")
        
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


@router.message(F.text & ~F.text.startswith("/"))
async def handle_text_message(message: types.Message):
    """Handle regular text messages with Redis-based batching and multi-brain pipeline"""
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
            first_name=message.from_user.first_name
        )
        
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
            try:
                from app.bot.loader import bot
                last_img_msg_id = chat_for_image_check.ext["last_image_msg_id"]
                await bot.edit_message_reply_markup(
                    chat_id=message.chat.id,
                    message_id=last_img_msg_id,
                    reply_markup=None
                )
                # Clear the stored message ID
                chat_for_image_check.ext["last_image_msg_id"] = None
                db.commit()
                log_verbose(f"[CHAT] 🗑️  Removed refresh button from image {last_img_msg_id}")
            except Exception as e:
                log_verbose(f"[CHAT] ⚠️  Failed to remove refresh button: {e}")
        
        # Get active chat
        log_verbose(f"[CHAT] 💬 Getting active chat for TG chat {message.chat.id}")
        chat = crud.get_active_chat(db, message.chat.id, user_id)
        
        if not chat:
            log_verbose(f"[CHAT] ❌ No active chat found for user {user_id}")
            await message.answer(ERROR_MESSAGES["no_persona"])
            return
        
        log_always(f"[CHAT] 💬 Chat {chat.id}")
        log_verbose(f"[CHAT]    Persona: {chat.persona_id}")
        
        # Extract data before session closes
        chat_id = chat.id
        tg_chat_id = chat.tg_chat_id
        
        # Update last user message timestamp and clear auto-message timestamp
        # (clearing auto-message timestamp allows scheduler to send another follow-up later if needed)
        crud.update_chat_timestamps(db, chat.id, user_at=datetime.utcnow())
        chat.last_auto_message_at = None
        db.commit()
    
    # Add message to Redis queue
    log_verbose(f"[CHAT] 📥 Adding message to Redis queue")
    queue_length = await redis_queue.add_message_to_queue(
        chat_id=chat_id,
        user_id=user_id,
        text=user_text,
        tg_chat_id=tg_chat_id
    )
    log_verbose(f"[CHAT] 📊 Queue length: {queue_length}")
    
    # Check if chat is currently being processed
    if await redis_queue.is_processing(chat_id):
        log_always(f"[CHAT] ⏳ Message queued (total: {queue_length})")
        return
    
    # Delay to allow batching of rapid messages
    batch_delay = config.get("limits", {}).get("batch_delay_seconds", 3)
    log_verbose(f"[CHAT] ⏱️  Waiting {batch_delay}s for potential batch...")
    
    import asyncio
    await asyncio.sleep(batch_delay)
    
    # Check final queue length after delay
    final_queue_length = await redis_queue.get_queue_length(chat_id)
    log_always(f"[CHAT] 🚀 Starting batch processing ({final_queue_length} message(s))")
    
    # Process through multi-brain pipeline
    try:
        log_verbose(f"[CHAT] 🧠 Calling multi-brain pipeline...")
        await process_message_pipeline(
            chat_id=chat_id,
            user_id=user_id,
            tg_chat_id=tg_chat_id
        )
        log_verbose(f"[CHAT] ✅ Pipeline completed successfully")
    except ValueError as e:
        print(f"[CHAT] ❌ Validation: {e}")
        await message.answer(ERROR_MESSAGES["chat_not_found"])
    except Exception as e:
        print(f"[CHAT] ❌ Pipeline error: {e}")
        await message.answer(ERROR_MESSAGES["processing_error"])

"""
Text chat handler with multi-brain AI pipeline
"""
from datetime import datetime, timedelta
from aiogram import types, F
from app.bot.loader import router
from app.db.base import get_db
from app.db import crud
from app.settings import get_app_config
from app.core.rate import check_rate_limit
from app.core.multi_brain_pipeline import process_message_pipeline
from app.core.constants import ERROR_MESSAGES

# Timeout after which we clear stale unprocessed messages and restart
MESSAGE_PROCESSING_TIMEOUT_MINUTES = 5


@router.message(F.text & ~F.text.startswith("/"))
async def handle_text_message(message: types.Message):
    """Handle regular text messages with batching and multi-brain pipeline"""
    user_id = message.from_user.id
    user_text = message.text
    
    print(f"[CHAT] 📨 Received message from user {user_id}: {user_text[:50]}...")
    
    # Don't process commands as regular messages
    if user_text.startswith("/"):
        print(f"[CHAT] ⏭️  Skipping command message")
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
        print(f"[CHAT] ⚠️  Rate limited user {user_id}")
        await message.answer(ERROR_MESSAGES["rate_limit"])
        return
    
    print(f"[CHAT] ✅ Rate limit passed ({count} messages)")
    
    with get_db() as db:
        # Get or create user
        print(f"[CHAT] 👤 Getting/creating user {user_id}")
        user = crud.get_or_create_user(
            db,
            telegram_id=user_id,
            username=message.from_user.username,
            first_name=message.from_user.first_name
        )
        
        # Get active chat
        print(f"[CHAT] 💬 Getting active chat for TG chat {message.chat.id}")
        chat = crud.get_active_chat(db, message.chat.id, user_id)
        
        if not chat:
            # No active persona selected
            print(f"[CHAT] ❌ No active chat found for user {user_id}")
            await message.answer(ERROR_MESSAGES["no_persona"])
            return
        
        print(f"[CHAT] ✅ Found chat {chat.id} with persona {chat.persona_id}")
        
        # Check for timeout - if we haven't responded in 5 minutes, clear stale messages
        last_assistant_time = crud.get_last_assistant_message_time(db, chat.id)
        timeout_threshold = datetime.utcnow() - timedelta(minutes=MESSAGE_PROCESSING_TIMEOUT_MINUTES)
        
        if last_assistant_time and last_assistant_time < timeout_threshold:
            print(f"[CHAT] ⏰ TIMEOUT: Last response was {(datetime.utcnow() - last_assistant_time).total_seconds() / 60:.1f} min ago")
            print(f"[CHAT] 🧹 Clearing stale unprocessed messages...")
            crud.clear_unprocessed_messages(db, chat.id)
        
        # Check existing unprocessed messages BEFORE saving current one
        print(f"[CHAT] 🔍 Checking for existing unprocessed messages")
        existing_unprocessed = crud.get_unprocessed_user_messages(db, chat.id)
        
        print(f"[CHAT] 📊 Found {len(existing_unprocessed)} existing unprocessed message(s)")
        
        # Save current user message (unprocessed)
        print(f"[CHAT] 💾 Saving current message as unprocessed")
        crud.create_message_with_state(
            db, 
            chat.id, 
            "user", 
            user_text,
            is_processed=False
        )
        
        # Update last user message timestamp
        crud.update_chat_timestamps(db, chat.id, user_at=datetime.utcnow())
        
        # Check if chat is currently being processed
        if crud.is_chat_processing(db, chat.id):
            print(f"[CHAT] ⏳ Message batched - pipeline still processing previous messages")
            print(f"[CHAT] 📊 Total unprocessed now: {len(existing_unprocessed) + 1}")
            return
        
        # Decide whether to process or batch
        if len(existing_unprocessed) > 0:
            # There are unprocessed messages but no active processing - this shouldn't happen normally
            # but could occur after timeout or error recovery
            print(f"[CHAT] ⚠️  Found {len(existing_unprocessed)} orphaned unprocessed message(s)")
            print(f"[CHAT] 🚀 Starting pipeline to process them now")
        else:
            print(f"[CHAT] 🚀 First unprocessed message - starting pipeline now")
        
        # Get ALL unprocessed messages (including the one we just saved)
        all_unprocessed = crud.get_unprocessed_user_messages(db, chat.id)
        
        # Extract data for pipeline
        chat_id = chat.id
        tg_chat_id = chat.tg_chat_id
        messages_data = [{"id": str(m.id), "text": m.text} for m in all_unprocessed]
        
        print(f"[CHAT] 📦 Prepared {len(messages_data)} message(s) for processing")
    
    # Batch all unprocessed messages
    batched_text = "\n".join([m["text"] for m in messages_data])
    
    print(f"[CHAT] 🎯 Processing {len(messages_data)} message(s) for chat {chat_id}")
    print(f"[CHAT] 📝 Batched text: {batched_text[:100]}...")
    
    # Process through multi-brain pipeline
    try:
        print(f"[CHAT] 🧠 Calling multi-brain pipeline...")
        await process_message_pipeline(
            chat_id=chat_id,
            user_id=user_id,
            batched_messages=messages_data,
            batched_text=batched_text,
            tg_chat_id=tg_chat_id
        )
        print(f"[CHAT] ✅ Pipeline completed successfully")
    except ValueError as e:
        # Handle validation errors (chat/persona not found)
        print(f"[CHAT] ❌ Validation error: {e}")
        await message.answer(ERROR_MESSAGES["chat_not_found"])
    except Exception as e:
        # Handle unexpected errors
        print(f"[CHAT] ❌ Error in pipeline: {e}")
        import traceback
        traceback.print_exc()
        await message.answer(ERROR_MESSAGES["processing_error"])

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
    
    print(f"[CHAT] 📨 Message from user {user_id} ({len(user_text)} chars)")
    
    # Don't process commands as regular messages
    if user_text.startswith("/"):
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
        await message.answer(ERROR_MESSAGES["rate_limit"])
        return
    
    with get_db() as db:
        # Get or create user
        user = crud.get_or_create_user(
            db,
            telegram_id=user_id,
            username=message.from_user.username,
            first_name=message.from_user.first_name
        )
        
        # Get active chat
        chat = crud.get_active_chat(db, message.chat.id, user_id)
        
        if not chat:
            await message.answer(ERROR_MESSAGES["no_persona"])
            return
        
        print(f"[CHAT] 💬 Chat {chat.id}")
        
        # Check for timeout - if we haven't responded in 5 minutes, clear stale messages
        last_assistant_time = crud.get_last_assistant_message_time(db, chat.id)
        timeout_threshold = datetime.utcnow() - timedelta(minutes=MESSAGE_PROCESSING_TIMEOUT_MINUTES)
        
        if last_assistant_time and last_assistant_time < timeout_threshold:
            mins_ago = (datetime.utcnow() - last_assistant_time).total_seconds() / 60
            print(f"[CHAT] ⏰ Timeout ({mins_ago:.1f}m ago), clearing stale messages")
            crud.clear_unprocessed_messages(db, chat.id)
        
        # Check existing unprocessed messages BEFORE saving current one
        existing_unprocessed = crud.get_unprocessed_user_messages(db, chat.id)
        
        # Save current user message (unprocessed)
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
            print(f"[CHAT] ⏳ Message batched (total: {len(existing_unprocessed) + 1})")
            return
        
        # Get ALL unprocessed messages (including the one we just saved)
        all_unprocessed = crud.get_unprocessed_user_messages(db, chat.id)
        
        # Extract data for pipeline
        chat_id = chat.id
        tg_chat_id = chat.tg_chat_id
        messages_data = [{"id": str(m.id), "text": m.text} for m in all_unprocessed]
    
    # Batch all unprocessed messages
    batched_text = "\n".join([m["text"] for m in messages_data])
    print(f"[CHAT] 🚀 Processing {len(messages_data)} message(s)")
    
    # Process through multi-brain pipeline
    try:
        await process_message_pipeline(
            chat_id=chat_id,
            user_id=user_id,
            batched_messages=messages_data,
            batched_text=batched_text,
            tg_chat_id=tg_chat_id
        )
    except ValueError as e:
        print(f"[CHAT] ❌ Validation: {e}")
        await message.answer(ERROR_MESSAGES["chat_not_found"])
    except Exception as e:
        print(f"[CHAT] ❌ Pipeline error: {e}")
        await message.answer(ERROR_MESSAGES["processing_error"])

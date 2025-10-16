"""
Text chat handler with multi-brain AI pipeline
"""
from datetime import datetime
from aiogram import types, F
from app.bot.loader import router
from app.db.base import get_db
from app.db import crud
from app.settings import get_app_config
from app.core.rate import check_rate_limit
from app.core.multi_brain_pipeline import process_message_pipeline
from app.core.constants import ERROR_MESSAGES


@router.message(F.text & ~F.text.startswith("/"))
async def handle_text_message(message: types.Message):
    """Handle regular text messages with batching and multi-brain pipeline"""
    user_id = message.from_user.id
    user_text = message.text
    
    print(f"[CHAT] 📨 Received message from user {user_id}: {user_text[:50]}...")
    
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
        
        # Save user message (unprocessed)
        print(f"[CHAT] 💾 Saving message as unprocessed")
        crud.create_message_with_state(
            db, 
            chat.id, 
            "user", 
            user_text,
            is_processed=False
        )
        
        # Update last user message timestamp
        crud.update_chat_timestamps(db, chat.id, user_at=datetime.utcnow())
        
        # Get all unprocessed messages
        print(f"[CHAT] 🔍 Fetching unprocessed messages")
        unprocessed = crud.get_unprocessed_user_messages(db, chat.id)
        
        print(f"[CHAT] 📊 Found {len(unprocessed)} unprocessed message(s)")
        
        if len(unprocessed) > 1:
            # Already processing - this message will be batched
            print(f"[CHAT] ⏳ Message batched ({len(unprocessed)} total unprocessed) - pipeline already running")
            return
        
        print(f"[CHAT] 🚀 First unprocessed message - starting pipeline")
        
        # Extract data for pipeline
        chat_id = chat.id
        tg_chat_id = chat.tg_chat_id
        messages_data = [{"id": str(m.id), "text": m.text} for m in unprocessed]
        
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

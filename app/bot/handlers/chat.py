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
            # No active persona selected
            await message.answer(ERROR_MESSAGES["no_persona"])
            return
        
        # Save user message (unprocessed)
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
        unprocessed = crud.get_unprocessed_user_messages(db, chat.id)
        
        if len(unprocessed) > 1:
            # Already processing - this message will be batched
            print(f"[CHAT] Message batched ({len(unprocessed)} total unprocessed)")
            return
        
        # Extract data for pipeline
        chat_id = chat.id
        tg_chat_id = chat.tg_chat_id
        messages_data = [{"id": str(m.id), "text": m.text} for m in unprocessed]
    
    # Batch all unprocessed messages
    batched_text = "\n".join([m["text"] for m in messages_data])
    
    print(f"[CHAT] Processing {len(messages_data)} message(s) for chat {chat_id}")
    
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
        # Handle validation errors (chat/persona not found)
        print(f"[CHAT] Validation error: {e}")
        await message.answer(ERROR_MESSAGES["chat_not_found"])
    except Exception as e:
        # Handle unexpected errors
        print(f"[CHAT] Error in pipeline: {e}")
        import traceback
        traceback.print_exc()
        await message.answer(ERROR_MESSAGES["processing_error"])

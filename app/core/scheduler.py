"""
Background scheduler for auto-messages and other periodic tasks
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
from app.db.base import get_db
from app.db import crud
from app.core import redis_queue
from app.core.multi_brain_pipeline import process_message_pipeline

scheduler = AsyncIOScheduler()


async def check_inactive_chats():
    """Check for chats inactive >5min and send follow-up"""
    print("[SCHEDULER] Checking for inactive chats...")
    
    try:
        # Extract chat data while in session context
        with get_db() as db:
            inactive_chats = crud.get_inactive_chats(db, minutes=5)
            # Extract needed data before session closes
            chat_data = [
                {"chat_id": chat.id, "tg_chat_id": chat.tg_chat_id}
                for chat in inactive_chats
            ]
        
        if not chat_data:
            print(f"[SCHEDULER] No inactive chats found")
            return
        
        print(f"[SCHEDULER] Found {len(chat_data)} inactive chats")
        
        for data in chat_data:
            try:
                await send_auto_message(data["chat_id"], data["tg_chat_id"])
            except Exception as e:
                print(f"[SCHEDULER] Auto-message error for chat {data['chat_id']}: {e}")
                
    except Exception as e:
        print(f"[SCHEDULER] Error checking inactive chats: {e}")


async def send_auto_message(chat_id, tg_chat_id):
    """
    Generate and send contextual follow-up using the full multi-brain pipeline
    
    This uses a special [AUTO_FOLLOWUP] marker to tell the AI to generate
    a natural follow-up message based on the conversation context.
    """
    print(f"[SCHEDULER] 🤖 Generating auto-follow-up for chat {chat_id}")
    
    # Get user_id from database
    with get_db() as db:
        chat_obj = crud.get_chat_by_id(db, chat_id)
        if not chat_obj:
            print(f"[SCHEDULER] ❌ Chat {chat_id} not found")
            return
        user_id = chat_obj.user_id
        
        # Mark that we're sending an auto-message to prevent repeated sends
        chat_obj.last_auto_message_at = datetime.utcnow()
        db.commit()
    
    # Add a special system message to the queue that triggers AI-initiated conversation
    # This will go through the full pipeline: State → Dialogue → Image → Send
    await redis_queue.add_message_to_queue(
        chat_id=chat_id,
        user_id=user_id,
        text="[AUTO_FOLLOWUP] You haven't heard from the user in a while. Send them a natural, contextual follow-up message to re-engage the conversation. Be playful, flirty, or curious based on your personality and the conversation state.",
        tg_chat_id=tg_chat_id
    )
    
    print(f"[SCHEDULER] 📥 Auto-follow-up queued, starting pipeline...")
    
    # Trigger the full multi-brain pipeline
    try:
        await process_message_pipeline(
            chat_id=chat_id,
            user_id=user_id,
            tg_chat_id=tg_chat_id
        )
        print(f"[SCHEDULER] ✅ Auto-follow-up sent successfully")
    except Exception as e:
        print(f"[SCHEDULER] ❌ Failed to send auto-follow-up: {e}")
        # Clear the auto-message timestamp so we can try again later
        with get_db() as db:
            chat_obj = crud.get_chat_by_id(db, chat_id)
            if chat_obj:
                chat_obj.last_auto_message_at = None
                db.commit()


def start_scheduler():
    """Start the background scheduler"""
    print("[SCHEDULER] Starting background scheduler...")
    
    # Check for inactive chats every minute
    scheduler.add_job(check_inactive_chats, 'interval', minutes=1)
    scheduler.start()
    
    print("[SCHEDULER] ✅ Scheduler started")


def stop_scheduler():
    """Stop the background scheduler"""
    print("[SCHEDULER] Stopping scheduler...")
    scheduler.shutdown()
    print("[SCHEDULER] ✅ Scheduler stopped")



"""
Background scheduler for auto-messages and other periodic tasks
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
from app.db.base import get_db
from app.db import crud
from app.bot.loader import bot

scheduler = AsyncIOScheduler()


async def check_inactive_chats():
    """Check for chats inactive >5min and send follow-up"""
    print("[SCHEDULER] Checking for inactive chats...")
    
    try:
        with get_db() as db:
            inactive_chats = crud.get_inactive_chats(db, minutes=5)
        
        if not inactive_chats:
            print(f"[SCHEDULER] No inactive chats found")
            return
        
        print(f"[SCHEDULER] Found {len(inactive_chats)} inactive chats")
        
        for chat in inactive_chats:
            try:
                await send_auto_message(chat)
            except Exception as e:
                print(f"[SCHEDULER] Auto-message error for chat {chat.id}: {e}")
                
    except Exception as e:
        print(f"[SCHEDULER] Error checking inactive chats: {e}")


async def send_auto_message(chat):
    """
    Generate and send contextual follow-up
    
    TODO: Implement auto-message generation logic
    For now, this is a placeholder that can be expanded later
    """
    print(f"[SCHEDULER] Would send auto-message to chat {chat.id}")
    
    # Placeholder - in future this could:
    # 1. Get last conversation context
    # 2. Generate contextual follow-up using dialogue specialist
    # 3. Generate image
    # 4. Send to user
    # 5. Update timestamps
    
    # For now, just update timestamp to avoid spam
    with get_db() as db:
        crud.update_chat_timestamps(db, chat.id, assistant_at=datetime.utcnow())


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



"""
Background scheduler for auto-messages and other periodic tasks
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
from app.db.base import get_db
from app.db import crud
from app.core import redis_queue
from app.core.multi_brain_pipeline import process_message_pipeline

scheduler = AsyncIOScheduler()


async def check_inactive_chats():
    """Check for chats inactive >30min and send follow-up"""
    print("[SCHEDULER] Checking for inactive chats (30min)...")
    
    try:
        # Extract chat data while in session context
        with get_db() as db:
            inactive_chats = crud.get_inactive_chats(db, minutes=30)
            # Extract needed data before session closes
            chat_data = [
                {"chat_id": chat.id, "tg_chat_id": chat.tg_chat_id}
                for chat in inactive_chats
            ]
        
        if not chat_data:
            print(f"[SCHEDULER] No inactive chats found (30min)")
            return
        
        print(f"[SCHEDULER] Found {len(chat_data)} inactive chats (30min)")
        
        for data in chat_data:
            try:
                await send_auto_message(data["chat_id"], data["tg_chat_id"])
            except Exception as e:
                print(f"[SCHEDULER] Auto-message error for chat {data['chat_id']}: {e}")
                
    except Exception as e:
        print(f"[SCHEDULER] Error checking inactive chats (30min): {e}")


async def check_inactive_chats_24h():
    """Check for chats inactive >24 hours and send re-engagement follow-up
    
    This allows sending a second auto-message even if we sent one at 30min
    and the user still hasn't responded. We only re-engage if it's been
    24 hours since our last auto-message attempt.
    """
    print("[SCHEDULER] Checking for inactive chats (24h re-engagement)...")
    
    try:
        # Extract chat data while in session context
        with get_db() as db:
            # Use the special re-engagement function that allows follow-ups
            # even if we already sent an auto-message (as long as it was 24h ago)
            inactive_chats = crud.get_inactive_chats_for_reengagement(db, minutes=1440)  # 24 hours
            # Extract needed data before session closes
            chat_data = [
                {"chat_id": chat.id, "tg_chat_id": chat.tg_chat_id}
                for chat in inactive_chats
            ]
        
        if not chat_data:
            print(f"[SCHEDULER] No inactive chats found (24h)")
            return
        
        print(f"[SCHEDULER] Found {len(chat_data)} inactive chats needing re-engagement (24h)")
        
        for data in chat_data:
            try:
                await send_auto_message(data["chat_id"], data["tg_chat_id"])
            except Exception as e:
                print(f"[SCHEDULER] Auto-message error for chat {data['chat_id']}: {e}")
                
    except Exception as e:
        print(f"[SCHEDULER] Error checking inactive chats (24h): {e}")


async def send_auto_message(chat_id, tg_chat_id):
    """
    Generate and send contextual follow-up using the full multi-brain pipeline
    
    This uses a special [AUTO_FOLLOWUP] marker to tell the AI to generate
    a natural follow-up message based on the conversation context.
    """
    print(f"[SCHEDULER] 🤖 Generating auto-follow-up for chat {chat_id}")
    
    # Get user_id and conversation context from database
    with get_db() as db:
        chat_obj = crud.get_chat_by_id(db, chat_id)
        if not chat_obj:
            print(f"[SCHEDULER] ❌ Chat {chat_id} not found")
            return
        user_id = chat_obj.user_id
        
        # Mark that we're sending an auto-message to prevent repeated sends
        chat_obj.last_auto_message_at = datetime.utcnow()
        db.commit()
    
    # Create varied, context-aware follow-up prompts
    import random
    followup_prompts = [
        "[AUTO_FOLLOWUP] The user hasn't replied in a while. Reach out naturally - ask what they've been up to, share a playful thought, or tease them gently about the silence. Keep it light, flirty, and conversational.",
        "[AUTO_FOLLOWUP] It's been quiet for a bit. Send a message that picks up naturally from your last conversation - reference what you were talking about, ask a curious question, or create a new hook to draw them back in.",
        "[AUTO_FOLLOWUP] Time to re-engage. Send a natural, spontaneous message - maybe share what you've been thinking about, tease them playfully, or suggest something fun. Make it feel organic, not forced.",
        "[AUTO_FOLLOWUP] The conversation paused. Reach out with genuine curiosity - ask about their day, bring up something from earlier, or shift the mood with a flirty or playful comment.",
    ]
    
    selected_prompt = random.choice(followup_prompts)
    
    # Add a special system message to the queue that triggers AI-initiated conversation
    # This will go through the full pipeline: State → Dialogue → Image → Send
    await redis_queue.add_message_to_queue(
        chat_id=chat_id,
        user_id=user_id,
        text=selected_prompt,
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
    
    # Check for inactive chats every minute (30min threshold)
    scheduler.add_job(check_inactive_chats, 'interval', minutes=1)
    
    # Check for inactive chats every hour (24h threshold)
    scheduler.add_job(check_inactive_chats_24h, 'interval', hours=1)
    
    scheduler.start()
    
    print("[SCHEDULER] ✅ Scheduler started - 30min check every 1min, 24h check every 1h")


def stop_scheduler():
    """Stop the background scheduler"""
    print("[SCHEDULER] Stopping scheduler...")
    scheduler.shutdown()
    print("[SCHEDULER] ✅ Scheduler stopped")



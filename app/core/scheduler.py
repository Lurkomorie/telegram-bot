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
    from app.settings import settings
    
    print("[SCHEDULER] Checking for inactive chats (30min)...")
    
    # Check if test user whitelist is enabled
    test_user_ids = settings.followup_test_user_ids
    if test_user_ids:
        print(f"[SCHEDULER] 🧪 Test mode: Followups restricted to user IDs: {test_user_ids}")
    
    try:
        # Extract chat data while in session context
        with get_db() as db:
            inactive_chats = crud.get_inactive_chats(db, minutes=30, test_user_ids=test_user_ids)
            # Extract needed data before session closes
            chat_data = [
                {"chat_id": chat.id, "tg_chat_id": chat.tg_chat_id, "user_id": chat.user_id}
                for chat in inactive_chats
            ]
        
        if not chat_data:
            print("[SCHEDULER] No inactive chats found (30min)")
            return
        
        print(f"[SCHEDULER] Found {len(chat_data)} inactive chats (30min)")
        
        for data in chat_data:
            try:
                await send_auto_message(data["chat_id"], data["tg_chat_id"], followup_type="30min")
            except Exception as e:
                print(f"[SCHEDULER] Auto-message error for chat {data['chat_id']}: {e}")
                
    except Exception as e:
        print(f"[SCHEDULER] Error checking inactive chats (30min): {e}")


async def check_inactive_chats_24h():
    """Check for chats inactive >24 hours and send re-engagement follow-up
    
    This allows sending a second auto-message even if we sent one at 30min
    and the user still hasn't responded. We only re-engage if it's been
    24 hours since our last auto-message attempt.
    
    Rate-limited to process max 4 chats per run to avoid overwhelming
    the image generation queue. With 5-minute intervals, this means
    4 low-priority image requests every 5 minutes.
    """
    from app.settings import settings
    
    print("[SCHEDULER] Checking for inactive chats (24h re-engagement)...")
    
    # Check if test user whitelist is enabled
    test_user_ids = settings.followup_test_user_ids
    if test_user_ids:
        print(f"[SCHEDULER] 🧪 Test mode: Followups restricted to user IDs: {test_user_ids}")
    
    try:
        # Extract chat data while in session context
        with get_db() as db:
            # Use the special re-engagement function that allows follow-ups
            # even if we already sent an auto-message (as long as it was 24h ago)
            # We check for required_count=1 (meaning they received the 30min message)
            inactive_chats = crud.get_inactive_chats_for_reengagement(db, minutes=1440, test_user_ids=test_user_ids, required_count=1)  # 24 hours
            # Extract needed data before session closes
            chat_data = [
                {"chat_id": chat.id, "tg_chat_id": chat.tg_chat_id, "user_id": chat.user_id}
                for chat in inactive_chats
            ]
        
        if not chat_data:
            print("[SCHEDULER] No inactive chats found (24h)")
            return
        
        total_chats = len(chat_data)
        print(f"[SCHEDULER] Found {total_chats} inactive chats needing re-engagement (24h)")
        
        # Rate limit: Process max 4 chats per run to prevent overwhelming the queue
        max_per_run = 4
        chats_to_process = chat_data[:max_per_run]
        
        if total_chats > max_per_run:
            print(f"[SCHEDULER] ⏱️  Rate limiting: Processing {max_per_run} of {total_chats} chats (remaining will be processed in next run)")
        
        for data in chats_to_process:
            try:
                await send_auto_message(data["chat_id"], data["tg_chat_id"], followup_type="24h")
            except Exception as e:
                print(f"[SCHEDULER] Auto-message error for chat {data['chat_id']}: {e}")
                
    except Exception as e:
        print(f"[SCHEDULER] Error checking inactive chats (24h): {e}")


async def check_inactive_chats_3day():
    """Check for chats inactive >3 days and send re-engagement follow-up
    
    This allows sending a follow-up 3 days after the last auto-message.
    We only re-engage if it's been 3 days since the last auto-message
    and the user still hasn't responded.
    
    Rate-limited to process max 4 chats per run to avoid overwhelming
    the image generation queue. With 10-minute intervals, this means
    4 low-priority image requests every 10 minutes.
    """
    from app.settings import settings
    
    print("[SCHEDULER] Checking for inactive chats (3 day re-engagement)...")
    
    # Check if test user whitelist is enabled
    test_user_ids = settings.followup_test_user_ids
    if test_user_ids:
        print(f"[SCHEDULER] 🧪 Test mode: Followups restricted to user IDs: {test_user_ids}")
    
    try:
        # Extract chat data while in session context
        with get_db() as db:
            # Use the re-engagement function with 3 days = 72 hours = 4320 minutes
            # We check for required_count=2 (meaning they received the 24h message)
            inactive_chats = crud.get_inactive_chats_for_reengagement(db, minutes=4320, test_user_ids=test_user_ids, required_count=2)
            # Extract needed data before session closes
            chat_data = [
                {"chat_id": chat.id, "tg_chat_id": chat.tg_chat_id, "user_id": chat.user_id}
                for chat in inactive_chats
            ]
        
        if not chat_data:
            print("[SCHEDULER] No inactive chats found (3 day)")
            return
        
        total_chats = len(chat_data)
        print(f"[SCHEDULER] Found {total_chats} inactive chats needing re-engagement (3 day)")
        
        # Rate limit: Process max 4 chats per run to prevent overwhelming the queue
        max_per_run = 4
        chats_to_process = chat_data[:max_per_run]
        
        if total_chats > max_per_run:
            print(f"[SCHEDULER] ⏱️  Rate limiting: Processing {max_per_run} of {total_chats} chats (remaining will be processed in next run)")
        
        for data in chats_to_process:
            try:
                await send_auto_message(data["chat_id"], data["tg_chat_id"], followup_type="3day")
            except Exception as e:
                print(f"[SCHEDULER] Auto-message error for chat {data['chat_id']}: {e}")
                
    except Exception as e:
        print(f"[SCHEDULER] Error checking inactive chats (3 day): {e}")


async def regenerate_daily_energy():
    """Regenerate 10 energy every day for all non-premium users"""
    print("[SCHEDULER] ⚡ Running daily energy regeneration...")
    
    try:
        with get_db() as db:
            count = crud.regenerate_all_users_energy(db)
        
        print(f"[SCHEDULER] ✅ Regenerated 10 energy for {count} users")
    except Exception as e:
        print(f"[SCHEDULER] ❌ Error regenerating energy: {e}")


async def send_auto_message(chat_id, tg_chat_id, followup_type: str = "30min"):
    """
    Generate and send contextual follow-up using the full multi-brain pipeline
    
    This uses a special [AUTO_FOLLOWUP] marker to tell the AI to generate
    a natural follow-up message based on the conversation context.
    
    Args:
        chat_id: Chat UUID
        tg_chat_id: Telegram chat ID
        followup_type: Type of followup ("30min" or "24h")
    """
    print(f"[SCHEDULER] 🤖 Generating auto-follow-up for chat {chat_id} (type: {followup_type})")
    
    # Get user_id and conversation context from database
    with get_db() as db:
        chat_obj = crud.get_chat_by_id(db, chat_id)
        if not chat_obj:
            print(f"[SCHEDULER] ❌ Chat {chat_id} not found")
            return
        user_id = chat_obj.user_id
        
        # Mark that we're sending an auto-message to prevent repeated sends
        chat_obj.last_auto_message_at = datetime.utcnow()
        
        # Update auto_message_count based on type to prevent infinite loops
        new_count = 1
        if followup_type == "24h":
            new_count = 2
        elif followup_type == "3day":
            new_count = 3
            
        # Initialize ext if None and ensure we update it properly
        if chat_obj.ext is None:
            chat_obj.ext = {}
            
        # Create a copy to ensure SQLAlchemy tracks the change for JSONB
        ext_copy = dict(chat_obj.ext)
        ext_copy['auto_message_count'] = new_count
        chat_obj.ext = ext_copy
        
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
        tg_chat_id=tg_chat_id,
        context={"followup_type": followup_type}
    )
    
    print("[SCHEDULER] 📥 Auto-follow-up queued, starting pipeline...")
    
    # Trigger the full multi-brain pipeline
    try:
        await process_message_pipeline(
            chat_id=chat_id,
            user_id=user_id,
            tg_chat_id=tg_chat_id
        )
        print("[SCHEDULER] ✅ Auto-follow-up sent successfully")
    except Exception as e:
        print(f"[SCHEDULER] ❌ Failed to send auto-follow-up: {e}")
        
        # Handle blocked users by archiving the chat
        error_str = str(e)
        if "Forbidden: bot was blocked" in error_str or "user is deactivated" in error_str:
            print(f"[SCHEDULER] 🚫 User {user_id} blocked the bot. Archiving chat {chat_id}.")
            with get_db() as db:
                chat_obj = crud.get_chat_by_id(db, chat_id)
                if chat_obj:
                    chat_obj.status = "archived"
                    db.commit()
        else:
            # Clear the auto-message timestamp so we can try again later (only if not blocked)
            with get_db() as db:
                chat_obj = crud.get_chat_by_id(db, chat_id)
                if chat_obj:
                    chat_obj.last_auto_message_at = None
                    db.commit()


def start_scheduler():
    """Start the background scheduler"""
    from app.settings import settings
    
    print("[SCHEDULER] Starting background scheduler...")
    
    # Only add followup jobs if enabled
    if settings.ENABLE_FOLLOWUPS:
        # Check for inactive chats every minute (30min threshold)
        scheduler.add_job(check_inactive_chats, 'interval', minutes=1)
        
        # Check for inactive chats every 5 minutes (24h threshold)
        # Processes max 4 chats per run = 4 low-priority image requests every 5 minutes
        scheduler.add_job(check_inactive_chats_24h, 'interval', minutes=5)
        
        # Check for inactive chats every 10 minutes (3 day threshold)
        # Processes max 4 chats per run = 4 low-priority image requests every 10 minutes
        scheduler.add_job(check_inactive_chats_3day, 'interval', minutes=10)
        
        print("[SCHEDULER] ✅ Followup jobs enabled (30min check every 1min, 24h check every 5min, 3day check every 10min with max 4 chats/run)")
    else:
        print("[SCHEDULER] ⚠️  Followup jobs disabled (ENABLE_FOLLOWUPS=False)")
    
    # Regenerate energy every day (if enabled)
    if settings.ENABLE_ENERGY_REGEN:
        scheduler.add_job(regenerate_daily_energy, 'interval', days=1)
        print("[SCHEDULER] ✅ Energy regeneration enabled (10 energy every day)")
    else:
        print("[SCHEDULER] ⚠️  Energy regeneration disabled (ENABLE_ENERGY_REGEN=False)")
    
    scheduler.start()
    
    print("[SCHEDULER] ✅ Scheduler started")


def stop_scheduler():
    """Stop the background scheduler"""
    print("[SCHEDULER] Stopping scheduler...")
    scheduler.shutdown()
    print("[SCHEDULER] ✅ Scheduler stopped")



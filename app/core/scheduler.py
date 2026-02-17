"""
Background scheduler for auto-messages and other periodic tasks
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
import logging
from app.db.base import get_db
from app.db import crud
from app.core import redis_queue
from app.core.multi_brain_pipeline import process_message_pipeline
from app.core import system_message_service

scheduler = AsyncIOScheduler()
logger = logging.getLogger(__name__)


async def check_inactive_chats_3min():
    """Check for chats inactive >3min and send first quick follow-up"""
    from app.settings import settings
    
    print("[SCHEDULER] Checking for inactive chats (3min)...")
    
    # Check if test user whitelist is enabled
    test_user_ids = settings.followup_test_user_ids
    if test_user_ids:
        print(f"[SCHEDULER] 🧪 Test mode: Followups restricted to user IDs: {test_user_ids}")
    
    try:
        # Extract chat data while in session context
        with get_db() as db:
            inactive_chats = crud.get_inactive_chats(db, minutes=3, test_user_ids=test_user_ids)
            # Extract needed data before session closes
            chat_data = [
                {"chat_id": chat.id, "tg_chat_id": chat.tg_chat_id, "user_id": chat.user_id}
                for chat in inactive_chats
            ]
        
        if not chat_data:
            print("[SCHEDULER] No inactive chats found (3min)")
            return
        
        print(f"[SCHEDULER] Found {len(chat_data)} inactive chats (3min)")
        
        for data in chat_data:
            try:
                await send_auto_message(data["chat_id"], data["tg_chat_id"], followup_type="3min")
            except Exception as e:
                print(f"[SCHEDULER] Auto-message error for chat {data['chat_id']}: {e}")
                
    except Exception as e:
        print(f"[SCHEDULER] Error checking inactive chats (3min): {e}")


async def check_inactive_chats():
    """Check for chats inactive >30min and send follow-up (after 3min followup)"""
    from app.settings import settings
    
    print("[SCHEDULER] Checking for inactive chats (30min)...")
    
    # Check if test user whitelist is enabled
    test_user_ids = settings.followup_test_user_ids
    if test_user_ids:
        print(f"[SCHEDULER] 🧪 Test mode: Followups restricted to user IDs: {test_user_ids}")
    
    try:
        # Extract chat data while in session context
        with get_db() as db:
            # Use reengagement with required_count=1 (3min followup was sent)
            inactive_chats = crud.get_inactive_chats_for_reengagement(db, minutes=30, test_user_ids=test_user_ids, required_count=1)
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
    
    This allows sending an auto-message if we sent one at 30min
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
            # We check for required_count=2 (meaning they received the 30min message)
            # Flow: 3min (count=1) → 30min (count=2) → 24h (count=3)
            inactive_chats = crud.get_inactive_chats_for_reengagement(db, minutes=1440, test_user_ids=test_user_ids, required_count=2)  # 24 hours
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
            # We check for required_count=3 (meaning they received the 24h message)
            # Flow: 3min (count=1) → 30min (count=2) → 24h (count=3) → 3day (count=4)
            inactive_chats = crud.get_inactive_chats_for_reengagement(db, minutes=4320, test_user_ids=test_user_ids, required_count=3)
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


async def add_daily_tokens_by_tier():
    """Add daily tokens to premium tier users based on their subscription level"""
    print("[SCHEDULER] 🪙 Running daily token addition by tier...")
    
    try:
        with get_db() as db:
            count = crud.add_daily_tokens_by_tier(db)
        
        print(f"[SCHEDULER] ✅ Added daily tokens for {count} premium tier users")
    except Exception as e:
        print(f"[SCHEDULER] ❌ Error adding daily tokens: {e}")


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
        # Flow: 3min (count=1) → 30min (count=2) → 24h (count=3) → 3day (count=4)
        new_count = 1  # Default for 3min
        if followup_type == "30min":
            new_count = 2
        elif followup_type == "24h":
            new_count = 3
        elif followup_type == "3day":
            new_count = 4
            
        # Initialize ext if None and ensure we update it properly
        if chat_obj.ext is None:
            chat_obj.ext = {}
            
        # Create a copy to ensure SQLAlchemy tracks the change for JSONB
        ext_copy = dict(chat_obj.ext)
        ext_copy['auto_message_count'] = new_count
        chat_obj.ext = ext_copy
        
        db.commit()
        
        # Store the count we just set for potential rollback on error
        committed_count = new_count
    
    # Create varied, stage-aware follow-up prompts
    import random
    followup_prompts_by_type = {
        "3min": [
            "[AUTO_FOLLOWUP] Stage: 3min. Send a quick, playful nudge right after the pause. Keep it light and short (1-2 sentences), with one natural hook to continue. Respond in the dialog's language.",
            "[AUTO_FOLLOWUP] Stage: 3min. The pause is recent. Send a warm check-in that feels spontaneous, flirty, and concise. Avoid heavy recap. Respond in the dialog's language.",
            "[AUTO_FOLLOWUP] Stage: 3min. Re-open smoothly with a small tease or curious question tied to the mood. Keep it breezy and short. Respond in the dialog's language.",
        ],
        "30min": [
            "[AUTO_FOLLOWUP] Stage: 30min (second follow-up). Re-engage from a fresh angle - use different wording from your last message and ask one new concrete question. Keep it natural and flirty. Respond in the dialog's language.",
            "[AUTO_FOLLOWUP] Stage: 30min (second follow-up). Create a NEW hook (not a paraphrase of your previous line): shift topic slightly, tease gently, and invite a reply. Respond in the dialog's language.",
            "[AUTO_FOLLOWUP] Stage: 30min (second follow-up). Keep momentum without repeating yourself: different opening action, different phrasing, and one curious prompt. Respond in the dialog's language.",
        ],
        "24h": [
            "[AUTO_FOLLOWUP] Stage: 24h re-engagement. Re-open warmly with fresh energy and a new idea. Do not repeat your last check-in wording. Keep it organic and inviting. Respond in the dialog's language.",
            "[AUTO_FOLLOWUP] Stage: 24h re-engagement. Send a message that feels like a new moment: playful, personal, and clearly different from prior follow-ups. Respond in the dialog's language.",
            "[AUTO_FOLLOWUP] Stage: 24h re-engagement. Use a vivid, natural opener and one question that reconnects emotionally. Avoid reminder-style phrasing. Respond in the dialog's language.",
        ],
        "3day": [
            "[AUTO_FOLLOWUP] Stage: 3day re-engagement. Start with a bold, fresh opener and a clearly new conversational direction. Keep it warm and magnetic, not repetitive. Respond in the dialog's language.",
            "[AUTO_FOLLOWUP] Stage: 3day re-engagement. Treat this as a new spark: use different structure, different verbs, and a compelling hook to pull them back in. Respond in the dialog's language.",
            "[AUTO_FOLLOWUP] Stage: 3day re-engagement. Reconnect naturally with a fresh playful tone and one strong invitation to reply. Avoid repeating earlier follow-up lines. Respond in the dialog's language.",
        ],
    }
    default_prompts = followup_prompts_by_type["30min"]
    followup_prompts = followup_prompts_by_type.get(followup_type, default_prompts)
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
        
        # Handle blocked users by archiving the chat and marking user as blocked
        error_str = str(e)
        if "Forbidden: bot was blocked" in error_str or "user is deactivated" in error_str:
            print(f"[SCHEDULER] 🚫 User {user_id} blocked the bot. Archiving chat {chat_id} and marking user as blocked.")
            with get_db() as db:
                chat_obj = crud.get_chat_by_id(db, chat_id)
                if chat_obj:
                    chat_obj.status = "archived"
                    db.commit()
                # Mark user as blocked so we don't try to send them messages anymore
                crud.mark_user_bot_blocked(db, user_id)
        else:
            # Reset both timestamp AND count so we can try again later (only if not blocked)
            # We need to rollback to the previous count value to allow the same scheduler to retry
            with get_db() as db:
                chat_obj = crud.get_chat_by_id(db, chat_id)
                if chat_obj:
                    chat_obj.last_auto_message_at = None
                    
                    # Rollback auto_message_count to allow retry
                    # committed_count was set before the pipeline call
                    previous_count = committed_count - 1 if committed_count > 0 else 0
                    if chat_obj.ext is None:
                        chat_obj.ext = {}
                    ext_copy = dict(chat_obj.ext)
                    ext_copy['auto_message_count'] = previous_count
                    chat_obj.ext = ext_copy
                    
                    db.commit()
                    print(f"[SCHEDULER] ↩️  Reset auto_message_count to {previous_count} for retry")


async def check_scheduled_messages():
    """
    Check for scheduled messages ready to send
    
    Uses database-level locking for concurrency safety across multiple instances
    """
    logger.debug("Checking for scheduled system messages")
    
    try:
        with get_db() as db:
            # This now uses SELECT FOR UPDATE SKIP LOCKED for concurrency safety
            scheduled_messages = crud.get_scheduled_messages(db)
            message_data = [
                {"id": msg.id, "status": msg.status}
                for msg in scheduled_messages
            ]
        
        if not message_data:
            logger.debug("No scheduled messages ready to send")
            return
        
        logger.info(f"Found {len(message_data)} scheduled messages ready to send", extra={
            "message_count": len(message_data),
            "message_ids": [str(d["id"]) for d in message_data]
        })
        
        for data in message_data:
            try:
                await system_message_service.send_system_message(data["id"])
                logger.info(f"Sent scheduled message", extra={
                    "message_id": str(data["id"])
                })
            except Exception as e:
                logger.error(f"Error sending scheduled message", extra={
                    "message_id": str(data["id"]),
                    "error": str(e)
                }, exc_info=True)
                
    except Exception as e:
        logger.error(f"Error checking scheduled messages", extra={
            "error": str(e)
        }, exc_info=True)


async def retry_failed_deliveries_task():
    """
    Retry failed system message deliveries
    
    Note: This task is NOT scheduled to run automatically.
    Users can manually retry failed deliveries via the UI button.
    This function remains here in case you want to re-enable auto-retry in the future.
    """
    logger.debug("Retrying failed system message deliveries")
    
    try:
        stats = await system_message_service.retry_failed_deliveries()
        if stats["retried"] > 0:
            logger.info(f"Retried deliveries", extra={
                "retried": stats["retried"],
                "success": stats["success"],
                "failed": stats["failed"]
            })
        else:
            logger.debug("No failed deliveries to retry")
    except Exception as e:
        logger.error(f"Error retrying failed deliveries", extra={
            "error": str(e)
        }, exc_info=True)


def start_scheduler():
    """Start the background scheduler"""
    from app.settings import settings
    
    print("[SCHEDULER] Starting background scheduler...")
    
    # Only add followup jobs if enabled
    if settings.ENABLE_FOLLOWUPS:
        # Check for inactive chats every minute (3min threshold - first quick followup)
        scheduler.add_job(check_inactive_chats_3min, 'interval', minutes=1)
        
        # Check for inactive chats every minute (30min threshold - after 3min followup)
        scheduler.add_job(check_inactive_chats, 'interval', minutes=1)
        
        # Check for inactive chats every 5 minutes (24h threshold)
        # Processes max 4 chats per run = 4 low-priority image requests every 5 minutes
        scheduler.add_job(check_inactive_chats_24h, 'interval', minutes=5)
        
        # Check for inactive chats every 10 minutes (3 day threshold)
        # Processes max 4 chats per run = 4 low-priority image requests every 10 minutes
        scheduler.add_job(check_inactive_chats_3day, 'interval', minutes=10)
        
        print("[SCHEDULER] ✅ Followup jobs enabled (3min, 30min checks every 1min, 24h every 5min, 3day every 10min)")
    else:
        print("[SCHEDULER] ⚠️  Followup jobs disabled (ENABLE_FOLLOWUPS=False)")
    
    # DISABLED: Daily energy regeneration for premium users
    # Premium now = unlimited energy, no need for daily refills
    # scheduler.add_job(add_daily_tokens_by_tier, 'interval', hours=1)
    # print("[SCHEDULER] ✅ Daily temp energy refill check enabled (hourly check, 24h per user)")
    print("[SCHEDULER] ⚠️  Daily energy refill disabled (Premium = unlimited energy)")
    
    # Check for scheduled system messages every minute
    scheduler.add_job(check_scheduled_messages, 'interval', minutes=1)
    print("[SCHEDULER] ✅ Scheduled system messages check enabled (every 1 minute)")
    
    # Note: Auto-retry disabled - use manual retry button in UI instead
    # scheduler.add_job(retry_failed_deliveries_task, 'interval', minutes=5)
    # print("[SCHEDULER] ⚠️  Auto-retry disabled (use manual retry in UI)")
    
    scheduler.start()
    
    print("[SCHEDULER] ✅ Scheduler started")


def stop_scheduler():
    """Stop the background scheduler"""
    print("[SCHEDULER] Stopping scheduler...")
    scheduler.shutdown()
    print("[SCHEDULER] ✅ Scheduler stopped")

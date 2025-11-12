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
            print(f"[SCHEDULER] No inactive chats found (30min)")
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
            inactive_chats = crud.get_inactive_chats_for_reengagement(db, minutes=1440, test_user_ids=test_user_ids)  # 24 hours
            # Extract needed data before session closes
            chat_data = [
                {"chat_id": chat.id, "tg_chat_id": chat.tg_chat_id, "user_id": chat.user_id}
                for chat in inactive_chats
            ]
        
        if not chat_data:
            print(f"[SCHEDULER] No inactive chats found (24h)")
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


async def regenerate_hourly_energy():
    """Regenerate 2 energy every hour for all non-premium users"""
    print("[SCHEDULER] ⚡ Running hourly energy regeneration...")
    
    try:
        with get_db() as db:
            count = crud.regenerate_all_users_energy(db)
        
        print(f"[SCHEDULER] ✅ Regenerated 2 energy for {count} users")
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
        # Check for inactive chats every minute (30min threshold)
        scheduler.add_job(check_inactive_chats, 'interval', minutes=1)
        
        # Check for inactive chats every 5 minutes (24h threshold)
        # Processes max 4 chats per run = 4 low-priority image requests every 5 minutes
        scheduler.add_job(check_inactive_chats_24h, 'interval', minutes=5)
        
        print("[SCHEDULER] ✅ Followup jobs enabled (30min check every 1min, 24h check every 5min with max 4 chats/run)")
    else:
        print("[SCHEDULER] ⚠️  Followup jobs disabled (ENABLE_FOLLOWUPS=False)")
    
    # Regenerate energy every hour (if enabled)
    if settings.ENABLE_ENERGY_REGEN:
        scheduler.add_job(regenerate_hourly_energy, 'interval', hours=1)
        print("[SCHEDULER] ✅ Energy regeneration enabled (2 energy every hour)")
    else:
        print("[SCHEDULER] ⚠️  Energy regeneration disabled (ENABLE_ENERGY_REGEN=False)")
    
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
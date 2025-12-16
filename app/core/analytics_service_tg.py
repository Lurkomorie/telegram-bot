"""
Analytics Service for Telegram Bot
Tracks all user interactions in a non-blocking way
All tracking functions use asyncio.create_task() to avoid blocking main bot operations
"""
import asyncio
from typing import Optional
from uuid import UUID
from app.db.base import get_db
from app.db import crud
from app.core.cloudflare_upload import upload_to_cloudflare_tg


async def _track_event_impl(
    client_id: int,
    event_name: str,
    persona_id: Optional[UUID] = None,
    persona_name: Optional[str] = None,
    message: Optional[str] = None,
    prompt: Optional[str] = None,
    negative_prompt: Optional[str] = None,
    image_url: Optional[str] = None,
    meta: Optional[dict] = None
):
    """
    Internal implementation of event tracking
    This function does the actual DB write
    """
    try:
        with get_db() as db:
            crud.create_analytics_event(
                db=db,
                client_id=client_id,
                event_name=event_name,
                persona_id=persona_id,
                persona_name=persona_name,
                message=message,
                prompt=prompt,
                negative_prompt=negative_prompt,
                image_url=image_url,
                meta=meta or {}
            )
            print(f"[ANALYTICS] ✅ Tracked event: {event_name} for user {client_id}")
    except Exception as e:
        print(f"[ANALYTICS] ❌ Error tracking event {event_name}: {e}")


def track_event_tg(
    client_id: int,
    event_name: str,
    **kwargs
):
    """
    Track an analytics event (non-blocking)
    
    This function immediately returns and processes the event in the background
    """
    asyncio.create_task(_track_event_impl(client_id, event_name, **kwargs))


# ========== EVENT TRACKING FUNCTIONS ==========


def track_start_command(client_id: int, deep_link_param: Optional[str] = None):
    """Track /start command"""
    track_event_tg(
        client_id=client_id,
        event_name="start_command",
        meta={
            "deep_link": deep_link_param
        }
    )


def track_user_message(
    client_id: int,
    message: str,
    persona_id: Optional[UUID] = None,
    persona_name: Optional[str] = None,
    chat_id: Optional[UUID] = None
):
    """Track user sending a message"""
    track_event_tg(
        client_id=client_id,
        event_name="user_message",
        persona_id=persona_id,
        persona_name=persona_name,
        message=message[:1000],  # Limit message length
        meta={
            "chat_id": str(chat_id) if chat_id else None,
            "message_length": len(message)
        }
    )


def track_ai_message(
    client_id: int,
    message: str,
    persona_id: Optional[UUID] = None,
    persona_name: Optional[str] = None,
    chat_id: Optional[UUID] = None,
    is_auto_followup: bool = False
):
    """Track AI sending a message"""
    event_name = "auto_followup_message" if is_auto_followup else "ai_message"
    track_event_tg(
        client_id=client_id,
        event_name=event_name,
        persona_id=persona_id,
        persona_name=persona_name,
        message=message[:1000],  # Limit message length
        meta={
            "chat_id": str(chat_id) if chat_id else None,
            "message_length": len(message),
            "is_auto_followup": is_auto_followup
        }
    )


async def _upload_and_track_image(
    client_id: int,
    event_name: str,
    image_url_or_bytes: str | bytes,
    filename: str,
    persona_id: Optional[UUID] = None,
    persona_name: Optional[str] = None,
    prompt: Optional[str] = None,
    negative_prompt: Optional[str] = None,
    chat_id: Optional[UUID] = None,
    job_id: Optional[str] = None,
    is_refresh: bool = False,
    is_auto_followup: bool = False
):
    """
    Upload image to Cloudflare and track event
    This runs in background, doesn't block main thread
    """
    try:
        # Upload to Cloudflare
        print(f"[ANALYTICS] 🖼️  Uploading image to Cloudflare for analytics...")
        result = await upload_to_cloudflare_tg(image_url_or_bytes, filename)
        
        if result.success:
            cloudflare_url = result.image_url
            print(f"[ANALYTICS] ✅ Image uploaded: {cloudflare_url}")
        else:
            print(f"[ANALYTICS] ⚠️  Image upload failed: {result.error}")
            cloudflare_url = None
        
        # Track event with Cloudflare URL
        await _track_event_impl(
            client_id=client_id,
            event_name=event_name,
            persona_id=persona_id,
            persona_name=persona_name,
            prompt=prompt,
            negative_prompt=negative_prompt,
            image_url=cloudflare_url,
            meta={
                "chat_id": str(chat_id) if chat_id else None,
                "job_id": job_id,
                "is_refresh": is_refresh,
                "is_auto_followup": is_auto_followup,
                "cloudflare_upload_success": result.success
            }
        )
    except Exception as e:
        print(f"[ANALYTICS] ❌ Error in _upload_and_track_image: {e}")


def track_image_generated(
    client_id: int,
    image_url_or_bytes: str | bytes,
    persona_id: Optional[UUID] = None,
    persona_name: Optional[str] = None,
    prompt: Optional[str] = None,
    negative_prompt: Optional[str] = None,
    chat_id: Optional[UUID] = None,
    job_id: Optional[str] = None,
    is_auto_followup: bool = False
):
    """
    Track image generation (uploads to Cloudflare in background)
    
    Args:
        image_url_or_bytes: Either Telegram photo URL or binary image data
        is_auto_followup: Whether image was generated from auto-followup message
    """
    import random
    filename = f"tg_image_{client_id}_{random.randint(1000, 9999)}.png"
    
    asyncio.create_task(
        _upload_and_track_image(
            client_id=client_id,
            event_name="image_generated",
            image_url_or_bytes=image_url_or_bytes,
            filename=filename,
            persona_id=persona_id,
            persona_name=persona_name,
            prompt=prompt,
            negative_prompt=negative_prompt,
            chat_id=chat_id,
            job_id=job_id,
            is_refresh=False,
            is_auto_followup=is_auto_followup
        )
    )


def track_image_refresh(
    client_id: int,
    original_job_id: str,
    persona_id: Optional[UUID] = None,
    persona_name: Optional[str] = None
):
    """Track image refresh request"""
    track_event_tg(
        client_id=client_id,
        event_name="image_refresh",
        persona_id=persona_id,
        persona_name=persona_name,
        meta={
            "original_job_id": original_job_id
        }
    )


def track_persona_selected(
    client_id: int,
    persona_id: UUID,
    persona_name: str,
    is_new_chat: bool = False
):
    """Track persona selection"""
    track_event_tg(
        client_id=client_id,
        event_name="persona_selected",
        persona_id=persona_id,
        persona_name=persona_name,
        meta={
            "is_new_chat": is_new_chat
        }
    )


def track_story_selected(
    client_id: int,
    persona_id: UUID,
    persona_name: str,
    story_id: str,
    story_name: Optional[str] = None
):
    """Track story selection"""
    track_event_tg(
        client_id=client_id,
        event_name="story_selected",
        persona_id=persona_id,
        persona_name=persona_name,
        meta={
            "story_id": story_id,
            "story_name": story_name
        }
    )


def track_chat_cleared(
    client_id: int,
    chat_id: UUID,
    persona_id: Optional[UUID] = None,
    persona_name: Optional[str] = None
):
    """Track /clear command"""
    track_event_tg(
        client_id=client_id,
        event_name="chat_cleared",
        persona_id=persona_id,
        persona_name=persona_name,
        meta={
            "chat_id": str(chat_id)
        }
    )


def track_chat_continued(
    client_id: int,
    chat_id: UUID,
    persona_id: UUID,
    persona_name: str
):
    """Track user continuing existing conversation"""
    track_event_tg(
        client_id=client_id,
        event_name="chat_continued",
        persona_id=persona_id,
        persona_name=persona_name,
        meta={
            "chat_id": str(chat_id)
        }
    )


def track_premium_action(
    client_id: int,
    action: str,
    meta: Optional[dict] = None
):
    """Track premium-related actions (purchases, energy, etc.)"""
    track_event_tg(
        client_id=client_id,
        event_name="premium_action",
        meta={
            "action": action,
            **(meta or {})
        }
    )


def track_command(
    client_id: int,
    command: str,
    persona_id: Optional[UUID] = None,
    persona_name: Optional[str] = None
):
    """Track generic command execution"""
    track_event_tg(
        client_id=client_id,
        event_name="command",
        persona_id=persona_id,
        persona_name=persona_name,
        meta={
            "command": command
        }
    )


def track_miniapp_opened(client_id: int):
    """Track mini app opening"""
    track_event_tg(
        client_id=client_id,
        event_name="miniapp_opened"
    )


def track_plans_page_viewed(client_id: int):
    """Track plans/premium page view"""
    track_event_tg(
        client_id=client_id,
        event_name="plans_page_viewed"
    )


def track_payment_initiated(
    client_id: int,
    product_id: str,
    amount_stars: int,
    transaction_type: str
):
    """Track payment initiation"""
    track_event_tg(
        client_id=client_id,
        event_name="payment_initiated",
        meta={
            "product_id": product_id,
            "amount_stars": amount_stars,
            "transaction_type": transaction_type
        }
    )


def track_daily_bonus_claimed(client_id: int, tokens_awarded: int):
    """Track daily bonus claim"""
    track_event_tg(
        client_id=client_id,
        event_name="daily_bonus_claimed",
        meta={
            "tokens_awarded": tokens_awarded
        }
    )


def track_referral_completed(referrer_id: int, new_user_id: int, tokens_awarded: int):
    """Track successful referral"""
    track_event_tg(
        client_id=referrer_id,
        event_name="referral_completed",
        meta={
            "new_user_id": new_user_id,
            "tokens_awarded": tokens_awarded
        }
    )


def track_voice_generated(
    client_id: int,
    persona_id: Optional[UUID] = None,
    persona_name: Optional[str] = None,
    chat_id: Optional[UUID] = None,
    message_length: int = 0,
    characters_used: int = 0,
    is_free: bool = False
):
    """Track voice message generation
    
    Args:
        client_id: Telegram user ID
        persona_id: Persona UUID
        persona_name: Persona name
        chat_id: Chat UUID
        message_length: Original message length
        characters_used: Characters sent to ElevenLabs API (billed characters)
        is_free: Whether this was a free voice generation
    """
    track_event_tg(
        client_id=client_id,
        event_name="voice_generated",
        persona_id=persona_id,
        persona_name=persona_name,
        meta={
            "chat_id": str(chat_id) if chat_id else None,
            "message_length": message_length,
            "characters_used": characters_used,
            "is_free": is_free
        }
    )



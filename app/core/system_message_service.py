"""
System message sending service with rate limiting and retry logic
"""
import asyncio
import json
import logging
import re
from typing import List, Optional, Tuple, Dict, Any
from uuid import UUID
from datetime import datetime
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.exceptions import TelegramBadRequest, TelegramAPIError
from app.db.base import get_db
from app.db import crud
from app.db.models import User, SystemMessageDelivery
from app.bot.loader import bot
from app.settings import settings

# Setup structured logging
logger = logging.getLogger(__name__)


def _sanitize_html_for_telegram(html: str) -> str:
    """
    Sanitize HTML from rich text editors (like ReactQuill) to Telegram-compatible HTML.
    
    Telegram Bot API only supports: <b>, <strong>, <i>, <em>, <u>, <ins>, <s>, <strike>, 
    <del>, <a>, <code>, <pre>
    
    This function:
    1. Converts <p> tags to line breaks
    2. Removes <div>, <span>, and other unsupported tags while keeping content
    3. Converts <h1-h6> to <b>
    4. Preserves supported tags
    5. Handles nested tags properly
    
    Args:
        html: HTML string from rich text editor
        
    Returns:
        Telegram-compatible HTML string
    """
    if not html:
        return ""
    
    # Replace paragraph tags with double line breaks
    html = re.sub(r'<p[^>]*>', '', html)
    html = re.sub(r'</p>', '\n\n', html)
    
    # Replace <br> and <br/> with newlines
    html = re.sub(r'<br\s*/?>', '\n', html, flags=re.IGNORECASE)
    
    # Convert headers to bold
    html = re.sub(r'<h[1-6][^>]*>', '<b>', html, flags=re.IGNORECASE)
    html = re.sub(r'</h[1-6]>', '</b>\n\n', html, flags=re.IGNORECASE)
    
    # Remove div tags (keep content)
    html = re.sub(r'</?div[^>]*>', '', html, flags=re.IGNORECASE)
    
    # Remove span tags but keep content (unless they have special classes)
    html = re.sub(r'<span(?![^>]*class="tg-spoiler")[^>]*>', '', html, flags=re.IGNORECASE)
    html = re.sub(r'</span>', '', html, flags=re.IGNORECASE)
    
    # Remove style attributes from all tags
    html = re.sub(r'\s+style="[^"]*"', '', html, flags=re.IGNORECASE)
    
    # Remove class attributes (except tg-spoiler)
    html = re.sub(r'\s+class="(?!tg-spoiler)[^"]*"', '', html, flags=re.IGNORECASE)
    
    # Convert <ul> and <ol> lists
    html = re.sub(r'<ul[^>]*>', '', html, flags=re.IGNORECASE)
    html = re.sub(r'</ul>', '\n', html, flags=re.IGNORECASE)
    html = re.sub(r'<ol[^>]*>', '', html, flags=re.IGNORECASE)
    html = re.sub(r'</ol>', '\n', html, flags=re.IGNORECASE)
    html = re.sub(r'<li[^>]*>', '• ', html, flags=re.IGNORECASE)
    html = re.sub(r'</li>', '\n', html, flags=re.IGNORECASE)
    
    # Remove any remaining unsupported tags (keep content)
    # List of supported tags to keep
    supported_tags = r'b|strong|i|em|u|ins|s|strike|del|a|code|pre'
    html = re.sub(
        r'<(?!/?)(?!' + supported_tags + r'\b)[^>]+>',
        '',
        html,
        flags=re.IGNORECASE
    )
    
    # Clean up multiple consecutive newlines
    html = re.sub(r'\n{3,}', '\n\n', html)
    
    # Trim whitespace
    html = html.strip()
    
    return html


def _extract_message_data(message) -> Dict[str, Any]:
    """
    Extract all message data from ORM object into plain Python types.
    This prevents SQLAlchemy detached instance errors and centralizes extraction logic.
    
    Args:
        message: SystemMessage ORM object
        
    Returns:
        Dictionary with all message data as plain Python types
    """
    # Force materialization of all attributes immediately
    msg_id = message.id
    msg_text = str(message.text) if message.text else ""
    msg_media_type = str(message.media_type) if message.media_type else "none"
    msg_media_url = str(message.media_url) if message.media_url else None
    msg_target_type = str(message.target_type) if message.target_type else "all"
    msg_target_group = str(message.target_group) if message.target_group else None
    
    # Extract JSONB columns with JSON serialization to break ORM references
    try:
        buttons_raw = message.buttons
        if buttons_raw is not None:
            buttons_val = json.loads(json.dumps(buttons_raw, default=str))
            if not isinstance(buttons_val, list):
                buttons_val = []
        else:
            buttons_val = []
    except Exception as e:
        logger.error(f"Error extracting buttons: {e}", exc_info=True)
        buttons_val = []
    
    try:
        ext_raw = message.ext
        if ext_raw is not None:
            ext_val = json.loads(json.dumps(ext_raw, default=str))
            if not isinstance(ext_val, dict):
                ext_val = {}
        else:
            ext_val = {}
    except Exception as e:
        logger.error(f"Error extracting ext: {e}", exc_info=True)
        ext_val = {}
    
    try:
        target_user_ids_raw = message.target_user_ids
        if target_user_ids_raw is not None:
            target_user_ids_val = list(target_user_ids_raw)
        else:
            target_user_ids_val = []
    except Exception as e:
        logger.error(f"Error extracting target_user_ids: {e}", exc_info=True)
        target_user_ids_val = []
    
    return {
        "id": msg_id,
        "text": msg_text,
        "media_type": msg_media_type,
        "media_url": msg_media_url,
        "buttons": buttons_val,
        "ext": ext_val,
        "target_type": msg_target_type,
        "target_user_ids": target_user_ids_val,
        "target_group": msg_target_group
    }


async def send_system_message(message_id: UUID) -> dict:
    """
    Main function to send a system message
    
    Args:
        message_id: System message UUID
        
    Returns:
        dict with status and statistics
    """
    logger.info(f"Starting system message send", extra={
        "message_id": str(message_id),
        "action": "send_system_message_start"
    })
    
    # Extract all data in a single session to avoid lazy loading issues
    with get_db() as db:
        message = crud.get_system_message(db, message_id)
        if not message:
            logger.error(f"Message not found", extra={"message_id": str(message_id)})
            return {"error": "Message not found"}
        
        # Check if message was cancelled
        status = message.status
        if status == "cancelled":
            logger.warning(f"Message was cancelled", extra={"message_id": str(message_id)})
            return {"error": "Message was cancelled"}
        
        # Update status to 'sending'
        if status != "sending":
            message.status = "sending"
            db.commit()
            logger.info(f"Status updated to sending", extra={"message_id": str(message_id)})
        
        # Extract all message data using centralized helper
        message_data = _extract_message_data(message)
        
        # Get target users
        user_ids = await _get_target_users(
            db, 
            message_data["target_type"], 
            message_data["target_user_ids"], 
            message_data["target_group"],
            message_data["ext"]
        )
        
        if not user_ids:
            logger.error(f"No target users found", extra={
                "message_id": str(message_id),
                "target_type": message_data["target_type"]
            })
            message.status = "failed"
            db.commit()
            return {"error": "No target users found"}
        
        # Create delivery records
        deliveries = crud.create_delivery_records(db, message_id, user_ids)
        
        logger.info(f"Sending to {len(user_ids)} users", extra={
            "message_id": str(message_id),
            "target_count": len(user_ids)
        })
    
    # Send messages with rate limiting
    try:
        stats = await _send_bulk(message_data, message_id, user_ids)
        
        # Update message status
        with get_db() as db:
            message = crud.get_system_message(db, message_id)
            if message:
                current_status = message.status
                if current_status == "cancelled":
                    logger.warning(f"Message cancelled during sending", extra={
                        "message_id": str(message_id),
                        "stats": stats
                    })
                    return {"error": "Message was cancelled during sending", **stats}
                
                # Mark as completed if all sent successfully
                if stats.get('failed', 0) == 0 and stats.get('pending', 0) == 0:
                    message.status = "completed"
                elif stats.get('failed', 0) > 0:
                    message.status = "failed"
                message.sent_at = datetime.utcnow()
                db.commit()
        
        logger.info(f"System message send completed", extra={
            "message_id": str(message_id),
            "stats": stats
        })
        return stats
    except Exception as e:
        logger.error(f"Error sending message", extra={
            "message_id": str(message_id),
            "error": str(e)
        }, exc_info=True)
        try:
            with get_db() as db:
                message = crud.get_system_message(db, message_id)
                if message:
                    message.status = "failed"
                    db.commit()
        except Exception as db_error:
            logger.error(f"Error updating status to failed", extra={
                "message_id": str(message_id),
                "error": str(db_error)
            })
        return {"error": str(e)}


async def _get_target_users(db, target_type: str, target_user_ids: List[int], target_group: Optional[str], ext: Optional[dict] = None) -> List[int]:
    """Resolve target user list based on target_type"""
    if target_type == "all":
        query = db.query(User)
        
        # Handle exclusion of specific acquisition source
        exclude_source = ext.get("exclude_acquisition_source") if ext else None
        if exclude_source:
            query = query.filter(
                (User.acquisition_source != exclude_source) | (User.acquisition_source.is_(None))
            )
        
        users = query.all()
        return [user.id for user in users]
    
    elif target_type == "user":
        if target_user_ids and len(target_user_ids) > 0:
            return [target_user_ids[0]]
        return []
    
    elif target_type == "users":
        return target_user_ids or []
    
    elif target_type == "group":
        if not target_group:
            return []
        users = crud.get_users_by_group(db, target_group)
        return [user.id for user in users]
    
    return []


def _build_keyboard(buttons: Optional[List[dict]]) -> Optional[InlineKeyboardMarkup]:
    """Convert button configs to aiogram InlineKeyboardMarkup"""
    if not buttons or (isinstance(buttons, list) and len(buttons) == 0):
        return None
    
    # Handle case where buttons might be stored as dict instead of list
    if isinstance(buttons, dict):
        buttons = [buttons]
    
    keyboard_buttons = []
    for btn in buttons:
        if not isinstance(btn, dict):
            continue
        if btn.get("url"):
            keyboard_buttons.append([InlineKeyboardButton(text=btn["text"], url=btn["url"])])
        elif btn.get("callback_data"):
            keyboard_buttons.append([InlineKeyboardButton(text=btn["text"], callback_data=btn["callback_data"])])
        elif btn.get("web_app"):
            web_app = btn["web_app"]
            if isinstance(web_app, dict) and web_app.get("url"):
                web_app_url = web_app["url"]
                # Convert relative URLs to absolute URLs using public_url
                if web_app_url.startswith("/"):
                    web_app_url = f"{settings.public_url}{web_app_url}"
                web_app_info = WebAppInfo(url=web_app_url)
                keyboard_buttons.append([InlineKeyboardButton(text=btn["text"], web_app=web_app_info)])
    
    if keyboard_buttons:
        return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    return None


async def _send_to_user(
    message_data: dict,
    user_id: int,
    delivery_id: UUID,
    parse_mode: str = "HTML"
) -> Tuple[bool, Optional[str], Optional[int]]:
    """
    Send message to single user
    
    Returns:
        (success, error_message, telegram_message_id)
    """
    keyboard = _build_keyboard(message_data.get("buttons"))
    parse_mode_value = parse_mode if parse_mode in ("HTML", "MarkdownV2") else "HTML"
    disable_web_page_preview = message_data.get("ext", {}).get("disable_web_page_preview", False)
    
    # Sanitize HTML for Telegram if using HTML parse mode
    message_text = message_data["text"]
    if parse_mode_value == "HTML" and message_text:
        message_text = _sanitize_html_for_telegram(message_text)
    
    try:
        # Handle media types
        if message_data.get("media_type") == "photo" and message_data.get("media_url"):
            sent_msg = await bot.send_photo(
                chat_id=user_id,
                photo=message_data["media_url"],
                caption=message_text,
                reply_markup=keyboard,
                parse_mode=parse_mode_value
                # Note: disable_web_page_preview is not valid for send_photo
            )
            return (True, None, sent_msg.message_id)
        
        elif message_data.get("media_type") == "video" and message_data.get("media_url"):
            sent_msg = await bot.send_video(
                chat_id=user_id,
                video=message_data["media_url"],
                caption=message_text,
                reply_markup=keyboard,
                parse_mode=parse_mode_value
                # Note: disable_web_page_preview is not valid for send_video
            )
            return (True, None, sent_msg.message_id)
        
        elif message_data.get("media_type") == "animation" and message_data.get("media_url"):
            sent_msg = await bot.send_animation(
                chat_id=user_id,
                animation=message_data["media_url"],
                caption=message_text,
                reply_markup=keyboard,
                parse_mode=parse_mode_value
                # Note: disable_web_page_preview is not valid for send_animation
            )
            return (True, None, sent_msg.message_id)
        
        else:
            # Text only - disable_web_page_preview is ONLY valid here
            sent_msg = await bot.send_message(
                chat_id=user_id,
                text=message_text,
                reply_markup=keyboard,
                parse_mode=parse_mode_value,
                disable_web_page_preview=disable_web_page_preview
            )
            return (True, None, sent_msg.message_id)
    
    except TelegramBadRequest as e:
        error_msg = str(e)
        logger.warning(f"Telegram bad request", extra={
            "user_id": user_id,
            "error": error_msg,
            "media_type": message_data.get("media_type")
        })
        if "chat not found" in error_msg.lower() or "blocked" in error_msg.lower():
            return (False, "blocked", None)
        return (False, error_msg, None)
    
    except TelegramAPIError as e:
        error_msg = str(e)
        logger.warning(f"Telegram API error", extra={
            "user_id": user_id,
            "error": error_msg,
            "media_type": message_data.get("media_type")
        })
        if "Too Many Requests" in error_msg or "429" in error_msg:
            return (False, "rate_limit", None)
        return (False, error_msg, None)
    
    except Exception as e:
        logger.error(f"Unexpected error sending message", extra={
            "user_id": user_id,
            "error": str(e),
            "error_type": type(e).__name__,
            "media_type": message_data.get("media_type")
        }, exc_info=True)
        return (False, str(e), None)


async def _send_bulk(message_data: dict, message_id: UUID, user_ids: List[int]) -> dict:
    """
    Send messages to multiple users with rate limiting
    
    Rate limit: 10 messages per minute to avoid spam and ensure delivery
    
    Optimized cancellation checking: checks once per batch instead of per message
    """
    stats = {
        "total": len(user_ids),
        "sent": 0,
        "failed": 0,
        "blocked": 0
    }
    
    parse_mode = message_data.get("ext", {}).get("parse_mode", "HTML")
    
    # Get delivery records and extract IDs before session closes
    delivery_map = {}  # user_id -> delivery_id
    with get_db() as db:
        deliveries = db.query(SystemMessageDelivery).filter(
            SystemMessageDelivery.system_message_id == message_id,
            SystemMessageDelivery.user_id.in_(user_ids)
        ).all()
        delivery_map = {d.user_id: d.id for d in deliveries}
    
    # Rate limiting: 10 messages per minute
    batch_size = 10
    batch_interval_seconds = 60  # Wait 60 seconds between batches
    
    logger.info(f"Starting bulk send", extra={
        "message_id": str(message_id),
        "total_recipients": len(user_ids),
        "batch_size": batch_size,
        "rate_limit": "10 per minute"
    })
    
    last_send_times = {}  # Track per-user send times for 1 msg/sec limit
    cancelled = False  # Track cancellation state to avoid repeated DB checks
    
    for i in range(0, len(user_ids), batch_size):
        batch = user_ids[i:i + batch_size]
        
        # OPTIMIZATION: Check cancellation once per batch, not per message
        if not cancelled:
            with get_db() as db:
                message = crud.get_system_message(db, message_id)
                if message and message.status == "cancelled":
                    cancelled = True
                    logger.warning(f"Batch send cancelled", extra={
                        "message_id": str(message_id),
                        "batch_num": i // batch_size + 1,
                        "remaining": len(user_ids) - i
                    })
        
        if cancelled:
            # Mark remaining deliveries as cancelled
            for user_id in user_ids[i:]:
                delivery_id = delivery_map.get(user_id)
                if delivery_id:
                    with get_db() as db:
                        delivery = crud.get_delivery_record(db, delivery_id)
                        if delivery:
                            delivery.status = "failed"
                            delivery.error = "Message cancelled"
                            db.commit()
                    stats["failed"] += 1
            break
        
        # Prepare batch tasks
        batch_tasks = []
        for user_id in batch:
            # Check if we need to wait for this user (1 msg/sec per chat)
            if user_id in last_send_times:
                elapsed = (datetime.utcnow() - last_send_times[user_id]).total_seconds()
                if elapsed < 1.0:
                    await asyncio.sleep(1.0 - elapsed)
            
            delivery_id = delivery_map.get(user_id)
            if not delivery_id:
                continue
            
            # Send message
            task = _send_to_user(message_data, user_id, delivery_id, parse_mode)
            batch_tasks.append((user_id, delivery_id, task))
            last_send_times[user_id] = datetime.utcnow()
        
        # Execute batch and update database
        for user_id, delivery_id, task in batch_tasks:
            success, error, msg_id = await task
            
            with get_db() as db:
                delivery = crud.get_delivery_record(db, delivery_id)
                if delivery:
                    if success:
                        delivery.status = "sent"
                        delivery.sent_at = datetime.utcnow()
                        delivery.message_id = msg_id
                        stats["sent"] += 1
                    else:
                        if error == "blocked":
                            delivery.status = "blocked"
                            stats["blocked"] += 1
                        else:
                            delivery.status = "failed"
                            delivery.error = error
                            stats["failed"] += 1
                    db.commit()
        
        # Log progress after each batch
        logger.info(f"Bulk send progress", extra={
            "message_id": str(message_id),
            "processed": min(i + batch_size, len(user_ids)),
            "total": len(user_ids),
            "sent": stats["sent"],
            "failed": stats["failed"],
            "blocked": stats["blocked"]
        })
        
        # Wait between batches to maintain 10 msgs/minute rate limit (except for last batch)
        if i + batch_size < len(user_ids):
            logger.info(f"Rate limit: waiting {batch_interval_seconds}s before next batch", extra={
                "message_id": str(message_id),
                "next_batch_in": batch_interval_seconds
            })
            await asyncio.sleep(batch_interval_seconds)
    
    logger.info(f"Bulk send completed", extra={
        "message_id": str(message_id),
        "stats": stats
    })
    return stats


async def retry_failed_deliveries(system_message_id: Optional[UUID] = None) -> dict:
    """
    Retry failed deliveries with exponential backoff
    
    Args:
        system_message_id: Optional message ID to retry, or None for all failed deliveries
        
    Returns:
        dict with retry statistics
    """
    logger.info(f"Starting retry of failed deliveries", extra={
        "system_message_id": str(system_message_id) if system_message_id else "all"
    })
    
    # Extract delivery data while session is open
    delivery_data = []
    with get_db() as db:
        failed_deliveries = crud.get_failed_deliveries(db, system_message_id)
        delivery_data = [
            (d.id, d.user_id, d.system_message_id, d.retry_count, d.max_retries)
            for d in failed_deliveries
        ]
    
    if not delivery_data:
        logger.info("No failed deliveries to retry")
        return {"retried": 0, "success": 0, "failed": 0}
    
    logger.info(f"Retrying {len(delivery_data)} failed deliveries")
    stats = {"retried": 0, "success": 0, "failed": 0}
    
    for delivery_id, user_id, system_message_id_val, retry_count, max_retries in delivery_data:
        # Calculate exponential backoff delay
        delay = 2 ** retry_count  # 1s, 2s, 4s
        await asyncio.sleep(delay)
        
        # Get message data using centralized helper
        message_data = None
        with get_db() as db:
            message = crud.get_system_message(db, system_message_id_val)
            if not message:
                logger.warning(f"Message not found for retry", extra={
                    "delivery_id": str(delivery_id),
                    "system_message_id": str(system_message_id_val)
                })
                continue
            
            # Use centralized extraction helper
            message_data = _extract_message_data(message)
        
        parse_mode = message_data.get("ext", {}).get("parse_mode", "HTML")
        
        # Retry send
        success, error, msg_id = await _send_to_user(message_data, user_id, delivery_id, parse_mode)
        
        # Update delivery
        with get_db() as db:
            delivery = crud.get_delivery_record(db, delivery_id)
            if delivery:
                stats["retried"] += 1
                if success:
                    delivery.status = "sent"
                    delivery.sent_at = datetime.utcnow()
                    delivery.message_id = msg_id
                    stats["success"] += 1
                    logger.debug(f"Retry successful", extra={
                        "delivery_id": str(delivery_id),
                        "user_id": user_id
                    })
                else:
                    delivery.retry_count += 1
                    delivery.error = error
                    if error == "blocked":
                        delivery.status = "blocked"
                    elif retry_count + 1 >= max_retries:
                        delivery.status = "failed"
                    stats["failed"] += 1
                    logger.warning(f"Retry failed", extra={
                        "delivery_id": str(delivery_id),
                        "user_id": user_id,
                        "error": error,
                        "retry_count": retry_count + 1
                    })
                db.commit()
    
    logger.info(f"Retry completed", extra={"stats": stats})
    return stats


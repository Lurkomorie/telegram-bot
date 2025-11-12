"""
Analytics API endpoints for viewing statistics and user event timelines
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import UUID
import asyncio
import logging
from app.db.base import get_db
from app.db import crud
from app.core.schemas import (
    SystemMessageCreate, SystemMessageUpdate, SystemMessageResponse,
    SystemMessageTemplateCreate, SystemMessageTemplateUpdate, SystemMessageTemplateResponse,
    DeliveryStatusResponse, DeliveryStatsResponse
)
from app.core import system_message_service

router = APIRouter(prefix="/api/analytics", tags=["analytics"])
logger = logging.getLogger(__name__)


def _create_monitored_task(coro, task_name: str, context: dict):
    """
    Create a background task with proper error handling and logging.
    
    This prevents silent failures in fire-and-forget tasks by:
    1. Wrapping in try/except with structured logging
    2. Tracking task completion/failure
    3. Ensuring errors are visible in production logs
    
    Args:
        coro: Coroutine to execute
        task_name: Human-readable task name for logging
        context: Dictionary with context for logging (e.g., message_id)
    """
    async def monitored_wrapper():
        try:
            logger.info(f"Starting background task: {task_name}", extra=context)
            result = await coro
            logger.info(f"Background task completed: {task_name}", extra={
                **context,
                "result": result
            })
            return result
        except Exception as e:
            logger.error(f"Background task failed: {task_name}", extra={
                **context,
                "error": str(e),
                "error_type": type(e).__name__
            }, exc_info=True)
            # Re-raise to ensure task shows as failed
            raise
    
    try:
        loop = asyncio.get_running_loop()
        task = loop.create_task(monitored_wrapper())
        # Add done callback to catch any unhandled exceptions
        task.add_done_callback(_log_task_result)
        return task
    except RuntimeError:
        # Fallback if no running loop
        return asyncio.create_task(monitored_wrapper())


def _log_task_result(task: asyncio.Task):
    """Log task completion or failure"""
    try:
        task.result()
    except asyncio.CancelledError:
        logger.warning("Background task was cancelled", extra={
            "task_name": task.get_name()
        })
    except Exception as e:
        logger.error("Background task raised exception", extra={
            "task_name": task.get_name(),
            "error": str(e)
        })


@router.get("/stats")
async def get_analytics_stats() -> Dict[str, Any]:
    """
    Get overall analytics statistics
    
    Returns:
        - total_users: Total unique users
        - total_events: Total events tracked
        - total_messages: Total messages (user + AI)
        - total_images: Total images generated
        - active_users_7d: Active users in last 7 days
        - avg_messages_per_user: Average messages per user
        - popular_personas: Top 10 personas by usage
    """
    try:
        with get_db() as db:
            stats = crud.get_analytics_stats(db)
            return stats
    except Exception as e:
        print(f"[ANALYTICS-API] Error fetching stats: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching statistics: {str(e)}")


@router.get("/users")
async def get_all_users() -> List[Dict[str, Any]]:
    """
    Get all users with their event counts
    
    Returns list of users with:
        - client_id: Telegram user ID
        - username: Telegram username (if available)
        - first_name: User's first name (if available)
        - total_events: Total events for this user
        - last_activity: Last activity timestamp
    """
    try:
        with get_db() as db:
            users = crud.get_all_users_from_analytics(db)
            return users
    except Exception as e:
        print(f"[ANALYTICS-API] Error fetching users: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching users: {str(e)}")


@router.get("/users/{client_id}/events")
async def get_user_events(client_id: int, limit: int = 1000) -> List[Dict[str, Any]]:
    """
    Get event timeline for a specific user
    
    Args:
        client_id: Telegram user ID
        limit: Maximum number of events to return (default 1000)
    
    Returns list of events with:
        - id: Event ID
        - event_name: Type of event
        - persona_id: Associated persona ID (if any)
        - persona_name: Persona name (if any)
        - message: Message content (for user/AI messages)
        - prompt: Image prompt (for image events)
        - negative_prompt: Negative prompt (for image events)
        - image_url: Cloudflare image URL (for image events)
        - meta: Additional metadata
        - created_at: Timestamp
    """
    try:
        with get_db() as db:
            events = crud.get_analytics_events_by_user(db, client_id, limit)
            
            # Convert to dict for JSON serialization
            events_data = []
            for event in events:
                events_data.append({
                    "id": str(event.id),
                    "event_name": event.event_name,
                    "persona_id": str(event.persona_id) if event.persona_id else None,
                    "persona_name": event.persona_name,
                    "message": event.message,
                    "prompt": event.prompt,
                    "negative_prompt": event.negative_prompt,
                    "image_url": event.image_url,
                    "meta": event.meta,
                    "created_at": event.created_at.isoformat()
                })
            
            return events_data
    except Exception as e:
        print(f"[ANALYTICS-API] Error fetching user events: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching user events: {str(e)}")


@router.get("/acquisition-sources")
async def get_acquisition_sources() -> List[Dict[str, Any]]:
    """
    Get acquisition source statistics
    
    Returns list of acquisition sources with:
        - source: Acquisition source name
        - user_count: Number of users from this source
        - total_events: Total events from users of this source
        - avg_events_per_user: Average events per user from this source
    """
    try:
        with get_db() as db:
            stats = crud.get_acquisition_source_stats(db)
            return stats
    except Exception as e:
        print(f"[ANALYTICS-API] Error fetching acquisition source stats: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching acquisition source stats: {str(e)}")


@router.get("/messages-over-time")
async def get_messages_over_time(interval: str = "1h") -> List[Dict[str, Any]]:
    """
    Get message counts over time bucketed by interval
    
    Args:
        interval: Time interval (1m, 5m, 15m, 30m, 1h, 6h, 12h, 1d)
    
    Returns:
        List of {timestamp, count} dictionaries
    """
    try:
        # Parse interval
        interval_map = {
            "1m": (1, 60),      # 1 min buckets, 60 min (1 hour) history
            "5m": (5, 180),     # 5 min buckets, 180 min (3 hours) history
            "15m": (15, 360),   # 15 min buckets, 360 min (6 hours) history
            "30m": (30, 720),   # 30 min buckets, 720 min (12 hours) history
            "1h": (60, 1440),   # 1 hour buckets, 1440 min (1 day) history
            "6h": (360, 10080), # 6 hour buckets, 10080 min (7 days) history
            "12h": (720, 20160),# 12 hour buckets, 20160 min (14 days) history
            "1d": (1440, 43200) # 1 day buckets, 43200 min (30 days) history
        }
        
        if interval not in interval_map:
            raise HTTPException(status_code=400, detail=f"Invalid interval. Must be one of: {', '.join(interval_map.keys())}")
        
        interval_minutes, limit_minutes = interval_map[interval]
        limit_hours = limit_minutes // 60
        
        with get_db() as db:
            data = crud.get_messages_over_time(db, interval_minutes, limit_hours)
            return data
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ANALYTICS-API] Error fetching messages over time: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching messages over time: {str(e)}")


@router.get("/scheduled-messages-over-time")
async def get_scheduled_messages_over_time(interval: str = "1h") -> List[Dict[str, Any]]:
    """
    Get auto-followup message counts over time bucketed by interval
    
    Args:
        interval: Time interval (1m, 5m, 15m, 30m, 1h, 6h, 12h, 1d)
    
    Returns:
        List of {timestamp, count} dictionaries
    """
    try:
        # Parse interval (same map as messages-over-time)
        interval_map = {
            "1m": (1, 60),
            "5m": (5, 180),
            "15m": (15, 360),
            "30m": (30, 720),
            "1h": (60, 1440),
            "6h": (360, 10080),
            "12h": (720, 20160),
            "1d": (1440, 43200)
        }
        
        if interval not in interval_map:
            raise HTTPException(status_code=400, detail=f"Invalid interval. Must be one of: {', '.join(interval_map.keys())}")
        
        interval_minutes, limit_minutes = interval_map[interval]
        limit_hours = limit_minutes // 60
        
        with get_db() as db:
            data = crud.get_scheduled_messages_over_time(db, interval_minutes, limit_hours)
            return data
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ANALYTICS-API] Error fetching scheduled messages over time: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching scheduled messages over time: {str(e)}")


@router.get("/user-messages-over-time")
async def get_user_messages_over_time(interval: str = "1h") -> List[Dict[str, Any]]:
    """
    Get user-sent message counts over time bucketed by interval
    
    Args:
        interval: Time interval (1m, 5m, 15m, 30m, 1h, 6h, 12h, 1d)
    
    Returns:
        List of {timestamp, count} dictionaries
    """
    try:
        # Parse interval (same map as messages-over-time)
        interval_map = {
            "1m": (1, 60),
            "5m": (5, 180),
            "15m": (15, 360),
            "30m": (30, 720),
            "1h": (60, 1440),
            "6h": (360, 10080),
            "12h": (720, 20160),
            "1d": (1440, 43200)
        }
        
        if interval not in interval_map:
            raise HTTPException(status_code=400, detail=f"Invalid interval. Must be one of: {', '.join(interval_map.keys())}")
        
        interval_minutes, limit_minutes = interval_map[interval]
        limit_hours = limit_minutes // 60
        
        with get_db() as db:
            data = crud.get_user_messages_over_time(db, interval_minutes, limit_hours)
            return data
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ANALYTICS-API] Error fetching user messages over time: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching user messages over time: {str(e)}")


@router.get("/active-users-over-time")
async def get_active_users_over_time(period: str = "7d") -> List[Dict[str, Any]]:
    """
    Get daily unique active user counts
    
    Args:
        period: Time period (7d, 30d, 90d)
    
    Returns:
        List of {date, count} dictionaries
    """
    try:
        period_map = {
            "7d": 7,
            "30d": 30,
            "90d": 90
        }
        
        if period not in period_map:
            raise HTTPException(status_code=400, detail=f"Invalid period. Must be one of: {', '.join(period_map.keys())}")
        
        days = period_map[period]
        
        with get_db() as db:
            data = crud.get_active_users_over_time(db, days)
            return data
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ANALYTICS-API] Error fetching active users over time: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching active users over time: {str(e)}")


@router.get("/messages-by-persona")
async def get_messages_by_persona() -> List[Dict[str, Any]]:
    """
    Get message count distribution by persona
    
    Returns:
        List of {persona_name, count} dictionaries
    """
    try:
        with get_db() as db:
            data = crud.get_messages_by_persona(db)
            return data
    except Exception as e:
        print(f"[ANALYTICS-API] Error fetching messages by persona: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching messages by persona: {str(e)}")


@router.get("/images-over-time")
async def get_images_over_time(period: str = "7d") -> List[Dict[str, Any]]:
    """
    Get daily image generation counts
    
    Args:
        period: Time period (7d, 30d, 90d)
    
    Returns:
        List of {date, count} dictionaries
    """
    try:
        period_map = {
            "7d": 7,
            "30d": 30,
            "90d": 90
        }
        
        if period not in period_map:
            raise HTTPException(status_code=400, detail=f"Invalid period. Must be one of: {', '.join(period_map.keys())}")
        
        days = period_map[period]
        
        with get_db() as db:
            data = crud.get_images_over_time(db, days)
            return data
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ANALYTICS-API] Error fetching images over time: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching images over time: {str(e)}")


@router.get("/image-waiting-time")
async def get_image_waiting_time(interval: str = "1h") -> List[Dict[str, Any]]:
    """
    Get average image generation waiting time over time with premium/free breakdown
    
    Args:
        interval: Time interval (1m, 5m, 15m, 30m, 1h, 6h, 12h, 1d)
    
    Returns:
        List of {timestamp, avg_waiting_time, avg_premium, avg_free} dictionaries
        All times in seconds
    """
    try:
        # Parse interval (same map as messages-over-time)
        interval_map = {
            "1m": (1, 60),
            "5m": (5, 180),
            "15m": (15, 360),
            "30m": (30, 720),
            "1h": (60, 1440),
            "6h": (360, 10080),
            "12h": (720, 20160),
            "1d": (1440, 43200)
        }
        
        if interval not in interval_map:
            raise HTTPException(status_code=400, detail=f"Invalid interval. Must be one of: {', '.join(interval_map.keys())}")
        
        interval_minutes, limit_minutes = interval_map[interval]
        limit_hours = limit_minutes // 60
        
        with get_db() as db:
            data = crud.get_image_waiting_time_over_time(db, interval_minutes, limit_hours)
            return data
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ANALYTICS-API] Error fetching image waiting time: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching image waiting time: {str(e)}")


@router.get("/engagement-heatmap")
async def get_engagement_heatmap() -> List[Dict[str, Any]]:
    """
    Get message counts by hour of day and day of week
    
    Returns:
        List of {hour, day_of_week, count} dictionaries
        hour: 0-23
        day_of_week: 0-6 (0=Sunday in PostgreSQL, 6=Saturday)
    """
    try:
        with get_db() as db:
            data = crud.get_engagement_heatmap(db)
            return data
    except Exception as e:
        print(f"[ANALYTICS-API] Error fetching engagement heatmap: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching engagement heatmap: {str(e)}")


@router.get("/images")
async def get_images(page: int = 1, per_page: int = 100) -> Dict[str, Any]:
    """
    Get all generated images with pagination
    
    Args:
        page: Page number (1-indexed, default: 1)
        per_page: Number of items per page (default: 100, max: 500)
    
    Returns:
        Dictionary with:
        - images: List of image records with user, persona, and source info
        - total: Total number of images
        - page: Current page number
        - per_page: Items per page
        - total_pages: Total number of pages
    """
    try:
        # Validate and cap per_page
        if per_page < 1:
            per_page = 100
        if per_page > 500:
            per_page = 500
        
        if page < 1:
            page = 1
        
        with get_db() as db:
            data = crud.get_all_images_paginated(db, page, per_page)
            return data
    except Exception as e:
        print(f"[ANALYTICS-API] Error fetching images: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching images: {str(e)}")


# ========== SYSTEM MESSAGES ENDPOINTS ==========

@router.post("/system-messages", response_model=SystemMessageResponse)
async def create_system_message(data: SystemMessageCreate, background_tasks: BackgroundTasks):
    """Create a new system message"""
    try:
        # Convert buttons list to list of dicts for storage
        buttons_list = []
        if data.buttons:
            buttons_list = [btn.model_dump() for btn in data.buttons]
        
        # Store parse_mode and disable_web_page_preview in ext
        ext = {
            "parse_mode": data.parse_mode,
            "disable_web_page_preview": data.disable_web_page_preview
        }
        
        with get_db() as db:
            message = crud.create_system_message(
                db,
                title=data.title,
                text=data.text,
                media_type=data.media_type,
                media_url=data.media_url,
                buttons=buttons_list,
                target_type=data.target_type,
                target_user_ids=data.target_user_ids,
                target_group=data.target_group,
                send_immediately=data.send_immediately,
                scheduled_at=data.scheduled_at,
                ext=ext,
                template_id=data.template_id
            )
            
            # Extract message_id before session closes
            message_id = message.id
            message_response = SystemMessageResponse.model_validate(message)
        
        # If send_immediately, trigger send in background
        if data.send_immediately:
            _create_monitored_task(
                system_message_service.send_system_message(message_id),
                task_name="send_system_message",
                context={"message_id": str(message_id), "trigger": "create_immediate"}
            )
        
        return message_response
    except Exception as e:
        print(f"[ANALYTICS-API] Error creating system message: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating system message: {str(e)}")


@router.get("/system-messages", response_model=Dict[str, Any])
async def list_system_messages(
    page: int = 1,
    per_page: int = 50,
    status: Optional[str] = None,
    target_type: Optional[str] = None
):
    """List system messages with pagination and filters"""
    try:
        if page < 1:
            page = 1
        if per_page < 1 or per_page > 100:
            per_page = 50
        
        with get_db() as db:
            result = crud.list_system_messages(
                db,
                page=page,
                per_page=per_page,
                status=status,
                target_type=target_type
            )
            
            return {
                "messages": [SystemMessageResponse.model_validate(msg).model_dump() for msg in result["messages"]],
                "total": result["total"],
                "page": result["page"],
                "per_page": result["per_page"],
                "total_pages": result["total_pages"]
            }
    except Exception as e:
        print(f"[ANALYTICS-API] Error listing system messages: {e}")
        raise HTTPException(status_code=500, detail=f"Error listing system messages: {str(e)}")


@router.get("/system-messages/{message_id}", response_model=SystemMessageResponse)
async def get_system_message(message_id: UUID):
    """Get specific system message details"""
    try:
        with get_db() as db:
            message = crud.get_system_message(db, message_id)
            if not message:
                raise HTTPException(status_code=404, detail="System message not found")
            return SystemMessageResponse.model_validate(message)
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ANALYTICS-API] Error fetching system message: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching system message: {str(e)}")


@router.put("/system-messages/{message_id}", response_model=SystemMessageResponse)
async def update_system_message(message_id: UUID, data: SystemMessageUpdate):
    """Update system message (only if status is 'draft' or 'scheduled')"""
    try:
        buttons_list = []
        if data.buttons:
            buttons_list = [btn.model_dump() for btn in data.buttons]
        
        ext = {}
        if data.parse_mode:
            ext["parse_mode"] = data.parse_mode
        if data.disable_web_page_preview is not None:
            ext["disable_web_page_preview"] = data.disable_web_page_preview
        
        with get_db() as db:
            message = crud.update_system_message(
                db,
                message_id,
                title=data.title,
                text=data.text,
                media_type=data.media_type,
                media_url=data.media_url,
                buttons=buttons_list,
                target_type=data.target_type,
                target_user_ids=data.target_user_ids,
                target_group=data.target_group,
                send_immediately=data.send_immediately,
                scheduled_at=data.scheduled_at,
                ext=ext if ext else None
            )
            
            if not message:
                raise HTTPException(status_code=404, detail="System message not found")
            
            return SystemMessageResponse.model_validate(message)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ANALYTICS-API] Error updating system message: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating system message: {str(e)}")


@router.delete("/system-messages/{message_id}")
async def delete_system_message(message_id: UUID):
    """Delete system message (only if status is 'draft', 'scheduled', or 'cancelled')"""
    try:
        with get_db() as db:
            success = crud.delete_system_message(db, message_id)
            if not success:
                raise HTTPException(status_code=404, detail="System message not found")
            return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ANALYTICS-API] Error deleting system message: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting system message: {str(e)}")


@router.post("/system-messages/{message_id}/send", response_model=Dict[str, Any])
async def send_system_message_now(message_id: UUID, background_tasks: BackgroundTasks):
    """Send system message immediately"""
    try:
        with get_db() as db:
            message = crud.get_system_message(db, message_id)
            if not message:
                raise HTTPException(status_code=404, detail="System message not found")
            # message_id is already a UUID parameter, no need to extract
        
        # Trigger send in background with monitoring
        _create_monitored_task(
            system_message_service.send_system_message(message_id),
            task_name="send_system_message",
            context={"message_id": str(message_id), "trigger": "manual_send"}
        )
        return {"success": True, "message": "Message sending started"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ANALYTICS-API] Error sending system message: {e}")
        raise HTTPException(status_code=500, detail=f"Error sending system message: {str(e)}")


@router.post("/system-messages/{message_id}/cancel")
async def cancel_system_message(message_id: UUID):
    """Cancel scheduled or sending system message"""
    try:
        with get_db() as db:
            message = crud.get_system_message(db, message_id)
            if not message:
                raise HTTPException(status_code=404, detail="System message not found")
            
            if message.status not in ("scheduled", "sending"):
                raise HTTPException(status_code=400, detail=f"Cannot cancel message with status '{message.status}'")
            
            message.status = "cancelled"
            db.commit()
            return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ANALYTICS-API] Error cancelling system message: {e}")
        raise HTTPException(status_code=500, detail=f"Error cancelling system message: {str(e)}")


@router.get("/system-messages/{message_id}/deliveries", response_model=Dict[str, Any])
async def get_system_message_deliveries(
    message_id: UUID,
    page: int = 1,
    per_page: int = 100,
    status: Optional[str] = None
):
    """Get delivery status for a system message"""
    try:
        if page < 1:
            page = 1
        if per_page < 1 or per_page > 500:
            per_page = 100
        
        with get_db() as db:
            result = crud.get_deliveries_by_message(db, message_id, page, per_page, status)
            return {
                "deliveries": [DeliveryStatusResponse.model_validate(d).model_dump() for d in result["deliveries"]],
                "total": result["total"],
                "page": result["page"],
                "per_page": result["per_page"],
                "total_pages": result["total_pages"]
            }
    except Exception as e:
        print(f"[ANALYTICS-API] Error fetching deliveries: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching deliveries: {str(e)}")


@router.get("/system-messages/{message_id}/stats", response_model=DeliveryStatsResponse)
async def get_system_message_stats(message_id: UUID):
    """Get delivery statistics for a system message"""
    try:
        with get_db() as db:
            stats = crud.get_delivery_stats(db, message_id)
            return DeliveryStatsResponse(**stats)
    except Exception as e:
        print(f"[ANALYTICS-API] Error fetching stats: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching stats: {str(e)}")


@router.post("/system-messages/{message_id}/retry-failed", response_model=Dict[str, Any])
async def retry_failed_deliveries(message_id: UUID, background_tasks: BackgroundTasks):
    """Manually retry failed deliveries for a system message"""
    try:
        with get_db() as db:
            message = crud.get_system_message(db, message_id)
            if not message:
                raise HTTPException(status_code=404, detail="System message not found")
            # message_id is already a UUID parameter, no need to extract
        
        # Trigger retry in background with monitoring
        _create_monitored_task(
            system_message_service.retry_failed_deliveries(message_id),
            task_name="retry_failed_deliveries",
            context={"message_id": str(message_id), "trigger": "manual_retry"}
        )
        return {"success": True, "message": "Retry started"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ANALYTICS-API] Error retrying deliveries: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrying deliveries: {str(e)}")


# ========== SYSTEM MESSAGE TEMPLATE ENDPOINTS ==========

@router.post("/system-message-templates", response_model=SystemMessageTemplateResponse)
async def create_template(data: SystemMessageTemplateCreate):
    """Create a new system message template"""
    try:
        buttons_list = []
        if data.buttons:
            buttons_list = [btn.model_dump() for btn in data.buttons]
        
        with get_db() as db:
            template = crud.create_template(
                db,
                name=data.name,
                title=data.title,
                text=data.text,
                media_type=data.media_type,
                media_url=data.media_url,
                buttons=buttons_list
            )
            return SystemMessageTemplateResponse.model_validate(template)
    except Exception as e:
        print(f"[ANALYTICS-API] Error creating template: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating template: {str(e)}")


@router.get("/system-message-templates", response_model=Dict[str, Any])
async def list_templates(page: int = 1, per_page: int = 50, is_active: Optional[bool] = None):
    """List templates with pagination"""
    try:
        if page < 1:
            page = 1
        if per_page < 1 or per_page > 100:
            per_page = 50
        
        with get_db() as db:
            result = crud.list_templates(db, page, per_page, is_active)
            return {
                "templates": [SystemMessageTemplateResponse.model_validate(t).model_dump() for t in result["templates"]],
                "total": result["total"],
                "page": result["page"],
                "per_page": result["per_page"],
                "total_pages": result["total_pages"]
            }
    except Exception as e:
        print(f"[ANALYTICS-API] Error listing templates: {e}")
        raise HTTPException(status_code=500, detail=f"Error listing templates: {str(e)}")


@router.get("/system-message-templates/{template_id}", response_model=SystemMessageTemplateResponse)
async def get_template(template_id: UUID):
    """Get template details"""
    try:
        with get_db() as db:
            template = crud.get_template(db, template_id)
            if not template:
                raise HTTPException(status_code=404, detail="Template not found")
            return SystemMessageTemplateResponse.model_validate(template)
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ANALYTICS-API] Error fetching template: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching template: {str(e)}")


@router.put("/system-message-templates/{template_id}", response_model=SystemMessageTemplateResponse)
async def update_template(template_id: UUID, data: SystemMessageTemplateUpdate):
    """Update template"""
    try:
        buttons_list = []
        if data.buttons:
            buttons_list = [btn.model_dump() for btn in data.buttons]
        
        with get_db() as db:
            template = crud.update_template(
                db,
                template_id,
                name=data.name,
                title=data.title,
                text=data.text,
                media_type=data.media_type,
                media_url=data.media_url,
                buttons=buttons_list,
                is_active=data.is_active
            )
            
            if not template:
                raise HTTPException(status_code=404, detail="Template not found")
            
            return SystemMessageTemplateResponse.model_validate(template)
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ANALYTICS-API] Error updating template: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating template: {str(e)}")


@router.delete("/system-message-templates/{template_id}")
async def delete_template(template_id: UUID):
    """Delete template"""
    try:
        with get_db() as db:
            success = crud.delete_template(db, template_id)
            if not success:
                raise HTTPException(status_code=404, detail="Template not found")
            return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ANALYTICS-API] Error deleting template: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting template: {str(e)}")


@router.post("/system-message-templates/{template_id}/create-message", response_model=SystemMessageResponse)
async def create_message_from_template(
    template_id: UUID,
    data: SystemMessageCreate,
    background_tasks: BackgroundTasks
):
    """Create message from template"""
    try:
        with get_db() as db:
            template = crud.get_template(db, template_id)
            if not template:
                raise HTTPException(status_code=404, detail="Template not found")
            
            # Use template data, but allow override from data
            buttons_list = []
            if data.buttons:
                buttons_list = [btn.model_dump() for btn in data.buttons]
            elif template.buttons:
                buttons_list = template.buttons
            
            ext = {
                "parse_mode": data.parse_mode,
                "disable_web_page_preview": data.disable_web_page_preview
            }
            
            message = crud.create_system_message(
                db,
                title=data.title or template.title,
                text=data.text or template.text,
                media_type=data.media_type if data.media_type != "none" else template.media_type,
                media_url=data.media_url or template.media_url,
                buttons=buttons_list,
                target_type=data.target_type,
                target_user_ids=data.target_user_ids,
                target_group=data.target_group,
                send_immediately=data.send_immediately,
                scheduled_at=data.scheduled_at,
                ext=ext,
                template_id=template_id
            )
            
            # Extract message_id before session closes
            message_id = message.id
            message_response = SystemMessageResponse.model_validate(message)
        
        if data.send_immediately:
            _create_monitored_task(
                system_message_service.send_system_message(message_id),
                task_name="send_system_message",
                context={"message_id": str(message_id), "trigger": "template_immediate", "template_id": str(template_id)}
            )
        
        return message_response
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ANALYTICS-API] Error creating message from template: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating message from template: {str(e)}")


# ========== HELPER ENDPOINTS ==========

@router.get("/user-groups")
async def get_user_groups():
    """List available user groups"""
    return {
        "groups": [
            {"name": "premium", "description": "Premium users with active subscription"},
            {"name": "inactive_7d", "description": "Users inactive for 7 days"},
            {"name": "inactive_30d", "description": "Users inactive for 30 days"},
            {"name": "acquisition_source:*", "description": "Users from specific acquisition source (e.g., acquisition_source:facebook)"}
        ]
    }


@router.get("/users/search")
async def search_users(query: str, limit: int = 20):
    """Search users by username or ID"""
    try:
        if limit < 1 or limit > 100:
            limit = 20
        
        with get_db() as db:
            # Try to parse as integer (user ID)
            try:
                user_id = int(query)
                user = crud.get_user(db, user_id)
                if user:
                    return [{
                        "id": user.id,
                        "username": user.username,
                        "first_name": user.first_name
                    }]
            except ValueError:
                pass
            
            # Search by username
            from app.db.models import User
            from sqlalchemy import or_
            users = db.query(User).filter(
                or_(
                    User.username.ilike(f"%{query}%"),
                    User.first_name.ilike(f"%{query}%")
                )
            ).limit(limit).all()
            
            return [{
                "id": user.id,
                "username": user.username,
                "first_name": user.first_name
            } for user in users]
    except Exception as e:
        print(f"[ANALYTICS-API] Error searching users: {e}")
        raise HTTPException(status_code=500, detail=f"Error searching users: {str(e)}")





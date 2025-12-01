"""
Analytics API endpoints for viewing statistics and user event timelines
"""
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, validator
from datetime import datetime, date
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
async def get_analytics_stats(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    acquisition_source: Optional[str] = Query(None, description="Acquisition source filter")
) -> Dict[str, Any]:
    """
    Get overall analytics statistics
    
    Args:
        start_date: Filter events from this date onwards (YYYY-MM-DD)
        end_date: Filter events up to this date (YYYY-MM-DD)
    
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
            stats = crud.get_analytics_stats(db, start_date=start_date, end_date=end_date, acquisition_source=acquisition_source)
            return stats
    except Exception as e:
        print(f"[ANALYTICS-API] Error fetching stats: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error fetching statistics: {str(e)}")


@router.get("/users")
async def get_all_users(limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    """
    Get all users with their event counts (paginated for performance)
    
    Args:
        limit: Number of users to return per page (default 100, max 500)
        offset: Number of users to skip (default 0)
    
    Returns:
        Dictionary with:
        - users: List of user objects with analytics data
        - total: Total number of users
        - limit: Items per page
        - offset: Current offset
        
    Each user object contains:
        - client_id: Telegram user ID
        - username: Telegram username (if available)
        - first_name: User's first name (if available)
        - total_events: Total events for this user
        - last_activity: Last activity timestamp
        - sparkline_data: 14-day activity chart data
        - consecutive_days_streak: Current active streak
        - message_events_count: Number of user messages
        - last_message_send: Last user message timestamp
    """
    try:
        # Validate and cap limit
        if limit < 1:
            limit = 100
        if limit > 500:
            limit = 500
        
        if offset < 0:
            offset = 0
        
        with get_db() as db:
            result = crud.get_all_users_from_analytics(db, limit=limit, offset=offset)
            return result
    except Exception as e:
        print(f"[ANALYTICS-API] Error fetching users: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error fetching users: {str(e)}")


@router.get("/users/{client_id}/events")
async def get_user_events(client_id: int, limit: int = 10000) -> List[Dict[str, Any]]:
    """
    Get event timeline for a specific user
    
    Args:
        client_id: Telegram user ID
        limit: Maximum number of events to return (default 10000)
    
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
async def get_acquisition_sources(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
) -> List[Dict[str, Any]]:
    """
    Get acquisition source statistics
    
    Args:
        start_date: Filter events from this date onwards (YYYY-MM-DD)
        end_date: Filter events up to this date (YYYY-MM-DD)
    
    Returns list of acquisition sources with:
        - source: Acquisition source name
        - user_count: Number of users from this source
        - total_events: Total events from users of this source
        - avg_events_per_user: Average events per user from this source
    """
    try:
        with get_db() as db:
            stats = crud.get_acquisition_source_stats(db, start_date=start_date, end_date=end_date)
            return stats
    except Exception as e:
        print(f"[ANALYTICS-API] Error fetching acquisition source stats: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching acquisition source stats: {str(e)}")


@router.get("/messages-over-time")
async def get_messages_over_time(
    interval: str = "1h",
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    acquisition_source: Optional[str] = Query(None, description="Acquisition source filter")
) -> List[Dict[str, Any]]:
    """
    Get message counts over time bucketed by interval
    
    Args:
        interval: Time interval (1m, 5m, 15m, 30m, 1h, 6h, 12h, 1d)
        start_date: Filter from this date onwards (YYYY-MM-DD)
        end_date: Filter up to this date (YYYY-MM-DD)
    
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
            data = crud.get_messages_over_time(db, interval_minutes, limit_hours, start_date=start_date, end_date=end_date, acquisition_source=acquisition_source)
            return data
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ANALYTICS-API] Error fetching messages over time: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching messages over time: {str(e)}")


@router.get("/scheduled-messages-over-time")
async def get_scheduled_messages_over_time(
    interval: str = "1h",
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    acquisition_source: Optional[str] = Query(None, description="Acquisition source filter")
) -> List[Dict[str, Any]]:
    """
    Get auto-followup message counts over time bucketed by interval
    
    Args:
        interval: Time interval (1m, 5m, 15m, 30m, 1h, 6h, 12h, 1d)
        start_date: Filter from this date onwards (YYYY-MM-DD)
        end_date: Filter up to this date (YYYY-MM-DD)
    
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
            data = crud.get_scheduled_messages_over_time(db, interval_minutes, limit_hours, start_date=start_date, end_date=end_date, acquisition_source=acquisition_source)
            return data
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ANALYTICS-API] Error fetching scheduled messages over time: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching scheduled messages over time: {str(e)}")


@router.get("/user-messages-over-time")
async def get_user_messages_over_time(
    interval: str = "1h",
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    acquisition_source: Optional[str] = Query(None, description="Acquisition source filter")
) -> List[Dict[str, Any]]:
    """
    Get user-sent message counts over time bucketed by interval
    
    Args:
        interval: Time interval (1m, 5m, 15m, 30m, 1h, 6h, 12h, 1d)
        start_date: Filter from this date onwards (YYYY-MM-DD)
        end_date: Filter up to this date (YYYY-MM-DD)
    
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
            data = crud.get_user_messages_over_time(db, interval_minutes, limit_hours, start_date=start_date, end_date=end_date, acquisition_source=acquisition_source)
            return data
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ANALYTICS-API] Error fetching user messages over time: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching user messages over time: {str(e)}")


@router.get("/active-users-over-time")
async def get_active_users_over_time(
    period: str = "7d",
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    acquisition_source: Optional[str] = Query(None, description="Acquisition source filter")
) -> List[Dict[str, Any]]:
    """
    Get daily unique active user counts
    
    Args:
        period: Time period (7d, 30d, 90d)
        start_date: Filter from this date onwards (YYYY-MM-DD)
        end_date: Filter up to this date (YYYY-MM-DD)
    
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
            data = crud.get_active_users_over_time(db, days, start_date=start_date, end_date=end_date, acquisition_source=acquisition_source)
            return data
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ANALYTICS-API] Error fetching active users over time: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching active users over time: {str(e)}")


@router.get("/messages-by-persona")
async def get_messages_by_persona(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    acquisition_source: Optional[str] = Query(None, description="Acquisition source filter")
) -> List[Dict[str, Any]]:
    """
    Get message count distribution by persona
    
    Args:
        start_date: Filter from this date onwards (YYYY-MM-DD)
        end_date: Filter up to this date (YYYY-MM-DD)
    
    Returns:
        List of {persona_name, count} dictionaries
    """
    try:
        with get_db() as db:
            data = crud.get_messages_by_persona(db, start_date=start_date, end_date=end_date, acquisition_source=acquisition_source)
            return data
    except Exception as e:
        print(f"[ANALYTICS-API] Error fetching messages by persona: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching messages by persona: {str(e)}")


@router.get("/images-over-time")
async def get_images_over_time(
    period: str = "7d",
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    acquisition_source: Optional[str] = Query(None, description="Acquisition source filter")
) -> List[Dict[str, Any]]:
    """
    Get daily image generation counts
    
    Args:
        period: Time period (7d, 30d, 90d)
        start_date: Filter from this date onwards (YYYY-MM-DD)
        end_date: Filter up to this date (YYYY-MM-DD)
    
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
            data = crud.get_images_over_time(db, days, start_date=start_date, end_date=end_date, acquisition_source=acquisition_source)
            return data
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ANALYTICS-API] Error fetching images over time: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching images over time: {str(e)}")


@router.get("/image-waiting-time")
async def get_image_waiting_time(
    interval: str = "1h",
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    acquisition_source: Optional[str] = Query(None, description="Acquisition source filter")
) -> List[Dict[str, Any]]:
    """
    Get average image generation waiting time over time with premium/free breakdown
    
    Args:
        interval: Time interval (1m, 5m, 15m, 30m, 1h, 6h, 12h, 1d)
        start_date: Filter from this date onwards (YYYY-MM-DD)
        end_date: Filter up to this date (YYYY-MM-DD)
    
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
            data = crud.get_image_waiting_time_over_time(db, interval_minutes, limit_hours, start_date=start_date, end_date=end_date, acquisition_source=acquisition_source)
            return data
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ANALYTICS-API] Error fetching image waiting time: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching image waiting time: {str(e)}")


@router.get("/engagement-heatmap")
async def get_engagement_heatmap(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    acquisition_source: Optional[str] = Query(None, description="Acquisition source filter")
) -> List[Dict[str, Any]]:
    """
    Get message counts by hour of day and day of week
    
    Args:
        start_date: Filter from this date onwards (YYYY-MM-DD)
        end_date: Filter up to this date (YYYY-MM-DD)
    
    Returns:
        List of {hour, day_of_week, count} dictionaries
        hour: 0-23
        day_of_week: 0-6 (0=Sunday in PostgreSQL, 6=Saturday)
    """
    try:
        with get_db() as db:
            data = crud.get_engagement_heatmap(db, start_date=start_date, end_date=end_date, acquisition_source=acquisition_source)
            return data
    except Exception as e:
        print(f"[ANALYTICS-API] Error fetching engagement heatmap: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching engagement heatmap: {str(e)}")


@router.get("/daily-user-stats")
async def get_daily_user_stats_endpoint(
    date_str: str = Query(..., alias="date", description="Date (YYYY-MM-DD)")
) -> List[Dict[str, Any]]:
    """
    Get daily stats per user (messages, scheduled messages, cost)
    
    Args:
        date: Date to fetch stats for (YYYY-MM-DD)
        
    Returns:
        List of user objects with:
        - user_id: Telegram user ID
        - username: Username (if available)
        - first_name: First name (if available)
        - is_premium: Premium status
        - user_messages: Number of messages sent by user
        - scheduled_messages: Number of scheduled messages received
        - estimated_cost: Estimated LLM cost in USD
    """
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        with get_db() as db:
            stats = crud.get_daily_user_stats(db, target_date)
            return stats
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    except Exception as e:
        print(f"[ANALYTICS-API] Error fetching daily user stats: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching daily user stats: {str(e)}")


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


# ========== START CODES ENDPOINTS ==========

class CreateStartCodeRequest(BaseModel):
    code: str = Field(..., min_length=5, max_length=5)
    description: Optional[str] = None
    persona_id: Optional[str] = None
    history_id: Optional[str] = None
    is_active: bool = True
    
    @validator('code')
    def validate_code(cls, v):
        if not v.isalnum():
            raise ValueError('Code must be alphanumeric')
        return v.upper()


class UpdateStartCodeRequest(BaseModel):
    description: Optional[str] = None
    persona_id: Optional[str] = None
    history_id: Optional[str] = None
    is_active: Optional[bool] = None


@router.get("/start-codes")
async def get_start_codes() -> List[Dict[str, Any]]:
    """
    Get all start codes with their configuration
    
    Returns:
        List of start codes with code, description, persona info, history info, is_active, and usage stats
    """
    try:
        with get_db() as db:
            from sqlalchemy import func
            
            start_codes = crud.get_all_start_codes(db)
            
            # Get user counts for all codes in a single query
            user_counts_query = db.query(
                crud.User.acquisition_source,
                func.count(crud.User.id).label('count')
            ).filter(
                crud.User.acquisition_source.in_([sc.code for sc in start_codes])
            ).group_by(crud.User.acquisition_source).all()
            
            # Build lookup dict
            user_counts = {row.acquisition_source: row.count for row in user_counts_query}
            
            result = []
            for sc in start_codes:
                code_data = {
                    "code": sc.code,
                    "description": sc.description,
                    "persona_id": str(sc.persona_id) if sc.persona_id else None,
                    "persona_name": sc.persona.name if sc.persona else None,
                    "history_id": str(sc.history_id) if sc.history_id else None,
                    "history_name": sc.history.name if sc.history else None,
                    "is_active": sc.is_active,
                    "user_count": user_counts.get(sc.code, 0),
                    "created_at": sc.created_at.isoformat(),
                    "updated_at": sc.updated_at.isoformat() if sc.updated_at else None
                }
                result.append(code_data)
            
            return result
    except Exception as e:
        print(f"[ANALYTICS-API] Error fetching start codes: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching start codes: {str(e)}")


@router.post("/start-codes")
async def create_start_code(request: CreateStartCodeRequest) -> Dict[str, Any]:
    """
    Create a new start code
    
    Args:
        request: Start code creation data
    
    Returns:
        Created start code data
    """
    try:
        with get_db() as db:
            # Check if code already exists
            existing = crud.get_start_code(db, request.code)
            if existing:
                raise HTTPException(status_code=400, detail=f"Start code '{request.code}' already exists")
            
            # Validate persona and history if provided
            if request.persona_id:
                from app.core.persona_cache import get_persona_by_id
                persona = get_persona_by_id(request.persona_id)
                if not persona:
                    raise HTTPException(status_code=404, detail=f"Persona not found: {request.persona_id}")
            
            if request.history_id:
                from app.core.persona_cache import get_persona_histories
                # Need to verify history exists and belongs to persona
                if not request.persona_id:
                    raise HTTPException(status_code=400, detail="persona_id required when history_id is provided")
                
                histories = get_persona_histories(request.persona_id)
                history_found = any(h["id"] == request.history_id for h in histories)
                if not history_found:
                    raise HTTPException(status_code=404, detail=f"History not found or doesn't belong to persona")
            
            # Create start code
            start_code = crud.create_start_code(
                db,
                code=request.code,
                description=request.description,
                persona_id=request.persona_id,
                history_id=request.history_id,
                is_active=request.is_active
            )
            
            # Reload cache to include new code
            from app.core.start_code_cache import reload_cache
            reload_cache()
            
            return {
                "code": start_code.code,
                "description": start_code.description,
                "persona_id": str(start_code.persona_id) if start_code.persona_id else None,
                "history_id": str(start_code.history_id) if start_code.history_id else None,
                "is_active": start_code.is_active,
                "created_at": start_code.created_at.isoformat()
            }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ANALYTICS-API] Error creating start code: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating start code: {str(e)}")


@router.put("/start-codes/{code}")
async def update_start_code(code: str, request: UpdateStartCodeRequest) -> Dict[str, Any]:
    """
    Update a start code
    
    Args:
        code: 5-character alphanumeric code
        request: Update data
    
    Returns:
        Updated start code data
    """
    try:
        with get_db() as db:
            # Check if code exists
            existing = crud.get_start_code(db, code)
            if not existing:
                raise HTTPException(status_code=404, detail=f"Start code '{code}' not found")
            
            # Validate persona and history if provided
            if request.persona_id:
                from app.core.persona_cache import get_persona_by_id
                persona = get_persona_by_id(request.persona_id)
                if not persona:
                    raise HTTPException(status_code=404, detail=f"Persona not found: {request.persona_id}")
            
            if request.history_id:
                persona_id = request.persona_id if request.persona_id else str(existing.persona_id)
                if not persona_id:
                    raise HTTPException(status_code=400, detail="persona_id required when history_id is provided")
                
                from app.core.persona_cache import get_persona_histories
                histories = get_persona_histories(persona_id)
                history_found = any(h["id"] == request.history_id for h in histories)
                if not history_found:
                    raise HTTPException(status_code=404, detail=f"History not found or doesn't belong to persona")
            
            # Update start code
            start_code = crud.update_start_code(
                db,
                code=code,
                description=request.description,
                persona_id=request.persona_id,
                history_id=request.history_id,
                is_active=request.is_active
            )
            
            if not start_code:
                raise HTTPException(status_code=404, detail=f"Start code '{code}' not found")
            
            # Reload cache to reflect updates
            from app.core.start_code_cache import reload_cache
            reload_cache()
            
            return {
                "code": start_code.code,
                "description": start_code.description,
                "persona_id": str(start_code.persona_id) if start_code.persona_id else None,
                "history_id": str(start_code.history_id) if start_code.history_id else None,
                "is_active": start_code.is_active,
                "updated_at": start_code.updated_at.isoformat() if start_code.updated_at else None
            }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ANALYTICS-API] Error updating start code: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating start code: {str(e)}")


@router.delete("/start-codes/{code}")
async def delete_start_code(code: str) -> Dict[str, Any]:
    """
    Delete a start code
    
    Args:
        code: 5-character alphanumeric code
    
    Returns:
        Success message
    """
    try:
        with get_db() as db:
            success = crud.delete_start_code(db, code)
            if not success:
                raise HTTPException(status_code=404, detail=f"Start code '{code}' not found")
            
            # Reload cache to remove deleted code
            from app.core.start_code_cache import reload_cache
            reload_cache()
            
            return {"message": f"Start code '{code}' deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ANALYTICS-API] Error deleting start code: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting start code: {str(e)}")


@router.get("/personas-with-histories")
async def get_personas_with_histories() -> List[Dict[str, Any]]:
    """
    Get all public personas with their histories for dropdown selection
    
    Returns:
        List of personas with their histories
    """
    try:
        from app.core.persona_cache import get_preset_personas, get_persona_histories
        
        personas = get_preset_personas()
        result = []
        
        for persona in personas:
            histories = get_persona_histories(persona["id"])
            result.append({
                "id": persona["id"],
                "name": persona["name"],
                "key": persona["key"],
                "histories": [
                    {
                        "id": h["id"],
                        "name": h["name"]
                    }
                    for h in histories
                ]
            })
        
        return result
    except Exception as e:
        print(f"[ANALYTICS-API] Error fetching personas with histories: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching personas: {str(e)}")


@router.delete("/users/{client_id}/chats")
async def delete_user_chats(client_id: int) -> Dict[str, Any]:
    """
    Delete all chats and messages for a specific user
    
    Args:
        client_id: Telegram user ID
    
    Returns:
        Success message with count of deleted chats
    """
    try:
        with get_db() as db:
            # Check if user exists
            user = crud.get_user(db, client_id)
            if not user:
                raise HTTPException(status_code=404, detail=f"User {client_id} not found")
            
            # Delete all user chats
            deleted_count = crud.delete_all_user_chats(db, client_id)
            
            return {
                "message": f"Successfully deleted {deleted_count} chat(s) for user {client_id}",
                "deleted_count": deleted_count,
                "user_id": client_id
            }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ANALYTICS-API] Error deleting user chats: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting user chats: {str(e)}")


@router.get("/premium-stats")
async def get_premium_stats(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    acquisition_source: Optional[str] = Query(None, description="Acquisition source filter")
) -> Dict[str, Any]:
    """
    Get premium user statistics and metrics
    
    Args:
        start_date: Filter from this date onwards (YYYY-MM-DD)
        end_date: Filter up to this date (YYYY-MM-DD)
    
    Returns:
        Dictionary with:
        - total_premium_users: Total premium users
        - total_free_users: Total free users
        - conversion_rate: Percentage of users who are premium
        - premium_users_over_time: Daily premium user counts
        - premium_vs_free_images: Image generation comparison
        - premium_vs_free_engagement: Message count comparison
    """
    try:
        with get_db() as db:
            stats = crud.get_premium_stats(db, start_date=start_date, end_date=end_date, acquisition_source=acquisition_source)
            return stats
    except Exception as e:
        print(f"[ANALYTICS-API] Error fetching premium stats: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching premium stats: {str(e)}")


# ========== PERSONA MANAGEMENT ENDPOINTS ==========

class CreatePersonaRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    key: Optional[str] = Field(None, max_length=100)
    prompt: Optional[str] = None
    image_prompt: Optional[str] = None
    badges: Optional[str] = None  # Comma-separated string
    visibility: str = Field(default="public")
    description: Optional[str] = None
    small_description: Optional[str] = None
    emoji: Optional[str] = Field(None, max_length=10)
    intro: Optional[str] = None
    avatar_url: Optional[str] = None
    order: Optional[int] = Field(default=999)
    main_menu: Optional[bool] = Field(default=True)
    
    @validator('visibility')
    def validate_visibility(cls, v):
        if v not in ['public', 'private', 'custom']:
            raise ValueError('Visibility must be one of: public, private, custom')
        return v


class UpdatePersonaRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    key: Optional[str] = Field(None, max_length=100)
    prompt: Optional[str] = None
    image_prompt: Optional[str] = None
    badges: Optional[str] = None  # Comma-separated string
    visibility: Optional[str] = None
    description: Optional[str] = None
    small_description: Optional[str] = None
    emoji: Optional[str] = Field(None, max_length=10)
    intro: Optional[str] = None
    avatar_url: Optional[str] = None
    order: Optional[int] = None
    main_menu: Optional[bool] = None
    
    @validator('visibility')
    def validate_visibility(cls, v):
        if v is not None and v not in ['public', 'private', 'custom']:
            raise ValueError('Visibility must be one of: public, private, custom')
        return v


@router.get("/personas")
async def get_personas() -> List[Dict[str, Any]]:
    """
    Get all personas (public and private) for management
    
    Returns:
        List of personas with all details
    """
    try:
        with get_db() as db:
            personas = crud.get_all_personas(db)
            result = []
            for persona in personas:
                result.append({
                    "id": str(persona.id),
                    "owner_user_id": persona.owner_user_id,
                    "key": persona.key,
                    "name": persona.name,
                    "prompt": persona.prompt,
                    "image_prompt": persona.image_prompt,
                    "badges": persona.badges or [],
                    "visibility": persona.visibility,
                    "description": persona.description,
                    "small_description": persona.small_description,
                    "emoji": persona.emoji,
                    "intro": persona.intro,
                    "avatar_url": persona.avatar_url,
                    "order": persona.order,
                    "main_menu": persona.main_menu,
                    "created_at": persona.created_at.isoformat()
                })
            return result
    except Exception as e:
        print(f"[ANALYTICS-API] Error fetching personas: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching personas: {str(e)}")


@router.get("/personas/{persona_id}")
async def get_persona(persona_id: str) -> Dict[str, Any]:
    """
    Get a single persona by ID with full details
    
    Args:
        persona_id: Persona UUID
    
    Returns:
        Persona data with all fields
    """
    try:
        from uuid import UUID
        persona_uuid = UUID(persona_id)
        
        with get_db() as db:
            persona = crud.get_persona_by_id(db, persona_uuid)
            if not persona:
                raise HTTPException(status_code=404, detail=f"Persona not found: {persona_id}")
            
            return {
                "id": str(persona.id),
                "owner_user_id": persona.owner_user_id,
                "key": persona.key,
                "name": persona.name,
                "prompt": persona.prompt,
                "image_prompt": persona.image_prompt,
                "badges": persona.badges or [],
                "visibility": persona.visibility,
                "description": persona.description,
                "small_description": persona.small_description,
                "emoji": persona.emoji,
                "intro": persona.intro,
                "avatar_url": persona.avatar_url,
                "order": persona.order,
                "main_menu": persona.main_menu,
                "created_at": persona.created_at.isoformat()
            }
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid persona ID format")
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ANALYTICS-API] Error fetching persona: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching persona: {str(e)}")


@router.post("/personas")
async def create_persona(request: CreatePersonaRequest) -> Dict[str, Any]:
    """
    Create a new persona (always public with owner_user_id = NULL)
    
    Args:
        request: Persona creation data
    
    Returns:
        Created persona data
    """
    try:
        with get_db() as db:
            # Parse badges from comma-separated string
            badges = []
            if request.badges:
                badges = [b.strip() for b in request.badges.split(',') if b.strip()]
            
            persona = crud.create_persona(
                db,
                name=request.name,
                key=request.key,
                prompt=request.prompt,
                badges=badges,
                visibility=request.visibility,
                description=request.description,
                intro=request.intro,
                owner_user_id=None,  # Always NULL for admin-created personas
                order=request.order if request.order is not None else 999,
                main_menu=request.main_menu if request.main_menu is not None else True
            )
            
            # Update additional fields
            if request.image_prompt or request.small_description or request.emoji or request.avatar_url:
                persona = crud.update_persona(
                    db,
                    persona.id,
                    image_prompt=request.image_prompt,
                    small_description=request.small_description,
                    emoji=request.emoji,
                    avatar_url=request.avatar_url
                )
            
            # Reload persona cache
            from app.core.persona_cache import reload_cache
            reload_cache()
            
            return {
                "id": str(persona.id),
                "owner_user_id": persona.owner_user_id,
                "key": persona.key,
                "name": persona.name,
                "prompt": persona.prompt,
                "image_prompt": persona.image_prompt,
                "badges": persona.badges or [],
                "visibility": persona.visibility,
                "description": persona.description,
                "small_description": persona.small_description,
                "emoji": persona.emoji,
                "intro": persona.intro,
                "avatar_url": persona.avatar_url,
                "order": persona.order,
                "main_menu": persona.main_menu,
                "created_at": persona.created_at.isoformat()
            }
    except Exception as e:
        print(f"[ANALYTICS-API] Error creating persona: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error creating persona: {str(e)}")


@router.put("/personas/{persona_id}")
async def update_persona(persona_id: str, request: UpdatePersonaRequest) -> Dict[str, Any]:
    """
    Update an existing persona
    
    Args:
        persona_id: Persona UUID
        request: Update data
    
    Returns:
        Updated persona data
    """
    try:
        from uuid import UUID
        persona_uuid = UUID(persona_id)
        
        with get_db() as db:
            # Parse badges from comma-separated string if provided
            badges = None
            if request.badges is not None:
                badges = [b.strip() for b in request.badges.split(',') if b.strip()]
            
            persona = crud.update_persona(
                db,
                persona_uuid,
                name=request.name,
                key=request.key,
                prompt=request.prompt,
                image_prompt=request.image_prompt,
                badges=badges,
                visibility=request.visibility,
                description=request.description,
                small_description=request.small_description,
                emoji=request.emoji,
                intro=request.intro,
                avatar_url=request.avatar_url,
                order=request.order,
                main_menu=request.main_menu
            )
            
            if not persona:
                raise HTTPException(status_code=404, detail=f"Persona not found: {persona_id}")
            
            # Reload persona cache
            from app.core.persona_cache import reload_cache
            reload_cache()
            
            return {
                "id": str(persona.id),
                "owner_user_id": persona.owner_user_id,
                "key": persona.key,
                "name": persona.name,
                "prompt": persona.prompt,
                "image_prompt": persona.image_prompt,
                "badges": persona.badges or [],
                "visibility": persona.visibility,
                "description": persona.description,
                "small_description": persona.small_description,
                "emoji": persona.emoji,
                "intro": persona.intro,
                "avatar_url": persona.avatar_url,
                "order": persona.order,
                "main_menu": persona.main_menu,
                "created_at": persona.created_at.isoformat()
            }
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid persona ID format")
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ANALYTICS-API] Error updating persona: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error updating persona: {str(e)}")


@router.delete("/personas/{persona_id}")
async def delete_persona(persona_id: str) -> Dict[str, Any]:
    """
    Delete a persona
    
    Args:
        persona_id: Persona UUID
    
    Returns:
        Success message
    """
    try:
        from uuid import UUID
        persona_uuid = UUID(persona_id)
        
        with get_db() as db:
            success = crud.delete_persona(db, persona_uuid)
            if not success:
                raise HTTPException(status_code=404, detail=f"Persona not found: {persona_id}")
            
            # Reload persona cache
            from app.core.persona_cache import reload_cache
            reload_cache()
            
            return {"message": f"Persona '{persona_id}' deleted successfully"}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid persona ID format")
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ANALYTICS-API] Error deleting persona: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting persona: {str(e)}")


# ========== PERSONA HISTORY ENDPOINTS ==========

class CreatePersonaHistoryRequest(BaseModel):
    persona_id: str
    text: str = Field(..., min_length=1)
    name: Optional[str] = Field(None, max_length=255)
    small_description: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    wide_menu_image_url: Optional[str] = None
    image_prompt: Optional[str] = None


class UpdatePersonaHistoryRequest(BaseModel):
    text: Optional[str] = Field(None, min_length=1)
    name: Optional[str] = Field(None, max_length=255)
    small_description: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    wide_menu_image_url: Optional[str] = None
    image_prompt: Optional[str] = None


@router.get("/personas/{persona_id}/histories")
async def get_persona_histories(persona_id: str) -> List[Dict[str, Any]]:
    """
    Get all history starts for a persona
    
    Args:
        persona_id: Persona UUID
    
    Returns:
        List of persona histories
    """
    try:
        from uuid import UUID
        persona_uuid = UUID(persona_id)
        
        with get_db() as db:
            histories = crud.get_persona_histories(db, persona_uuid)
            result = []
            for history in histories:
                result.append({
                    "id": str(history.id),
                    "persona_id": str(history.persona_id),
                    "name": history.name,
                    "small_description": history.small_description,
                    "description": history.description,
                    "text": history.text,
                    "image_url": history.image_url,
                    "wide_menu_image_url": history.wide_menu_image_url,
                    "image_prompt": history.image_prompt,
                    "created_at": history.created_at.isoformat()
                })
            return result
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid persona ID format")
    except Exception as e:
        print(f"[ANALYTICS-API] Error fetching persona histories: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching persona histories: {str(e)}")


@router.post("/persona-histories")
async def create_persona_history(request: CreatePersonaHistoryRequest) -> Dict[str, Any]:
    """
    Create a new persona history start
    
    Args:
        request: History creation data
    
    Returns:
        Created history data
    """
    try:
        from uuid import UUID
        persona_uuid = UUID(request.persona_id)
        
        with get_db() as db:
            # Verify persona exists
            persona = crud.get_persona_by_id(db, persona_uuid)
            if not persona:
                raise HTTPException(status_code=404, detail=f"Persona not found: {request.persona_id}")
            
            history = crud.create_persona_history(
                db,
                persona_id=persona_uuid,
                text=request.text,
                name=request.name,
                small_description=request.small_description,
                description=request.description,
                image_url=request.image_url,
                wide_menu_image_url=request.wide_menu_image_url,
                image_prompt=request.image_prompt
            )
            
            # Reload persona cache
            from app.core.persona_cache import reload_cache
            reload_cache()
            
            return {
                "id": str(history.id),
                "persona_id": str(history.persona_id),
                "name": history.name,
                "small_description": history.small_description,
                "description": history.description,
                "text": history.text,
                "image_url": history.image_url,
                "wide_menu_image_url": history.wide_menu_image_url,
                "image_prompt": history.image_prompt,
                "created_at": history.created_at.isoformat()
            }
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid persona ID format")
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ANALYTICS-API] Error creating persona history: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error creating persona history: {str(e)}")


@router.put("/persona-histories/{history_id}")
async def update_persona_history(history_id: str, request: UpdatePersonaHistoryRequest) -> Dict[str, Any]:
    """
    Update an existing persona history start
    
    Args:
        history_id: History UUID
        request: Update data
    
    Returns:
        Updated history data
    """
    try:
        from uuid import UUID
        history_uuid = UUID(history_id)
        
        with get_db() as db:
            history = crud.update_persona_history(
                db,
                history_uuid,
                text=request.text,
                name=request.name,
                small_description=request.small_description,
                description=request.description,
                image_url=request.image_url,
                wide_menu_image_url=request.wide_menu_image_url,
                image_prompt=request.image_prompt
            )
            
            if not history:
                raise HTTPException(status_code=404, detail=f"History not found: {history_id}")
            
            # Reload persona cache
            from app.core.persona_cache import reload_cache
            reload_cache()
            
            return {
                "id": str(history.id),
                "persona_id": str(history.persona_id),
                "name": history.name,
                "small_description": history.small_description,
                "description": history.description,
                "text": history.text,
                "image_url": history.image_url,
                "wide_menu_image_url": history.wide_menu_image_url,
                "image_prompt": history.image_prompt,
                "created_at": history.created_at.isoformat()
            }
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid history ID format")
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ANALYTICS-API] Error updating persona history: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error updating persona history: {str(e)}")


@router.delete("/persona-histories/{history_id}")
async def delete_persona_history(history_id: str) -> Dict[str, Any]:
    """
    Delete a persona history start
    
    Args:
        history_id: History UUID
    
    Returns:
        Success message
    """
    try:
        from uuid import UUID
        history_uuid = UUID(history_id)
        
        with get_db() as db:
            success = crud.delete_persona_history(db, history_uuid)
            if not success:
                raise HTTPException(status_code=404, detail=f"History not found: {history_id}")
            
            # Reload persona cache
            from app.core.persona_cache import reload_cache
            reload_cache()
            
            return {"message": f"History '{history_id}' deleted successfully"}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid history ID format")
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ANALYTICS-API] Error deleting persona history: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting persona history: {str(e)}")


# ========== TRANSLATION MANAGEMENT ENDPOINTS ==========

class TranslationRequest(BaseModel):
    """Request model for creating/updating translations"""
    key: str = Field(..., description="Translation key (dot notation)")
    lang: str = Field(..., description="Language code (en, ru)")
    value: str = Field(..., description="Translated text")
    category: Optional[str] = Field(None, description="Category (ui, persona, history)")

    @validator('lang')
    def validate_lang(cls, v):
        if v not in ['en', 'ru']:
            raise ValueError('Language must be en or ru')
        return v


@router.get("/translations")
async def get_translations(
    lang: Optional[str] = Query(None, description="Filter by language"),
    category: Optional[str] = Query(None, description="Filter by category"),
    key_prefix: Optional[str] = Query(None, description="Filter by key prefix"),
    search: Optional[str] = Query(None, description="Search in keys or values"),
    limit: int = Query(100, ge=1, le=50000),
    offset: int = Query(0, ge=0)
) -> Dict[str, Any]:
    """
    Get all translations with filtering and pagination
    
    Returns paginated list of translations with all language versions
    """
    try:
        with get_db() as db:
            from app.db.models import Translation
            
            # Build query
            query = db.query(Translation)
            
            if lang:
                query = query.filter(Translation.lang == lang)
            if category:
                query = query.filter(Translation.category == category)
            if key_prefix:
                query = query.filter(Translation.key.like(f"{key_prefix}%"))
            if search:
                search_pattern = f"%{search}%"
                query = query.filter(
                    (Translation.key.like(search_pattern)) | 
                    (Translation.value.like(search_pattern))
                )
            
            # Get total count
            total = query.count()
            
            # Get paginated results
            translations = query.order_by(Translation.key, Translation.lang).offset(offset).limit(limit).all()
            
            # Group by key to show all languages together
            from collections import defaultdict
            grouped = defaultdict(dict)
            for trans in translations:
                if 'key' not in grouped[trans.key]:
                    grouped[trans.key] = {
                        'key': trans.key,
                        'category': trans.category,
                        'translations': {}
                    }
                grouped[trans.key]['translations'][trans.lang] = trans.value
            
            return {
                'translations': list(grouped.values()),
                'total': total,
                'limit': limit,
                'offset': offset
            }
    except Exception as e:
        print(f"[ANALYTICS-API] Error fetching translations: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error fetching translations: {str(e)}")


@router.post("/translations")
async def create_translation(request: TranslationRequest) -> Dict[str, Any]:
    """
    Create a new translation
    
    Args:
        request: Translation data
    
    Returns:
        Created translation
    """
    try:
        with get_db() as db:
            translation = crud.create_or_update_translation(
                db,
                key=request.key,
                lang=request.lang,
                value=request.value,
                category=request.category
            )
            
            return {
                'id': str(translation.id),
                'key': translation.key,
                'lang': translation.lang,
                'value': translation.value,
                'category': translation.category,
                'created_at': translation.created_at.isoformat(),
                'updated_at': translation.updated_at.isoformat()
            }
    except Exception as e:
        print(f"[ANALYTICS-API] Error creating translation: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error creating translation: {str(e)}")


@router.put("/translations/{key:path}/{lang}")
async def update_translation(key: str, lang: str, value: str = Query(...)) -> Dict[str, Any]:
    """
    Update an existing translation
    
    Args:
        key: Translation key (URL-encoded)
        lang: Language code
        value: New translated text (as query param to avoid encoding issues)
    
    Returns:
        Updated translation
    """
    if lang not in ['en', 'ru']:
        raise HTTPException(status_code=400, detail=f"Unsupported language: {lang}")

    try:
        with get_db() as db:
            translation = crud.create_or_update_translation(
                db,
                key=key,
                lang=lang,
                value=value
            )
            
            return {
                'id': str(translation.id),
                'key': translation.key,
                'lang': translation.lang,
                'value': translation.value,
                'category': translation.category,
                'updated_at': translation.updated_at.isoformat()
            }
    except Exception as e:
        print(f"[ANALYTICS-API] Error updating translation: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating translation: {str(e)}")


@router.delete("/translations/{key:path}/{lang}")
async def delete_translation(key: str, lang: str) -> Dict[str, Any]:
    """
    Delete a translation
    
    Args:
        key: Translation key (URL-encoded)
        lang: Language code
    
    Returns:
        Success message
    """
    try:
        with get_db() as db:
            count = crud.delete_translation(db, key, lang)
            
            if count == 0:
                raise HTTPException(status_code=404, detail=f"Translation not found: {key} ({lang})")
            
            return {"message": f"Translation deleted: {key} ({lang})"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ANALYTICS-API] Error deleting translation: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting translation: {str(e)}")


@router.post("/translations/bulk-import")
async def bulk_import_translations(
    translations: List[Dict[str, str]]
) -> Dict[str, Any]:
    """
    Bulk import translations from JSON array
    
    Args:
        translations: List of translation objects with keys: key, lang, value, category (optional)
    
    Returns:
        Import statistics
    """
    try:
        with get_db() as db:
            # Validate and import
            valid_translations = []
            errors = []
            
            for idx, trans_data in enumerate(translations):
                # Validate required fields
                if 'key' not in trans_data or 'lang' not in trans_data or 'value' not in trans_data:
                    errors.append(f"Row {idx}: Missing required fields (key, lang, value)")
                    continue
                
                # Validate language
                if trans_data['lang'] not in ['en', 'ru']:
                    errors.append(f"Row {idx}: Unsupported language '{trans_data['lang']}'")
                    continue
                
                valid_translations.append(trans_data)
            
            # Bulk create
            if valid_translations:
                count = crud.bulk_create_translations(db, valid_translations)
            else:
                count = 0
            
            return {
                'imported': count,
                'errors': errors,
                'total': len(translations)
            }
    except Exception as e:
        print(f"[ANALYTICS-API] Error importing translations: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error importing translations: {str(e)}")


@router.get("/translations/export")
async def export_translations(
    format: str = Query("json", pattern="^(json|csv)$"),
    lang: Optional[str] = Query(None)
) -> Any:
    """
    Export all translations as JSON or CSV
    
    Args:
        format: Export format (json or csv)
        lang: Optional language filter
    
    Returns:
        File download response
    """
    try:
        from fastapi.responses import StreamingResponse
        import io
        import csv
        
        with get_db() as db:
            translations = crud.get_all_translations(db, lang)
            
            if format == "csv":
                # Export as CSV
                output = io.StringIO()
                writer = csv.writer(output)
                writer.writerow(['key', 'lang', 'value', 'category'])
                
                for trans in translations:
                    writer.writerow([trans.key, trans.lang, trans.value, trans.category or ''])
                
                output.seek(0)
                return StreamingResponse(
                    iter([output.getvalue()]),
                    media_type="text/csv",
                    headers={"Content-Disposition": "attachment; filename=translations.csv"}
                )
            else:
                # Export as JSON
                data = [
                    {
                        'key': trans.key,
                        'lang': trans.lang,
                        'value': trans.value,
                        'category': trans.category
                    }
                    for trans in translations
                ]
                
                import json
                output = io.StringIO()
                json.dump(data, output, indent=2, ensure_ascii=False)
                output.seek(0)
                
                return StreamingResponse(
                    iter([output.getvalue()]),
                    media_type="application/json",
                    headers={"Content-Disposition": "attachment; filename=translations.json"}
                )
    except Exception as e:
        print(f"[ANALYTICS-API] Error exporting translations: {e}")
        raise HTTPException(status_code=500, detail=f"Error exporting translations: {str(e)}")


@router.post("/translations/refresh-cache")
async def refresh_translation_cache() -> Dict[str, Any]:
    """
    Refresh the translation cache from database
    
    This should be called after bulk updates to translations
    
    Returns:
        Success message with statistics
    """
    try:
        from app.core.translation_service import translation_service
        
        translation_service.reload()
        
        # Get statistics
        stats = {}
        for lang in translation_service.get_supported_languages():
            count = len(translation_service.get_all(lang))
            stats[lang] = count
        
        return {
            'message': 'Translation cache refreshed successfully',
            'statistics': stats
        }
    except Exception as e:
        print(f"[ANALYTICS-API] Error refreshing cache: {e}")
        raise HTTPException(status_code=500, detail=f"Error refreshing cache: {str(e)}")


@router.get("/translations/{key:path}")
async def get_translation_by_key(key: str) -> Dict[str, Any]:
    """
    Get all language versions of a specific translation key
    
    Args:
        key: Translation key (URL-encoded if contains special characters)
    
    Returns:
        Key with all language versions
    """
    try:
        with get_db() as db:
            from app.db.models import Translation
            
            translations = db.query(Translation).filter(Translation.key == key).all()
            
            if not translations:
                raise HTTPException(status_code=404, detail=f"Translation key not found: {key}")
            
            result = {
                'key': key,
                'category': translations[0].category,
                'translations': {}
            }
            
            for trans in translations:
                result['translations'][trans.lang] = trans.value
            
            return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ANALYTICS-API] Error fetching translation: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching translation: {str(e)}")


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

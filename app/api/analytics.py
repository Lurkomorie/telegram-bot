"""
Analytics API endpoints for viewing statistics and user event timelines
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, validator
from datetime import datetime, date
from app.db.base import get_db
from app.db import crud

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


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



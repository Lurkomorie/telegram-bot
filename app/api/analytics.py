"""
Analytics API endpoints for viewing statistics and user event timelines
"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from app.db.base import get_db
from app.db import crud

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


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





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





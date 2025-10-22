"""
Mini App API endpoints
Provides data for the Telegram Web App
"""
from fastapi import APIRouter, Header, HTTPException
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from urllib.parse import parse_qsl
from app.core.security import validate_telegram_webapp_data
from app.db.base import get_db
from app.db import crud
from app.settings import settings

router = APIRouter(prefix="/api/miniapp", tags=["miniapp"])


class ChatCheckRequest(BaseModel):
    persona_id: str
    history_id: Optional[str] = None


@router.get("/personas")
async def get_personas(
    x_telegram_init_data: Optional[str] = Header(None)
) -> List[Dict[str, Any]]:
    """
    Get all public personas for the Mini App gallery
    
    Returns persona data with:
    - id, name, description, badges
    - avatar_url (primary image for gallery)
    """
    # Validate Telegram Web App authentication
    # In development, we can skip validation for testing
    if settings.ENV == "production" and not validate_telegram_webapp_data(x_telegram_init_data or ""):
        raise HTTPException(status_code=403, detail="Invalid Telegram authentication")
    
    with get_db() as db:
        # Get all public personas
        personas = crud.get_preset_personas(db)
        
        # Build response with persona data
        result = []
        for persona in personas:
            # Use avatar_url as primary image, fallback to first history image
            avatar_url = persona.avatar_url
            if not avatar_url:
                history_start = crud.get_random_history_start(db, str(persona.id))
                avatar_url = history_start.image_url if history_start else None
            
            result.append({
                "id": str(persona.id),
                "name": persona.name,
                "description": persona.description or "",
                "badges": persona.badges or [],
                "avatar_url": avatar_url,
            })
    
    return result


@router.get("/personas/{persona_id}/histories")
async def get_persona_histories(
    persona_id: str,
    x_telegram_init_data: Optional[str] = Header(None)
) -> List[Dict[str, Any]]:
    """
    Get all history starts for a specific persona
    
    Returns list of history scenarios with:
    - id, description, text (greeting), image_url
    """
    # Validate authentication
    if settings.ENV == "production" and not validate_telegram_webapp_data(x_telegram_init_data or ""):
        raise HTTPException(status_code=403, detail="Invalid Telegram authentication")
    
    with get_db() as db:
        # Get histories for this persona
        histories = crud.get_persona_histories(db, persona_id)
        
        result = []
        for history in histories:
            result.append({
                "id": str(history.id),
                "description": history.description or "",
                "text": history.text,
                "image_url": history.image_url,
                "wide_menu_image_url": history.wide_menu_image_url,
            })
    
    return result


@router.get("/user/energy")
async def get_user_energy(
    x_telegram_init_data: Optional[str] = Header(None)
) -> Dict[str, int]:
    """
    Get current user's energy
    
    Returns: {energy: int, max_energy: int}
    """
    # Validate and extract user ID from init data
    if not x_telegram_init_data:
        return {"energy": 100, "max_energy": 100}  # Default for testing
    
    try:
        # Parse init data to get user ID
        parsed = dict(parse_qsl(x_telegram_init_data))
        import json
        user_data = json.loads(parsed.get('user', '{}'))
        user_id = user_data.get('id')
        
        if not user_id:
            raise HTTPException(status_code=400, detail="User ID not found in init data")
        
        with get_db() as db:
            # Get or create user
            user = crud.get_or_create_user(db, telegram_id=user_id)
            return {"energy": user.energy, "max_energy": user.max_energy}
    
    except Exception as e:
        print(f"[ENERGY-API] Error: {e}")
        return {"energy": 100, "max_energy": 100}  # Default fallback


@router.get("/health")
async def health():
    """Health check for Mini App API"""
    return {"status": "ok", "service": "miniapp-api"}


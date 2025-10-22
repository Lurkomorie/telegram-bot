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
    
    result = []
    
    with get_db() as db:
        # Get all public personas
        personas = crud.get_preset_personas(db)
        
        # Build response with persona data
        # Extract all data while session is active to avoid lazy loading issues
        for persona in personas:
            # Access all attributes within the session
            persona_id = str(persona.id)
            persona_name = persona.name
            persona_description = persona.description or ""
            persona_badges = persona.badges or []
            
            # Use avatar_url as primary image, fallback to first history image
            avatar_url = persona.avatar_url
            if not avatar_url:
                history_start = crud.get_random_history_start(db, persona_id)
                avatar_url = history_start.image_url if history_start else None
            
            result.append({
                "id": persona_id,
                "name": persona_name,
                "description": persona_description,
                "badges": persona_badges,
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
    
    # Convert string persona_id to UUID
    try:
        from uuid import UUID
        persona_uuid = UUID(persona_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid persona ID format")
    
    result = []
    
    with get_db() as db:
        # Get histories for this persona
        histories = crud.get_persona_histories(db, persona_uuid)
        
        # Extract all data while session is active to avoid lazy loading issues
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
) -> Dict[str, Any]:
    """
    Get current user's energy and premium status
    
    Returns: {energy: int, max_energy: int, is_premium: bool}
    """
    # Validate and extract user ID from init data
    if not x_telegram_init_data:
        return {"energy": 100, "max_energy": 100, "is_premium": False}  # Default for testing
    
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
            is_premium = crud.check_user_premium(db, user_id)
            return {
                "energy": user.energy, 
                "max_energy": user.max_energy,
                "is_premium": is_premium
            }
    
    except Exception as e:
        print(f"[ENERGY-API] Error: {e}")
        return {"energy": 100, "max_energy": 100, "is_premium": False}  # Default fallback


class SelectScenarioRequest(BaseModel):
    persona_id: str
    history_id: Optional[str] = None


class CreateInvoiceRequest(BaseModel):
    plan_id: str  # 2days, month, 3months, year


@router.post("/select-scenario")
async def select_scenario(
    request: SelectScenarioRequest,
    x_telegram_init_data: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Handle scenario selection from Mini App
    Creates a chat and sends the greeting message
    
    Returns: {success: bool, message: str}
    """
    # Validate authentication
    if settings.ENV == "production" and not validate_telegram_webapp_data(x_telegram_init_data or ""):
        raise HTTPException(status_code=403, detail="Invalid Telegram authentication")
    
    # Parse user ID and chat ID from init data
    try:
        parsed = dict(parse_qsl(x_telegram_init_data or ""))
        import json
        user_data = json.loads(parsed.get('user', '{}'))
        user_id = user_data.get('id')
        
        if not user_id:
            raise HTTPException(status_code=400, detail="User ID not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse user data: {e}")
    
    # Import bot and necessary functions
    from app.bot.loader import bot
    from app.core.telegram_utils import escape_markdown_v2
    from app.core import redis_queue
    from uuid import UUID
    
    try:
        persona_uuid = UUID(request.persona_id)
        history_uuid = UUID(request.history_id) if request.history_id else None
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    
    with get_db() as db:
        # Get persona
        persona = crud.get_persona_by_id(db, str(persona_uuid))
        if not persona:
            raise HTTPException(status_code=404, detail="Persona not found")
        
        persona_name = persona.name
        persona_intro = persona.intro
        
        # Check if chat already exists
        existing_chat = crud.check_existing_chat(
            db,
            tg_chat_id=user_id,  # For private messages, tg_chat_id = user_id
            user_id=user_id,
            persona_id=persona.id
        )
        
        if existing_chat:
            return {
                "success": False,
                "message": "existing_chat",
                "persona_name": persona_name
            }
        
        # Create new chat
        chat = crud.create_new_chat(
            db,
            tg_chat_id=user_id,
            user_id=user_id,
            persona_id=persona.id
        )
        
        chat_id = chat.id
        
        # Clear any unprocessed messages
        print(f"[MINIAPP-SELECT] 🧹 Clearing unprocessed messages for chat {chat_id}")
        crud.clear_unprocessed_messages(db, chat_id)
    
    # Clear Redis queue and processing lock
    await redis_queue.clear_batch_messages(chat_id)
    await redis_queue.set_processing_lock(chat_id, False)
    
    with get_db() as db:
        # Get specific history or random one
        if history_uuid:
            from app.db.models import PersonaHistoryStart
            history_start = db.query(PersonaHistoryStart).filter(
                PersonaHistoryStart.id == history_uuid,
                PersonaHistoryStart.persona_id == persona_uuid
            ).first()
            if not history_start:
                history_start = crud.get_random_history_start(db, str(persona_uuid))
        else:
            history_start = crud.get_random_history_start(db, str(persona_uuid))
        
        history_start_data = None
        description_text = None
        if history_start:
            history_start_data = {
                "text": history_start.text,
                "image_url": history_start.image_url
            }
            description_text = history_start.description
        
        # Determine greeting text
        if history_start_data:
            greeting_text = history_start_data['text']
        else:
            greeting_text = persona_intro or f"Hi! I'm {persona_name}. Let's chat!"
        
        # Save description as system message if exists
        if description_text:
            crud.create_message_with_state(
                db,
                chat_id=chat_id,
                role="system",
                text=description_text,
                is_processed=True
            )
        
        # Save greeting as assistant message
        crud.create_message_with_state(
            db,
            chat_id=chat_id,
            role="assistant",
            text=greeting_text,
            is_processed=True
        )
    
    # Send messages to user
    try:
        # Clear any previous image's refresh button (scenario selection starts fresh)
        with get_db() as db:
            existing_chat_check = crud.get_chat_by_tg_chat_id(db, user_id)
            if existing_chat_check and existing_chat_check.ext and existing_chat_check.ext.get("last_image_msg_id"):
                last_img_msg_id = existing_chat_check.ext["last_image_msg_id"]
                try:
                    await bot.edit_message_reply_markup(
                        chat_id=user_id,
                        message_id=last_img_msg_id,
                        reply_markup=None
                    )
                    print(f"[MINIAPP-SELECT] 🗑️  Removed refresh button from previous chat's image")
                except Exception as e:
                    # Button might already be removed, that's okay
                    print(f"[MINIAPP-SELECT] ⚠️  Could not remove previous refresh button (likely already removed): {e}")
                finally:
                    # Always clear the stored message ID, even if removal failed
                    # For JSONB fields, we must mark as modified or reassign the whole dict
                    from sqlalchemy.orm.attributes import flag_modified
                    existing_chat_check.ext["last_image_msg_id"] = None
                    flag_modified(existing_chat_check, "ext")
                    db.commit()
        
        # Send description first if exists
        if description_text:
            escaped_description = escape_markdown_v2(description_text)
            formatted_description = f"_{escaped_description}_"
            await bot.send_message(
                chat_id=user_id,
                text=formatted_description,
                parse_mode="MarkdownV2"
            )
        
        # Send greeting (images from history starts don't get refresh buttons - they're static greeting images)
        escaped_greeting = escape_markdown_v2(greeting_text)
        if history_start_data and history_start_data["image_url"]:
            await bot.send_photo(
                chat_id=user_id,
                photo=history_start_data["image_url"],
                caption=escaped_greeting,
                parse_mode="MarkdownV2"
            )
        else:
            await bot.send_message(
                chat_id=user_id,
                text=escaped_greeting,
                parse_mode="MarkdownV2"
            )
        
        print(f"[MINIAPP-SELECT] ✅ Created chat and sent greeting for persona {persona_name}")
        
        return {
            "success": True,
            "message": "Chat created successfully"
        }
    
    except Exception as e:
        print(f"[MINIAPP-SELECT] ❌ Error sending messages: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send messages: {str(e)}")


@router.post("/create-invoice")
async def create_invoice(
    request: CreateInvoiceRequest,
    x_telegram_init_data: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Create a Telegram Stars invoice for premium subscription
    
    Returns: {invoice_link: str}
    """
    # Validate authentication
    if settings.ENV == "production" and not validate_telegram_webapp_data(x_telegram_init_data or ""):
        raise HTTPException(status_code=403, detail="Invalid Telegram authentication")
    
    # Parse user ID from init data
    try:
        parsed = dict(parse_qsl(x_telegram_init_data or ""))
        import json
        user_data = json.loads(parsed.get('user', '{}'))
        user_id = user_data.get('id')
        
        if not user_id:
            raise HTTPException(status_code=400, detail="User ID not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse user data: {e}")
    
    # Plan mapping
    PLANS = {
        "2days": {"duration": "2 Days", "stars": 250, "description": "Premium for 2 days"},
        "month": {"duration": "1 Month", "stars": 500, "description": "Premium for 1 month"},
        "3months": {"duration": "3 Months", "stars": 1000, "description": "Premium for 3 months"},
        "year": {"duration": "1 Year", "stars": 2500, "description": "Premium for 1 year"},
    }
    
    plan = PLANS.get(request.plan_id)
    if not plan:
        raise HTTPException(status_code=400, detail="Invalid plan ID")
    
    # Import bot and types
    from app.bot.loader import bot
    from aiogram.types import LabeledPrice
    
    try:
        # Create invoice using Telegram Bot API
        # For Stars payment, provider_token should be empty string
        invoice_link = await bot.create_invoice_link(
            title=f"Premium - {plan['duration']}",
            description=plan['description'],
            payload=request.plan_id,  # This will be sent back in successful_payment
            provider_token="",  # Empty for Telegram Stars
            currency="XTR",  # XTR = Telegram Stars
            prices=[LabeledPrice(label=f"Premium {plan['duration']}", amount=plan['stars'])]
        )
        
        print(f"[INVOICE-API] Created invoice for user {user_id}, plan {request.plan_id}: {invoice_link}")
        
        return {"invoice_link": invoice_link}
    
    except Exception as e:
        print(f"[INVOICE-API] Error creating invoice: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create invoice: {str(e)}")


@router.get("/health")
async def health():
    """Health check for Mini App API"""
    return {"status": "ok", "service": "miniapp-api"}


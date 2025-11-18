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


def extract_user_id_from_init_data(x_telegram_init_data: Optional[str]) -> Optional[int]:
    """Extract user ID from Telegram Web App init data"""
    if not x_telegram_init_data:
        return None
    
    try:
        import json
        parsed = dict(parse_qsl(x_telegram_init_data))
        user_data = json.loads(parsed.get('user', '{}'))
        return user_data.get('id')
    except:
        return None


@router.get("/personas")
async def get_personas(
    x_telegram_init_data: Optional[str] = Header(None)
) -> List[Dict[str, Any]]:
    """
    Get all public personas for the Mini App gallery
    
    Returns persona data with:
    - id, name, description, badges
    - avatar_url (primary image for gallery)
    - Descriptions are returned in user's language if available
    """
    # Validate Telegram Web App authentication
    # In development, we can skip validation for testing
    if settings.ENV == "production" and not validate_telegram_webapp_data(x_telegram_init_data or ""):
        raise HTTPException(status_code=403, detail="Invalid Telegram authentication")
    
    # Get user ID and language preference
    user_id = extract_user_id_from_init_data(x_telegram_init_data)
    user_language = 'en'
    if user_id:
        with get_db() as db:
            user_language = crud.get_user_language(db, user_id)
    
    # Get personas from cache (much faster!)
    from app.core.persona_cache import get_preset_personas, get_random_history, get_persona_field
    personas = get_preset_personas()
    
    result = []
    for persona in personas:
        persona_id = persona["id"]
        
        # Use avatar_url as primary image, fallback to first history image from cache
        avatar_url = persona["avatar_url"]
        if not avatar_url:
            history_start = get_random_history(persona_id)
            avatar_url = history_start["image_url"] if history_start else None
        
        # Get translated descriptions
        description = get_persona_field(persona, 'description', language=user_language) or ""
        small_description = get_persona_field(persona, 'small_description', language=user_language) or ""
        
        result.append({
            "id": persona_id,
            "name": persona["name"],  # Names are not translated
            "description": description,
            "smallDescription": small_description,
            "badges": persona["badges"] or [],
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
    - Descriptions and text are returned in user's language if available
    """
    # Validate authentication
    if settings.ENV == "production" and not validate_telegram_webapp_data(x_telegram_init_data or ""):
        raise HTTPException(status_code=403, detail="Invalid Telegram authentication")
    
    # Validate persona_id format
    try:
        from uuid import UUID
        UUID(persona_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid persona ID format")
    
    # Get user ID and language preference
    user_id = extract_user_id_from_init_data(x_telegram_init_data)
    user_language = 'en'
    if user_id:
        with get_db() as db:
            user_language = crud.get_user_language(db, user_id)
    
    # Get histories from cache
    from app.core import persona_cache
    from app.core.persona_cache import get_history_field
    histories = persona_cache.get_persona_histories(persona_id)
    
    # Transform to camelCase for frontend
    result = []
    for h in histories:
        # Get translated fields
        name = get_history_field(h, 'name', language=user_language) or h["name"]
        small_description = get_history_field(h, 'small_description', language=user_language) or h["small_description"]
        description = get_history_field(h, 'description', language=user_language) or h["description"]
        text = get_history_field(h, 'text', language=user_language) or h["text"]
        
        result.append({
            "id": h["id"],
            "name": name,
            "smallDescription": small_description,
            "description": description,
            "text": text,
            "image_url": h["image_url"],
            "wide_menu_image_url": h["wide_menu_image_url"]
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


@router.get("/user/language")
async def get_user_language(
    x_telegram_init_data: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Get user's language preference
    
    Returns: {language: str}
    """
    # Validate and extract user ID from init data
    if not x_telegram_init_data:
        return {"language": "en"}  # Default for testing
    
    try:
        # Parse init data to get user ID and language_code
        parsed = dict(parse_qsl(x_telegram_init_data))
        import json
        user_data = json.loads(parsed.get('user', '{}'))
        user_id = user_data.get('id')
        telegram_language_code = user_data.get('language_code', 'en')
        
        if not user_id:
            raise HTTPException(status_code=400, detail="User ID not found in init data")
        
        with get_db() as db:
            # Get or create user with language from Telegram
            user = crud.get_or_create_user(db, telegram_id=user_id, language_code=telegram_language_code)
            # Always prefer Telegram's current language setting
            language = crud.get_user_language(db, user_id)
            return {"language": language}
    
    except Exception as e:
        print(f"[LANGUAGE-API] Error: {e}")
        return {"language": "en"}  # Default fallback


@router.get("/user/age-status")
async def get_user_age_status(
    x_telegram_init_data: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Get user's age verification status
    
    Returns: {age_verified: bool}
    """
    # Validate and extract user ID from init data
    if not x_telegram_init_data:
        return {"age_verified": False}  # Default for testing
    
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
            return {"age_verified": user.age_verified}
    
    except Exception as e:
        print(f"[AGE-STATUS-API] Error: {e}")
        return {"age_verified": False}  # Default fallback


@router.post("/user/verify-age")
async def verify_user_age(
    x_telegram_init_data: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Mark user as age verified
    
    Returns: {success: bool, age_verified: bool}
    """
    # Validate and extract user ID from init data
    if not x_telegram_init_data:
        raise HTTPException(status_code=400, detail="No init data provided")
    
    try:
        # Parse init data to get user ID
        parsed = dict(parse_qsl(x_telegram_init_data))
        import json
        user_data = json.loads(parsed.get('user', '{}'))
        user_id = user_data.get('id')
        
        if not user_id:
            raise HTTPException(status_code=400, detail="User ID not found in init data")
        
        with get_db() as db:
            # Update user's age_verified status
            user = crud.update_user_age_verified(db, telegram_id=user_id)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            print(f"[AGE-VERIFY-API] ✅ User {user_id} verified age from miniapp")
            return {"success": True, "age_verified": True}
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"[AGE-VERIFY-API] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to verify age: {str(e)}")


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
    Returns immediately while processing in background
    
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
    
    # Import necessary functions
    from uuid import UUID
    import asyncio
    
    try:
        persona_uuid = UUID(request.persona_id)
        history_uuid = UUID(request.history_id) if request.history_id else None
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    
    # Get persona from cache
    from app.core.persona_cache import get_persona_by_id
    persona = get_persona_by_id(str(persona_uuid))
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    
    # Return immediately and process in background
    asyncio.create_task(_process_scenario_selection(
        user_id=user_id,
        persona_uuid=persona_uuid,
        history_uuid=history_uuid
    ))
    
    return {
        "success": True,
        "message": "Chat creation started"
    }


async def _process_scenario_selection(
    user_id: int,
    persona_uuid,
    history_uuid: Optional
):
    """Background task to process scenario selection"""
    from app.bot.loader import bot
    from app.core.telegram_utils import escape_markdown_v2
    from app.core import redis_queue
    from app.core.persona_cache import get_persona_by_id, get_persona_histories as get_cached_histories
    
    try:
        persona = get_persona_by_id(str(persona_uuid))
        if not persona:
            print(f"[MINIAPP-SELECT] ❌ Persona {persona_uuid} not found")
            return
        
        persona_name = persona["name"]
        persona_intro = persona["intro"]
        
        # Clear any previous image's refresh button before deleting chat
        with get_db() as db:
            existing_chat = crud.check_existing_chat(
                db,
                tg_chat_id=user_id,
                user_id=user_id,
                persona_id=str(persona_uuid)
            )
            
            if existing_chat and existing_chat.ext and existing_chat.ext.get("last_image_msg_id"):
                last_img_msg_id = existing_chat.ext["last_image_msg_id"]
                try:
                    await bot.edit_message_reply_markup(
                        chat_id=user_id,
                        message_id=last_img_msg_id,
                        reply_markup=None
                    )
                    print("[MINIAPP-SELECT] 🗑️  Removed refresh button from previous image")
                except Exception as e:
                    print(f"[MINIAPP-SELECT] ⚠️  Could not remove previous refresh button: {e}")
        
        with get_db() as db:
            # Check if chat already exists
            existing_chat = crud.check_existing_chat(
                db,
                tg_chat_id=user_id,
                user_id=user_id,
                persona_id=str(persona_uuid)
            )
            
            # If chat exists, delete it to start fresh (using proper deletion that handles image_jobs)
            if existing_chat:
                print(f"[MINIAPP-SELECT] 🗑️  Deleting existing chat {existing_chat.id} for fresh start")
                crud.delete_chat(db, existing_chat.id)
            
            # Create new chat
            chat = crud.create_new_chat(
                db,
                tg_chat_id=user_id,
                user_id=user_id,
                persona_id=str(persona_uuid)
            )
            
            chat_id = chat.id
            
            # Clear any unprocessed messages
            print(f"[MINIAPP-SELECT] 🧹 Clearing unprocessed messages for chat {chat_id}")
            crud.clear_unprocessed_messages(db, chat_id)
        
        # Clear Redis queue and processing lock
        await redis_queue.clear_batch_messages(chat_id)
        await redis_queue.set_processing_lock(chat_id, False)
        
        # Get specific history from cache (no random selection)
        history_start = None
        if history_uuid:
            histories = get_cached_histories(str(persona_uuid))
            for h in histories:
                if h["id"] == str(history_uuid):
                    history_start = h
                    break
            if not history_start:
                print(f"[MINIAPP-SELECT] ⚠️  History {history_uuid} not found, using persona intro")
        else:
            print(f"[MINIAPP-SELECT] ℹ️  No history selected, using persona intro")
        
        history_start_data = None
        description_text = None
        if history_start:
            history_start_data = {
                "text": history_start["text"],
                "image_url": history_start["image_url"],
                "image_prompt": history_start.get("image_prompt")
            }
            description_text = history_start["description"]
        
        with get_db() as db:
            
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
            
            # Create initial ImageJob for continuity if history has image_prompt
            if history_start_data and history_start_data.get("image_prompt"):
                print("[MINIAPP-SELECT] 🎨 Creating initial image job for visual continuity")
                crud.create_initial_image_job(
                    db,
                    user_id=user_id,
                    persona_id=str(persona_uuid),
                    chat_id=chat_id,
                    prompt=history_start_data["image_prompt"],
                    result_url=history_start_data.get("image_url")
                )
        
        # Send messages to user
        # Get user's language for bot messages
        with get_db() as db:
            user_language = crud.get_user_language(db, user_id)
        
        # Send hint message FIRST (before story starts)
        from app.settings import get_ui_text
        hint_text = get_ui_text("hints.restart", language=user_language)
        await bot.send_message(
            chat_id=user_id,
            text=escape_markdown_v2(hint_text),
            parse_mode="MarkdownV2"
        )
        
        # Send description if exists
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
    
    except Exception as e:
        print(f"[MINIAPP-SELECT] ❌ Error in background processing: {e}")


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


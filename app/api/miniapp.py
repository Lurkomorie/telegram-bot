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


async def generate_initial_state_for_story(
    persona_name: str,
    story_description: str,
    greeting_text: str
) -> str:
    """Generate initial state from story description using State Resolver"""
    from app.core.brains.state_resolver import resolve_state
    
    # Build chat history with system message (story description) and greeting
    chat_history = [
        {"role": "system", "content": story_description},
        {"role": "assistant", "content": greeting_text}
    ]
    
    # Call State Resolver with no previous state (will create initial state)
    print(f"[MINIAPP-SELECT] 🧠 Generating initial state for story...")
    state = await resolve_state(
        previous_state=None,
        chat_history=chat_history,
        user_message="[INITIAL_STORY_START]",  # Placeholder for initial generation
        persona_name=persona_name,
        previous_image_prompt=None
    )
    
    print(f"[MINIAPP-SELECT] ✅ Initial state generated ({len(state)} chars)")
    return state


async def generate_initial_story_image_prompts(
    persona: dict,
    state: str,
    story_description: str,
    greeting_text: str
) -> tuple[str, str]:
    """Generate image prompts for initial story using Image Brain"""
    from app.core.brains.image_prompt_engineer import generate_image_plan, assemble_final_prompt
    
    # Build chat history
    chat_history = [
        {"role": "system", "content": story_description},
        {"role": "assistant", "content": greeting_text}
    ]
    
    # Call Image Brain to generate image plan
    print(f"[MINIAPP-SELECT] 🎨 Generating image plan using AI...")
    image_prompt = await generate_image_plan(
        state=state,
        dialogue_response=greeting_text,
        user_message="[INITIAL_STORY_START]",  # Placeholder
        persona=persona,
        chat_history=chat_history,
        previous_image_prompt=None
    )
    
    # Assemble final prompt
    positive, negative = assemble_final_prompt(
        image_prompt,
        persona_image_prompt=persona.get("image_prompt", "")
    )
    
    print(f"[MINIAPP-SELECT] ✅ Image prompts generated (pos: {len(positive)} chars, neg: {len(negative)} chars)")
    return positive, negative


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
    
    # Add user's custom characters FIRST (at the top)
    if user_id:
        with get_db() as db:
            user_personas = crud.get_user_personas(db, user_id)
            # Sort by created_at descending (newest first)
            user_personas.sort(key=lambda p: p.created_at, reverse=True)
            for up in user_personas:
                result.append({
                    "id": str(up.id),
                    "name": up.name,
                    "description": up.description or "",
                    "smallDescription": up.small_description or "Your custom character",
                    "badges": [],
                    "avatar_url": up.avatar_url,
                    "is_custom": True,
                    "owner_user_id": user_id,
                    "has_voice": up.voice_id is not None,
                })
    
    # Then add public personas
    for persona in personas:
        persona_id = persona["id"]
        
        # Use avatar_url as primary image, fallback to first history image from cache
        avatar_url = persona["avatar_url"]
        if not avatar_url:
            history_start = get_random_history(persona_id)
            avatar_url = history_start["image_url"] if history_start else None
        
        # Get translated descriptions and name
        name = get_persona_field(persona, 'name', language=user_language) or persona["name"]
        description = get_persona_field(persona, 'description', language=user_language) or ""
        small_description = get_persona_field(persona, 'small_description', language=user_language) or ""
        
        result.append({
            "id": persona_id,
            "name": name,
            "description": description,
            "smallDescription": small_description,
            "badges": persona["badges"] or [],
            "avatar_url": avatar_url,
            "is_custom": False,
            "has_voice": persona.get("voice_id") is not None,
        })
    
    return result


@router.get("/personas/{persona_id}/active-chat")
async def get_persona_active_chat(
    persona_id: str,
    x_telegram_init_data: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Check if user has an existing chat with this persona
    
    Returns:
    - hasActiveChat: boolean
    - chatId: string (if exists)
    """
    # Validate authentication
    if settings.ENV == "production" and not validate_telegram_webapp_data(x_telegram_init_data or ""):
        raise HTTPException(status_code=403, detail="Invalid Telegram authentication")
    
    # Validate persona_id format
    try:
        from uuid import UUID
        persona_uuid = UUID(persona_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid persona ID format")
    
    # Get user ID
    user_id = extract_user_id_from_init_data(x_telegram_init_data)
    if not user_id:
        return {"hasActiveChat": False, "chatId": None}
    
    # Check for existing chat
    with get_db() as db:
        chat = crud.get_user_chat_with_persona(db, user_id, persona_uuid)
        if chat:
            return {"hasActiveChat": True, "chatId": str(chat.id)}
    
    return {"hasActiveChat": False, "chatId": None}


@router.get("/personas/{persona_id}/histories")
async def get_persona_histories(
    persona_id: str,
    x_telegram_init_data: Optional[str] = Header(None)
) -> List[Dict[str, Any]]:
    """
    Get all history starts for a specific persona
    
    For custom characters: Generates 3 AI stories on first access if none exist
    For preset personas: Returns existing histories from cache
    
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
        persona_uuid = UUID(persona_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid persona ID format")
    
    # Get user ID and language preference
    user_id = extract_user_id_from_init_data(x_telegram_init_data)
    user_language = 'en'
    if user_id:
        with get_db() as db:
            user_language = crud.get_user_language(db, user_id)
    
    # Try to get histories from cache (for preset personas)
    from app.core import persona_cache
    from app.core.persona_cache import get_history_field
    histories = persona_cache.get_persona_histories(persona_id)
    
    # If no cached histories, check if this is a custom character
    if not histories:
        with get_db() as db:
            persona = crud.get_persona_by_id(db, persona_uuid)
            
            # If custom character, check if histories exist in database
            if persona and persona.visibility == "custom":
                db_histories = crud.get_persona_histories(db, persona_uuid)
                
                # Convert DB histories to response format
                result = []
                for h in db_histories:
                    result.append({
                        "id": str(h.id),
                        "name": h.name or "Story",
                        "smallDescription": h.small_description or "",
                        "description": h.description or "",
                        "text": h.text,
                        "image_url": h.image_url,
                        "wide_menu_image_url": h.wide_menu_image_url
                    })
                return result
    
    # Transform cached histories to camelCase for frontend
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
    Get current user's token balance and premium tier
    
    Returns: {
        tokens: int,
        premium_tier: str,
        is_premium: bool,
        can_claim_daily_bonus: bool,
        next_bonus_in_seconds: int,
        daily_bonus_streak: int,
        char_created: bool
    }
    """
    # Validate and extract user ID from init data
    if not x_telegram_init_data:
        return {"tokens": 100, "premium_tier": "free", "is_premium": False, "can_claim_daily_bonus": False, "next_bonus_in_seconds": 86400, "daily_bonus_streak": 0, "char_created": False, "voice_enabled": False}
    
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
            
            # Check and award referral tokens (when user opens miniapp for the first time)
            if user.referred_by_user_id and not user.referral_tokens_awarded:
                success = crud.award_referral_tokens(db, user.referred_by_user_id, user_id)
                if success:
                    print(f"[REFERRAL] 🎉 Awarded 50 tokens to referrer {user.referred_by_user_id} for user {user_id}")
                    # Track referral completion
                    from app.core import analytics_service_tg
                    analytics_service_tg.track_referral_completed(user.referred_by_user_id, user_id, 50)
            
            premium_info = crud.check_user_premium(db, user_id)
            bonus_info = crud.can_claim_daily_bonus(db, user_id)
            
            # Calculate total energy (temp_energy + regular energy)
            total_tokens = (user.temp_energy or 0) + user.energy
            
            # Get voice setting (inverted: voice_buttons_hidden=True means voice_enabled=False)
            # Default to True (hidden) so new users have voice disabled by default
            voice_enabled = not user.settings.get("voice_buttons_hidden", True)
            
            return {
                "tokens": total_tokens,
                "premium_tier": premium_info["tier"],
                "is_premium": premium_info["is_premium"],
                "can_claim_daily_bonus": bonus_info["can_claim"],
                "next_bonus_in_seconds": bonus_info["next_claim_seconds"],
                "daily_bonus_streak": user.daily_bonus_streak or 0,
                "char_created": user.char_created or False,
                "voice_enabled": voice_enabled
            }
    
    except Exception as e:
        print(f"[ENERGY-API] Error: {e}")
        return {"tokens": 100, "premium_tier": "free", "is_premium": False, "can_claim_daily_bonus": False, "next_bonus_in_seconds": 86400, "daily_bonus_streak": 0, "char_created": False, "voice_enabled": False}


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


class UpdateLanguageRequest(BaseModel):
    language: str  # 'en', 'ru'


@router.post("/user/update-language")
async def update_user_language(
    request: UpdateLanguageRequest,
    x_telegram_init_data: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Manually update user's language preference
    
    Returns: {success: bool, language: str}
    """
    # Validate language
    supported_languages = ['en', 'ru']
    if request.language not in supported_languages:
        raise HTTPException(status_code=400, detail=f"Unsupported language: {request.language}")
    
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
            # Force update user's language (manual override from miniapp)
            from app.db.models import User
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user.locale = request.language
                user.locale_manually_set = True  # Mark as manually set - takes priority over Telegram language
                db.commit()
                db.refresh(user)
                print(f"[UPDATE-LANGUAGE-API] ✅ User {user_id} language MANUALLY updated: {user.locale}")
            else:
                # Create user if doesn't exist
                user = crud.get_or_create_user(db, telegram_id=user_id, language_code=request.language)
                user.locale_manually_set = True  # Mark as manually set
                db.commit()
                db.refresh(user)
                print(f"[UPDATE-LANGUAGE-API] ✅ User {user_id} created with language: {request.language}")
            
            return {"success": True, "language": request.language}
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"[UPDATE-LANGUAGE-API] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update language: {str(e)}")


class UpdateVoiceSettingsRequest(BaseModel):
    voice_enabled: bool  # True = show voice buttons, False = hide them


@router.post("/user/update-voice-settings")
async def update_user_voice_settings(
    request: UpdateVoiceSettingsRequest,
    x_telegram_init_data: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Update user's voice button visibility preference
    
    Returns: {success: bool, voice_enabled: bool}
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
            from app.db.models import User
            from sqlalchemy.orm.attributes import flag_modified
            
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            # Update voice_buttons_hidden setting (inverted logic: enabled=True means hidden=False)
            if user.settings is None:
                user.settings = {}
            user.settings["voice_buttons_hidden"] = not request.voice_enabled
            flag_modified(user, "settings")
            db.commit()
            
            print(f"[VOICE-SETTINGS-API] ✅ User {user_id} voice buttons {'enabled' if request.voice_enabled else 'disabled'}")
            
            return {"success": True, "voice_enabled": request.voice_enabled}
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"[VOICE-SETTINGS-API] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update voice settings: {str(e)}")


class SelectScenarioRequest(BaseModel):
    persona_id: str
    history_id: Optional[str] = None
    location: Optional[str] = None  # For custom character location selection
    continue_existing: Optional[bool] = False  # Continue existing chat instead of starting new


class CreateInvoiceRequest(BaseModel):
    product_id: str  # tokens_100, premium_month, etc.


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
    
    # Get persona from cache OR database (for custom characters)
    from app.core.persona_cache import get_persona_by_id as get_cached_persona
    persona = get_cached_persona(str(persona_uuid))
    
    # If not in cache, check database for custom character
    if not persona:
        with get_db() as db:
            db_persona = crud.get_persona_by_id(db, persona_uuid)
            if db_persona:
                # Convert to dict format matching cache
                persona = {
                    "id": str(db_persona.id),
                    "name": db_persona.name,
                    "intro": db_persona.intro or f"Hey! I'm {db_persona.name} 💕",
                    "prompt": db_persona.prompt,
                    "image_prompt": db_persona.image_prompt,
                }
                print(f"[MINIAPP-SELECT] Found custom character: {persona['name']}")
    
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    
    # Return immediately and process in background
    asyncio.create_task(_process_scenario_selection(
        user_id=user_id,
        persona_uuid=persona_uuid,
        history_uuid=history_uuid,
        location=request.location,
        continue_existing=request.continue_existing
    ))
    
    return {
        "success": True,
        "message": "Chat continuation started" if request.continue_existing else "Chat creation started"
    }


async def _process_scenario_selection(
    user_id: int,
    persona_uuid,
    history_uuid: Optional,
    location: Optional[str] = None,
    continue_existing: bool = False
):
    """Background task to process scenario selection"""
    from app.bot.loader import bot
    from app.core.telegram_utils import escape_markdown_v2
    from app.core import redis_queue
    from app.core.persona_cache import get_persona_by_id, get_persona_histories as get_cached_histories
    from app.core.img_runpod import dispatch_image_generation
    from app.core.actions import send_action_repeatedly
    import random
    
    try:
        # Get persona from cache OR database (for custom characters)
        persona = get_persona_by_id(str(persona_uuid))
        
        # If not in cache, check database for custom character
        if not persona:
            with get_db() as db:
                db_persona = crud.get_persona_by_id(db, persona_uuid)
                if db_persona:
                    # Convert to dict format matching cache
                    persona = {
                        "id": str(db_persona.id),
                        "name": db_persona.name,
                        "intro": db_persona.intro or f"Hey! I'm {db_persona.name} 💕",
                        "prompt": db_persona.prompt,
                        "image_prompt": db_persona.image_prompt,
                    }
                    print(f"[MINIAPP-SELECT] Found custom character: {persona['name']}")
        
        if not persona:
            print(f"[MINIAPP-SELECT] ❌ Persona {persona_uuid} not found")
            return
        
        persona_intro = persona["intro"]
        
        # Get user's language for translations
        with get_db() as db:
            user_language = crud.get_user_language(db, user_id)
        
        # Get persona name (custom characters don't have translations)
        from app.core.persona_cache import get_persona_field
        persona_name = persona["name"]  # Use name directly for custom characters
        # Try to get translated name only if it's a cached persona
        try:
            translated_name = get_persona_field(persona, 'name', language=user_language)
            if translated_name:
                persona_name = translated_name
        except:
            pass  # Custom character, no translation available
        
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
            
            # Handle continue_existing - just activate the chat without creating new one
            if continue_existing and existing_chat:
                print(f"[MINIAPP-SELECT] ▶️  Continuing existing chat {existing_chat.id}")
                crud.activate_chat(db, existing_chat.id, user_id)
                
                # Send "returned to chat" message
                from app.bot.loader import bot
                from app.settings import get_ui_text
                
                user_language = crud.get_user_language(db, user_id)
                
                # Get persona name
                db_persona = crud.get_persona_by_id(db, persona_uuid)
                persona_name_for_msg = db_persona.name if db_persona else "Unknown"
                
                # Send notification message
                return_text = get_ui_text("system.returned_to_chat", language=user_language)
                return_text = return_text.replace("{name}", persona_name_for_msg)
                
                try:
                    await bot.send_message(
                        chat_id=user_id,
                        text=return_text
                    )
                    print(f"[MINIAPP-SELECT] 📨 Sent 'returned to chat' message for {persona_name_for_msg}")
                except Exception as e:
                    print(f"[MINIAPP-SELECT] ⚠️ Failed to send return message: {e}")
                
                return
            
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
        
        # Clear Redis queue and processing lock (with error handling for Redis issues)
        try:
            await redis_queue.clear_batch_messages(chat_id)
            await redis_queue.set_processing_lock(chat_id, False)
            print(f"[MINIAPP-SELECT] ✅ Redis queue cleared for chat {chat_id}")
        except Exception as redis_error:
            print(f"[MINIAPP-SELECT] ⚠️  Redis error (continuing anyway): {redis_error}")
            # Continue even if Redis fails - the messages can still be sent
        
        # Get specific history from cache (preset personas) or database (custom characters)
        history_start = None
        is_custom_character_story = False
        
        if history_uuid:
            # Try cache first (for preset personas)
            histories = get_cached_histories(str(persona_uuid))
            for h in histories:
                if h["id"] == str(history_uuid):
                    history_start = h
                    print(f"[MINIAPP-SELECT] Found preset persona story from cache: {h.get('name', 'Unknown')}")
                    break
            
            # If not in cache, check database (for custom characters)
            if not history_start:
                with get_db() as db:
                    from app.db.models import PersonaHistoryStart
                    db_history = db.query(PersonaHistoryStart).filter(
                        PersonaHistoryStart.id == history_uuid
                    ).first()
                    
                    if db_history:
                        is_custom_character_story = True
                        # Convert to dict format matching cache
                        history_start = {
                            "id": str(db_history.id),
                            "name": db_history.name,
                            "small_description": db_history.small_description,
                            "description": db_history.description,
                            "text": db_history.text,
                            "image_url": db_history.image_url,
                            "wide_menu_image_url": db_history.wide_menu_image_url,
                            "image_prompt": db_history.image_prompt
                        }
                        print(f"[MINIAPP-SELECT] Found custom character story from DB: {db_history.name}")
                    else:
                        print(f"[MINIAPP-SELECT] ⚠️  History {history_uuid} not found in cache or database")
        else:
            # No history selected - check if location provided
            if location:
                # Generate location-specific greeting for custom character
                print(f"[MINIAPP-SELECT] 📍 Generating location-specific greeting for: {location}")
                
                # Location-specific greeting templates
                location_greetings = {
                    "home": {
                        "en": f"You arrive at {persona_name}'s cozy home. She opens the door with a warm smile, inviting you inside.",
                        "ru": f"Вы приходите в уютный дом {persona_name}. Она открывает дверь с теплой улыбкой, приглашая вас внутрь."
                    },
                    "office": {
                        "en": f"You step into {persona_name}'s modern office. She looks up from her desk with a professional smile.",
                        "ru": f"Вы входите в современный офис {persona_name}. Она поднимает взгляд от стола с профессиональной улыбкой."
                    },
                    "school": {
                        "en": f"You meet {persona_name} in the school hallway. She approaches you with an enthusiastic wave.",
                        "ru": f"Вы встречаете {persona_name} в школьном коридоре. Она подходит к вам с восторженным приветствием."
                    },
                    "cafe": {
                        "en": f"You walk into a cozy cafe and spot {persona_name} sitting at a corner table, sipping her drink.",
                        "ru": f"Вы заходите в уютное кафе и замечаете {persona_name}, сидящую за столиком в углу и потягивающую напиток."
                    },
                    "gym": {
                        "en": f"You enter the gym and see {persona_name} working out, her athletic form glistening with effort.",
                        "ru": f"Вы заходите в спортзал и видите {persona_name}, занимающуюся тренировкой, её атлетичная фигура блестит от усилий."
                    },
                    "park": {
                        "en": f"You stroll through a beautiful park and find {persona_name} enjoying the fresh air and sunshine.",
                        "ru": f"Вы прогуливаетесь по красивому парку и находите {persona_name}, наслаждающуюся свежим воздухом и солнцем."
                    }
                }
                
                # Get location-specific greeting in user's language
                if location in location_greetings:
                    greeting_templates = location_greetings[location]
                    location_greeting = greeting_templates.get(user_language, greeting_templates["en"])
                    
                    # Create a pseudo-history for location scenario
                    # Note: image_prompt will be generated by AI pipeline later
                    history_start = {
                        "id": None,
                        "name": f"{location.capitalize()} Scenario",
                        "text": location_greeting,
                        "description": f"A scenario set in a {location}",
                        "image_url": None,
                        "image_prompt": None  # Will be generated by AI pipeline
                    }
                    
                    print(f"[MINIAPP-SELECT] ✅ Generated location greeting: {location_greeting[:100]}...")
                else:
                    print(f"[MINIAPP-SELECT] ⚠️  Unknown location: {location}, using default intro")
            else:
                print(f"[MINIAPP-SELECT] ℹ️  No history selected, using persona intro")
        
        # Get translated texts using persona_cache helpers
        from app.core.persona_cache import get_history_field, get_persona_field
        
        history_start_data = None
        description_text = None
        if history_start:
            # Handle preset vs custom character stories differently
            if is_custom_character_story:
                # Custom character - use direct values (no translations)
                translated_text = history_start["text"]
                translated_description = history_start.get("description", "")
                print(f"[MINIAPP-SELECT] Using custom character story text directly (no translation)")
            else:
                # Preset persona - get translated text
                translated_text = get_history_field(history_start, 'text', language=user_language) or history_start["text"]
                translated_description = get_history_field(history_start, 'description', language=user_language) or history_start["description"]
                print(f"[MINIAPP-SELECT] Using translated preset persona story for language: {user_language}")
            
            history_start_data = {
                "text": translated_text,
                "image_url": history_start.get("image_url"),
                "image_prompt": history_start.get("image_prompt")
            }
            description_text = translated_description
        
        with get_db() as db:
            
            # Determine greeting text (use translated version)
            if history_start_data:
                greeting_text = history_start_data['text']
            else:
                # Get translated persona intro (only for cached personas)
                greeting_text = persona_intro
                try:
                    translated_intro = get_persona_field(persona, 'intro', language=user_language)
                    if translated_intro:
                        greeting_text = translated_intro
                except:
                    pass  # Custom character, no translation
                
                # Fallback if no intro exists
                if not greeting_text:
                    greeting_text = f"Hi! I'm {persona_name}. Let's chat!"
            
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
            
            # Create initial ImageJob for continuity
            job_id = None
            should_generate_image = False
            
            if history_start_data and history_start_data.get("image_url"):
                # For preset personas with existing images, use them
                # Check if this is a custom character by checking if it has owner_user_id
                if persona.get("image_prompt"):
                    with get_db() as db:
                        db_persona = crud.get_persona_by_id(db, persona_uuid)
                        if db_persona and db_persona.owner_user_id is not None:
                            should_generate_image = True
                
                if not should_generate_image:
                    print("[MINIAPP-SELECT] 🎨 Using preset persona image for visual continuity")
                    crud.create_initial_image_job(
                        db,
                        user_id=user_id,
                        persona_id=str(persona_uuid),
                        chat_id=chat_id,
                        prompt=history_start_data.get("image_prompt", ""),
                        result_url=history_start_data.get("image_url")
                    )
            
            # For custom characters, mark for AI image generation (but don't run it yet)
            if persona.get("image_prompt") and description_text:
                with get_db() as db:
                    db_persona = crud.get_persona_by_id(db, persona_uuid)
                    if db_persona and db_persona.owner_user_id is not None:
                        should_generate_image = True
                        print(f"[MINIAPP-SELECT] 🎨 Custom character detected - will use AI pipeline for image")
        
        # Determine if this is a custom location scenario vs public persona story
        is_location_scenario = location is not None and history_uuid is None
        
        # Send messages to user FIRST (before AI pipeline)
        # Send hint message FIRST (before story starts)
        from app.settings import get_ui_text
        hint_text = get_ui_text("hints.restart", language=user_language)
        await bot.send_message(
            chat_id=user_id,
            text=escape_markdown_v2(hint_text),
            parse_mode="MarkdownV2"
        )
        
        # Wait 1 second before sending next message
        import asyncio
        await asyncio.sleep(1)
        
        # Send description if exists
        if description_text:
            escaped_description = escape_markdown_v2(description_text)
            formatted_description = f"_{escaped_description}_"
            await bot.send_message(
                chat_id=user_id,
                text=formatted_description,
                parse_mode="MarkdownV2"
            )
        
        # For custom location scenarios, send greeting text immediately (don't wait for image)
        # For public persona stories, wait 3 seconds then send greeting
        if is_location_scenario:
            # Send greeting text immediately for location scenarios
            escaped_greeting = escape_markdown_v2(greeting_text)
            await bot.send_message(
                chat_id=user_id,
                text=escaped_greeting,
                parse_mode="MarkdownV2"
            )
        else:
            # Wait 3 seconds before sending greeting/image for public stories
            await asyncio.sleep(3)
            
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
        
        # NOW run AI pipeline for custom characters (after messages are sent)
        if should_generate_image and description_text:
            print("[MINIAPP-SELECT] 🤖 Starting AI pipeline to generate initial image (after messages sent)")
            
            # Step 1: Generate initial state from story description
            initial_state = await generate_initial_state_for_story(
                persona_name=persona_name,
                story_description=description_text,
                greeting_text=greeting_text
            )
            
            # Step 2: Generate image prompts using Image Brain
            positive_prompt, negative_prompt = await generate_initial_story_image_prompts(
                persona=persona,
                state=initial_state,
                story_description=description_text,
                greeting_text=greeting_text
            )
            
            # Step 3: Create image job with AI-generated prompts
            seed = random.randint(1, 2147483647)
            job_ext = {"seed": seed, "source": "ai_initial_story"}
            
            with get_db() as db:
                job = crud.create_image_job(
                    db,
                    user_id=user_id,
                    persona_id=persona_uuid,
                    prompt=positive_prompt,
                    negative_prompt=negative_prompt,
                    chat_id=chat_id,
                    ext=job_ext
                )
                job_id = job.id
                print(f"[MINIAPP-SELECT] 📋 Created AI-generated image job {job_id}")
                
                # Step 4: Save initial state to chat
                crud.update_chat_state(db, chat_id, {"state": initial_state})
                print(f"[MINIAPP-SELECT] ✅ Saved initial state to chat")
        
        # Dispatch image generation for custom characters immediately
        if job_id:
            print(f"[MINIAPP-SELECT] 🚀 Dispatching image generation for job {job_id}")
            
            # Increment user image count
            await redis_queue.increment_user_image_count(user_id)
            print(f"[MINIAPP-SELECT] 📊 Incremented user image count")
            
            # Check if user is premium for priority
            with get_db() as db:
                is_premium = crud.check_user_premium(db, user_id)["is_premium"]
                from app.db.models import User
                user = db.query(User).filter(User.id == user_id).first()
                global_message_count = user.global_message_count if user else 999
            
            # Determine priority
            if is_premium:
                queue_priority = "high"
                priority_reason = "premium user"
            elif global_message_count <= 2:
                queue_priority = "high"
                priority_reason = f"first 2 messages globally (count: {global_message_count})"
            else:
                queue_priority = "medium"
                priority_reason = "regular user message"
            
            print(f"[MINIAPP-SELECT] 📊 Queue priority: {queue_priority} ({priority_reason})")
            
            # Get job details
            with get_db() as db:
                job = crud.get_image_job(db, job_id)
                if not job:
                    print(f"[MINIAPP-SELECT] ⚠️ Job {job_id} not found!")
                    await redis_queue.decrement_user_image_count(user_id)
                    return
                positive_prompt = job.prompt
                negative_prompt = job.negative_prompt
            
            # Show upload_photo status and dispatch to Runpod
            try:
                async with send_action_repeatedly(bot, user_id, "upload_photo"):
                    success = await dispatch_image_generation(
                        job_id=job_id,
                        prompt=positive_prompt,
                        negative_prompt=negative_prompt,
                        tg_chat_id=user_id,
                        queue_priority=queue_priority
                    )
                    
                    if success:
                        print(f"[MINIAPP-SELECT] ✅ Image generation dispatched successfully")
                    else:
                        print(f"[MINIAPP-SELECT] ⚠️ Image generation dispatch failed")
                        # Decrement counter on failure
                        await redis_queue.decrement_user_image_count(user_id)
            except Exception as e:
                print(f"[MINIAPP-SELECT] ❌ Error dispatching image: {e}")
                # Decrement counter on error
                await redis_queue.decrement_user_image_count(user_id)
        
        print(f"[MINIAPP-SELECT] ✅ Created chat and sent greeting for persona {persona_name}")
    
    except Exception as e:
        print(f"[MINIAPP-SELECT] ❌ Error in background processing: {e}")


@router.post("/create-invoice")
async def create_invoice(
    request: CreateInvoiceRequest,
    x_telegram_init_data: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Create a Telegram Stars invoice for token package or tier subscription
    
    When SIMULATE_PAYMENTS=True: Processes payment immediately without creating invoice
    When SIMULATE_PAYMENTS=False: Creates real Telegram Stars invoice link
    
    Returns: {invoice_link: str} OR {success: bool, simulated: bool, ...}
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
    
    # Get payment products from payment handler
    from app.bot.handlers.payment import PAYMENT_PRODUCTS, process_payment_transaction
    
    product = PAYMENT_PRODUCTS.get(request.product_id)
    if not product:
        raise HTTPException(status_code=400, detail="Invalid product ID")
    
    # Track payment initiation
    from app.core import analytics_service_tg
    analytics_service_tg.track_payment_initiated(
        user_id,
        request.product_id,
        product["stars"],
        product["type"]
    )
    
    # SIMULATE PAYMENTS: Process immediately without creating invoice
    if settings.SIMULATE_PAYMENTS:
        print(f"[SIMULATED-PAYMENT] 💳 Processing simulated payment for user {user_id}, product: {request.product_id}")
        
        with get_db() as db:
            result = process_payment_transaction(
                db,
                user_id,
                request.product_id,
                telegram_payment_charge_id=None  # No real payment charge
            )
            
            if result["success"]:
                print(f"[SIMULATED-PAYMENT] ✅ Simulated payment successful for user {user_id}")
                return {
                    "success": True,
                    "simulated": True,
                    "message": result["message"],
                    "tokens": result.get("tokens"),
                    "tier": result.get("tier"),
                    "premium_until": result.get("premium_until")
                }
            else:
                print(f"[SIMULATED-PAYMENT] ❌ Simulated payment failed for user {user_id}: {result.get('error')}")
                raise HTTPException(status_code=400, detail=result["message"])
    
    # REAL PAYMENT: Create Telegram Stars invoice
    # Import bot and types
    from app.bot.loader import bot
    from aiogram.types import LabeledPrice
    
    try:
        # Build title and description based on product type
        if product["type"] == "tokens":
            title = f"{product['amount']} Tokens"
            description = f"Purchase {product['amount']} tokens"
            label = f"{product['amount']} tokens"
        else:  # tier subscription
            tier_names = {
                "plus": "Plus",
                "premium": "Premium",
                "pro": "Pro",
                "legendary": "Legendary"
            }
            tier_display = tier_names.get(product["tier"], product["tier"].capitalize())
            title = f"{tier_display} - {product['duration']} days"
            description = f"{tier_display} tier subscription (+{product['daily_tokens']} tokens daily)"
            label = f"{tier_display} {product['duration']} days"
        
        # Create invoice using Telegram Bot API
        # For Stars payment, provider_token should be empty string
        invoice_link = await bot.create_invoice_link(
            title=title,
            description=description,
            payload=request.product_id,  # This will be sent back in successful_payment
            provider_token="",  # Empty for Telegram Stars
            currency="XTR",  # XTR = Telegram Stars
            prices=[LabeledPrice(label=label, amount=product["stars"])]
        )
        
        print(f"[INVOICE-API] Created invoice for user {user_id}, product {request.product_id}: {invoice_link}")
        
        return {"invoice_link": invoice_link}
    
    except Exception as e:
        print(f"[INVOICE-API] Error creating invoice: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create invoice: {str(e)}")


@router.post("/claim-daily-bonus")
async def claim_daily_bonus(
    x_telegram_init_data: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Claim daily bonus (10 tokens)
    
    Returns: {success: bool, tokens: int, message: str}
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
            result = crud.claim_daily_bonus(db, user_id)
            
            if result["success"]:
                # Track the claim
                from app.core import analytics_service_tg
                analytics_service_tg.track_daily_bonus_claimed(user_id, 10)
            
            return result
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"[DAILY-BONUS-API] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to claim bonus: {str(e)}")


@router.get("/can-claim-daily-bonus")
async def can_claim_daily_bonus_endpoint(
    x_telegram_init_data: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Check if user can claim daily bonus
    
    Returns: {can_claim: bool, next_claim_seconds: int}
    """
    # Validate and extract user ID from init data
    if not x_telegram_init_data:
        return {"can_claim": False, "next_claim_seconds": 86400}
    
    try:
        # Parse init data to get user ID
        parsed = dict(parse_qsl(x_telegram_init_data))
        import json
        user_data = json.loads(parsed.get('user', '{}'))
        user_id = user_data.get('id')
        
        if not user_id:
            raise HTTPException(status_code=400, detail="User ID not found in init data")
        
        with get_db() as db:
            result = crud.can_claim_daily_bonus(db, user_id)
            return result
    
    except Exception as e:
        print(f"[CAN-CLAIM-BONUS-API] Error: {e}")
        return {"can_claim": False, "next_claim_seconds": 86400}


class TrackEventRequest(BaseModel):
    event_name: str
    metadata: Optional[Dict[str, Any]] = None


@router.post("/track-event")
async def track_event(
    request: TrackEventRequest,
    x_telegram_init_data: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Track analytics event from mini app
    
    Returns: {success: bool}
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
        
        # Track the event
        from app.core import analytics_service_tg
        
        if request.event_name == "miniapp_opened":
            analytics_service_tg.track_miniapp_opened(user_id)
        elif request.event_name == "plans_page_viewed":
            analytics_service_tg.track_plans_page_viewed(user_id)
        elif request.event_name == "payment_initiated":
            meta = request.metadata or {}
            analytics_service_tg.track_payment_initiated(
                user_id,
                meta.get("product_id", ""),
                meta.get("amount_stars", 0),
                meta.get("transaction_type", "")
            )
        else:
            # Generic event tracking
            from app.db import crud
            with get_db() as db:
                crud.create_analytics_event(
                    db=db,
                    client_id=user_id,
                    event_name=request.event_name,
                    meta=request.metadata or {}
                )
        
        return {"success": True}
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"[TRACK-EVENT-API] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to track event: {str(e)}")


@router.get("/user/referrals")
async def get_user_referrals(
    x_telegram_init_data: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Get user's referral statistics
    
    Returns: {
        referrals_count: int,
        bot_username: str
    }
    """
    if not x_telegram_init_data:
        raise HTTPException(status_code=401, detail="Telegram init data required")
    
    try:
        # Parse init data to get user ID
        parsed = dict(parse_qsl(x_telegram_init_data))
        import json
        user_data = json.loads(parsed.get('user', '{}'))
        user_id = user_data.get('id')
        
        if not user_id:
            raise HTTPException(status_code=400, detail="User ID not found in init data")
        
        with get_db() as db:
            # Count users referred by this user who have been awarded tokens (activated)
            from app.db.models import User
            referrals_count = db.query(User).filter(
                User.referred_by_user_id == user_id,
                User.referral_tokens_awarded == True
            ).count()
            
            # Get bot username from bot instance
            from app.bot.loader import bot
            bot_user = await bot.get_me()
            bot_username = bot_user.username or "bot"
            
            return {
                "referrals_count": referrals_count,
                "bot_username": bot_username
            }
    except Exception as e:
        print(f"[REFERRALS-API] Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch referral data")

class GenerateStoriesRequest(BaseModel):
    name: str
    hair_color: str
    hair_style: str
    eye_color: str
    body_type: str
    extra_prompt: str


class CreateCharacterRequest(BaseModel):
    name: str
    race_type: str = "european"
    hair_color: str
    hair_style: str
    eye_color: str
    body_type: str
    breast_size: str
    butt_size: str
    extra_prompt: str
    voice_id: Optional[str] = None  # ElevenLabs voice ID for custom voice


class CreateCustomStoryRequest(BaseModel):
    persona_id: str
    story_description: str


@router.post("/generate-stories")
async def generate_stories(
    request: GenerateStoriesRequest,
    x_telegram_init_data: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Generate 3 AI story scenarios for a custom character (free, no token cost)
    
    Returns: {success: bool, stories: List[Dict], error: str}
    """
    # Validate authentication
    if settings.ENV == "production" and not validate_telegram_webapp_data(x_telegram_init_data or ""):
        raise HTTPException(status_code=403, detail="Invalid Telegram authentication")
    
    # Extract user_id
    user_id = extract_user_id_from_init_data(x_telegram_init_data)
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID not found")
    
    try:
        from app.core.story_generator import generate_character_stories
        
        print(f"[GENERATE-STORIES] Generating stories for {request.name} (user {user_id})")
        
        # Generate stories using AI
        stories = await generate_character_stories(
            name=request.name,
            personality_description=request.extra_prompt,
            hair_color=request.hair_color,
            hair_style=request.hair_style,
            eye_color=request.eye_color,
            body_type=request.body_type,
            user_id=user_id
        )
        
        print(f"[GENERATE-STORIES] Generated {len(stories)} stories")
        
        return {
            "success": True,
            "stories": stories
        }
    
    except Exception as e:
        print(f"[GENERATE-STORIES] Error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": "generation_failed",
            "message": "Failed to generate stories. Please try again or enter your own."
        }


@router.post("/create-character")
async def create_character(
    request: CreateCharacterRequest,
    x_telegram_init_data: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Create a custom character (costs 50 tokens for regular users, 25 for premium)
    
    Returns: {success: bool, persona_id: str, message: str, error: str}
    """
    # Validate authentication
    if settings.ENV == "production" and not validate_telegram_webapp_data(x_telegram_init_data or ""):
        raise HTTPException(status_code=403, detail="Invalid Telegram authentication")
    
    # Extract user_id
    user_id = extract_user_id_from_init_data(x_telegram_init_data)
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID not found")
    
    # Import character builder
    from app.core.character_builder import (
        build_character_dna,
        build_dialogue_prompt,
        validate_attributes
    )
    
    try:
        with get_db() as db:
            # Get user to check if first character creation
            user = crud.get_user(db, user_id)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            # Check if this is the first character creation (free!)
            is_first_character = not user.char_created
            
            # Check premium status to determine cost
            premium_info = crud.check_user_premium(db, user_id)
            is_premium = premium_info["is_premium"]
            is_legendary = premium_info["tier"] == "legendary"
            
            # Base cost
            base_cost = 0 if is_first_character else (25 if is_premium else 50)
            
            # Fantasy race cost (250 extra, free for Legendary)
            fantasy_races = ["elf", "catgirl", "succubus"]
            is_fantasy_race = request.race_type in fantasy_races
            fantasy_cost = 250 if (is_fantasy_race and not is_legendary) else 0
            
            token_cost = base_cost + fantasy_cost
            max_description_length = 4000 if is_premium else 500
            
            print(f"[CREATE-CHARACTER] User {user_id}: first_char={is_first_character}, race={request.race_type}, fantasy={is_fantasy_race}, legendary={is_legendary}, cost={token_cost}")
            
            # Validate name length
            if not request.name or len(request.name) > 100:
                return {
                    "success": False,
                    "error": "invalid_name",
                    "message": "Name must be between 1 and 100 characters"
                }
            
            # Validate extra_prompt length
            if not request.extra_prompt or len(request.extra_prompt) > max_description_length:
                return {
                    "success": False,
                    "error": "invalid_description",
                    "message": f"Description must be between 1 and {max_description_length} characters"
                }
            
            # Validate attribute choices
            is_valid, error_field = validate_attributes(
                request.hair_color,
                request.hair_style,
                request.eye_color,
                request.body_type,
                request.breast_size,
                request.butt_size,
                request.race_type
            )
            
            if not is_valid:
                return {
                    "success": False,
                    "error": "invalid_attribute",
                    "field": error_field,
                    "message": f"Invalid value for {error_field}"
                }
            
            # Handle token deduction
            if token_cost > 0:
                # Check token balance
                if not crud.check_user_energy(db, user_id, required=token_cost):
                    user_energy = crud.get_user_energy(db, user_id)
                    return {
                        "success": False,
                        "error": "insufficient_tokens",
                        "required": token_cost,
                        "current": user_energy["tokens"],
                        "message": f"Insufficient tokens. Need {token_cost}, have {user_energy['tokens']}"
                    }
                
                # Deduct tokens
                if not crud.deduct_user_energy(db, user_id, amount=token_cost):
                    return {
                        "success": False,
                        "error": "deduction_failed",
                        "message": "Failed to deduct tokens"
                    }
                
                print(f"[CREATE-CHARACTER] Deducted {token_cost} tokens from user {user_id}")
            
            # Mark first character creation
            if is_first_character:
                print(f"[CREATE-CHARACTER] First character creation for user {user_id}")
                user.char_created = True
                db.commit()
            
            # Build character DNA with extra_prompt for visual detail extraction
            character_dna = build_character_dna(
                request.hair_color,
                request.hair_style,
                request.eye_color,
                request.body_type,
                request.breast_size,
                request.butt_size,
                request.extra_prompt,  # Pass user's description for visual parsing
                request.race_type
            )
            
            dialogue_prompt = build_dialogue_prompt(request.name, request.extra_prompt)
            
            print(f"[CREATE-CHARACTER] Built DNA ({len(character_dna)} chars) and dialogue prompt ({len(dialogue_prompt)} chars)")
            
            # Create persona in database
            persona = crud.create_persona(
                db,
                name=request.name,
                prompt=dialogue_prompt,
                badges=[],
                visibility="custom",
                description=request.extra_prompt[:200],  # First 200 chars for preview
                intro=f"Hey! I'm {request.name} 💕",
                owner_user_id=user_id,
                key=None
            )
            
            # Update with additional fields (image_prompt, small_description, emoji, voice_id)
            persona = crud.update_persona(
                db,
                persona.id,
                image_prompt=character_dna,
                small_description="Your custom character",
                emoji="💝",
                voice_id=request.voice_id  # Custom voice selection
            )
            
            print(f"[CREATE-CHARACTER] Created persona {persona.id} for user {user_id}")
            
            # Generate initial portrait image (high priority, NOT sent to chat)
            from app.core.pipeline_adapter import BASE_QUALITY_PROMPT, BASE_NEGATIVE_PROMPT
            from app.core.img_runpod import submit_image_job
            import random
            
            # Build first image prompt - standing in white room with lingerie
            first_image_composition = (
                "standing in white room, wearing white lingerie, "
                "portrait shot, head and shoulders framing, face clearly visible, "
                "(upper body:1.2), (face focus:1.3), looking at camera, confident expression, "
                "soft studio lighting, clean white background, "
                "professional photography"
            )
            
            # Assemble full prompt: composition + character DNA + quality
            first_image_prompt = f"{first_image_composition}, {character_dna}, {BASE_QUALITY_PROMPT}"
            
            # Enhanced negative prompt - prevent body-only images
            first_image_negative = (
                BASE_NEGATIVE_PROMPT + 
                ", cropped face, face out of frame, no face visible, face cropped off, "
                "(body only:1.4), (no head:1.4), headless body, torso only, "
                "face cut off, partial face, incomplete face"
            )
            
            # Create image job in database with special flag to NOT send to chat
            job = crud.create_image_job(
                db,
                user_id=user_id,
                persona_id=persona.id,
                prompt=first_image_prompt,
                negative_prompt=first_image_negative,
                chat_id=None  # No chat yet
            )
            
            # Add special flag to ext to indicate this is a character creation image
            # that should NOT be sent to the user's chat
            from sqlalchemy.orm.attributes import flag_modified
            if not job.ext:
                job.ext = {}
            job.ext["skip_chat_send"] = True
            flag_modified(job, "ext")
            db.commit()
            
            job_id = job.id
            
            print(f"[CREATE-CHARACTER] Created image job {job_id} (skip_chat_send=True)")
            print(f"[CREATE-CHARACTER] First image prompt: {first_image_prompt[:200]}...")
            
            # Submit to Runpod with HIGH priority
            try:
                await submit_image_job(
                    job_id=job_id,
                    prompt=first_image_prompt,
                    negative_prompt=first_image_negative,
                    seed=random.randint(0, 2147483647),
                    queue_priority="high"  # Changed from medium to high
                )
                print(f"[CREATE-CHARACTER] Submitted HIGH priority image job to Runpod")
            except Exception as img_error:
                print(f"[CREATE-CHARACTER] Warning: Image generation failed: {img_error}")
                # Continue anyway - character is created, image can be generated later
            
            return {
                "success": True,
                "persona_id": str(persona.id),
                "message": f"{request.name} created successfully! Portrait is being generated.",
                "tokens_spent": token_cost
            }
    
    except Exception as e:
        print(f"[CREATE-CHARACTER] Error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": "server_error",
            "message": "An unexpected error occurred. Please try again."
        }


@router.delete("/characters/{persona_id}")
async def delete_character(
    persona_id: str,
    x_telegram_init_data: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Delete a custom character (only owner can delete)
    
    Returns: {success: bool, message: str}
    """
    # Validate authentication
    if settings.ENV == "production" and not validate_telegram_webapp_data(x_telegram_init_data or ""):
        raise HTTPException(status_code=403, detail="Invalid Telegram authentication")
    
    # Extract user_id
    user_id = extract_user_id_from_init_data(x_telegram_init_data)
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID not found")
    
    try:
        from uuid import UUID
        persona_uuid = UUID(persona_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid persona ID format")
    
    try:
        with get_db() as db:
            # Get persona
            persona = crud.get_persona_by_id(db, persona_uuid)
            if not persona:
                raise HTTPException(status_code=404, detail="Character not found")
            
            # Verify ownership
            if persona.owner_user_id != user_id:
                raise HTTPException(status_code=403, detail="You can only delete your own characters")
            
            # Delete persona (cascade will delete chats, messages, image_jobs)
            crud.delete_persona(db, persona_uuid)
            
            print(f"[DELETE-CHARACTER] Deleted persona {persona_id} for user {user_id}")
            
            return {
                "success": True,
                "message": f"{persona.name} deleted successfully"
            }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"[REFERRALS-API] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get referral stats: {str(e)}")


@router.post("/create-custom-story")
async def create_custom_story(
    request: CreateCustomStoryRequest,
    x_telegram_init_data: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Create a custom story for a custom character
    
    Args:
        persona_id: ID of the custom character
        story_description: User's custom story description (min 5 chars)
    
    Returns: {success: bool, history_id: str, message: str}
    """
    # Validate authentication
    if settings.ENV == "production" and not validate_telegram_webapp_data(x_telegram_init_data or ""):
        raise HTTPException(status_code=403, detail="Invalid Telegram authentication")
    
    # Extract user_id
    user_id = extract_user_id_from_init_data(x_telegram_init_data)
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID not found")
    
    # Validate story description
    if not request.story_description or len(request.story_description) < 5:
        return {
            "success": False,
            "error": "story_too_short",
            "message": "Story description must be at least 5 characters"
        }
    
    try:
        from uuid import UUID
        persona_uuid = UUID(request.persona_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid persona ID format")
    
    try:
        with get_db() as db:
            # Get persona and verify ownership
            persona = crud.get_persona_by_id(db, persona_uuid)
            if not persona:
                return {
                    "success": False,
                    "error": "persona_not_found",
                    "message": "Character not found"
                }
            
            if persona.owner_user_id != user_id:
                return {
                    "success": False,
                    "error": "not_owner",
                    "message": "You can only create stories for your own characters"
                }
            
            # Create persona history start
            from app.db.models import PersonaHistoryStart
            from uuid import uuid4
            
            history = PersonaHistoryStart(
                id=uuid4(),
                persona_id=persona_uuid,
                name="Custom Story",
                description=request.story_description[:200],  # First 200 chars
                text=f"*{persona.name} enters the scene...*\n\n{request.story_description[:500]}",
                small_description="Your custom story"
            )
            
            db.add(history)
            db.commit()
            db.refresh(history)
            
            print(f"[CREATE-CUSTOM-STORY] Created story {history.id} for persona {persona_uuid} by user {user_id}")
            
            return {
                "success": True,
                "history_id": str(history.id),
                "message": "Custom story created successfully"
            }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"[CREATE-CUSTOM-STORY] Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to create custom story: {str(e)}")


@router.get("/health")
async def health():
    """Health check for Mini App API"""
    return {"status": "ok", "service": "miniapp-api"}


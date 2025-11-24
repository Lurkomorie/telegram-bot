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
    Get current user's token balance and premium tier
    
    Returns: {
        tokens: int,
        premium_tier: str,
        is_premium: bool,
        can_claim_daily_bonus: bool,
        next_bonus_in_seconds: int,
        daily_bonus_streak: int
    }
    """
    # Validate and extract user ID from init data
    if not x_telegram_init_data:
        return {"tokens": 100, "premium_tier": "free", "is_premium": False, "can_claim_daily_bonus": False, "next_bonus_in_seconds": 86400, "daily_bonus_streak": 0}
    
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
            
            return {
                "tokens": user.energy,
                "premium_tier": premium_info["tier"],
                "is_premium": premium_info["is_premium"],
                "can_claim_daily_bonus": bonus_info["can_claim"],
                "next_bonus_in_seconds": bonus_info["next_claim_seconds"],
                "daily_bonus_streak": user.daily_bonus_streak or 0
            }
    
    except Exception as e:
        print(f"[ENERGY-API] Error: {e}")
        return {"tokens": 100, "premium_tier": "free", "is_premium": False, "can_claim_daily_bonus": False, "next_bonus_in_seconds": 86400, "daily_bonus_streak": 0}


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


class SelectScenarioRequest(BaseModel):
    persona_id: str
    history_id: Optional[str] = None


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
        
        persona_intro = persona["intro"]
        
        # Get user's language for translations
        with get_db() as db:
            user_language = crud.get_user_language(db, user_id)
        
        # Get translated persona name
        from app.core.persona_cache import get_persona_field
        persona_name = get_persona_field(persona, 'name', language=user_language) or persona["name"]
        
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
        
        # Clear Redis queue and processing lock (with error handling for Redis issues)
        try:
            await redis_queue.clear_batch_messages(chat_id)
            await redis_queue.set_processing_lock(chat_id, False)
            print(f"[MINIAPP-SELECT] ✅ Redis queue cleared for chat {chat_id}")
        except Exception as redis_error:
            print(f"[MINIAPP-SELECT] ⚠️  Redis error (continuing anyway): {redis_error}")
            # Continue even if Redis fails - the messages can still be sent
        
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
        
        # Get translated texts using persona_cache helpers
        from app.core.persona_cache import get_history_field, get_persona_field
        
        history_start_data = None
        description_text = None
        if history_start:
            # Get translated history text and description
            translated_text = get_history_field(history_start, 'text', language=user_language) or history_start["text"]
            translated_description = get_history_field(history_start, 'description', language=user_language) or history_start["description"]
            
            history_start_data = {
                "text": translated_text,
                "image_url": history_start["image_url"],
                "image_prompt": history_start.get("image_prompt")
            }
            description_text = translated_description
        
        with get_db() as db:
            
            # Determine greeting text (use translated version)
            if history_start_data:
                greeting_text = history_start_data['text']
            else:
                # Get translated persona intro
                translated_intro = get_persona_field(persona, 'intro', language=user_language) or persona_intro
                greeting_text = translated_intro or f"Hi! I'm {persona_name}. Let's chat!"
            
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
    Create a Telegram Stars invoice for token package or tier subscription
    
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
    
    # Get payment products from payment handler
    from app.bot.handlers.payment import PAYMENT_PRODUCTS
    
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
            
            # Get bot username from settings
            bot_username = settings.BOT_NAME
            
            return {
                "referrals_count": referrals_count,
                "bot_username": bot_username
            }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"[REFERRALS-API] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get referral stats: {str(e)}")


@router.get("/health")
async def health():
    """Health check for Mini App API"""
    return {"status": "ok", "service": "miniapp-api"}


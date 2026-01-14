"""
FastAPI application with Telegram webhook and image callback endpoints
"""
print("📦 Importing FastAPI modules...")
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from aiogram.types import Update
from contextlib import asynccontextmanager
import json
import asyncio
from pathlib import Path
from uuid import UUID

print("⚙️  Loading settings...")
from app.settings import settings, load_configs
print("✅ Settings loaded")

# Conditionally initialize bot based on ENABLE_BOT flag
bot = None
dp = None
if settings.ENABLE_BOT:
    print("🤖 Initializing bot...")
    from app.bot.loader import bot, dp
    print("✅ Bot initialized")
    
    # Import handlers to register them (imported for side effects - registration)
    print("📝 Registering handlers...")
    from app.bot.handlers import start, chat, image, settings as settings_handler, payment  # noqa: F401
    print("✅ Handlers registered")
else:
    print("⚠️  Bot disabled (ENABLE_BOT=False)")

print("🔧 Loading core modules...")
from app.core.security import verify_hmac_signature
from app.core.rate import close_redis
from app.db.base import get_db
from app.db import crud
from app.core import analytics_service_tg
print("✅ Core modules loaded")

print("🌐 Loading Mini App API...")
from app.api import miniapp
print("✅ Mini App API loaded")

print("📊 Loading Analytics API...")
from app.api import analytics
print("✅ Analytics API loaded")



@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    print("🚀 Starting application...")
    load_configs()
    
    # Load translation service FIRST (before persona cache, as it depends on it)
    from app.core.translation_service import translation_service
    translation_service.load()
    print("✅ Translation service loaded")
    
    # Load persona cache (depends on translation_service)
    from app.core.persona_cache import load_cache
    load_cache()
    print("✅ Persona cache loaded")
    
    # Load start code cache
    from app.core.start_code_cache import load_cache as load_start_code_cache
    load_start_code_cache()
    print("✅ Start code cache loaded")
    
    # Set Mini App menu button (only if bot is enabled)
    if settings.ENABLE_BOT and bot:
        try:
            from aiogram.types import MenuButtonWebApp, WebAppInfo
            from app.settings import get_app_config
            app_config = get_app_config()
            miniapp_config = app_config.get('miniapp', {})
            button_name = miniapp_config.get('menu_button_name', 'App')
            miniapp_url = f"{settings.public_url}/miniapp"
            menu_button = MenuButtonWebApp(text=button_name, web_app=WebAppInfo(url=miniapp_url))
            await bot.set_chat_menu_button(menu_button=menu_button)
            print(f"✅ Mini App menu button set: {miniapp_url}")
        except Exception as e:
            print(f"⚠️  Failed to set Mini App menu button: {e}")
    
    # Start background scheduler
    from app.core.scheduler import start_scheduler
    start_scheduler()
    
    if settings.ENABLE_BOT:
        print("✅ Bot started successfully")
    else:
        print("✅ Application started (bot disabled)")
    
    yield
    
    # Shutdown
    print("🛑 Shutting down application...")
    
    # Stop scheduler
    from app.core.scheduler import stop_scheduler
    stop_scheduler()
    
    await close_redis()
    
    # Close bot session only if bot was initialized
    if settings.ENABLE_BOT and bot:
        await bot.session.close()
    
    # Dispose SQLAlchemy engine to properly close all database connections
    from app.db.base import engine
    engine.dispose()
    print("✅ Database connections closed")
    
    print("✅ Application stopped")


app = FastAPI(lifespan=lifespan, title="AI Telegram Bot")

# Include API routers
app.include_router(miniapp.router)
app.include_router(analytics.router)

# Serve Mini App static files (React build)
miniapp_build_path = Path(__file__).parent.parent / "miniapp" / "dist"
if miniapp_build_path.exists():
    # Mount assets directory
    app.mount("/miniapp/assets", StaticFiles(directory=miniapp_build_path / "assets"), name="miniapp-assets")
    
    # Serve index.html at /miniapp
    @app.get("/miniapp")
    async def serve_miniapp():
        """Serve Mini App index.html"""
        index_path = miniapp_build_path / "index.html"
        if index_path.exists():
            return FileResponse(index_path)
        return {"error": "Mini App not built"}
    
    # Serve other static files (like vite.svg)
    @app.get("/miniapp/{filename}")
    async def serve_miniapp_files(filename: str):
        """Serve static files from Mini App build"""
        file_path = miniapp_build_path / filename
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return {"error": "File not found"}
    
    print(f"✅ Mini App static files mounted at /miniapp")
else:
    print(f"⚠️  Mini App build not found at {miniapp_build_path}")

# Serve Analytics Dashboard static files (React build)
analytics_build_path = Path(__file__).parent.parent / "analytics-dashboard" / "dist"
if analytics_build_path.exists():
    # Mount assets directory
    app.mount("/analytics/assets", StaticFiles(directory=analytics_build_path / "assets"), name="analytics-assets")
    
    # Serve index.html at /analytics
    @app.get("/analytics")
    async def serve_analytics():
        """Serve Analytics Dashboard index.html"""
        index_path = analytics_build_path / "index.html"
        if index_path.exists():
            return FileResponse(index_path)
        return {"error": "Analytics Dashboard not built"}
    
    # Catch-all route for React Router (must be after /analytics/assets)
    @app.get("/analytics/{full_path:path}")
    async def serve_analytics_routes(full_path: str):
        """Serve Analytics Dashboard for all routes (React Router)"""
        # If requesting a file that exists, serve it
        file_path = analytics_build_path / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        # Otherwise serve index.html (for React Router)
        index_path = analytics_build_path / "index.html"
        if index_path.exists():
            return FileResponse(index_path)
        return {"error": "File not found"}
    
    print(f"✅ Analytics Dashboard mounted at /analytics")
else:
    print(f"⚠️  Analytics Dashboard build not found at {analytics_build_path}")

# Mount uploads directory for serving uploaded files
uploads_path = Path(__file__).parent.parent / "uploads"
uploads_path.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_path), name="uploads")
print(f"✅ Uploads directory mounted at /uploads")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "status": "ok",
        "bot": "AI Telegram Companion",
        "version": "1.0.0"
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


async def process_update_async(update: Update):
    """Process update asynchronously without blocking webhook response"""
    import traceback
    try:
        await dp.feed_update(bot, update)
    except Exception as e:
        # ALWAYS log full traceback - critical for debugging production payment issues
        print(f"[WEBHOOK] ❌ Error processing update: {type(e).__name__}: {e}")
        traceback.print_exc()
        
        # Log update details for debugging
        try:
            if update.message:
                user_id = update.message.from_user.id if update.message.from_user else "unknown"
                print(f"[WEBHOOK] 📋 Update details: message from user {user_id}")
                if update.message.successful_payment:
                    payment = update.message.successful_payment
                    print(f"[WEBHOOK] 💰 PAYMENT UPDATE - User: {user_id}, Product: {payment.invoice_payload}, Amount: {payment.total_amount}")
            elif update.pre_checkout_query:
                user_id = update.pre_checkout_query.from_user.id if update.pre_checkout_query.from_user else "unknown"
                print(f"[WEBHOOK] 🛒 PRE-CHECKOUT - User: {user_id}")
        except:
            pass
        # Don't propagate - already returned 200 to Telegram


# Only register webhook endpoint if bot is enabled
if settings.ENABLE_BOT:
    @app.post("/webhook/{token}")
    async def telegram_webhook(token: str, request: Request, background_tasks: BackgroundTasks):
        """
        Telegram webhook endpoint
        Receives updates from Telegram and processes them in background
        Returns 200 OK immediately to prevent Telegram timeouts
        """
        if token != settings.WEBHOOK_SECRET:
            raise HTTPException(status_code=403, detail="Invalid webhook token")
        
        try:
            data = await request.json()
            update = Update.model_validate(data)
            
            # Process in background - return 200 immediately
            background_tasks.add_task(process_update_async, update)
            
            return {"ok": True}  # ✅ Immediate response!
        
        except Exception as e:
            print(f"[WEBHOOK] Error parsing update: {e}")
            # Still return 200 to prevent Telegram retries
            return {"ok": True}
else:
    print("⚠️  Webhook endpoint disabled (ENABLE_BOT=False)")


async def _update_persona_avatar_with_fallback(persona_id: UUID, image_data: bytes, file_id: str = None):
    """
    Upload image to Cloudflare, with fallback to Telegram CDN if upload fails
    More reliable - works even if Cloudflare has connectivity issues
    
    Args:
        persona_id: UUID of the persona to update
        image_data: Image binary data
        file_id: Telegram file_id (optional, for fallback to Telegram CDN)
    """
    try:
        from app.bot.loader import bot
        from app.db.base import get_db
        from app.db import crud
        from app.core.cloudflare_upload import upload_to_cloudflare_tg
        import random
        
        cloudflare_url = None
        
        # Try Cloudflare upload first (preferred)
        try:
            print(f"[CHARACTER-AVATAR] 🖼️  Uploading {len(image_data)} bytes to Cloudflare...")
            filename = f"character_{persona_id}_{random.randint(1000, 9999)}.png"
            result = await upload_to_cloudflare_tg(image_data, filename)
            
            if result.success:
                cloudflare_url = result.image_url
                print(f"[CHARACTER-AVATAR] ✅ Uploaded to Cloudflare: {cloudflare_url}")
            else:
                print(f"[CHARACTER-AVATAR] ⚠️  Cloudflare upload failed: {result.error}, falling back to Telegram CDN")
        except Exception as cf_error:
            print(f"[CHARACTER-AVATAR] ⚠️  Cloudflare error: {cf_error}, falling back to Telegram CDN")
        
        # Fallback to Telegram CDN URL if Cloudflare failed and we have a file_id
        if not cloudflare_url and file_id:
            try:
                # Get file path from Telegram
                file = await bot.get_file(file_id)
                telegram_url = f"https://api.telegram.org/file/bot{settings.BOT_TOKEN}/{file.file_path}"
                cloudflare_url = telegram_url
                print(f"[CHARACTER-AVATAR] 🔄 Using Telegram CDN as fallback: {telegram_url[:80]}...")
            except Exception as tg_error:
                print(f"[CHARACTER-AVATAR] ❌ Failed to get Telegram URL: {tg_error}")
                return
        
        # Update persona's avatar_url
        if cloudflare_url:
            with get_db() as db:
                updated_persona = crud.update_persona(
                    db,
                    persona_id,
                    avatar_url=cloudflare_url
                )
                if updated_persona:
                    print(f"[CHARACTER-AVATAR] ✅ Updated persona {persona_id} avatar_url in database")
                else:
                    print(f"[CHARACTER-AVATAR] ⚠️  Persona {persona_id} not found in database")
    
    except Exception as e:
        print(f"[CHARACTER-AVATAR] ❌ Error updating avatar: {e}")
        import traceback
        traceback.print_exc()


@app.post("/image/callback")
async def image_callback(request: Request):
    """
    Runpod image generation callback endpoint
    Receives job completion notifications and sends image to user
    """
    # Get query params
    job_id_str = request.query_params.get("job_id")
    signature = request.query_params.get("sig")
    
    if not job_id_str or not signature:
        raise HTTPException(status_code=400, detail="Missing job_id or signature")
    
    # Verify HMAC signature
    if not verify_hmac_signature(job_id_str, signature):
        raise HTTPException(status_code=403, detail="Invalid signature")
    
    # Initialize variables
    image_data = None
    image_url = None
    status = None
    error = None
    
    # Check Content-Type header to determine how to parse
    content_type = request.headers.get("content-type", "").lower()
    print(f"[IMAGE-CALLBACK] Content-Type: {content_type}")
    
    # Handle different content types
    if "application/json" in content_type:
        # JSON response with status/URLs or base64 data
        try:
            body = await request.body()
            payload = json.loads(body)
            print(f"[IMAGE-CALLBACK] JSON payload keys: {list(payload.keys())}")
            
            status = payload.get("status", "").upper()
            output = payload.get("output", {})
            error = payload.get("error")
            
            # Check for images in output
            images = output.get("images", [])
            if images:
                first_image = images[0]
                
                # Handle base64 format from ComfyUI handler: {"filename": "...", "type": "base64", "data": "..."}
                if isinstance(first_image, dict) and first_image.get("type") == "base64":
                    import base64 as b64
                    image_data = b64.b64decode(first_image.get("data", ""))
                    print(f"[IMAGE-CALLBACK] Decoded base64 image: {len(image_data)} bytes")
                    status = "COMPLETED"
                elif isinstance(first_image, str):
                    # URL format
                    image_url = first_image
                    print(f"[IMAGE-CALLBACK] Got image URL from JSON: {image_url}")
                else:
                    print(f"[IMAGE-CALLBACK] Unknown image format: {type(first_image)}")
        except Exception as e:
            print(f"[IMAGE-CALLBACK] Failed to parse JSON: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")
    
    elif "multipart/form-data" in content_type:
        # FormData with image file
        try:
            form = await request.form()
            image_file = form.get("image")
            if image_file:
                image_data = await image_file.read()
                print(f"[IMAGE-CALLBACK] Got image from FormData: {len(image_data)} bytes")
                status = "COMPLETED"
            else:
                raise HTTPException(status_code=400, detail="No image in form data")
        except Exception as e:
            print(f"[IMAGE-CALLBACK] Failed to parse FormData: {e}")
            raise HTTPException(status_code=400, detail=f"Invalid FormData: {e}")
    
    elif "image/" in content_type or not content_type:
        # Direct binary image upload
        try:
            body = await request.body()
            print(f"[IMAGE-CALLBACK] Got binary image: {len(body)} bytes")
            
            # Find PNG start if needed
            png_start = body.find(b'\x89PNG')
            if png_start != -1 and png_start > 0:
                image_data = body[png_start:]
                print(f"[IMAGE-CALLBACK] Extracted PNG from offset {png_start}: {len(image_data)} bytes")
            else:
                image_data = body
            
            status = "COMPLETED"
        except Exception as e:
            print(f"[IMAGE-CALLBACK] Failed to read binary: {e}")
            raise HTTPException(status_code=400, detail=f"Invalid binary: {e}")
    
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported content type: {content_type}")
    
    if not status:
        status = "COMPLETED"  # Default if we got data
    
    print(f"[IMAGE-CALLBACK] Job {job_id_str}: status={status}")
    
    # Initialize tg_chat_id
    tg_chat_id = None
    
    # Get job from database
    with get_db() as db:
        job = crud.get_image_job(db, job_id_str)
        if not job:
            print(f"[IMAGE-CALLBACK] Job {job_id_str} not found in database")
            return {"ok": True, "message": "Job not found"}
        
        # Check idempotency - if already completed/failed, ignore
        if job.status in ("completed", "failed"):
            print(f"[IMAGE-CALLBACK] Job {job_id_str} already {job.status}, ignoring duplicate callback")
            return {"ok": True, "message": "Already processed"}
        
        # Update job status
        if status == "COMPLETED":
            # Handle both binary image data and URL-based responses
            if image_data:
                # Binary image received directly
                image_url = f"binary:{len(image_data)}"  # Placeholder for DB
            else:
                # URL-based response (fallback)
                images = output.get("images", [])
                if not images:
                    crud.update_image_job_status(
                        db,
                        job_id_str,
                        status="failed",
                        error="No images in output"
                    )
                    return {"ok": True, "message": "No images generated"}
                image_url = images[0]
            
            crud.update_image_job_status(
                db,
                job_id_str,
                status="completed",
                result_url=image_url
            )
            
            # Decrement concurrent image counter
            user_id_for_decrement = job.user_id
            
            # Extract job.ext data while still in session (to avoid detached instance errors)
            job_ext_data = job.ext if job.ext else {}
            pending_caption = job_ext_data.get("pending_caption")
            is_auto_followup = job_ext_data.get("is_auto_followup", False)
            skip_chat_send = job_ext_data.get("skip_chat_send", False)  # Check if we should skip sending
            loading_msg_id = job_ext_data.get("loading_msg_id")  # Loading message to delete
            ext_tg_chat_id = job_ext_data.get("tg_chat_id")  # For standalone image gen
            job_user_id = job.user_id
            job_persona_id = job.persona_id
            job_prompt = job.prompt
            job_negative_prompt = job.negative_prompt
            job_chat_id = job.chat_id
            
            # Get chat info for sending photo
            if skip_chat_send:
                # Skip sending to chat (for character creation images)
                tg_chat_id = None
                print(f"[IMAGE-CALLBACK] ⏭️  Skipping chat send (skip_chat_send=True)")
                
                # Update avatar if this is for a persona
                if job_persona_id and (image_url or image_data):
                    print(f"[CHARACTER-AVATAR] 🎨 Character creation image received, updating avatar for persona {job_persona_id}")
                    
                    # If we have image_data, upload to Cloudflare
                    if image_data:
                        asyncio.create_task(_update_persona_avatar_with_fallback(
                            persona_id=job_persona_id,
                            image_data=image_data,
                            file_id=None  # We don't have file_id yet since not sent to Telegram
                        ))
                        print(f"[CHARACTER-AVATAR] 🚀 Started avatar upload task (from image_data)")
                    elif image_url:
                        # Use image_url directly
                        crud.update_persona(db, job_persona_id, avatar_url=image_url)
                        print(f"[CHARACTER-AVATAR] ✅ Updated persona avatar with URL: {image_url[:80]}...")
            elif job.chat_id:
                # Get existing chat
                from app.db.models import Chat
                chat = db.query(Chat).filter(Chat.id == job.chat_id).first()
                if chat:
                    tg_chat_id = chat.tg_chat_id
                else:
                    tg_chat_id = job.user_id
            elif ext_tg_chat_id:
                # Standalone image gen - use tg_chat_id from job.ext
                tg_chat_id = ext_tg_chat_id
            else:
                # No chat associated, send to user directly
                tg_chat_id = job.user_id
        
        elif status == "FAILED":
            error_msg = error or (output.get("error") if 'output' in locals() else "Unknown error")
            print(f"[IMAGE-CALLBACK] ❌ Job failed with error: {error_msg}")
            crud.update_image_job_status(
                db,
                job_id_str,
                status="failed",
                error=error_msg
            )
            
            # Decrement concurrent image counter
            user_id_for_decrement = job.user_id
            
            tg_chat_id = None
        
        else:
            # IN_PROGRESS, IN_QUEUE - update status but don't send anything
            new_status = "running" if status == "IN_PROGRESS" else "queued"
            crud.update_image_job_status(db, job_id_str, status=new_status)
            return {"ok": True, "message": f"Status updated to {new_status}"}
    
    # Decrement concurrent image counter for completed/failed jobs
    if status in ("COMPLETED", "FAILED") and 'user_id_for_decrement' in locals():
        from app.core import redis_queue
        await redis_queue.decrement_user_image_count(user_id_for_decrement)
        print(f"[IMAGE-CALLBACK] 📊 Decremented user image count for user {user_id_for_decrement}")
    
    # Send photo to user if completed
    if status == "COMPLETED" and tg_chat_id and (image_url or image_data):
        try:
            # Delete loading message if exists
            if loading_msg_id:
                try:
                    await bot.delete_message(chat_id=tg_chat_id, message_id=loading_msg_id)
                    print(f"[IMAGE-CALLBACK] 🗑️  Deleted loading message {loading_msg_id}")
                except Exception as e:
                    print(f"[IMAGE-CALLBACK] ⚠️  Could not delete loading message: {e}")
            
            # Build refresh keyboard
            from app.bot.keyboards.inline import build_image_refresh_keyboard
            refresh_keyboard = build_image_refresh_keyboard(job_id_str)
            
            # Get the chat and check for previous image message
            with get_db() as db:
                chat = crud.get_chat_by_tg_chat_id(db, tg_chat_id)
                if chat and chat.ext and chat.ext.get("last_image_msg_id"):
                    # Remove refresh button from previous image
                    prev_msg_id = chat.ext["last_image_msg_id"]
                    try:
                        await bot.edit_message_reply_markup(
                            chat_id=tg_chat_id,
                            message_id=prev_msg_id,
                            reply_markup=None
                        )
                        print(f"[IMAGE-CALLBACK] 🗑️  Removed refresh button from previous image (msg {prev_msg_id})")
                    except Exception as e:
                        # Button might already be removed, that's okay
                        print(f"[IMAGE-CALLBACK] ⚠️  Could not remove previous button (likely already removed): {e}")
                    finally:
                        # Always clear the message ID to avoid trying to remove it again
                        # For JSONB fields, we must mark as modified or reassign the whole dict
                        from sqlalchemy.orm.attributes import flag_modified
                        chat.ext["last_image_msg_id"] = None
                        flag_modified(chat, "ext")
                        db.commit()
            
            # Check if there's a pending caption (for 24h follow-ups)
            # Note: pending_caption was extracted earlier in the db session
            if pending_caption:
                print(f"[IMAGE-CALLBACK] 📝 Found pending caption - will send text with image (24h followup)")
                
                # Format caption for Telegram MarkdownV2
                from app.core.telegram_utils import escape_markdown_v2
                pending_caption = escape_markdown_v2(pending_caption)
            
            # Check if image should be blurred for non-premium low-token users
            should_blur = False
            with get_db() as db:
                is_premium = crud.check_user_premium(db, job_user_id)["is_premium"]
                
                if not is_premium:
                    user_energy = crud.get_user_energy(db, job_user_id)
                    tokens = user_energy.get('tokens', 0)
                    
                    # Get chat and its image counter
                    chat = crud.get_chat_by_tg_chat_id(db, tg_chat_id)
                    if chat:
                        if not chat.ext:
                            chat.ext = {}
                        blurred_counter = chat.ext.get('blurred_image_counter', 0)
                        blurred_counter += 1
                        
                        # Decide if should blur based on token count and counter
                        # <20 tokens: every 2nd photo, <40: every 3rd, <70: every 4th
                        if tokens < 20 and blurred_counter % 2 == 0:
                            should_blur = True
                        elif tokens < 40 and blurred_counter % 3 == 0:
                            should_blur = True
                        elif tokens < 70 and blurred_counter % 4 == 0:
                            should_blur = True
                        
                        # Save counter
                        from sqlalchemy.orm.attributes import flag_modified
                        chat.ext['blurred_image_counter'] = blurred_counter
                        flag_modified(chat, "ext")
                        db.commit()
                        
                        if should_blur:
                            print(f"[IMAGE-CALLBACK] 🔒 Image will be blurred (tokens={tokens}, counter={blurred_counter})")
            
            # If should blur, dynamically blur the actual image and send with caption
            if should_blur:
                import base64
                from app.bot.keyboards.inline import build_blurred_image_keyboard
                from app.core.image_utils import blur_image_safe
                from aiogram.types import BufferedInputFile
                
                # Get user language for button text
                with get_db() as db:
                    user_language = crud.get_user_language(db, job_user_id)
                
                # Get image data if we have URL but no data
                actual_image_data = image_data
                if not actual_image_data and image_url:
                    import httpx
                    try:
                        async with httpx.AsyncClient() as client:
                            resp = await client.get(image_url, timeout=30)
                            if resp.status_code == 200:
                                actual_image_data = resp.content
                    except Exception as e:
                        print(f"[IMAGE-CALLBACK] ⚠️  Failed to download image for blur: {e}")
                
                # Blur the actual image
                blurred_data = None
                if actual_image_data:
                    blurred_data = blur_image_safe(actual_image_data)
                
                if blurred_data:
                    # Store original image data in job.ext for unlock
                    with get_db() as db:
                        job = crud.get_image_job(db, job_id_str)
                        if job:
                            if not job.ext:
                                job.ext = {}
                            job.ext['blurred_original_data'] = base64.b64encode(actual_image_data).decode('utf-8')
                            from sqlalchemy.orm.attributes import flag_modified
                            flag_modified(job, "ext")
                            db.commit()
                    
                    # Build keyboard and send blurred image WITH caption
                    miniapp_url = f"{settings.public_url}/miniapp"
                    blurred_keyboard = build_blurred_image_keyboard(job_id_str, miniapp_url, user_language)
                    
                    blurred_file = BufferedInputFile(blurred_data, filename="blurred.jpg")
                    sent_message = await bot.send_photo(
                        chat_id=tg_chat_id,
                        photo=blurred_file,
                        caption=pending_caption,
                        parse_mode="MarkdownV2" if pending_caption else None,
                        reply_markup=blurred_keyboard
                    )
                    pending_caption = None  # Clear so we don't send again below
                    print(f"[IMAGE-CALLBACK] 🔒 Blurred image sent to user {job_user_id}")
                else:
                    print(f"[IMAGE-CALLBACK] ⚠️  Failed to blur image, sending original")
                    should_blur = False  # Fallback to original
            
            if not should_blur:
                # Send photo - handle both binary data and URL
                if image_data:
                    # Strip color profile to prevent yellowish tint in Telegram
                    from app.core.image_utils import strip_color_profile_safe
                    image_data = strip_color_profile_safe(image_data)
                    
                    # Send binary image data
                    from aiogram.types import BufferedInputFile
                    input_file = BufferedInputFile(image_data, filename="generated.png")
                    sent_message = await bot.send_photo(
                        chat_id=tg_chat_id,
                        photo=input_file,
                        caption=pending_caption,
                        parse_mode="MarkdownV2" if pending_caption else None,
                        reply_markup=refresh_keyboard
                    )
                else:
                    # Send via URL
                    sent_message = await bot.send_photo(
                        chat_id=tg_chat_id,
                        photo=image_url,
                        caption=pending_caption,
                        parse_mode="MarkdownV2" if pending_caption else None,
                        reply_markup=refresh_keyboard
                    )
            
            if pending_caption:
                print(f"[IMAGE-CALLBACK] ✅ Image sent with caption (24h followup mode)")
            
            # Save file_id and message_id for caching and tracking
            if sent_message.photo:
                file_id = sent_message.photo[-1].file_id
                with get_db() as db:
                    crud.update_image_job_status(
                        db,
                        job_id_str,
                        status="completed",
                        result_file_id=file_id
                    )
                    
                    # Store this message ID as the last image message
                    chat = crud.get_chat_by_tg_chat_id(db, tg_chat_id)
                    if chat:
                        if not chat.ext:
                            chat.ext = {}
                        chat.ext["last_image_msg_id"] = sent_message.message_id
                        # For JSONB fields, we must mark as modified
                        from sqlalchemy.orm.attributes import flag_modified
                        flag_modified(chat, "ext")
                        db.commit()
                        print(f"[IMAGE-CALLBACK] 💾 Stored message ID {sent_message.message_id} as last image")
                
                # If this is a character creation image (skip_chat_send=True), update avatar immediately
                # Note: standalone image generation also has no chat_id but should NOT update avatar
                if skip_chat_send and job_persona_id:
                    # Get Telegram CDN URL for the avatar
                    telegram_cdn_url = f"https://api.telegram.org/file/bot{settings.BOT_TOKEN}/{sent_message.photo[-1].file_unique_id}"
                    
                    # Try Cloudflare upload, but fallback to Telegram file_id if it fails
                    if image_data:
                        asyncio.create_task(_update_persona_avatar_with_fallback(
                            persona_id=job_persona_id,
                            image_data=image_data,
                            file_id=file_id
                        ))
                        print(f"[CHARACTER-AVATAR] 🚀 Started avatar upload task for persona {job_persona_id}")
            
            # Stop upload_photo action now that image is sent
            from app.core.action_registry import stop_and_remove_action
            await stop_and_remove_action(tg_chat_id)
            
            print(f"[IMAGE-CALLBACK] ✅ Image sent to chat {tg_chat_id}")
            
            # Track image generation for analytics (with Cloudflare upload in background)
            # Use job details extracted earlier from the db session
            # NOTE: For character creation images, analytics tracking is skipped to avoid duplicate Cloudflare uploads
            if job_chat_id:  # Only track analytics for chat images, not character creation
                with get_db() as db:
                    chat_details = crud.get_chat_by_id(db, job_chat_id) if job_chat_id else None
                    persona_details = crud.get_persona_by_id(db, job_persona_id) if job_persona_id else None
                    
                    # Use image_data if available, otherwise use image_url
                    image_source = image_data if image_data else image_url
                    
                    # Use is_auto_followup extracted earlier
                    analytics_service_tg.track_image_generated(
                        client_id=job_user_id,
                        image_url_or_bytes=image_source,
                        persona_id=job_persona_id,
                        persona_name=persona_details.name if persona_details else None,
                        prompt=job_prompt,
                        negative_prompt=job_negative_prompt,
                        chat_id=job_chat_id,
                        job_id=job_id_str,
                        is_auto_followup=is_auto_followup
                    )
        
        except Exception as e:
            print(f"[IMAGE-CALLBACK] ❌ Error sending photo: {e}")
            
            # Stop upload_photo action on error
            from app.core.action_registry import stop_and_remove_action
            await stop_and_remove_action(tg_chat_id)
            
            # Try to send error message
            from app.core.constants import ERROR_MESSAGES
            try:
                await bot.send_message(
                    chat_id=tg_chat_id,
                    text=ERROR_MESSAGES["image_failed"]
                )
            except:
                pass
    
    elif status == "FAILED" and tg_chat_id:
        # Stop upload_photo action on failure
        from app.core.action_registry import stop_and_remove_action
        await stop_and_remove_action(tg_chat_id)
        
        # Send failure message
        from app.core.constants import ERROR_MESSAGES
        try:
            await bot.send_message(
                chat_id=tg_chat_id,
                text=ERROR_MESSAGES["image_failed"]
            )
        except Exception as e:
            print(f"[IMAGE-CALLBACK] ❌ Error sending failure message: {e}")
    
    return {"ok": True}


# Webhook setting removed - set manually after deployment
# Use: python scripts/manage.py set-webhook https://your-app.up.railway.app



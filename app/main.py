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
from pathlib import Path

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
    
    # Load persona cache
    from app.core.persona_cache import load_cache
    load_cache()
    print("✅ Persona cache loaded")
    
    # Set Mini App menu button (only if bot is enabled)
    if settings.ENABLE_BOT and bot:
        try:
            from aiogram.types import MenuButtonWebApp, WebAppInfo
            miniapp_url = f"{settings.public_url}/miniapp"
            menu_button = MenuButtonWebApp(text="App Gallery", web_app=WebAppInfo(url=miniapp_url))
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
    try:
        await dp.feed_update(bot, update)
    except Exception as e:
        print(f"[WEBHOOK] Error processing update: {e}")
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
        # JSON response with status/URLs
        try:
            body = await request.body()
            payload = json.loads(body)
            print(f"[IMAGE-CALLBACK] JSON payload: {json.dumps(payload, indent=2)}")
            
            status = payload.get("status", "").upper()
            output = payload.get("output", {})
            error = payload.get("error")
            
            # Check for image URLs in output
            images = output.get("images", [])
            if images:
                image_url = images[0]
                print(f"[IMAGE-CALLBACK] Got image URL from JSON: {image_url}")
        except Exception as e:
            print(f"[IMAGE-CALLBACK] Failed to parse JSON: {e}")
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
            
            # Get chat info for sending photo
            if job.chat_id:
                # Get existing chat
                from app.db.models import Chat
                chat = db.query(Chat).filter(Chat.id == job.chat_id).first()
                if chat:
                    tg_chat_id = chat.tg_chat_id
                else:
                    tg_chat_id = job.user_id
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
            tg_chat_id = None
        
        else:
            # IN_PROGRESS, IN_QUEUE - update status but don't send anything
            new_status = "running" if status == "IN_PROGRESS" else "queued"
            crud.update_image_job_status(db, job_id_str, status=new_status)
            return {"ok": True, "message": f"Status updated to {new_status}"}
    
    # Send photo to user if completed
    if status == "COMPLETED" and tg_chat_id and (image_url or image_data):
        try:
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
                    reply_markup=refresh_keyboard
                )
            else:
                # Send via URL
                sent_message = await bot.send_photo(
                    chat_id=tg_chat_id,
                    photo=image_url,
                    reply_markup=refresh_keyboard
                )
            
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
            
            # Stop upload_photo action now that image is sent
            from app.core.action_registry import stop_and_remove_action
            await stop_and_remove_action(tg_chat_id)
            
            print(f"[IMAGE-CALLBACK] ✅ Image sent to chat {tg_chat_id}")
            
            # Track image generation for analytics (with Cloudflare upload in background)
            # Get job details for tracking
            with get_db() as db:
                job_details = crud.get_image_job(db, job_id_str)
                if job_details:
                    chat_details = crud.get_chat_by_id(db, job_details.chat_id) if job_details.chat_id else None
                    persona_details = crud.get_persona_by_id(db, job_details.persona_id) if job_details.persona_id else None
                    
                    # Use image_data if available, otherwise use image_url
                    image_source = image_data if image_data else image_url
                    
                    # Extract source metadata from job
                    is_auto_followup = job_details.ext.get("is_auto_followup", False) if job_details.ext else False
                    
                    analytics_service_tg.track_image_generated(
                        client_id=job_details.user_id,
                        image_url_or_bytes=image_source,
                        persona_id=job_details.persona_id,
                        persona_name=persona_details.name if persona_details else None,
                        prompt=job_details.prompt,
                        negative_prompt=job_details.negative_prompt,
                        chat_id=job_details.chat_id,
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



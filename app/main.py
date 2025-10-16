"""
FastAPI application with Telegram webhook and image callback endpoints
"""
print("📦 Importing FastAPI modules...")
from fastapi import FastAPI, Request, HTTPException
from aiogram.types import Update
from contextlib import asynccontextmanager
import httpx
import json

print("⚙️  Loading settings...")
from app.settings import settings, load_configs
print("✅ Settings loaded")

print("🤖 Initializing bot...")
from app.bot.loader import bot, dp
print("✅ Bot initialized")

print("🔧 Loading core modules...")
from app.core.security import verify_hmac_signature
from app.core.rate import close_redis
from app.db.base import get_db
from app.db import crud
print("✅ Core modules loaded")

# Import handlers to register them
print("📝 Registering handlers...")
from app.bot.handlers import start, chat, image, settings as settings_handler
print("✅ Handlers registered")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    print("🚀 Starting bot...")
    load_configs()
    
    # Start background scheduler
    from app.core.scheduler import start_scheduler
    start_scheduler()
    
    print("✅ Bot started successfully")
    
    yield
    
    # Shutdown
    print("🛑 Shutting down bot...")
    
    # Stop scheduler
    from app.core.scheduler import stop_scheduler
    stop_scheduler()
    
    await close_redis()
    await bot.session.close()
    print("✅ Bot stopped")


app = FastAPI(lifespan=lifespan, title="AI Telegram Bot")


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


@app.post("/webhook/{token}")
async def telegram_webhook(token: str, request: Request):
    """
    Telegram webhook endpoint
    Receives updates from Telegram and feeds them to aiogram dispatcher
    """
    if token != settings.WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Invalid webhook token")
    
    try:
        data = await request.json()
        update = Update.model_validate(data)
        
        # Feed update to dispatcher
        await dp.feed_update(bot, update)
        
        return {"ok": True}
    
    except Exception as e:
        print(f"[WEBHOOK] Error processing update: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


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
            # Send photo - handle both binary data and URL
            if image_data:
                # Send binary image data
                from aiogram.types import BufferedInputFile
                input_file = BufferedInputFile(image_data, filename="generated.png")
                sent_message = await bot.send_photo(
                    chat_id=tg_chat_id,
                    photo=input_file,
                    caption="🎨 <b>Here's your image!</b>"
                )
            else:
                # Send via URL
                sent_message = await bot.send_photo(
                    chat_id=tg_chat_id,
                    photo=image_url,
                    caption="🎨 <b>Here's your image!</b>"
                )
            
            # Save file_id for caching
            if sent_message.photo:
                file_id = sent_message.photo[-1].file_id
                with get_db() as db:
                    crud.update_image_job_status(
                        db,
                        job_id_str,
                        status="completed",
                        result_file_id=file_id
                    )
            
            print(f"[IMAGE-CALLBACK] ✅ Image sent to chat {tg_chat_id}")
        
        except Exception as e:
            print(f"[IMAGE-CALLBACK] ❌ Error sending photo: {e}")
            
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



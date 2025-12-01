"""
Image generation handler
"""
from aiogram import types
from aiogram.filters import Command
from app.bot.loader import router, bot
from app.bot.keyboards.inline import build_image_prompt_keyboard
from app.db.base import get_db
from app.db import crud
from app.db.models import User
from app.settings import get_app_config
from app.core.actions import send_action_repeatedly
from app.core.rate import check_rate_limit
from app.core.pipeline_adapter import build_image_prompts
from app.core.img_runpod import submit_image_job
from app.core.constants import ERROR_MESSAGES
from app.core import analytics_service_tg
import random


@router.message(Command("image"))
async def cmd_image(message: types.Message):
    """Handle /image command"""
    # Show image prompt options
    await message.answer(
        "🎨 <b>What kind of image would you like me to generate?</b>",
        reply_markup=build_image_prompt_keyboard()
    )


@router.callback_query(lambda c: c.data.startswith("img_prompt:"))
async def image_prompt_callback(callback: types.CallbackQuery):
    """Handle image prompt selection"""
    prompt_type = callback.data.split(":")[1]
    
    if prompt_type == "custom":
        await callback.message.edit_text(
            "✍️ <b>Send me a custom prompt for the image you want!</b>\n\n"
            "Example: <i>wearing a red dress, at the beach, sunset</i>"
        )
        await callback.answer()
        # Note: You'd need to implement FSM (Finite State Machine) to capture next message
        # For now, this is a simplified version
        return
    
    # Predefined prompts
    prompt_texts = {
        "selfie": "taking a cute selfie, smiling at camera, casual pose",
        "flirty": "flirty expression, seductive pose, looking at viewer",
        "casual": "casual portrait, natural lighting, friendly expression"
    }
    
    user_prompt = prompt_texts.get(prompt_type, "portrait")
    
    await callback.answer()
    await generate_image_for_user(callback.message, callback.from_user.id, user_prompt)


async def generate_image_for_user(message: types.Message, user_id: int, user_prompt: str):
    """Generate image for user with given prompt"""
    config = get_app_config()
    
    # Check if user is premium (premium users get free images)
    with get_db() as db:
        is_premium = crud.check_user_premium(db, user_id)["is_premium"]
    
    # Check energy for non-premium users (image costs 5 energy)
    if not is_premium:
        with get_db() as db:
            if not crud.check_user_energy(db, user_id, required=5):
                # Show energy upsell message
                await show_energy_upsell_message(message, user_id)
                return
    
    # Rate limit check
    allowed, _ = await check_rate_limit(
        user_id,
        "image",
        config["limits"]["image_per_min"],
        60
    )
    
    if not allowed:
        await message.answer(ERROR_MESSAGES["rate_limit_image"])
        return
    
    # Check concurrent image limit
    from app.core import redis_queue
    from app.settings import settings
    current_count = await redis_queue.get_user_image_count(user_id)
    if current_count >= settings.MAX_CONCURRENT_IMAGES_PER_USER:
        print(f"[IMAGE] ⏭️  User {user_id} has reached concurrent image limit ({current_count}/{settings.MAX_CONCURRENT_IMAGES_PER_USER}) - skipping")
        return
    
    with get_db() as db:
        # Deduct energy for non-premium users
        if not is_premium:
            if not crud.deduct_user_energy(db, user_id, amount=5):
                await message.answer("❌ Failed to deduct energy. Please try again.")
                return
            print(f"[IMAGE] ⚡ Deducted 5 energy from user {user_id}")
        else:
            print(f"[IMAGE] 💎 Premium user - free image generation")
        
        # Get user's global message count for priority determination
        user = db.query(User).filter(User.id == user_id).first()
        global_message_count = user.global_message_count if user else 999
        
        # Get active chat
        chat = crud.get_active_chat(db, message.chat.id, user_id)
        
        if not chat:
            await message.answer(ERROR_MESSAGES["no_persona"])
            return
        
        # Get persona
        persona = crud.get_persona_by_id(db, chat.persona_id)
        if not persona:
            await message.answer(ERROR_MESSAGES["persona_not_found"])
            return
        
        # Build image prompts using pipeline adapter (prompts dict not needed anymore)
        positive_prompt, negative_prompt = build_image_prompts(
            {},  # Empty dict - pipeline_adapter should handle this
            persona,
            user_prompt,
            chat,
            ""  # No dialogue response for manual image gen
        )
        
        # Create image job
        seed = random.randint(1, 2147483647)
        job = crud.create_image_job(
            db,
            user_id=user_id,
            persona_id=persona.id,
            prompt=positive_prompt,
            negative_prompt=negative_prompt,
            chat_id=chat.id,
            ext={"seed": seed, "user_prompt": user_prompt}
        )
        
        job_id = job.id
    
    # Increment concurrent image counter (after job creation, before submission)
    await redis_queue.increment_user_image_count(user_id)
    print(f"[IMAGE] 📊 Incremented user image count")
    
    # Determine priority based on rules (same as pipeline)
    if is_premium:
        queue_priority = "high"
        priority_reason = "premium user"
    elif global_message_count <= 2:
        queue_priority = "high"
        priority_reason = f"first 2 messages globally (count: {global_message_count})"
    else:
        queue_priority = "medium"
        priority_reason = "regular user message"
    
    print(f"[IMAGE] 📊 Queue priority: {queue_priority} ({priority_reason})")
    
    # Submit to Runpod with upload_photo action
    try:
        async with send_action_repeatedly(bot, message.chat.id, "upload_photo"):
            await submit_image_job(
                job_id=job_id,
                prompt=positive_prompt,
                negative_prompt=negative_prompt,
                seed=seed,
                queue_priority=queue_priority
            )
            
            # Job submitted successfully
            # Actual image will be delivered via webhook callback
            print(f"[IMAGE] Job {job_id} submitted to Runpod")
    
    except Exception as e:
        print(f"[IMAGE] Error submitting job: {e}")
        
        # Decrement counter since submission failed
        await redis_queue.decrement_user_image_count(user_id)
        print(f"[IMAGE] 📊 Decremented user image count (submission failed)")
        
        with get_db() as db:
            crud.update_image_job_status(
                db,
                job_id,
                status="failed",
                error=str(e)
            )
        
        await message.answer(
            ERROR_MESSAGES["image_failed"]
        )


async def show_energy_upsell_message(message: types.Message, user_id: int):
    """Show energy upsell message with button to open premium page"""
    from app.bot.keyboards.inline import build_energy_upsell_keyboard
    from app.settings import settings
    
    with get_db() as db:
        user_energy = crud.get_user_energy(db, user_id)
        
        # Delete previous upsell message if exists
        upsell_msg_id, upsell_chat_id = crud.get_and_clear_energy_upsell_message(db, user_id)
        if upsell_msg_id and upsell_chat_id:
            try:
                await bot.delete_message(chat_id=upsell_chat_id, message_id=upsell_msg_id)
            except Exception:
                pass
    
    # Send new upsell message
    miniapp_url = f"{settings.public_url}/miniapp"
    keyboard = build_energy_upsell_keyboard(miniapp_url)
    
    sent_msg = await message.answer(
        f"🪙 <b>You're out of tokens!</b>\n\n"
        f"You have {user_energy['tokens']} tokens.\n"
        f"• Text messages cost <b>1 token</b> each\n"
        f"• Image generation costs <b>5 tokens</b> (3 tokens for premium)\n"
        f"• Image refresh costs <b>3 tokens</b> (2 tokens for premium)\n\n"
        f"💎 Get more tokens:\n"
        f"• Purchase token packages\n"
        f"• Subscribe to premium tiers for daily tokens\n"
        f"• Claim your daily 10-token bonus!",
        reply_markup=keyboard
    )
    
    # Save this message ID for later deletion
    with get_db() as db:
        crud.save_energy_upsell_message(db, user_id, sent_msg.message_id, message.chat.id)


async def generate_image_for_refresh(user_id: int, original_job_id: str, tg_chat_id: int):
    """Generate image for refresh - costs 3 energy for free users, 2 for premium
    
    Reuses the EXACT same prompts from the original job, only changes the seed.
    """
    config = get_app_config()
    
    # Rate limit check
    allowed, _ = await check_rate_limit(
        user_id,
        "image",
        config["limits"]["image_per_min"],
        60
    )
    
    if not allowed:
        # Send error message directly instead of editing
        await bot.send_message(tg_chat_id, ERROR_MESSAGES["rate_limit_image"])
        return
    
    # Check concurrent image limit
    from app.core import redis_queue
    from app.settings import settings
    current_count = await redis_queue.get_user_image_count(user_id)
    if current_count >= settings.MAX_CONCURRENT_IMAGES_PER_USER:
        print(f"[REFRESH-IMAGE] ⏭️  User {user_id} has reached concurrent image limit ({current_count}/{settings.MAX_CONCURRENT_IMAGES_PER_USER}) - skipping")
        return
    
    # Check if user is premium for priority determination
    with get_db() as db:
        is_premium = crud.check_user_premium(db, user_id)["is_premium"]
        # Get user's global message count for priority determination
        user = db.query(User).filter(User.id == user_id).first()
        global_message_count = user.global_message_count if user else 999
    
    with get_db() as db:
        # Get original job to reuse its prompts
        original_job = crud.get_image_job(db, original_job_id)
        if not original_job:
            await bot.send_message(tg_chat_id, ERROR_MESSAGES["image_failed"])
            return
        
        # Get active chat
        chat = crud.get_active_chat(db, tg_chat_id, user_id)
        
        if not chat:
            await bot.send_message(tg_chat_id, ERROR_MESSAGES["no_persona"])
            return
        
        # Get persona
        persona = crud.get_persona_by_id(db, chat.persona_id)
        
        if not persona:
            await bot.send_message(tg_chat_id, ERROR_MESSAGES["persona_not_found"])
            return
        
        # REUSE EXACT PROMPTS from original job (don't regenerate!)
        positive_prompt = original_job.prompt
        negative_prompt = original_job.negative_prompt
        user_prompt = original_job.ext.get("user_prompt", "") if original_job.ext else ""
        
        print(f"[REFRESH-IMAGE] 🔄 Reusing exact prompts from job {original_job_id}")
        print(f"[REFRESH-IMAGE]    Positive: {positive_prompt[:100]}...")
        print(f"[REFRESH-IMAGE]    Negative: {negative_prompt[:100]}...")
        
        # Create new image job with SAME prompts, different seed
        seed = random.randint(1, 2147483647)
        job = crud.create_image_job(
            db,
            user_id=user_id,
            persona_id=persona.id,
            prompt=positive_prompt,
            negative_prompt=negative_prompt,
            chat_id=chat.id,
            ext={"seed": seed, "user_prompt": user_prompt, "refreshed_from": original_job_id}
        )
        
        job_id = job.id
    
    # Increment concurrent image counter (after job creation, before submission)
    await redis_queue.increment_user_image_count(user_id)
    print(f"[REFRESH-IMAGE] 📊 Incremented user image count")
    
    # Determine priority based on rules (same as pipeline)
    if is_premium:
        queue_priority = "high"
        priority_reason = "premium user"
    elif global_message_count <= 2:
        queue_priority = "high"
        priority_reason = f"first 2 messages globally (count: {global_message_count})"
    else:
        queue_priority = "medium"
        priority_reason = "regular user message"
    
    print(f"[REFRESH-IMAGE] 📊 Queue priority: {queue_priority} ({priority_reason})")
    
    # Submit to Runpod with upload_photo action
    try:
        async with send_action_repeatedly(bot, tg_chat_id, "upload_photo"):
            await submit_image_job(
                job_id=job_id,
                prompt=positive_prompt,
                negative_prompt=negative_prompt,
                seed=seed,
                queue_priority=queue_priority
            )
            
            # Job submitted successfully
            print(f"[REFRESH-IMAGE] ✅ Job {job_id} submitted to Runpod (3 energy)")
    
    except Exception as e:
        print(f"[REFRESH-IMAGE] ❌ Error submitting job: {e}")
        
        # Decrement counter since submission failed
        await redis_queue.decrement_user_image_count(user_id)
        print(f"[REFRESH-IMAGE] 📊 Decremented user image count (submission failed)")
        
        with get_db() as db:
            crud.update_image_job_status(
                db,
                job_id,
                status="failed",
                error=str(e)
            )
        
        await bot.send_message(tg_chat_id, ERROR_MESSAGES["image_failed"])


@router.callback_query(lambda c: c.data.startswith("refresh_image:"))
async def refresh_image_callback(callback: types.CallbackQuery):
    """Handle refresh image button click - costs 3 energy (2 less than original)"""
    job_id_str = callback.data.split(":")[1]
    user_id = callback.from_user.id
    
    print(f"[REFRESH-IMAGE] 🔄 Refresh requested for job {job_id_str} by user {user_id}")
    
    # Check if user is premium
    with get_db() as db:
        is_premium = crud.check_user_premium(db, user_id)["is_premium"]
    
    # Check energy for non-premium users (refresh costs 3 energy)
    if not is_premium:
        with get_db() as db:
            if not crud.check_user_energy(db, user_id, required=3):
                await callback.answer("⚡ Not enough energy!", show_alert=True)
                await show_energy_upsell_message(callback.message, user_id)
                return
    
    # Get original job details
    with get_db() as db:
        job = crud.get_image_job(db, job_id_str)
        if not job:
            await callback.answer("❌ Job not found", show_alert=True)
            return
        
        chat = crud.get_chat_by_id(db, job.chat_id)
        if not chat:
            await callback.answer("❌ Chat not found", show_alert=True)
            return
        
        # Get persona for analytics
        persona = crud.get_persona_by_id(db, chat.persona_id)
        
        # Track refresh request
        analytics_service_tg.track_image_refresh(
            client_id=user_id,
            original_job_id=job_id_str,
            persona_id=chat.persona_id if chat else None,
            persona_name=persona.name if persona else None
        )
        
        # Deduct energy for refresh (3 for free users, 0 for premium)
        if not is_premium:
            if not crud.deduct_user_energy(db, user_id, amount=3):
                await callback.answer("❌ Failed to deduct energy", show_alert=True)
                return
            print(f"[REFRESH-IMAGE] ⚡ Deducted 3 energy for refresh")
        else:
            print(f"[REFRESH-IMAGE] 💎 Premium user - free refresh")
    
    # Answer the callback first
    await callback.answer("🔄 Refreshing image...")
    
    # Delete the old image message
    try:
        await callback.message.delete()
        print(f"[REFRESH-IMAGE] 🗑️  Deleted original image message")
        
        # Clear the stored message ID since we deleted it
        with get_db() as db:
            chat = crud.get_chat_by_tg_chat_id(db, callback.message.chat.id)
            if chat and chat.ext:
                # For JSONB fields, we must mark as modified
                from sqlalchemy.orm.attributes import flag_modified
                chat.ext["last_image_msg_id"] = None
                flag_modified(chat, "ext")
                db.commit()
                print(f"[REFRESH-IMAGE] 🗑️  Cleared last_image_msg_id tracking")
    except Exception as e:
        print(f"[REFRESH-IMAGE] ⚠️  Could not delete original image: {e}")
    
    # Generate new image with EXACT same prompts from original job (only seed changes)
    await generate_image_for_refresh(user_id, job_id_str, callback.message.chat.id)


@router.callback_query(lambda c: c.data == "cancel_image")
async def cancel_image_callback(callback: types.CallbackQuery):
    """Cancel image generation"""
    await callback.message.edit_text("✅ <b>Image generation cancelled.</b>")
    await callback.answer()



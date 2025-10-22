"""
Image generation handler
"""
from aiogram import types
from aiogram.filters import Command
from app.bot.loader import router, bot
from app.bot.keyboards.inline import build_image_prompt_keyboard
from app.db.base import get_db
from app.db import crud
from app.settings import get_app_config
from app.core.actions import send_action_repeatedly
from app.core.rate import check_rate_limit
from app.core.pipeline_adapter import build_image_prompts
from app.core.img_runpod import submit_image_job
from app.core.constants import ERROR_MESSAGES
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
        is_premium = crud.check_user_premium(db, user_id)
    
    # Check energy for non-premium users
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
    
    with get_db() as db:
        # Deduct energy for non-premium users
        if not is_premium:
            if not crud.deduct_user_energy(db, user_id, amount=5):
                await message.answer("❌ Failed to deduct energy. Please try again.")
                return
            print(f"[IMAGE] ⚡ Deducted 5 energy from user {user_id}")
        else:
            print(f"[IMAGE] 💎 Premium user {user_id} - free image generation")
        
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
    
    # Send generating message
    generating_msg = await message.answer(
        ERROR_MESSAGES["image_generating"]
    )
    
    # Submit to Runpod with upload_photo action
    try:
        async with send_action_repeatedly(bot, message.chat.id, "upload_photo"):
            await submit_image_job(
                job_id=job_id,
                prompt=positive_prompt,
                negative_prompt=negative_prompt,
                seed=seed
            )
            
            # Job submitted successfully
            # Actual image will be delivered via webhook callback
            print(f"[IMAGE] Job {job_id} submitted to Runpod")
    
    except Exception as e:
        print(f"[IMAGE] Error submitting job: {e}")
        
        with get_db() as db:
            crud.update_image_job_status(
                db,
                job_id,
                status="failed",
                error=str(e)
            )
        
        await generating_msg.edit_text(
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
        f"⚡ <b>You're out of energy!</b>\n\n"
        f"You have {user_energy['energy']}/{user_energy['max_energy']} energy.\n"
        f"Image generation costs <b>5 energy</b> per image.\n\n"
        f"💎 Get more energy to continue generating amazing images!",
        reply_markup=keyboard
    )
    
    # Save this message ID for later deletion
    with get_db() as db:
        crud.save_energy_upsell_message(db, user_id, sent_msg.message_id, message.chat.id)


async def generate_image_for_refresh_with_msg(generating_msg: types.Message, user_id: int, user_prompt: str, tg_chat_id: int):
    """Generate image for refresh (energy already deducted - costs 3 energy)"""
    config = get_app_config()
    
    # Rate limit check
    allowed, _ = await check_rate_limit(
        user_id,
        "image",
        config["limits"]["image_per_min"],
        60
    )
    
    if not allowed:
        await generating_msg.edit_text(ERROR_MESSAGES["rate_limit_image"])
        return
    
    with get_db() as db:
        # Get active chat
        chat = crud.get_active_chat(db, tg_chat_id, user_id)
        
        if not chat:
            await generating_msg.edit_text(ERROR_MESSAGES["no_persona"])
            return
        
        # Get persona
        persona = crud.get_persona_by_id(db, chat.persona_id)
        
        if not persona:
            await generating_msg.edit_text(ERROR_MESSAGES["persona_not_found"])
            return
        
        # Build image prompts using pipeline adapter
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
    
    # Submit to Runpod with upload_photo action
    try:
        async with send_action_repeatedly(bot, tg_chat_id, "upload_photo"):
            await submit_image_job(
                job_id=job_id,
                prompt=positive_prompt,
                negative_prompt=negative_prompt,
                seed=seed
            )
            
            # Job submitted successfully
            print(f"[REFRESH-IMAGE] ✅ Job {job_id} submitted to Runpod (3 energy)")
    
    except Exception as e:
        print(f"[REFRESH-IMAGE] ❌ Error submitting job: {e}")
        
        with get_db() as db:
            crud.update_image_job_status(
                db,
                job_id,
                status="failed",
                error=str(e)
            )
        
        await generating_msg.edit_text(ERROR_MESSAGES["image_failed"])


@router.callback_query(lambda c: c.data.startswith("refresh_image:"))
async def refresh_image_callback(callback: types.CallbackQuery):
    """Handle refresh image button click - costs 3 energy (2 less than original)"""
    job_id_str = callback.data.split(":")[1]
    user_id = callback.from_user.id
    
    print(f"[REFRESH-IMAGE] 🔄 Refresh requested for job {job_id_str} by user {user_id}")
    
    # Check if user is premium
    with get_db() as db:
        is_premium = crud.check_user_premium(db, user_id)
    
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
        
        # Get user prompt from original job
        user_prompt = job.ext.get("user_prompt", "") if job.ext else ""
        
        # Deduct 3 energy for refresh (non-premium only)
        if not is_premium:
            if not crud.deduct_user_energy(db, user_id, amount=3):
                await callback.answer("❌ Failed to deduct energy", show_alert=True)
                return
            print(f"[REFRESH-IMAGE] ⚡ Deducted 3 energy for refresh")
        else:
            print(f"[REFRESH-IMAGE] 💎 Premium user - free refresh")
    
    # Answer the callback first
    await callback.answer("🔄 Refreshing image...")
    
    # Send "Generating..." message before deleting the old image
    generating_msg = await callback.message.answer("🎨 <b>Generating your image...</b>")
    
    # Delete the old image message
    try:
        await callback.message.delete()
        print(f"[REFRESH-IMAGE] 🗑️  Deleted original image message")
        
        # Clear the stored message ID since we deleted it
        with get_db() as db:
            chat = crud.get_chat_by_tg_chat_id(db, callback.message.chat.id)
            if chat and chat.ext:
                chat.ext["last_image_msg_id"] = None
                db.commit()
                print(f"[REFRESH-IMAGE] 🗑️  Cleared last_image_msg_id tracking")
    except Exception as e:
        print(f"[REFRESH-IMAGE] ⚠️  Could not delete original image: {e}")
    
    # Generate new image with same prompt (but skip energy deduction since we already did it)
    await generate_image_for_refresh_with_msg(generating_msg, user_id, user_prompt, callback.message.chat.id)


@router.callback_query(lambda c: c.data == "cancel_image")
async def cancel_image_callback(callback: types.CallbackQuery):
    """Cancel image generation"""
    await callback.message.edit_text("✅ <b>Image generation cancelled.</b>")
    await callback.answer()



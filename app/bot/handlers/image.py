"""
Image generation handler
"""
from aiogram import types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from app.bot.loader import router, bot
from app.bot.keyboards.inline import build_image_prompt_keyboard
from app.bot.states import ImageGeneration
from app.db.base import get_db
from app.db import crud
from app.db.models import User
from app.settings import get_app_config, get_ui_text
from app.core.actions import send_action_repeatedly
from app.core.rate import check_rate_limit
from app.core.pipeline_adapter import build_image_prompts
from app.core.img_runpod import submit_image_job
from app.core.constants import ERROR_MESSAGES
from app.core import analytics_service_tg
from app.core.persona_cache import get_persona_by_id, get_persona_field
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
    
    # Check if user is premium (premium users pay 3 energy, free users pay 5)
    with get_db() as db:
        is_premium = crud.check_user_premium(db, user_id)["is_premium"]
    
    # Check energy (3 for premium, 5 for free users)
    energy_cost = 3 if is_premium else 5
    with get_db() as db:
        if not crud.check_user_energy(db, user_id, required=energy_cost):
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
    
    # Check concurrent image limit (if enabled)
    from app.core import redis_queue
    from app.settings import settings
    if settings.CONCURRENT_IMAGE_LIMIT_ENABLED:
        current_count = await redis_queue.get_user_image_count(user_id)
        if current_count >= settings.CONCURRENT_IMAGE_LIMIT_NUMBER:
            print(f"[IMAGE] ⏭️  User {user_id} has reached concurrent image limit ({current_count}/{settings.CONCURRENT_IMAGE_LIMIT_NUMBER}) - skipping")
            return
    
    with get_db() as db:
        # Deduct energy (3 for premium, 5 for free users)
        energy_cost = 3 if is_premium else 5
        if not crud.deduct_user_energy(db, user_id, amount=energy_cost):
            await message.answer("❌ Failed to deduct energy. Please try again.")
            return
        print(f"[IMAGE] ⚡ Deducted {energy_cost} energy from user {user_id} ({'premium' if is_premium else 'free'})")
        
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
    from app.settings import settings, get_ui_text
    
    with get_db() as db:
        user_energy = crud.get_user_energy(db, user_id)
        user_language = crud.get_user_language(db, user_id)
        is_premium = crud.check_user_premium(db, user_id)["is_premium"]
        
        # Delete previous upsell message if exists
        upsell_msg_id, upsell_chat_id = crud.get_and_clear_energy_upsell_message(db, user_id)
        if upsell_msg_id and upsell_chat_id:
            try:
                await bot.delete_message(chat_id=upsell_chat_id, message_id=upsell_msg_id)
            except Exception:
                pass
    
    # Send new upsell message
    miniapp_url = f"{settings.public_url}/miniapp"
    keyboard = build_energy_upsell_keyboard(miniapp_url, language=user_language)
    
    tokens = user_energy['tokens']
    
    # Different message for premium users
    if is_premium:
        message_text = (
            f"<b>{get_ui_text('tokens.outOfTokensPremium.title', user_language)}</b>\n\n"
            f"{get_ui_text('tokens.outOfTokensPremium.balance', user_language, tokens=tokens)}\n\n"
            f"<b>{get_ui_text('tokens.outOfTokensPremium.costs', user_language)}</b>\n"
            f"{get_ui_text('tokens.outOfTokensPremium.message', user_language)}\n"
            f"{get_ui_text('tokens.outOfTokensPremium.image', user_language)}\n"
            f"{get_ui_text('tokens.outOfTokensPremium.voice', user_language)}\n\n"
            f"{get_ui_text('tokens.outOfTokensPremium.buyMore', user_language)}"
        )
    else:
        # Emotional message for free users
        message_text = (
            f"<b>{get_ui_text('tokens.outOfTokens.title', user_language)}</b>\n\n"
            f"{get_ui_text('tokens.outOfTokens.subtitle', user_language)}\n\n"
            f"{get_ui_text('tokens.outOfTokens.balance', user_language, tokens=tokens)}\n\n"
            f"{get_ui_text('tokens.outOfTokens.waiting', user_language)}\n\n"
            f"<b>{get_ui_text('tokens.outOfTokens.costs', user_language)}</b>\n"
            f"{get_ui_text('tokens.outOfTokens.messageBack', user_language)}\n"
            f"{get_ui_text('tokens.outOfTokens.generateImage', user_language)}\n"
            f"{get_ui_text('tokens.outOfTokens.generateVoice', user_language)}\n\n"
            f"<b>{get_ui_text('tokens.outOfTokens.fixNow', user_language)}</b>\n"
            f"{get_ui_text('tokens.outOfTokens.claimDaily', user_language)}\n"
            f"{get_ui_text('tokens.outOfTokens.premiumBenefits', user_language)}\n"
            f"{get_ui_text('tokens.outOfTokens.instantTokens', user_language)}"
        )
    
    sent_msg = await message.answer(
        message_text,
        reply_markup=keyboard
    )
    
    # Save this message ID for later deletion
    with get_db() as db:
        crud.save_energy_upsell_message(db, user_id, sent_msg.message_id, message.chat.id)


async def generate_image_for_refresh(user_id: int, original_job_id: str, tg_chat_id: int):
    """Generate image for refresh - costs 3 energy for free users, 0 for premium
    
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
    
    # Check concurrent image limit (if enabled)
    from app.core import redis_queue
    from app.settings import settings
    if settings.CONCURRENT_IMAGE_LIMIT_ENABLED:
        current_count = await redis_queue.get_user_image_count(user_id)
        if current_count >= settings.CONCURRENT_IMAGE_LIMIT_NUMBER:
            print(f"[REFRESH-IMAGE] ⏭️  User {user_id} has reached concurrent image limit ({current_count}/{settings.CONCURRENT_IMAGE_LIMIT_NUMBER}) - skipping")
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
        
        # Get persona directly from original job (works for both chat and standalone images)
        persona = crud.get_persona_by_id(db, original_job.persona_id)
        
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
        # Use original job's chat_id (None for standalone images, chat.id for chat images)
        seed = random.randint(1, 2147483647)
        job = crud.create_image_job(
            db,
            user_id=user_id,
            persona_id=persona.id,
            prompt=positive_prompt,
            negative_prompt=negative_prompt,
            chat_id=original_job.chat_id,
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
    """Handle refresh image button click - costs 3 energy for free, 0 for premium"""
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
        
        # Get persona for analytics directly from job (job always has persona_id)
        persona = crud.get_persona_by_id(db, job.persona_id)
        
        # Track refresh request
        analytics_service_tg.track_image_refresh(
            client_id=user_id,
            original_job_id=job_id_str,
            persona_id=job.persona_id,
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


@router.callback_query(lambda c: c.data.startswith("generate_image_for_persona:"))
async def generate_image_for_persona_callback(callback: types.CallbackQuery, state: FSMContext):
    """Handle 'Generate Image' button - ask for user prompt"""
    persona_id = callback.data.split(":")[1]
    
    # Get user language and archive all chats
    with get_db() as db:
        from app.bot.handlers.start import get_and_update_user_language
        user_language = get_and_update_user_language(db, callback.from_user)
        
        # Archive all user chats so messages don't continue previous conversation
        crud.archive_all_user_chats(db, callback.from_user.id)
        print(f"[IMAGE-GEN] 📦 Archived all chats for user {callback.from_user.id}")
    
    # Get persona from cache
    persona = get_persona_by_id(persona_id)
    if not persona:
        error_msg = get_ui_text("errors.persona_not_found", language=user_language)
        await callback.answer(error_msg, show_alert=True)
        return
    
    persona_name = get_persona_field(persona, 'name', language=user_language) or persona["name"]
    
    # Save persona_id to state for later use
    await state.update_data(persona_id=persona_id, persona_name=persona_name, user_language=user_language)
    await state.set_state(ImageGeneration.waiting_for_prompt)
    
    # Ask user for prompt
    prompt_text = get_ui_text("image.prompt_request", language=user_language, persona_name=persona_name)
    await callback.message.edit_text(prompt_text)
    await callback.answer()


@router.message(ImageGeneration.waiting_for_prompt)
async def handle_image_prompt_input(message: types.Message, state: FSMContext):
    """Handle user's custom image prompt and generate image"""
    # Get stored data from state
    state_data = await state.get_data()
    persona_id = state_data.get("persona_id")
    persona_name = state_data.get("persona_name")
    user_language = state_data.get("user_language", "en")
    
    if not persona_id:
        await state.clear()
        await message.answer(get_ui_text("errors.session_expired", language=user_language))
        return
    
    user_prompt = message.text
    
    # IMMEDIATELY switch to waiting_for_another state to prevent duplicate processing
    await state.update_data(persona_id=persona_id, persona_name=persona_name, user_language=user_language)
    await state.set_state(ImageGeneration.waiting_for_another)
    
    # Show loading message
    loading_text = get_ui_text("image.generating", language=user_language, persona_name=persona_name)
    loading_msg = await message.answer(loading_text)
    
    # Generate image (pass loading_msg_id so it can be deleted when image is ready)
    await generate_image_with_prompt(
        message, 
        message.from_user.id, 
        persona_id, 
        user_prompt, 
        user_language,
        loading_msg_id=loading_msg.message_id
    )
    # Loading message will be deleted by webhook callback when image is ready


@router.message(ImageGeneration.waiting_for_another)
async def handle_another_image_prompt(message: types.Message, state: FSMContext):
    """Handle text input when user already generated an image - ask for confirmation"""
    from app.bot.keyboards.inline import build_another_image_keyboard
    
    # Get stored data from state
    state_data = await state.get_data()
    persona_id = state_data.get("persona_id")
    persona_name = state_data.get("persona_name")
    user_language = state_data.get("user_language", "en")
    
    if not persona_id:
        await state.clear()
        await message.answer(get_ui_text("errors.session_expired", language=user_language))
        return
    
    user_prompt = message.text
    
    # Save the new prompt for later use
    await state.update_data(pending_prompt=user_prompt)
    
    # Ask for confirmation
    confirm_text = get_ui_text("image.another_prompt", language=user_language, prompt=user_prompt, persona_name=persona_name)
    keyboard = build_another_image_keyboard(language=user_language)
    await message.answer(confirm_text, reply_markup=keyboard)


@router.callback_query(lambda c: c.data == "confirm_another_image")
async def confirm_another_image_callback(callback: types.CallbackQuery, state: FSMContext):
    """Confirm and generate another image"""
    # Get stored data from state
    state_data = await state.get_data()
    persona_id = state_data.get("persona_id")
    persona_name = state_data.get("persona_name")
    user_language = state_data.get("user_language", "en")
    pending_prompt = state_data.get("pending_prompt")
    
    if not persona_id or not pending_prompt:
        await state.clear()
        await callback.answer(get_ui_text("errors.session_expired", language=user_language), show_alert=True)
        return
    
    await callback.answer()
    
    # Delete the confirmation message
    try:
        await callback.message.delete()
    except Exception:
        pass
    
    # Show loading message
    loading_text = get_ui_text("image.generating", language=user_language, persona_name=persona_name)
    loading_msg = await callback.message.answer(loading_text)
    
    # Generate image (pass loading_msg_id so it can be deleted when image is ready)
    await generate_image_with_prompt(
        callback.message, 
        callback.from_user.id, 
        persona_id, 
        pending_prompt, 
        user_language,
        loading_msg_id=loading_msg.message_id
    )
    # Loading message will be deleted by webhook callback when image is ready
    
    # Stay in waiting_for_another state
    await state.update_data(pending_prompt=None)


@router.callback_query(lambda c: c.data == "cancel_another_image")
async def cancel_another_image_callback(callback: types.CallbackQuery, state: FSMContext):
    """Cancel another image generation and clear state"""
    await state.clear()
    await callback.answer()
    
    # Delete the confirmation message
    try:
        await callback.message.delete()
    except Exception:
        pass


async def generate_image_with_prompt(message: types.Message, user_id: int, persona_id: str, user_prompt: str, user_language: str = "en", loading_msg_id: int = None):
    """Generate image for user with given persona and prompt using image brain
    
    Does NOT create a chat - just generates the image based on persona and user prompt.
    If loading_msg_id is provided, it will be stored in job.ext so the callback can delete it.
    """
    config = get_app_config()
    
    # Check if user is premium (premium users pay 3 energy, free users pay 5)
    with get_db() as db:
        is_premium = crud.check_user_premium(db, user_id)["is_premium"]
    
    # Check energy (3 for premium, 5 for free users)
    energy_cost = 3 if is_premium else 5
    with get_db() as db:
        if not crud.check_user_energy(db, user_id, required=energy_cost):
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
    
    # Check concurrent image limit (if enabled)
    from app.core import redis_queue
    from app.settings import settings
    if settings.CONCURRENT_IMAGE_LIMIT_ENABLED:
        current_count = await redis_queue.get_user_image_count(user_id)
        if current_count >= settings.CONCURRENT_IMAGE_LIMIT_NUMBER:
            print(f"[IMAGE] ⏭️  User {user_id} has reached concurrent image limit ({current_count}/{settings.CONCURRENT_IMAGE_LIMIT_NUMBER}) - skipping")
            return
    
    # Get persona from cache
    persona = get_persona_by_id(persona_id)
    if not persona:
        await message.answer(get_ui_text("errors.persona_not_found", language=user_language))
        return
    
    with get_db() as db:
        # Deduct energy (3 for premium, 5 for free users)
        if not crud.deduct_user_energy(db, user_id, amount=energy_cost):
            await message.answer("❌ Failed to deduct energy. Please try again.")
            return
        print(f"[IMAGE] ⚡ Deducted {energy_cost} energy from user {user_id} ({'premium' if is_premium else 'free'})")
        
        # Get user's global message count for priority determination
        user = db.query(User).filter(User.id == user_id).first()
        global_message_count = user.global_message_count if user else 999
        
        # Use image brain to generate prompt (without system message)
        from app.core.brains.image_prompt_engineer import generate_image_plan, assemble_final_prompt
        
        # Generate image tags using the brain
        try:
            # Get persona name for context
            persona_name = persona.get("name", "She")
            
            # Build context that matches what the brain expects:
            # - dialogue_response = what the assistant (persona) is DOING (the scene)
            # - state = current scene description from persona
            # - user_message = the original request
            
            # Format dialogue_response as if the persona is doing/showing what user requested
            # This tells the brain "this is what's actually happening"
            dialogue_response = f"*{persona_name} {user_prompt}*"
            
            # Use persona description as scene state
            state = persona.get("description", "")
            
            image_tags = await generate_image_plan(
                state=state,
                dialogue_response=dialogue_response,  # What persona is doing
                user_message=user_prompt,  # What user requested
                persona=persona,
                chat_history=[],  # No chat history for standalone
                previous_image_prompt=None
            )
            
            print(f"[IMAGE] Generated tags via brain: {image_tags[:100]}...")
            
            # Assemble final prompt - use only image_prompt (SDXL tags), NOT prompt (dialogue description)
            persona_image_prompt = persona.get("image_prompt") or ""
            positive_prompt, negative_prompt = assemble_final_prompt(image_tags, persona_image_prompt)
            
        except Exception as e:
            print(f"[IMAGE] ⚠️ Failed to generate prompt via brain: {e}, falling back to simple prompt")
            # Fallback to simple prompt building
            positive_prompt, negative_prompt = build_image_prompts(
                {},
                persona,
                user_prompt,
                None,  # No chat
                ""
            )
        
        # Create image job (without chat_id - standalone image generation)
        seed = random.randint(1, 2147483647)
        job_ext = {
            "seed": seed, 
            "user_prompt": user_prompt,
            "tg_chat_id": message.chat.id  # Store tg_chat_id for callback
        }
        if loading_msg_id:
            job_ext["loading_msg_id"] = loading_msg_id
        
        job = crud.create_image_job(
            db,
            user_id=user_id,
            persona_id=persona_id,
            prompt=positive_prompt,
            negative_prompt=negative_prompt,
            chat_id=None,  # No chat needed
            ext=job_ext
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



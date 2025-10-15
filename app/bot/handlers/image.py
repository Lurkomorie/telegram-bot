"""
Image generation handler
"""
from aiogram import types
from aiogram.filters import Command
from app.bot.loader import router, bot
from app.bot.keyboards.inline import build_image_prompt_keyboard
from app.db.base import get_db
from app.db import crud
from app.settings import get_prompts_config, get_app_config
from app.core.actions import send_action_repeatedly
from app.core.rate import check_rate_limit
from app.core.pipeline_adapter import build_image_prompts
from app.core.img_runpod import submit_image_job
import random


@router.message(Command("image"))
async def cmd_image(message: types.Message):
    """Handle /image command"""
    prompts = get_prompts_config()
    
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
    prompts = get_prompts_config()
    
    # Rate limit check
    allowed, count = await check_rate_limit(
        user_id,
        "image",
        config["limits"]["image_per_min"],
        60
    )
    
    if not allowed:
        await message.answer(prompts["text_blocks"]["rate_limit_image"])
        return
    
    with get_db() as db:
        # Get active chat
        chat = crud.get_active_chat(db, message.chat.id, user_id)
        
        if not chat:
            await message.answer("Please select an AI girl first using /start")
            return
        
        # Get persona
        persona = crud.get_persona_by_id(db, chat.persona_id)
        if not persona:
            await message.answer("Persona not found. Please start over with /start")
            return
        
        # Build image prompts using pipeline adapter
        positive_prompt, negative_prompt = build_image_prompts(
            prompts,
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
        prompts["text_blocks"]["image_generating"]
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
            prompts["text_blocks"]["image_failed"]
        )


@router.callback_query(lambda c: c.data == "cancel_image")
async def cancel_image_callback(callback: types.CallbackQuery):
    """Cancel image generation"""
    await callback.message.edit_text("✅ <b>Image generation cancelled.</b>")
    await callback.answer()



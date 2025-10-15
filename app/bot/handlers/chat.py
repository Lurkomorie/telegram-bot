"""
Text chat handler with AI responses
"""
from aiogram import types, F
from app.bot.loader import router, bot
from app.db.base import get_db
from app.db import crud
from app.settings import get_prompts_config, get_app_config
from app.core.actions import send_action_repeatedly
from app.core.rate import check_rate_limit
from app.core.pipeline_adapter import (
    build_llm_messages,
    update_conversation_state,
    parse_previous_state,
    create_initial_state
)
from app.core.llm_openrouter import generate_text


@router.message(F.text & ~F.text.startswith("/"))
async def handle_text_message(message: types.Message):
    """Handle regular text messages"""
    user_id = message.from_user.id
    user_text = message.text
    
    prompts = get_prompts_config()
    config = get_app_config()
    
    # Rate limit check
    allowed, count = await check_rate_limit(
        user_id,
        "text",
        config["limits"]["text_per_min"],
        60
    )
    
    if not allowed:
        await message.answer(prompts["text_blocks"]["rate_limit_text"])
        return
    
    with get_db() as db:
        # Get or create user
        user = crud.get_or_create_user(
            db,
            telegram_id=user_id,
            username=message.from_user.username,
            first_name=message.from_user.first_name
        )
        
        # Get active chat
        chat = crud.get_active_chat(db, message.chat.id, user_id)
        
        if not chat:
            # No active persona selected
            await message.answer(
                "Please select an AI girl first using /start"
            )
            return
        
        # Get persona
        persona = crud.get_persona_by_id(db, chat.persona_id)
        if not persona:
            await message.answer("Persona not found. Please start over with /start")
            return
        
        # Extract data from ORM objects before session closes
        chat_id = chat.id
        chat_state_snapshot = chat.state_snapshot
        persona_data = {
            "id": persona.id,
            "name": persona.name,
            "key": persona.key,
            "system_prompt": persona.system_prompt,
            "style": persona.style,
            "negatives": persona.negatives,
            "appearance": persona.appearance
        }
        
        # Save user message
        crud.create_message(db, chat_id, "user", user_text)
        
        # Get recent messages for context
        messages = crud.get_chat_messages(
            db,
            chat_id,
            limit=config["limits"]["max_history_messages"]
        )
        
        # Extract message data from ORM objects
        messages_data = [
            {"role": m.role, "text": m.text, "created_at": m.created_at}
            for m in messages
        ]
    
    # Generate AI response with typing indicator
    try:
        async with send_action_repeatedly(bot, message.chat.id, "typing"):
            # Build LLM messages using extracted data
            llm_messages = build_llm_messages(
                prompts,
                persona_data,
                messages_data[:-1],  # Exclude the just-saved user message
                user_text,
                {"state_snapshot": chat_state_snapshot},
                config["limits"]["max_history_messages"]
            )
            
            # Get persona style overrides
            persona_style = persona_data["style"] or {}
            temperature = persona_style.get("temperature")
            max_tokens = persona_style.get("max_tokens")
            
            # Generate response
            assistant_response = await generate_text(
                llm_messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
    
    except Exception as e:
        print(f"[CHAT] Error generating response: {e}")
        await message.answer(
            "Sorry, I'm having trouble responding right now. Please try again in a moment."
        )
        return
    
    # Update conversation state
    with get_db() as db:
        # Get current state
        current_state = parse_previous_state(chat_state_snapshot)
        if not current_state:
            current_state = create_initial_state(persona_data)
        
        # Update state based on conversation
        new_state = update_conversation_state(
            current_state,
            user_text,
            assistant_response,
            persona_data
        )
        
        # Save state and assistant message
        crud.update_chat_state(db, chat_id, new_state)
        crud.create_message(db, chat_id, "assistant", assistant_response)
    
    # Send response
    await message.answer(assistant_response)



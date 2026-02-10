"""
Multi-Brain Pipeline Orchestrator
Coordinates Dialogue Specialist → State Resolver → Image Generation
"""
import asyncio
import json
from datetime import datetime
from uuid import UUID
from app.core.brains.state_resolver import resolve_state
from app.core.brains.dialogue_specialist import generate_dialogue
from app.core.brains.image_prompt_engineer import generate_image_plan, assemble_final_prompt
from app.core.chat_actions import ChatActionManager
from app.core.logging_utils import log_verbose, log_always, is_development, PipelineTimer, log_dev_section
from app.core.telegram_utils import escape_markdown_v2
from app.core import redis_queue
from app.core.context_summarizer import generate_context_summary
from app.db.base import get_db
from app.db import crud
from app.db.models import User
from app.bot.loader import bot
from app.core import analytics_service_tg
from app.settings import get_ui_text


def _is_explicit_visual_request(text: str) -> bool:
    """Check if user explicitly requests to see something visual.
    
    Supports both English and Russian keywords.
    """
    text_lower = text.lower()
    
    # English patterns
    en_patterns = [
        "show me",
        "let me see",
        "can i see",
        "want to see",
        "i want to see",
        "i wanna see",
        "what do you look like",
        "how do you look",
        "send me a pic",
        "send a pic",
        "send a photo",
        "send me a photo",
        "take a photo",
        "take a picture",
        "selfie",
    ]
    
    # Russian patterns
    ru_patterns = [
        # Прямые просьбы показать
        "покажи",
        "покажись",
        "покаж",
        "показывай",
        "показать",
        "показала",
        "показываешь",
        # Хочу увидеть/посмотреть
        "хочу увидеть",
        "хочу посмотреть",
        "хочу глянуть",
        "хочу взглянуть",
        "хотел бы увидеть",
        "хотел бы посмотреть",
        "хотелось бы увидеть",
        "хотелось бы посмотреть",
        # Дай/можно посмотреть
        "дай посмотреть",
        "дай глянуть",
        "дай взглянуть",
        "можно посмотреть",
        "можно глянуть",
        "можно взглянуть",
        "можно увидеть",
        # Как выглядишь
        "как ты выглядишь",
        "как выглядишь",
        "как ты сейчас выглядишь",
        "выглядишь сейчас",
        # Фото/фотки
        "скинь фото",
        "скинь фотку",
        "скинь фоточку",
        "скинь картинку",
        "скинь пикчу",
        "скинь пик",
        "скидывай фото",
        "скидывай фотку",
        "кинь фото",
        "кинь фотку",
        "кинь фоточку",
        "кидай фото",
        "кидай фотку",
        "пришли фото",
        "пришли фотку",
        "пришли фоточку",
        "присылай фото",
        "отправь фото",
        "отправь фотку",
        # Селфи
        "сфоткайся",
        "сфоткай себя",
        "сфотографируйся",
        "сфотографируй себя",
        "сделай фото",
        "сделай фотку",
        "сделай фоточку",
        "сделай селфи",
        "селфи",
        "селфак",
        "селфачок",
        # Давай посмотрим
        "давай посмотрю",
        "давай гляну",
        "давай взгляну",
        "ну покажи",
        "а покажи",
        "ну давай покажи",
        # Видеть тебя
        "вижу тебя",
        "увидеть тебя",
        "посмотреть на тебя",
        "глянуть на тебя",
        "взглянуть на тебя",
        # Что на тебе
        "что на тебе",
        "что ты носишь",
        "что ты надела",
        "что одето",
        "во что одета",
        "как одета",
        # Покажи себя/тело
        "покажи себя",
        "покажи тело",
        "покажи грудь",
        "покажи попу",
        "покажи попку",
        "покажи ножки",
        "покажи ноги",
        "покажи киску",
        "покажи письку",
        "покажи всё",
        "покажи все",
        # Разные формулировки
        "продемонстрируй",
        "продемонстрируй себя",
        "засветись",
        "засвети",
        "открой камеру",
        "включи камеру",
    ]
    
    all_patterns = en_patterns + ru_patterns
    return any(pattern in text_lower for pattern in all_patterns)


def _log_brain_inputs(brain_name: str, **kwargs):
    """Helper to log all inputs sent to a brain"""
    print(f"\n{'='*20} BRAIN INPUT: {brain_name} {'='*20}")
    for key, value in kwargs.items():
        print(f"🔹 {key}:")
        try:
            if isinstance(value, list):
                print(f"   (List with {len(value)} items)")
                if value and isinstance(value[0], dict) and "role" in value[0]:
                    # Chat history - log all of it
                    for i, msg in enumerate(value, 1):
                        content = msg.get("content", "")
                        # Indent content for readability
                        print(f"   {i}. [{msg.get('role')}] {content}")
                else:
                    # Try to dump as JSON, fallback to string
                    try:
                        print(f"   {json.dumps(value, default=str, indent=2)}")
                    except:
                        print(f"   {str(value)}")
            elif isinstance(value, dict):
                try:
                    print(f"   {json.dumps(value, default=str, indent=2)}")
                except:
                    print(f"   {str(value)}")
            else:
                print(f"   {value}")
        except Exception as e:
            print(f"   (Error logging value: {e})")
            print(f"   {str(value)}")
    print(f"{'='*60}\n")


async def process_message_pipeline(
    chat_id: UUID,
    user_id: int,
    tg_chat_id: int
):
    """
    Main pipeline with Redis-based batching: Dialogue → State → [Save] → Image (background)
    
    Flow:
    1. Set processing lock
    2. Loop while messages in queue:
       a. Get batch from Redis
       b. Fetch data (chat, persona, history)
       c. Brain 1: Generate dialogue (using previous state)
       d. Brain 2: Resolve state (update based on dialogue)
       e. Save batch + response to DB
       f. Send response to user
       g. Clear batch from Redis
    3. Start image generation (background)
    4. Clear processing lock
    """
    print(f"[PIPELINE] 🚀 ============= STARTING PIPELINE =============")
    print(f"[PIPELINE] 📊 Chat ID: {chat_id}")
    print(f"[PIPELINE] 👤 User ID: {user_id}")
    print(f"[PIPELINE] 📱 TG Chat ID: {tg_chat_id}")
    
    # Create pipeline timer for development
    pipeline_timer = PipelineTimer(f"Message Pipeline (Chat: {chat_id})")
    pipeline_timer.start_stage("Initialization")
    
    # Processing lock already set in handler (before batch delay)
    print(f"[PIPELINE] 🔒 Processing lock confirmed active")
    
    # Stop any existing action (e.g. upload_photo from previous image generation)
    from app.core.action_registry import stop_and_remove_action
    await stop_and_remove_action(tg_chat_id)
    print(f"[PIPELINE] 🧹 Cleared any existing chat actions")
    
    # Create action manager for persistent indicators
    action_mgr = ChatActionManager(bot, tg_chat_id)
    
    pipeline_timer.end_stage()
    
    try:
        batch_num = 0
        
        # Loop to handle messages that arrive during processing
        while True:
            batch_num += 1
            
            pipeline_timer.start_stage(f"Batch #{batch_num}: Get Messages from Queue")
            
            # Get ALL messages currently in queue
            batch_messages = await redis_queue.get_batch_messages(chat_id)
            
            if not batch_messages:
                if batch_num == 1:
                    log_always(f"[PIPELINE] ⚠️  Queue empty (unexpected)")
                else:
                    log_always(f"[PIPELINE] ✅ No more messages in queue")
                pipeline_timer.end_stage()
                break
            
            pipeline_timer.end_stage()
            
            log_always(f"[PIPELINE] 📦 Batch #{batch_num}: {len(batch_messages)} message(s)")
            
            # Combine ALL messages into one text
            batched_text = "\n".join([msg["text"] for msg in batch_messages])
            if len(batch_messages) > 1:
                log_always(f"[PIPELINE] ✅ BATCHING {len(batch_messages)} messages together!")
                for i, msg in enumerate(batch_messages, 1):
                    log_always(f"[PIPELINE]    #{i}: {msg['text'][:50]}")
            log_always(f"[PIPELINE] 💬 Combined text: {batched_text[:200]}...")
            
            pipeline_timer.start_stage(f"Batch #{batch_num}: Process Messages")
            
            # Process as ONE batch with ONE response
            await _process_single_batch(
                chat_id=chat_id,
                user_id=user_id,
                tg_chat_id=tg_chat_id,
                batch_messages=batch_messages,
                batched_text=batched_text,
                action_mgr=action_mgr,
                pipeline_timer=pipeline_timer
            )
            
            pipeline_timer.end_stage()
            
            pipeline_timer.start_stage(f"Batch #{batch_num}: Clear Queue")
            
            # Clear queue ONLY after successful processing (prevents message loss on error)
            await redis_queue.clear_batch_messages(chat_id)
            log_always(f"[PIPELINE] ✅ Batch #{batch_num} complete, queue cleared")
            
            pipeline_timer.end_stage()
            
            # Brief wait to catch any messages that arrived during processing
            await asyncio.sleep(0.5)
            log_verbose(f"[PIPELINE] 🔍 Checking for more...")
        
        # Finish timing
        pipeline_timer.finish()
        
    except Exception as e:
        print(f"[PIPELINE] ❌ Pipeline error: {type(e).__name__}: {e}")
        if is_development():
            import traceback
            traceback.print_exc()
        
        # Clear processing lock on error
        await redis_queue.set_processing_lock(chat_id, False)
        log_verbose(f"[PIPELINE] 🔓 Processing lock CLEARED (error recovery)")
        
        await action_mgr.stop()
        raise
    finally:
        # Always clear processing lock
        await redis_queue.set_processing_lock(chat_id, False)
        log_verbose(f"[PIPELINE] 🔓 Processing lock CLEARED")


async def _process_single_batch(
    chat_id: UUID,
    user_id: int,
    tg_chat_id: int,
    batch_messages: list[dict],  # List of {user_id, text, tg_chat_id}
    batched_text: str,
    action_mgr: ChatActionManager,
    pipeline_timer: PipelineTimer
):
    """Process a single batch of messages"""
    try:
        log_dev_section("BATCH PROCESSING")
        
        pipeline_timer.start_stage("Start Typing Indicator")
        
        # Show typing indicator
        log_verbose(f"[BATCH] ⌨️  Starting typing indicator...")
        await action_mgr.start("typing")
        log_verbose(f"[BATCH] ✅ Typing indicator started")
        
        pipeline_timer.end_stage()
        pipeline_timer.start_stage("Fetch Data from Database")
        
        # 1. Fetch data
        log_verbose(f"[BATCH] 📚 Step 1: Fetching data from database...")
        with get_db() as db:
            log_verbose(f"[BATCH] 🔍 Looking up chat {chat_id}")
            chat = crud.get_chat_by_id(db, chat_id)
            if not chat:
                raise ValueError(f"Chat {chat_id} not found")
            log_verbose(f"[BATCH] ✅ Chat found")
                
            log_verbose(f"[BATCH] 🔍 Looking up persona {chat.persona_id}")
            persona = crud.get_persona_by_id(db, chat.persona_id)
            if not persona:
                raise ValueError(f"Persona {chat.persona_id} not found")
            log_verbose(f"[BATCH] ✅ Persona found: {persona.name}")
                
            messages = crud.get_chat_messages(db, chat_id, limit=20)
            
            # Get previous image prompt if available
            log_verbose(f"[BATCH] 🔍 Looking up previous image job...")
            previous_image_job = crud.get_last_completed_image_job(db, chat_id)
            previous_image_prompt = previous_image_job.prompt if previous_image_job else None
            if previous_image_prompt:
                log_verbose(f"[BATCH] ✅ Found previous image prompt ({len(previous_image_prompt)} chars)")
                if previous_image_job:
                    log_verbose(f"[BATCH]    Job ID: {previous_image_job.id}, Source: {previous_image_job.ext.get('source', 'unknown') if previous_image_job.ext else 'unknown'}")
            else:
                log_verbose(f"[BATCH] ℹ️  No previous image prompt found")
            
            # Extract data before session closes
            previous_state_dict = chat.state_snapshot
            if previous_state_dict and isinstance(previous_state_dict, dict):
                # Extract state string from wrapper dict
                previous_state = previous_state_dict.get("state")
            else:
                previous_state = None
            
            # Extract memory
            memory = chat.memory
            
            # Extract mood and purchases for AI context
            chat_mood = chat.mood or 50  # Default neutral mood
            chat_purchases = crud.get_chat_purchases(db, chat_id)
            
            # Extract context summary and gift suggestion tracking from chat.ext
            context_summary = None
            messages_since_last_image = 0
            last_suggested_gift = None
            if chat.ext and isinstance(chat.ext, dict):
                context_summary = chat.ext.get("context_summary")
                messages_since_last_image = chat.ext.get("messages_since_last_image", 0)
                last_suggested_gift = chat.ext.get("last_suggested_gift")
            
            # Build chat history (all existing processed messages - up to 20 for summary)
            chat_history = [
                {"role": m.role, "content": m.text} 
                for m in messages[-20:] 
                if m.text
            ]
            
            persona_data = {
                "id": persona.id,
                "name": persona.name,
                "prompt": persona.prompt or "",
                "image_prompt": persona.image_prompt or "",
                "voice_id": persona.voice_id  # ElevenLabs voice ID for TTS
            }
            
            # Get message count for image decision
            current_message_count = chat.message_count
            
            # Check if user is premium (for memory feature)
            is_premium = crud.check_user_premium(db, user_id)["is_premium"]
            
            # Get user's language preference for prompt selection
            user = db.query(User).filter(User.id == user_id).first()
            user_language = user.locale if user and user.locale else "en"
            
            # Get per-chat discovered name (from chat.ext, NOT Telegram's first_name)
            user_display_name = chat.ext.get("user_display_name") if chat.ext else None
            name_known = bool(user_display_name)
        
        pipeline_timer.end_stage()
        
        log_always(f"[BATCH] ✅ Data fetched: {len(chat_history)} msgs, persona={persona_data['name']}")
        log_verbose(f"[BATCH]    History: {len(chat_history)} messages")
        log_verbose(f"[BATCH]    Previous state: {'Found' if previous_state else 'None (creating new)'}")
        log_verbose(f"[BATCH]    Memory: {len(memory) if memory else 0} chars")
        log_verbose(f"[BATCH]    Context summary: {'Found (' + str(len(context_summary)) + ' chars)' if context_summary else 'None'}")
        log_verbose(f"[BATCH]    Message count: {current_message_count}")
        
        # Log conversation history for debugging
        if chat_history:
            print(f"[BATCH] 📚 Conversation history ({len(chat_history)} messages):")
            for i, msg in enumerate(chat_history[-5:], 1):  # Last 5 messages
                print(f"[BATCH]    {i}. {msg['role']}: {msg['content'][:80]}...")
        else:
            print(f"[BATCH] 📚 No conversation history (new chat)")
        
        print(f"[BATCH] 💬 Current batch text: {batched_text[:100]}...")
        
        pipeline_timer.start_stage("Brain 4: Image Decision")
        
        # 1.5 Brain 4: Image Decision (decide before dialogue generation)
        from app.settings import settings
        should_generate_image_flag = False
        decision_reason = "not determined"
        
        # Check if user explicitly requests a visual
        is_explicit_request = _is_explicit_visual_request(batched_text)
        
        log_verbose(f"[BATCH] 📊 Image decision context: messages_since_last_image={messages_since_last_image}, is_explicit_request={is_explicit_request}")
        
        # Check feature flag to force images always (debug mode)
        if settings.FORCE_IMAGES_ALWAYS:
            should_generate_image_flag = True
            decision_reason = "FORCE_IMAGES_ALWAYS flag enabled"
            log_always(f"[BATCH] 🎨 Image decision: FORCED YES - {decision_reason}")
        # First two messages in chat always get images
        elif current_message_count <= 2:
            should_generate_image_flag = True
            decision_reason = "first two messages in chat"
            log_always(f"[BATCH] 🎨 Image decision: YES - {decision_reason}")
        # Explicit visual request from user always gets image
        elif is_explicit_request:
            should_generate_image_flag = True
            decision_reason = "explicit visual request from user"
            log_always(f"[BATCH] 🎨 Image decision: YES - {decision_reason}")
        # If less than 2 messages since last image, skip (rate limiting)
        elif messages_since_last_image < 2:
            should_generate_image_flag = False
            decision_reason = f"too soon since last image ({messages_since_last_image} messages)"
            log_always(f"[BATCH] 🎨 Image decision: NO - {decision_reason}")
        # Force image after 3+ messages without one (ensure reasonable frequency)
        elif messages_since_last_image >= 3:
            should_generate_image_flag = True
            decision_reason = f"due for image ({messages_since_last_image} messages since last)"
            log_always(f"[BATCH] 🎨 Image decision: YES - {decision_reason}")
        else:
            # Use AI to decide (only for 2 messages since last image)
            from app.core.brains.image_decision_specialist import should_generate_image
            log_always(f"[BATCH] 🧠 Brain 4: Deciding image generation (messages_since_last_image={messages_since_last_image})...")
            
            _log_brain_inputs(
                "Brain 4 (Image Decision)",
                previous_state=previous_state or "",
                user_message=batched_text,
                chat_history=chat_history,
                persona_name=persona_data["name"],
                context_summary=context_summary
            )
            
            should_generate_image_flag, decision_reason = await should_generate_image(
                previous_state=previous_state or "",
                user_message=batched_text,
                chat_history=chat_history,
                persona_name=persona_data["name"],
                context_summary=context_summary
            )
            log_always(f"[BATCH] ✅ Brain 4: Decision = {'YES' if should_generate_image_flag else 'NO'} - {decision_reason}")
        
        pipeline_timer.end_stage()
        pipeline_timer.start_stage("Brain 1: Dialogue Generation")
        
        # 2. Brain 1: Dialogue Specialist (responds based on current state)
        log_always(f"[BATCH] 🧠 Brain 1: Generating dialogue...")
        
        # Check if this is a system-initiated message
        is_resume = "[SYSTEM_RESUME]" in batched_text
        is_auto_followup = "[AUTO_FOLLOWUP]" in batched_text
        
        # Get followup type from context (if applicable)
        followup_type = None
        if batch_messages and batch_messages[0].get("context"):
            followup_type = batch_messages[0]["context"].get("followup_type")
        
        if is_resume:
            log_verbose(f"[BATCH]    Resume mode: AI initiating conversation")
            # Generate a welcome-back style message
            user_message_for_ai = "The user is returning to continue our conversation. Greet them warmly and naturally pick up where we left off."
        elif is_auto_followup:
            log_verbose(f"[BATCH]    Auto-followup mode: AI re-engaging after inactivity")
            # Extract the instruction after the marker
            user_message_for_ai = batched_text.replace("[AUTO_FOLLOWUP]", "").strip()
        else:
            log_verbose(f"[BATCH]    For message: {batched_text[:50]}...")
            user_message_for_ai = batched_text
        
        # Check for gift suggestion BEFORE dialogue (7% probability, mood-based)
        gift_suggestion = {"should_suggest": False}
        gift_keyboard = None
        gift_hint = None
        if not is_auto_followup:
            from app.core.brains.gift_suggester import should_suggest_gift, get_gift_dialogue_hint
            gift_suggestion = should_suggest_gift(chat_mood, last_suggested_gift)
            
            if gift_suggestion["should_suggest"]:
                gift_hint = get_gift_dialogue_hint(gift_suggestion["item_key"], user_language)
                
                from app.bot.keyboards.inline import build_gift_suggestion_keyboard
                from app.settings import settings
                item_info = gift_suggestion["item_info"]
                gift_keyboard = build_gift_suggestion_keyboard(
                    item_key=gift_suggestion["item_key"],
                    item_emoji=item_info["emoji"],
                    item_name=item_info["name"] if user_language == "en" else item_info["name_ru"],
                    miniapp_url=settings.miniapp_url,
                    chat_id=str(chat_id),
                    language=user_language
                )
                log_always(f"[BATCH] 🎁 Gift suggestion: {gift_suggestion['item_key']} (tier: {gift_suggestion['reason']})")
        
        _log_brain_inputs(
            "Brain 1 (Dialogue)",
            state=previous_state,
            chat_history=chat_history,
            user_message=user_message_for_ai,
            persona=persona_data,
            memory=memory,
            is_auto_followup=is_auto_followup,
            context_summary=context_summary
        )
        
        dialogue_response = await generate_dialogue(
            state=previous_state,  # Use previous state for dialogue generation
            chat_history=chat_history,
            user_message=user_message_for_ai,
            persona=persona_data,
            memory=memory,  # Pass conversation memory
            is_auto_followup=is_auto_followup,  # Use cheaper model with enhanced prompt for followups
            user_id=user_id,
            context_summary=context_summary,  # Use summary for context efficiency
            language=user_language,  # User's language for prompt selection
            mood=chat_mood,  # Chat mood (0-100)
            purchases=chat_purchases,  # Recent purchases for context
            gift_hint=gift_hint,  # Gift suggestion hint for AI to incorporate naturally
            user_name=user_display_name,  # Per-chat discovered name (not Telegram first_name)
            name_known=name_known  # Whether name has been discovered for this chat
        )
        log_always(f"[BATCH] ✅ Brain 1: Dialogue generated ({len(dialogue_response)} chars)")
        log_verbose(f"[BATCH]    Preview: {dialogue_response[:100]}...")
        
        pipeline_timer.end_stage()
        pipeline_timer.start_stage("Brain 2: State Resolution")
        
        # 3. Brain 2: State Resolver (updates state after dialogue)
        log_always(f"[BATCH] 🧠 Brain 2: Resolving state...")
        log_verbose(f"[BATCH]    Input: {len(chat_history)} history messages + user message + dialogue response")
        
        _log_brain_inputs(
            "Brain 2 (State Resolver)",
            previous_state=previous_state,
            chat_history=chat_history,
            user_message=batched_text,
            persona_name=persona_data["name"],
            previous_image_prompt=previous_image_prompt,
            context_summary=context_summary
        )

        new_state = await resolve_state(
            previous_state=previous_state,
            chat_history=chat_history,
            user_message=batched_text,
            persona_name=persona_data["name"],
            previous_image_prompt=previous_image_prompt,
            context_summary=context_summary
        )
        log_always(f"[BATCH] ✅ Brain 2: State resolved")
        log_verbose(f"[BATCH]    State preview: {new_state[:100]}...")
        
        pipeline_timer.end_stage()
        pipeline_timer.start_stage("Save to Database")
        
        # 4. Save batch messages & response to DB + Clear refresh button
        log_always(f"[BATCH] 💾 Saving batch to database...")
        assistant_message_id = None
        # user_language already retrieved earlier for prompt selection
        # VOICE DISABLED - voice settings no longer needed
        # voice_buttons_hidden = False
        # voice_free_available = True
        with get_db() as db:
            # Save ALL user messages from batch (mark as processed)
            # Skip system markers ([SYSTEM_RESUME], [AUTO_FOLLOWUP])
            messages_to_save = [
                msg["text"] for msg in batch_messages 
                if "[SYSTEM_RESUME]" not in msg["text"] and "[AUTO_FOLLOWUP]" not in msg["text"]
            ]
            if messages_to_save:
                log_always(f"[BATCH]    💾 Saving {len(messages_to_save)} user message(s) to DB")
                crud.create_batch_messages(db, chat_id, messages_to_save)
            else:
                log_verbose(f"[BATCH]    No user messages to save")
            
            # Save assistant message with state and capture the ID for voice button
            assistant_message = crud.create_message_with_state(
                db, 
                chat_id, 
                "assistant", 
                dialogue_response,
                state_snapshot={"state": new_state},
                is_processed=True
            )
            assistant_message_id = assistant_message.id
            log_verbose(f"[BATCH]    Assistant message ID: {assistant_message_id}")
            
            # Update chat state and timestamps
            crud.update_chat_state(db, chat_id, {"state": new_state})
            crud.update_chat_timestamps(db, chat_id, assistant_at=datetime.utcnow())
            
            # Remove refresh button from last image (in same session to ensure we see current data)
            chat_for_button = crud.get_chat_by_tg_chat_id(db, tg_chat_id)
            log_always(f"[BATCH] 🔍 Checking for refresh button... ext={chat_for_button.ext if chat_for_button else None}")
            if chat_for_button and chat_for_button.ext and chat_for_button.ext.get("last_image_msg_id"):
                last_img_msg_id = chat_for_button.ext["last_image_msg_id"]
                log_always(f"[BATCH] 🗑️  Found refresh button on message {last_img_msg_id}, removing...")
                try:
                    await bot.edit_message_reply_markup(
                        chat_id=tg_chat_id,
                        message_id=last_img_msg_id,
                        reply_markup=None
                    )
                    log_always(f"[BATCH] ✅ Removed refresh button from image {last_img_msg_id}")
                except Exception as e:
                    # Button might already be removed, that's okay
                    log_always(f"[BATCH] ⚠️  Could not remove refresh button (likely already removed): {e}")
                finally:
                    # Always clear the stored message ID, even if removal failed
                    # For JSONB fields, we must mark as modified or reassign the whole dict
                    from sqlalchemy.orm.attributes import flag_modified
                    chat_for_button.ext["last_image_msg_id"] = None
                    flag_modified(chat_for_button, "ext")
                    db.commit()
                    log_always(f"[BATCH] ✅ Cleared last_image_msg_id from database")
            else:
                log_always(f"[BATCH] ℹ️  No refresh button to remove")
            
            # Update last_suggested_gift if a gift was suggested
            if gift_suggestion["should_suggest"]:
                from sqlalchemy.orm.attributes import flag_modified
                chat_for_gift = crud.get_chat_by_tg_chat_id(db, tg_chat_id)
                if chat_for_gift:
                    if not chat_for_gift.ext:
                        chat_for_gift.ext = {}
                    chat_for_gift.ext["last_suggested_gift"] = gift_suggestion["item_key"]
                    flag_modified(chat_for_gift, "ext")
                    db.commit()
                    log_verbose(f"[BATCH] 🎁 Updated last_suggested_gift to {gift_suggestion['item_key']}")
        
        log_verbose(f"[BATCH] ✅ Batch saved to database")
        
        # 5.5 Update mood based on user engagement
        try:
            from app.core.pipeline_adapter import detect_message_engagement
            mood_change, is_cold = detect_message_engagement(
                user_message=batched_text,
                chat_history=chat_history,
                state_snapshot=previous_state_dict
            )
            if mood_change != 0:
                crud.update_chat_mood(db, chat_id, mood_change, is_cold)
                log_verbose(f"[BATCH] 💭 Mood updated: change={mood_change}, is_cold={is_cold}")
        except Exception as mood_error:
            log_verbose(f"[BATCH] ⚠️ Failed to update mood: {mood_error}")
        
        pipeline_timer.end_stage()
        
        # 6. Determine image generation logic
        # Check specific flags for each followup type
        should_skip_image = False
        if followup_type == "30min":
            should_skip_image = not settings.ENABLE_IMAGES_IN_FOLLOWUP
        elif followup_type == "24h":
            should_skip_image = not settings.ENABLE_IMAGES_24HOURS
        elif followup_type == "3day":
            should_skip_image = not settings.ENABLE_IMAGES_3DAYS
        
        final_should_generate = should_generate_image_flag and not should_skip_image
        
        # If image will be generated, wait and send text as caption with the image
        should_wait_for_image = final_should_generate
        
        pipeline_timer.start_stage("Send Response to User")
        
        # 5. Send response to user (with MarkdownV2 formatting preserved)
        # If image will be generated, delay sending text until image is ready (send together)
        if should_wait_for_image:
            log_always(f"[BATCH] ⏳ Delaying text message - will be sent as image caption")
        else:
            escaped_response = escape_markdown_v2(dialogue_response)
            
            # VOICE DISABLED - voice button functionality commented out
            # Build voice button keyboard if ElevenLabs is configured, persona has voice, not hidden by user, and response is short enough
            # from app.settings import settings
            # voice_keyboard = None
            # persona_voice_id = persona_data.get("voice_id")
            # response_length = len(dialogue_response)
            # max_voice_length = 500
            # if settings.ELEVENLABS_API_KEY and assistant_message_id and not voice_buttons_hidden and persona_voice_id and response_length < max_voice_length:
            #     from app.bot.keyboards.inline import build_voice_button_keyboard
            #     voice_keyboard = build_voice_button_keyboard(
            #         message_id=assistant_message_id,
            #         language=user_language,
            #         is_free=voice_free_available
            #     )
            #     log_verbose(f"[BATCH]    Voice button added for message {assistant_message_id} (free={voice_free_available})")
            # elif voice_buttons_hidden:
            #     log_verbose(f"[BATCH]    Voice buttons hidden for user {user_id}")
            # elif not persona_voice_id:
            #     log_verbose(f"[BATCH]    Voice button skipped - persona has no voice_id")
            # elif response_length >= max_voice_length:
            #     log_verbose(f"[BATCH]    Voice button skipped - response too long ({response_length} chars >= {max_voice_length})")
            
            await bot.send_message(
                tg_chat_id, 
                escaped_response, 
                parse_mode="MarkdownV2",
                reply_markup=gift_keyboard  # Gift suggestion button (None if no suggestion)
            )
            log_always(f"[BATCH] ✅ Response sent to user{' (with gift button)' if gift_keyboard else ''}")
            log_verbose(f"[BATCH]    TG chat: {tg_chat_id}")
        
        pipeline_timer.end_stage()
        
        # Track AI message (distinguish auto-followup from regular messages)
        analytics_service_tg.track_ai_message(
            client_id=user_id,
            message=dialogue_response,
            persona_id=persona_data["id"],
            persona_name=persona_data["name"],
            chat_id=chat_id,
            is_auto_followup=is_auto_followup
        )
        
        # Stop typing indicator
        await action_mgr.stop()
        
        pipeline_timer.start_stage("Trigger Background Tasks")
        
        # 5.5. Trigger background memory update (fire and forget) - PREMIUM ONLY
        if is_premium:
            from app.core.memory_service import trigger_memory_update
            asyncio.create_task(trigger_memory_update(
                chat_id=chat_id,
                user_message=batched_text,
                ai_message=dialogue_response
            ))
            log_verbose(f"[BATCH] 🧠 Memory update triggered (background) - premium user")
        else:
            log_verbose(f"[BATCH] ⏭️ Memory update skipped (free user - premium feature)")
        
        # 5.55. Trigger background name extraction (fire and forget) - only if name not yet known
        if not name_known:
            from app.core.memory_service import trigger_name_extraction
            asyncio.create_task(trigger_name_extraction(chat_id=chat_id))
            log_verbose(f"[BATCH] 🏷️ Name extraction triggered (background)")
        
        # 5.6. Trigger background context summary update (fire and forget)
        # Update summary with new messages for next round
        asyncio.create_task(_update_context_summary(
            chat_id=chat_id,
            chat_history=chat_history,
            user_message=batched_text,
            ai_message=dialogue_response,
            persona_name=persona_data["name"]
        ))
        
        pipeline_timer.end_stage()
        
        # 7. Start background image generation based on AI decision
        
        if final_should_generate:
            log_always(f"[BATCH] 🎨 Starting background image generation (reason: {decision_reason})...")
            asyncio.create_task(_background_image_generation(
                chat_id=chat_id,
                user_id=user_id,
                persona_id=persona_data["id"],
                state=new_state,
                dialogue_response=dialogue_response,
                batched_text=batched_text,
                persona=persona_data,
                tg_chat_id=tg_chat_id,
                action_mgr=action_mgr,
                chat_history=chat_history,
                previous_image_prompt=previous_image_prompt,
                is_auto_followup=is_auto_followup,
                followup_type=followup_type,
                should_send_as_caption=should_wait_for_image,  # Pass flag to send text with image
                context_summary=context_summary,  # Pass summary for efficient context
                mood=chat_mood,  # Chat mood for image context
                purchases=chat_purchases,  # Recent purchases for image context
                gift_suggestion=gift_suggestion  # Gift suggestion for button on image
            ))
            if should_wait_for_image:
                log_always(f"[BATCH] ✅ Batch complete (text will be sent with image)")
            else:
                log_always(f"[BATCH] ✅ Batch complete (text sent, image in background)")
        else:
            if should_skip_image:
                if followup_type == "30min":
                    skip_reason = "30min scheduler (ENABLE_IMAGES_IN_FOLLOWUP=False)"
                elif followup_type == "24h":
                    skip_reason = "24h scheduler (ENABLE_IMAGES_24HOURS=False)"
                elif followup_type == "3day":
                    skip_reason = "3day scheduler (ENABLE_IMAGES_3DAYS=False)"
                else:
                    skip_reason = "auto-followup images disabled"
            else:
                skip_reason = decision_reason
            log_always(f"[BATCH] ⏭️  Skipping image generation (reason: {skip_reason})")
            log_always(f"[BATCH] ✅ Batch complete (text sent, no image)")
        
        # Update messages_since_last_image counter
        # Reset to 0 if generating image, increment if not
        try:
            with get_db() as db:
                chat_for_counter = crud.get_chat_by_id(db, chat_id)
                if chat_for_counter:
                    if not chat_for_counter.ext:
                        chat_for_counter.ext = {}
                    
                    if final_should_generate:
                        # Reset counter when generating an image
                        chat_for_counter.ext["messages_since_last_image"] = 0
                        log_verbose(f"[BATCH] 📊 Reset messages_since_last_image to 0 (image generated)")
                    else:
                        # Increment counter when not generating an image
                        current_count = chat_for_counter.ext.get("messages_since_last_image", 0)
                        chat_for_counter.ext["messages_since_last_image"] = current_count + 1
                        log_verbose(f"[BATCH] 📊 Incremented messages_since_last_image to {current_count + 1}")
                    
                    from sqlalchemy.orm.attributes import flag_modified
                    flag_modified(chat_for_counter, "ext")
                    db.commit()
        except Exception as counter_error:
            print(f"[BATCH] ⚠️ Failed to update messages_since_last_image: {counter_error}")
        
    except Exception as e:
        print(f"[BATCH] ❌ Batch processing error: {type(e).__name__}: {e}")
        if is_development():
            import traceback
            traceback.print_exc()
        
        await action_mgr.stop()
        raise


async def _background_image_generation(
    chat_id: UUID,
    user_id: int,
    persona_id: UUID,
    state: str,
    dialogue_response: str,
    batched_text: str,
    persona: dict,
    tg_chat_id: int,
    action_mgr: ChatActionManager,  # Reused to show upload_photo action
    chat_history: list[dict],  # Add chat history parameter
    previous_image_prompt: str = None,  # Add previous image prompt parameter
    is_auto_followup: bool = False,  # Track if image is from scheduler
    followup_type: str = None,  # Type of followup ("30min" or "24h")
    should_send_as_caption: bool = False,  # If True, send dialogue_response as photo caption
    context_summary: str = None,  # Pre-generated context summary for efficiency
    mood: int = 50,  # Chat mood for image context
    purchases: list = None,  # Recent purchases for image context
    gift_suggestion: dict = None  # Gift suggestion data for button on image
):
    """Non-blocking image generation"""
    counter_incremented = False  # Track if we incremented counter for error handling
    try:
        from app.settings import settings
        
        # Check concurrent image limit (if enabled)
        if settings.CONCURRENT_IMAGE_LIMIT_ENABLED:
            current_count = await redis_queue.get_user_image_count(user_id)
            if current_count >= settings.CONCURRENT_IMAGE_LIMIT_NUMBER:
                log_always(f"[IMAGE-BG] ⏭️  User {user_id} has reached concurrent image limit ({current_count}/{settings.CONCURRENT_IMAGE_LIMIT_NUMBER}) - skipping")
                await action_mgr.stop()
                return
        
        # Check if user is premium
        with get_db() as db:
            is_premium = crud.check_user_premium(db, user_id)["is_premium"]
            # Get user's global message count for priority determination
            user = db.query(User).filter(User.id == user_id).first()
            global_message_count = user.global_message_count if user else 999
            
            # Free users pay 3 energy for images, premium users don't
            if not is_premium:
                if not crud.check_user_energy(db, user_id, required=3):
                    log_always(f"[IMAGE-BG] ⚠️ User {user_id} has insufficient energy for image")
                    await action_mgr.stop()
                    return
                
                # Deduct energy for free users
                if not crud.deduct_user_energy(db, user_id, amount=3):
                    log_always(f"[IMAGE-BG] ⚠️ Failed to deduct energy for user {user_id}")
                    await action_mgr.stop()
                    return
                log_always(f"[IMAGE-BG] 🖼️ Generating image for free user {user_id} (3 energy deducted)")
            else:
                log_always(f"[IMAGE-BG] 🖼️ Generating image for premium user {user_id} (no energy cost)")
        
        log_always(f"[IMAGE-BG] 🎨 Starting image generation for chat {chat_id}")
        log_verbose(f"[IMAGE-BG]    Chat ID: {chat_id}")
        log_verbose(f"[IMAGE-BG]    User ID: {user_id}")
        log_verbose(f"[IMAGE-BG]    Persona: {persona.get('name', 'unknown')}")
        
        # Start upload_photo action and register it globally
        from app.core.action_registry import register_action_manager
        await action_mgr.start("upload_photo")
        register_action_manager(tg_chat_id, action_mgr)
        log_verbose(f"[IMAGE-BG] 📤 Started upload_photo action")
        
        # Brain 3: Generate image plan
        log_always(f"[IMAGE-BG] 🧠 Brain 3: Generating image plan...")
        
        _log_brain_inputs(
            "Brain 3 (Image Plan)",
            state=state,
            dialogue_response=dialogue_response,
            user_message=batched_text,
            persona=persona,
            chat_history=chat_history,
            previous_image_prompt=previous_image_prompt,
            context_summary=context_summary
        )
        
        image_prompt = await generate_image_plan(
            state=state,
            dialogue_response=dialogue_response,
            user_message=batched_text,
            persona=persona,
            chat_history=chat_history,
            previous_image_prompt=previous_image_prompt,
            context_summary=context_summary,
            mood=mood,
            purchases=purchases
        )
        log_always(f"[IMAGE-BG] ✅ Image plan generated")
        log_verbose(f"[IMAGE-BG]    Prompt preview: {image_prompt[:100]}...")
        
        # Assemble prompts
        log_verbose(f"[IMAGE-BG] 🔧 Assembling final SDXL prompts...")
        positive, negative = assemble_final_prompt(
            image_prompt,
            persona_image_prompt=persona.get("image_prompt") or ""  # Only use image_prompt, NOT dialogue prompt
        )
        
        log_always(f"[IMAGE-BG] ✅ Prompts assembled (pos: {len(positive)} chars, neg: {len(negative)} chars)")
        log_verbose(f"[IMAGE-BG]    Positive preview: {positive[:100]}...")
        log_verbose(f"[IMAGE-BG]    Negative preview: {negative[:100]}...")
        
        # Check image cache before generating
        prompt_hash = crud.compute_prompt_hash(positive)
        log_verbose(f"[IMAGE-BG] 🔍 Checking cache for hash: {prompt_hash[:16]}...")
        
        with get_db() as db:
            cached_image = crud.find_cached_image(db, prompt_hash, user_id)
            
            if cached_image and cached_image.result_url:
                log_always(f"[IMAGE-BG] ✅ CACHE HIT! Found cached image {cached_image.id}")
                log_verbose(f"[IMAGE-BG]    URL: {cached_image.result_url[:80]}...")
                
                # Send cached image to user
                try:
                    from app.bot.main import bot
                    from app.bot.keyboards.inline import build_image_refresh_keyboard
                    
                    # Build refresh keyboard with cached image job ID
                    refresh_keyboard = build_image_refresh_keyboard(str(cached_image.id))
                    
                    # Handle caption if needed
                    caption = None
                    if should_send_as_caption and dialogue_response:
                        from app.core.telegram_utils import escape_markdown_v2
                        caption = escape_markdown_v2(dialogue_response)
                    
                    # Remove refresh button from previous image
                    chat = crud.get_chat_by_tg_chat_id(db, tg_chat_id)
                    if chat and chat.ext and chat.ext.get("last_image_msg_id"):
                        prev_msg_id = chat.ext["last_image_msg_id"]
                        try:
                            await bot.edit_message_reply_markup(
                                chat_id=tg_chat_id,
                                message_id=prev_msg_id,
                                reply_markup=None
                            )
                            log_verbose(f"[IMAGE-BG] 🗑️ Removed refresh button from previous image")
                        except Exception:
                            pass
                    
                    # Send cached image
                    sent_message = await bot.send_photo(
                        chat_id=tg_chat_id,
                        photo=cached_image.result_url,
                        caption=caption,
                        parse_mode="MarkdownV2" if caption else None,
                        reply_markup=refresh_keyboard
                    )
                    
                    # Update tracking
                    if sent_message.photo and chat:
                        from sqlalchemy.orm.attributes import flag_modified
                        if not chat.ext:
                            chat.ext = {}
                        chat.ext["last_image_msg_id"] = sent_message.message_id
                        flag_modified(chat, "ext")
                        db.commit()
                    
                    # Mark image as shown to this user and increment cache serve count
                    crud.mark_image_shown(db, user_id, cached_image.id)
                    crud.increment_cache_serve_count(db, cached_image.id)
                    
                    # Track analytics
                    from app.core import analytics_service_tg
                    analytics_service_tg.track_image_from_cache(
                        client_id=user_id,
                        image_job_id=cached_image.id,
                        prompt_hash=prompt_hash
                    )
                    
                    log_always(f"[IMAGE-BG] ✅ Cached image sent successfully! (served {cached_image.cache_serve_count + 1} times)")
                    await action_mgr.stop()
                    return  # Exit early - no need to generate
                    
                except Exception as e:
                    log_always(f"[IMAGE-BG] ⚠️ Failed to send cached image: {e}, falling back to generation")
                    # Continue to normal generation if cache send fails
            else:
                log_verbose(f"[IMAGE-BG] 📭 Cache miss - will generate new image")
        
        # Create job record
        log_verbose(f"[IMAGE-BG] 💾 Creating job record in database...")
        
        # Build ext metadata
        job_ext = {
            "is_auto_followup": is_auto_followup
        }
        
        # Store dialogue text to send as caption with the image
        if should_send_as_caption:
            job_ext["pending_caption"] = dialogue_response
            log_always(f"[IMAGE-BG] 📝 Storing dialogue text as pending caption")
        
        # Store gift suggestion data for button on image
        if gift_suggestion and gift_suggestion.get("should_suggest"):
            job_ext["gift_suggestion"] = {
                "item_key": gift_suggestion["item_key"],
                "item_emoji": gift_suggestion["item_info"]["emoji"],
                "item_name": gift_suggestion["item_info"]["name"],
                "item_name_ru": gift_suggestion["item_info"]["name_ru"],
            }
            log_always(f"[IMAGE-BG] 🎁 Storing gift suggestion for image button")
        
        # Increment concurrent image counter (track that we incremented for error handling)
        new_count = await redis_queue.increment_user_image_count(user_id)
        counter_incremented = True
        log_verbose(f"[IMAGE-BG] 📊 Incremented user image count to {new_count}")
        
        with get_db() as db:
            job = crud.create_image_job(
                db, user_id, persona_id, positive, negative, chat_id,
                ext=job_ext
            )
            job_id = job.id
        log_verbose(f"[IMAGE-BG]    Job ID: {job_id}")
        
        # Determine priority based on rules:
        # - Premium users: high
        # - First 2 global messages: high
        # - 24h/3day scheduler: low
        # - Default: medium
        if is_premium:
            queue_priority = "high"
            priority_reason = "premium user"
        elif global_message_count <= 2:
            queue_priority = "high"
            priority_reason = f"first 2 messages globally (count: {global_message_count})"
        elif followup_type in ["24h", "3day"]:
            queue_priority = "low"
            priority_reason = f"{followup_type} scheduler re-engagement"
        else:
            queue_priority = "medium"
            priority_reason = "regular user message"
        
        log_always(f"[IMAGE-BG] 📊 Queue priority: {queue_priority} ({priority_reason})")
        
        # Dispatch to RunPod
        from app.core.img_runpod import dispatch_image_generation
        result = await dispatch_image_generation(
            job_id=job_id,
            prompt=positive,
            negative_prompt=negative,
            tg_chat_id=tg_chat_id,
            queue_priority=queue_priority
        )
        
        if not result:
            print(f"[IMAGE-BG] ⚠️ Job dispatch failed")
            # Decrement counter since dispatch failed
            await redis_queue.decrement_user_image_count(user_id)
            print(f"[IMAGE-BG] 📊 Decremented user image count (dispatch failed)")
            # Stop action on dispatch failure
            from app.core.action_registry import stop_and_remove_action
            await stop_and_remove_action(tg_chat_id)
        
        log_always(f"[IMAGE-BG] ✅ Image generation task complete")
            
    except Exception as e:
        print(f"[IMAGE-BG] ❌ Error: {type(e).__name__}: {e}")
        if is_development():
            import traceback
            traceback.print_exc()
        
        # Decrement counter if we incremented it (error occurred after increment)
        if counter_incremented:
            await redis_queue.decrement_user_image_count(user_id)
            print(f"[IMAGE-BG] 📊 Decremented user image count (error recovery)")
        
        # Stop action on exception
        from app.core.action_registry import stop_and_remove_action
        await stop_and_remove_action(tg_chat_id)


async def _update_context_summary(
    chat_id: UUID,
    chat_history: list[dict],
    user_message: str,
    ai_message: str,
    persona_name: str
):
    """
    Background task to update context summary after each message exchange.
    Generates new summary and saves to chat.ext["context_summary"].
    """
    try:
        # Build full history including the new messages
        full_history = chat_history + [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": ai_message}
        ]
        
        # Only generate summary if we have enough messages
        if len(full_history) < 5:
            log_verbose(f"[CONTEXT-SUMMARY] ⏭️ Skipping - only {len(full_history)} messages (need 5+)")
            return
        
        log_verbose(f"[CONTEXT-SUMMARY] 🧠 Generating summary for {len(full_history)} messages...")
        
        # Generate new summary
        new_summary = await generate_context_summary(
            chat_history=full_history[-20:],  # Last 20 messages
            persona_name=persona_name
        )
        
        if not new_summary:
            log_verbose(f"[CONTEXT-SUMMARY] ⚠️ Empty summary generated, skipping save")
            return
        
        # Save to database
        with get_db() as db:
            from sqlalchemy.orm.attributes import flag_modified
            chat = crud.get_chat_by_id(db, chat_id)
            if chat:
                if not chat.ext:
                    chat.ext = {}
                chat.ext["context_summary"] = new_summary
                flag_modified(chat, "ext")
                db.commit()
                log_always(f"[CONTEXT-SUMMARY] ✅ Summary saved ({len(new_summary)} chars)")
            else:
                log_verbose(f"[CONTEXT-SUMMARY] ⚠️ Chat {chat_id} not found")
                
    except Exception as e:
        log_always(f"[CONTEXT-SUMMARY] ❌ Error updating summary: {e}")
        # Non-critical - don't raise, just log


async def process_gift_purchase(
    chat_id: UUID,
    user_id: int,
    tg_chat_id: int,
    item_key: str,
    item_name: str,
    item_emoji: str = "🎁",
    context_effect: str = "",
    new_mood: int = 50
):
    """
    Background task triggered after a gift purchase from the shop.
    Sends a character reaction message + generates an image with the gift context.
    """
    try:
        log_always(f"[GIFT-PURCHASE] 🎁 Processing gift purchase: {item_key} for chat {chat_id}")
        
        # Fetch chat and persona data
        with get_db() as db:
            chat = crud.get_chat_by_id(db, chat_id)
            if not chat:
                log_always(f"[GIFT-PURCHASE] ❌ Chat {chat_id} not found")
                return
            
            persona = crud.get_persona_by_id(db, chat.persona_id)
            if not persona:
                log_always(f"[GIFT-PURCHASE] ❌ Persona not found for chat {chat_id}")
                return
            
            # Get user language
            user_language = crud.get_user_language(db, user_id)
            
            # Build and send system message
            persona_name = persona.name
            if user_language == "ru":
                from app.db.crud import SHOP_ITEMS
                item_name_localized = SHOP_ITEMS.get(item_key, {}).get("name_ru", item_name)
                system_text = f"{item_emoji} Вы подарили {persona_name} подарок — {item_name_localized}"
            else:
                system_text = f"{item_emoji} You bought {persona_name} a {item_name}"
            
            escaped_system = escape_markdown_v2(system_text)
            await bot.send_message(tg_chat_id, escaped_system, parse_mode="MarkdownV2")
            is_premium = crud.check_user_premium(db, user_id)["is_premium"]
            
            # Get per-chat discovered name (from chat.ext, NOT Telegram's first_name)
            gift_user_display_name = chat.ext.get("user_display_name") if chat.ext else None
            
            # Get chat history for context
            messages = crud.get_chat_messages(db, chat_id, limit=10)
            chat_history = [{"role": m.role, "content": m.text} for m in reversed(messages)]
            
            # Get previous image prompt
            previous_image_job = crud.get_last_completed_image_job(db, chat_id)
            previous_image_prompt = previous_image_job.prompt if previous_image_job else None
            
            # Get recent purchases for context
            chat_purchases = crud.get_chat_purchases(db, chat_id)
            
            # Build persona data dict
            persona_data = {
                "id": str(persona.id),
                "name": persona.name,
                "prompt": persona.prompt,
                "image_prompt": persona.image_prompt,
            }
            
            # Get state
            previous_state = chat.state_snapshot.get("state", "chatting") if chat.state_snapshot else "chatting"
            memory = chat.memory
            context_summary = chat.ext.get("context_summary") if chat.ext else None
        
        # Show typing indicator
        action_mgr = ChatActionManager(bot, tg_chat_id)
        await action_mgr.start("typing")
        
        # Generate gift reaction dialogue — instruct her to describe USING the gift
        gift_reaction_hint = f"The user just bought you a gift: {item_name}! You are now using/enjoying the {item_name}. Describe in vivid detail what you're doing with it — how it feels, how you're using it. Be excited, grateful, and flirty. Do NOT just thank them — show them you're actively using and enjoying the gift right now."
        if user_language == "ru":
            gift_reaction_hint = f"Пользователь только что подарил тебе подарок: {item_name}! Ты сейчас используешь/наслаждаешься подарком {item_name}. Опиши подробно, что ты с ним делаешь — как ощущается, как ты его используешь. Будь восторженной, благодарной и кокетливой. НЕ просто благодари — покажи, что ты прямо сейчас активно используешь и наслаждаешься подарком."
        
        log_always(f"[GIFT-PURCHASE] 🧠 Generating gift reaction dialogue...")
        dialogue_response = await generate_dialogue(
            state=previous_state,
            chat_history=chat_history,
            user_message=f"[User bought you a gift: {item_name}]",
            persona=persona_data,
            memory=memory,
            is_auto_followup=False,
            user_id=user_id,
            context_summary=context_summary,
            language=user_language,
            mood=new_mood,
            purchases=chat_purchases,
            gift_hint=gift_reaction_hint,
            user_name=gift_user_display_name
        )
        log_always(f"[GIFT-PURCHASE] ✅ Gift reaction generated: {dialogue_response[:80]}...")
        
        # Save the assistant message to chat history
        with get_db() as db:
            crud.create_message_with_state(
                db, chat_id, "assistant", dialogue_response,
                state_snapshot={"state": previous_state}
            )
            crud.update_chat_timestamps(db, chat_id, assistant_at=datetime.utcnow())
        
        # Trigger memory update so the gift is remembered in future conversations
        from app.core.memory_service import trigger_memory_update
        asyncio.create_task(trigger_memory_update(
            chat_id=chat_id,
            user_message=f"[User bought a gift: {item_name}]",
            ai_message=dialogue_response
        ))
        log_always(f"[GIFT-PURCHASE] 🧠 Memory update triggered (background)")
        
        # Send the reaction message as caption with image (don't send text separately)
        # Generate image with gift context
        await action_mgr.start("upload_photo")
        from app.core.action_registry import register_action_manager
        register_action_manager(tg_chat_id, action_mgr)
        
        log_always(f"[GIFT-PURCHASE] 🎨 Generating image with gift context: {context_effect}")
        
        image_prompt = await generate_image_plan(
            state=previous_state,
            dialogue_response=dialogue_response,
            user_message=f"GIFT PURCHASE — she is actively using the gift: {item_name}. MANDATORY VISUAL: {context_effect}",
            persona=persona_data,
            chat_history=chat_history,
            previous_image_prompt=previous_image_prompt,
            context_summary=context_summary,
            mood=new_mood,
            purchases=chat_purchases
        )
        log_always(f"[GIFT-PURCHASE] ✅ Image plan generated")
        
        positive, negative = assemble_final_prompt(
            image_prompt,
            persona_image_prompt=persona_data.get("image_prompt") or ""
        )
        
        # Check cache
        prompt_hash = crud.compute_prompt_hash(positive)
        with get_db() as db:
            cached_image = crud.find_cached_image(db, prompt_hash, user_id)
            
            if cached_image and cached_image.result_url:
                log_always(f"[GIFT-PURCHASE] ✅ CACHE HIT for gift image")
                try:
                    caption = escape_markdown_v2(dialogue_response)
                    sent_message = await bot.send_photo(
                        chat_id=tg_chat_id,
                        photo=cached_image.result_url,
                        caption=caption,
                        parse_mode="MarkdownV2"
                    )
                    # Track image msg
                    from sqlalchemy.orm.attributes import flag_modified
                    chat = crud.get_chat_by_tg_chat_id(db, tg_chat_id)
                    if chat and sent_message.photo:
                        if not chat.ext:
                            chat.ext = {}
                        chat.ext["last_image_msg_id"] = sent_message.message_id
                        flag_modified(chat, "ext")
                        db.commit()
                    crud.mark_image_shown(db, user_id, cached_image.id)
                    crud.increment_cache_serve_count(db, cached_image.id)
                    await action_mgr.stop()
                    log_always(f"[GIFT-PURCHASE] ✅ Gift image + reaction sent (cached)")
                    return
                except Exception as e:
                    log_always(f"[GIFT-PURCHASE] ⚠️ Cache send failed: {e}, generating new")
        
        # Create job and dispatch
        await redis_queue.increment_user_image_count(user_id)
        
        with get_db() as db:
            job = crud.create_image_job(
                db, user_id, UUID(persona_data["id"]),
                positive, negative, chat_id,
                ext={"pending_caption": dialogue_response, "is_gift_purchase": True}
            )
            job_id = job.id
        
        queue_priority = "high" if is_premium else "medium"
        
        from app.core.img_runpod import dispatch_image_generation
        result = await dispatch_image_generation(
            job_id=job_id,
            prompt=positive,
            negative_prompt=negative,
            tg_chat_id=tg_chat_id,
            queue_priority=queue_priority
        )
        
        if not result:
            log_always(f"[GIFT-PURCHASE] ⚠️ Image dispatch failed, sending text only")
            await redis_queue.decrement_user_image_count(user_id)
            # Fall back to text-only message
            escaped = escape_markdown_v2(dialogue_response)
            await bot.send_message(tg_chat_id, escaped, parse_mode="MarkdownV2")
            await action_mgr.stop()
            return
        
        log_always(f"[GIFT-PURCHASE] ✅ Gift purchase processing complete (image dispatched)")
        
    except Exception as e:
        log_always(f"[GIFT-PURCHASE] ❌ Error: {type(e).__name__}: {e}")
        if is_development():
            import traceback
            traceback.print_exc()
        
        # Try to send text-only as fallback
        try:
            if dialogue_response:
                escaped = escape_markdown_v2(dialogue_response)
                await bot.send_message(tg_chat_id, escaped, parse_mode="MarkdownV2")
        except Exception:
            pass
        
        try:
            from app.core.action_registry import stop_and_remove_action
            await stop_and_remove_action(tg_chat_id)
        except Exception:
            pass


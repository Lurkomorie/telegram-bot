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
from app.db.base import get_db
from app.db import crud
from app.db.models import User
from app.bot.loader import bot
from app.core import analytics_service_tg


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
            
            # Build chat history (all existing processed messages)
            chat_history = [
                {"role": m.role, "content": m.text} 
                for m in messages[-10:] 
                if m.text
            ]
            
            persona_data = {
                "id": persona.id,
                "name": persona.name,
                "prompt": persona.prompt or "",
                "image_prompt": persona.image_prompt or ""
            }
            
            # Get message count for image decision
            current_message_count = chat.message_count
        
        pipeline_timer.end_stage()
        
        log_always(f"[BATCH] ✅ Data fetched: {len(chat_history)} msgs, persona={persona_data['name']}")
        log_verbose(f"[BATCH]    History: {len(chat_history)} messages")
        log_verbose(f"[BATCH]    Previous state: {'Found' if previous_state else 'None (creating new)'}")
        log_verbose(f"[BATCH]    Memory: {len(memory) if memory else 0} chars")
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
        else:
            # Use AI to decide
            from app.core.brains.image_decision_specialist import should_generate_image
            log_always(f"[BATCH] 🧠 Brain 4: Deciding image generation...")
            
            _log_brain_inputs(
                "Brain 4 (Image Decision)",
                previous_state=previous_state or "",
                user_message=batched_text,
                chat_history=chat_history,
                persona_name=persona_data["name"]
            )
            
            should_generate_image_flag, decision_reason = await should_generate_image(
                previous_state=previous_state or "",
                user_message=batched_text,
                chat_history=chat_history,
                persona_name=persona_data["name"]
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
        
        _log_brain_inputs(
            "Brain 1 (Dialogue)",
            state=previous_state,
            chat_history=chat_history,
            user_message=user_message_for_ai,
            persona=persona_data,
            memory=memory,
            is_auto_followup=is_auto_followup
        )
        
        dialogue_response = await generate_dialogue(
            state=previous_state,  # Use previous state for dialogue generation
            chat_history=chat_history,
            user_message=user_message_for_ai,
            persona=persona_data,
            memory=memory,  # Pass conversation memory
            is_auto_followup=is_auto_followup,  # Use cheaper model with enhanced prompt for followups
            user_id=user_id
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
            previous_image_prompt=previous_image_prompt
        )

        new_state = await resolve_state(
            previous_state=previous_state,
            chat_history=chat_history,
            user_message=batched_text,
            persona_name=persona_data["name"],
            previous_image_prompt=previous_image_prompt
        )
        log_always(f"[BATCH] ✅ Brain 2: State resolved")
        log_verbose(f"[BATCH]    State preview: {new_state[:100]}...")
        
        pipeline_timer.end_stage()
        pipeline_timer.start_stage("Save to Database")
        
        # 4. Save batch messages & response to DB + Clear refresh button
        log_always(f"[BATCH] 💾 Saving batch to database...")
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
            
            # Save assistant message with state
            crud.create_message_with_state(
                db, 
                chat_id, 
                "assistant", 
                dialogue_response,
                state_snapshot={"state": new_state},
                is_processed=True
            )
            
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
        
        log_verbose(f"[BATCH] ✅ Batch saved to database")
        
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
        
        # For 24h and 3day follow-ups with images, send text as caption
        should_wait_for_image = followup_type in ["24h", "3day"] and final_should_generate
        
        pipeline_timer.start_stage("Send Response to User")
        
        # 5. Send response to user (with MarkdownV2 formatting preserved)
        # For 24h follow-ups with images, delay sending text until image is ready
        if should_wait_for_image:
            log_always(f"[BATCH] ⏳ Delaying text message send - will be sent as image caption (24h followup)")
        else:
            escaped_response = escape_markdown_v2(dialogue_response)
            await bot.send_message(tg_chat_id, escaped_response, parse_mode="MarkdownV2")
            log_always(f"[BATCH] ✅ Response sent to user")
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
        
        # 5.5. Trigger background memory update (fire and forget)
        from app.core.memory_service import trigger_memory_update
        asyncio.create_task(trigger_memory_update(
            chat_id=chat_id,
            user_message=batched_text,
            ai_message=dialogue_response
        ))
        log_verbose(f"[BATCH] 🧠 Memory update triggered (background)")
        
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
                should_send_as_caption=should_wait_for_image  # Pass flag to send text with image
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
    should_send_as_caption: bool = False  # If True, send dialogue_response as photo caption
):
    """Non-blocking image generation"""
    counter_incremented = False  # Track if we incremented counter for error handling
    try:
        from app.settings import settings
        
        # Check concurrent image limit
        current_count = await redis_queue.get_user_image_count(user_id)
        if current_count >= settings.MAX_CONCURRENT_IMAGES_PER_USER:
            log_always(f"[IMAGE-BG] ⏭️  User {user_id} has reached concurrent image limit ({current_count}/{settings.MAX_CONCURRENT_IMAGES_PER_USER}) - skipping")
            await action_mgr.stop()
            return
        
        # Check if user is premium (premium users get free images)
        with get_db() as db:
            is_premium = crud.check_user_premium(db, user_id)
            # Get user's global message count for priority determination
            user = db.query(User).filter(User.id == user_id).first()
            global_message_count = user.global_message_count if user else 999
        
        if is_premium:
            log_always(f"[IMAGE-BG] 💎 Premium user {user_id} - free image generation")
        else:
            # Deduct energy for non-premium users (5 energy per image)
            with get_db() as db:
                if not crud.deduct_user_energy(db, user_id, amount=5):
                    log_always(f"[IMAGE-BG] ⚠️ User {user_id} has insufficient energy for image - skipping")
                    await action_mgr.stop()
                    return
                log_always(f"[IMAGE-BG] ⚡ Deducted 5 energy from user {user_id}")
        
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
            previous_image_prompt=previous_image_prompt
        )
        
        image_prompt = await generate_image_plan(
            state=state,
            dialogue_response=dialogue_response,
            user_message=batched_text,
            persona=persona,
            chat_history=chat_history,
            previous_image_prompt=previous_image_prompt
        )
        log_always(f"[IMAGE-BG] ✅ Image plan generated")
        log_verbose(f"[IMAGE-BG]    Prompt preview: {image_prompt[:100]}...")
        
        # Assemble prompts
        log_verbose(f"[IMAGE-BG] 🔧 Assembling final SDXL prompts...")
        positive, negative = assemble_final_prompt(
            image_prompt,
            persona_image_prompt=persona.get("image_prompt") or persona.get("prompt", "")
        )
        
        log_always(f"[IMAGE-BG] ✅ Prompts assembled (pos: {len(positive)} chars, neg: {len(negative)} chars)")
        log_verbose(f"[IMAGE-BG]    Positive preview: {positive[:100]}...")
        log_verbose(f"[IMAGE-BG]    Negative preview: {negative[:100]}...")
        
        # Create job record
        log_verbose(f"[IMAGE-BG] 💾 Creating job record in database...")
        
        # Build ext metadata
        job_ext = {
            "is_auto_followup": is_auto_followup
        }
        
        # For 24h follow-ups, store dialogue text to send as caption
        if should_send_as_caption:
            job_ext["pending_caption"] = dialogue_response
            log_always(f"[IMAGE-BG] 📝 Storing dialogue text as pending caption (24h followup)")
        
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


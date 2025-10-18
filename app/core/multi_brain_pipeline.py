"""
Multi-Brain Pipeline Orchestrator
Coordinates State Resolver → Dialogue Specialist → Image Generation
"""
import asyncio
from datetime import datetime
from uuid import UUID
from app.core.brains.state_resolver import resolve_state
from app.core.brains.dialogue_specialist import generate_dialogue
from app.core.brains.image_prompt_engineer import generate_image_plan, assemble_final_prompt
from app.core.chat_actions import ChatActionManager
from app.core.logging_utils import log_verbose, log_always, is_development
from app.core.telegram_utils import escape_markdown_v2
from app.core import redis_queue
from app.db.base import get_db
from app.db import crud
from app.bot.loader import bot


async def process_message_pipeline(
    chat_id: UUID,
    user_id: int,
    tg_chat_id: int
):
    """
    Main pipeline with Redis-based batching: State → Dialogue → [Save] → Image (background)
    
    Flow:
    1. Set processing lock
    2. Loop while messages in queue:
       a. Get batch from Redis
       b. Fetch data (chat, persona, history)
       c. Brain 1: Resolve state
       d. Brain 2: Generate dialogue
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
    
    # Set processing lock to prevent overlapping executions (Redis-based)
    await redis_queue.set_processing_lock(chat_id, True)
    print(f"[PIPELINE] 🔒 Processing lock SET (Redis)")
    
    # Stop any existing action (e.g. upload_photo from previous image generation)
    from app.core.action_registry import stop_and_remove_action
    await stop_and_remove_action(tg_chat_id)
    print(f"[PIPELINE] 🧹 Cleared any existing chat actions")
    
    # Create action manager for persistent indicators
    action_mgr = ChatActionManager(bot, tg_chat_id)
    
    try:
        # Loop through batches until queue is empty
        batch_count = 0
        while True:
            batch_count += 1
            
            # Get current batch from Redis
            batch_messages = await redis_queue.get_batch_messages(chat_id)
            
            if not batch_messages:
                log_always(f"[PIPELINE] ✅ Queue empty, stopping loop")
                break
            
            log_always(f"[PIPELINE] 📦 Processing batch #{batch_count} ({len(batch_messages)} message(s))")
            
            # Extract text from batch
            batched_text = "\n".join([msg["text"] for msg in batch_messages])
            log_verbose(f"[PIPELINE] 💬 Text preview: {batched_text[:100]}...")
            
            # Process this batch
            await _process_single_batch(
                chat_id=chat_id,
                user_id=user_id,
                tg_chat_id=tg_chat_id,
                batch_messages=batch_messages,
                batched_text=batched_text,
                action_mgr=action_mgr
            )
            
            # Clear this batch from Redis
            await redis_queue.clear_batch_messages(chat_id)
            log_verbose(f"[PIPELINE] 🧹 Batch cleared from Redis queue")
            
        log_always(f"[PIPELINE] ✅ All batches processed ({batch_count - 1} total)")
        
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
    action_mgr: ChatActionManager
):
    """Process a single batch of messages"""
    try:
        # Show typing indicator
        log_verbose(f"[BATCH] ⌨️  Starting typing indicator...")
        await action_mgr.start("typing")
        log_verbose(f"[BATCH] ✅ Typing indicator started")
        
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
            
            # Extract data before session closes
            previous_state_dict = chat.state_snapshot
            if previous_state_dict and isinstance(previous_state_dict, dict):
                # Extract state string from wrapper dict
                previous_state = previous_state_dict.get("state")
            else:
                previous_state = None
            
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
        
        log_always(f"[BATCH] ✅ Data fetched: {len(chat_history)} msgs, persona={persona_data['name']}")
        log_verbose(f"[BATCH]    History: {len(chat_history)} messages")
        log_verbose(f"[BATCH]    Previous state: {'Found' if previous_state else 'None (creating new)'}")
        
        # Log conversation history for debugging
        if chat_history:
            print(f"[BATCH] 📚 Conversation history ({len(chat_history)} messages):")
            for i, msg in enumerate(chat_history[-5:], 1):  # Last 5 messages
                print(f"[BATCH]    {i}. {msg['role']}: {msg['content'][:80]}...")
        else:
            print(f"[BATCH] 📚 No conversation history (new chat)")
        
        print(f"[BATCH] 💬 Current batch text: {batched_text[:100]}...")
        
        # 2. Brain 1: State Resolver
        log_always(f"[BATCH] 🧠 Brain 1: Resolving state...")
        log_verbose(f"[BATCH]    Input: {len(chat_history)} history messages + user message")
        new_state = await resolve_state(
            previous_state=previous_state,
            chat_history=chat_history,
            user_message=batched_text,
            persona_name=persona_data["name"]
        )
        log_always(f"[BATCH] ✅ Brain 1: State resolved")
        log_verbose(f"[BATCH]    State preview: {new_state[:100]}...")
        
        # 3. Brain 2: Dialogue Specialist
        log_always(f"[BATCH] 🧠 Brain 2: Generating dialogue...")
        
        # Check if this is a system-initiated message
        is_resume = "[SYSTEM_RESUME]" in batched_text
        is_auto_followup = "[AUTO_FOLLOWUP]" in batched_text
        
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
        
        dialogue_response = await generate_dialogue(
            state=new_state,
            chat_history=chat_history,
            user_message=user_message_for_ai,
            persona=persona_data
        )
        log_always(f"[BATCH] ✅ Brain 2: Dialogue generated ({len(dialogue_response)} chars)")
        log_verbose(f"[BATCH]    Preview: {dialogue_response[:100]}...")
        
        # 4. Save batch messages & response to DB
        log_always(f"[BATCH] 💾 Saving batch to database...")
        with get_db() as db:
            # Save all user messages from this batch (as processed)
            # Skip saving system markers ([SYSTEM_RESUME], [AUTO_FOLLOWUP])
            messages_to_save = [
                msg["text"] for msg in batch_messages 
                if "[SYSTEM_RESUME]" not in msg["text"] and "[AUTO_FOLLOWUP]" not in msg["text"]
            ]
            if messages_to_save:
                log_verbose(f"[BATCH]    Saving {len(messages_to_save)} user message(s)...")
                crud.create_batch_messages(db, chat_id, messages_to_save)
            else:
                log_verbose(f"[BATCH]    No user messages to save (system-initiated mode)")
            
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
        
        log_verbose(f"[BATCH] ✅ Batch saved to database")
        
        # 5. Send response to user (with MarkdownV2 formatting preserved)
        escaped_response = escape_markdown_v2(dialogue_response)
        await bot.send_message(tg_chat_id, escaped_response, parse_mode="MarkdownV2")
        log_always(f"[BATCH] ✅ Response sent to user")
        log_verbose(f"[BATCH]    TG chat: {tg_chat_id}")
        
        # Stop typing indicator
        await action_mgr.stop()
        
        # 6. Start background image generation for this batch
        log_always(f"[BATCH] 🎨 Starting background image generation...")
        asyncio.create_task(_background_image_generation(
            chat_id=chat_id,
            user_id=user_id,
            persona_id=persona_data["id"],
            state=new_state,
            dialogue_response=dialogue_response,
            batched_text=batched_text,
            persona=persona_data,
            tg_chat_id=tg_chat_id,
            action_mgr=action_mgr
        ))
        log_always(f"[BATCH] ✅ Batch complete (text sent, image in background)")
        
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
    action_mgr: ChatActionManager  # Reused to show upload_photo action
):
    """Non-blocking image generation"""
    try:
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
        image_prompt = await generate_image_plan(
            state=state,
            dialogue_response=dialogue_response,
            user_message=batched_text,
            persona=persona
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
        with get_db() as db:
            job = crud.create_image_job(
                db, user_id, persona_id, positive, negative, chat_id
            )
            job_id = job.id
        log_verbose(f"[IMAGE-BG]    Job ID: {job_id}")
        
        # Dispatch to RunPod
        from app.core.img_runpod import dispatch_image_generation
        result = await dispatch_image_generation(
            job_id=job_id,
            prompt=positive,
            negative_prompt=negative,
            tg_chat_id=tg_chat_id
        )
        
        if not result:
            print(f"[IMAGE-BG] ⚠️ Job dispatch failed")
            # Stop action on dispatch failure
            from app.core.action_registry import stop_and_remove_action
            await stop_and_remove_action(tg_chat_id)
        
        log_always(f"[IMAGE-BG] ✅ Image generation task complete")
            
    except Exception as e:
        print(f"[IMAGE-BG] ❌ Error: {type(e).__name__}: {e}")
        if is_development():
            import traceback
            traceback.print_exc()
        
        # Stop action on exception
        from app.core.action_registry import stop_and_remove_action
        await stop_and_remove_action(tg_chat_id)


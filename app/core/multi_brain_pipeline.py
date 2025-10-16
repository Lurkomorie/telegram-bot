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
from app.core.schemas import FullState
from app.db.base import get_db
from app.db import crud
from app.bot.loader import bot


async def process_message_pipeline(
    chat_id: UUID,
    user_id: int,
    batched_messages: list[dict],  # List of {id, text}
    batched_text: str,
    tg_chat_id: int
):
    """
    Main pipeline: State → Dialogue → [Save] → Image (background)
    
    Flow:
    1. Fetch data (chat, persona, history)
    2. Brain 1: Resolve state
    3. Brain 2: Generate dialogue
    4. Save & send response immediately
    5. Brain 3: Generate image (background, non-blocking)
    """
    print(f"[PIPELINE] 🚀 ============= STARTING PIPELINE =============")
    print(f"[PIPELINE] 📊 Chat ID: {chat_id}")
    print(f"[PIPELINE] 👤 User ID: {user_id}")
    print(f"[PIPELINE] 📱 TG Chat ID: {tg_chat_id}")
    print(f"[PIPELINE] 📝 Batched messages: {len(batched_messages)}")
    print(f"[PIPELINE] 💬 Text preview: {batched_text[:100]}...")
    
    # Set processing lock to prevent overlapping executions
    with get_db() as db:
        crud.set_chat_processing(db, chat_id, True)
        print(f"[PIPELINE] 🔒 Processing lock SET")
    
    # Create action manager for persistent indicators
    action_mgr = ChatActionManager(bot, tg_chat_id)
    
    try:
        # Show typing indicator
        print(f"[PIPELINE] ⌨️  Starting typing indicator...")
        await action_mgr.start("typing")
        print(f"[PIPELINE] ✅ Typing indicator started")
        
        # 1. Fetch data
        print(f"[PIPELINE] 📚 Step 1: Fetching data from database...")
        with get_db() as db:
            print(f"[PIPELINE] 🔍 Looking up chat {chat_id}")
            chat = crud.get_chat_by_id(db, chat_id)
            if not chat:
                raise ValueError(f"Chat {chat_id} not found")
            print(f"[PIPELINE] ✅ Chat found")
                
            print(f"[PIPELINE] 🔍 Looking up persona {chat.persona_id}")
            persona = crud.get_persona_by_id(db, chat.persona_id)
            if not persona:
                raise ValueError(f"Persona {chat.persona_id} not found")
            print(f"[PIPELINE] ✅ Persona found: {persona.name}")
                
            messages = crud.get_chat_messages(db, chat_id, limit=20)
            
            # Extract data before session closes
            previous_state_dict = chat.state_snapshot
            if previous_state_dict and isinstance(previous_state_dict, dict):
                try:
                    previous_state = FullState(**previous_state_dict)
                except Exception:
                    previous_state = None
            else:
                previous_state = None
            
            chat_history = [
                {"role": m.role, "content": m.text} 
                for m in messages[-10:] 
                if m.text
            ]
            
            persona_data = {
                "id": persona.id,
                "name": persona.name,
                "prompt": persona.prompt or ""
            }
        
        print(f"[PIPELINE] ✅ Data fetch complete:")
        print(f"[PIPELINE]    - History: {len(chat_history)} messages")
        print(f"[PIPELINE]    - Persona: {persona_data['name']}")
        print(f"[PIPELINE]    - Previous state: {'Found' if previous_state else 'None (creating new)'}")
        
        # 2. Brain 1: State Resolver
        print(f"[PIPELINE] 🧠 ============= BRAIN 1: STATE RESOLVER =============")
        print(f"[PIPELINE] 🎯 Input: {len(chat_history)} history messages + user message")
        new_state = await resolve_state(
            previous_state=previous_state,
            chat_history=chat_history,
            user_message=batched_text,
            persona_name=persona_data["name"]
        )
        print(f"[PIPELINE] ✅ Brain 1 complete: State resolved")
        print(f"[PIPELINE]    - Relationship stage: {new_state.rel.relationshipStage}")
        print(f"[PIPELINE]    - Emotions: {new_state.rel.emotions}")
        print(f"[PIPELINE]    - Location: {new_state.scene.location}")
        
        # 3. Brain 2: Dialogue Specialist
        print(f"[PIPELINE] 🧠 ============= BRAIN 2: DIALOGUE SPECIALIST =============")
        print(f"[PIPELINE] 🎯 Generating response for: {batched_text[:50]}...")
        dialogue_response = await generate_dialogue(
            state=new_state,
            chat_history=chat_history,
            user_message=batched_text,
            persona=persona_data
        )
        print(f"[PIPELINE] ✅ Brain 2 complete: Response generated ({len(dialogue_response)} chars)")
        print(f"[PIPELINE]    Preview: {dialogue_response[:100]}...")
        
        # 4. Save & send response immediately
        print(f"[PIPELINE] 💾 ============= SAVING & SENDING =============")
        print(f"[PIPELINE] 📝 Marking {len(batched_messages)} message(s) as processed...")
        with get_db() as db:
            # Mark user messages as processed
            message_ids = [UUID(m["id"]) for m in batched_messages]
            crud.mark_messages_processed(db, message_ids)
            
            # Save assistant message with state
            crud.create_message_with_state(
                db, 
                chat_id, 
                "assistant", 
                dialogue_response,
                state_snapshot=new_state.dict()
            )
            
            # Update chat state and timestamps
            crud.update_chat_state(db, chat_id, new_state.dict())
            crud.update_chat_timestamps(db, chat_id, assistant_at=datetime.utcnow())
        
        print(f"[PIPELINE] ✅ Database updates complete")
        
        # Send response to user
        print(f"[PIPELINE] 📤 Sending response to user...")
        await bot.send_message(tg_chat_id, dialogue_response, parse_mode="HTML")
        print(f"[PIPELINE] ✅ Response sent to TG chat {tg_chat_id}")
        
        # Stop typing indicator
        print(f"[PIPELINE] ⌨️  Stopping typing indicator...")
        await action_mgr.stop()
        print(f"[PIPELINE] ✅ Typing indicator stopped")
        
        # Clear processing lock - text response complete, new messages can be processed
        with get_db() as db:
            crud.set_chat_processing(db, chat_id, False)
            print(f"[PIPELINE] 🔓 Processing lock CLEARED (text response sent)")
        
        # 5. Brain 3 + Image dispatch (background, non-blocking)
        print(f"[PIPELINE] 🎨 ============= BRAIN 3: IMAGE GENERATION (BACKGROUND) =============")
        print(f"[PIPELINE] 🚀 Creating background task for image generation...")
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
        print(f"[PIPELINE] ✅ Background task created")
        print(f"[PIPELINE] ✅ ============= PIPELINE COMPLETE (main path) =============")
        
    except Exception as e:
        print(f"[PIPELINE] ❌ ============= PIPELINE ERROR =============")
        print(f"[PIPELINE] ❌ Error type: {type(e).__name__}")
        print(f"[PIPELINE] ❌ Error message: {e}")
        import traceback
        traceback.print_exc()
        
        # Clear processing lock on error
        with get_db() as db:
            crud.set_chat_processing(db, chat_id, False)
            print(f"[PIPELINE] 🔓 Processing lock CLEARED (error recovery)")
        
        await action_mgr.stop()
        raise


async def _background_image_generation(
    chat_id: UUID,
    user_id: int,
    persona_id: UUID,
    state: FullState,
    dialogue_response: str,
    batched_text: str,
    persona: dict,
    tg_chat_id: int,
    action_mgr: ChatActionManager  # No longer used, image sends via webhook
):
    """Non-blocking image generation"""
    try:
        print(f"[IMAGE-BG] 🎨 ============= BACKGROUND IMAGE TASK STARTED =============")
        print(f"[IMAGE-BG] 📊 Chat ID: {chat_id}")
        print(f"[IMAGE-BG] 👤 User ID: {user_id}")
        print(f"[IMAGE-BG] 🎭 Persona: {persona.get('name', 'unknown')}")
        print(f"[IMAGE-BG] 📝 User message: {batched_text[:100]}...")
        print(f"[IMAGE-BG] 💬 Assistant response: {dialogue_response[:100]}...")
        
        # Brain 3: Generate image plan
        print(f"[IMAGE-BG] 🧠 Calling Brain 3 to generate image plan...")
        image_plan = await generate_image_plan(
            state=state,
            dialogue_response=dialogue_response,
            user_message=batched_text,
            persona=persona
        )
        print(f"[IMAGE-BG] ✅ Image plan generated")
        print(f"[IMAGE-BG]    - Composition tags: {len(image_plan.composition_tags)}")
        print(f"[IMAGE-BG]    - Action tags: {len(image_plan.action_tags)}")
        print(f"[IMAGE-BG]    - Clothing tags: {len(image_plan.clothing_tags)}")
        
        # Assemble prompts
        print(f"[IMAGE-BG] 🔧 Assembling final SDXL prompts...")
        positive, negative = assemble_final_prompt(
            image_plan,
            persona_prompt=persona.get("prompt", "")
        )
        
        print(f"[IMAGE-BG] ✅ Prompts assembled")
        print(f"[IMAGE-BG]    - Positive: {len(positive)} chars")
        print(f"[IMAGE-BG]    - Negative: {len(negative)} chars")
        print(f"[IMAGE-BG]    - Preview: {positive[:100]}...")
        
        # Create job record
        print(f"[IMAGE-BG] 💾 Creating job record in database...")
        with get_db() as db:
            job = crud.create_image_job(
                db, user_id, persona_id, positive, negative, chat_id
            )
            job_id = job.id
        print(f"[IMAGE-BG] ✅ Job {job_id} created")
        
        # Dispatch to RunPod
        print(f"[IMAGE-BG] 🚀 Dispatching to RunPod...")
        from app.core.img_runpod import dispatch_image_generation
        result = await dispatch_image_generation(
            job_id=job_id,
            prompt=positive,
            negative_prompt=negative,
            tg_chat_id=tg_chat_id
        )
        
        if result:
            print(f"[IMAGE-BG] ✅ Job dispatched successfully to RunPod")
        else:
            print(f"[IMAGE-BG] ⚠️ Job dispatch failed (check RunPod logs)")
        
        print(f"[IMAGE-BG] ✅ ============= BACKGROUND IMAGE TASK COMPLETE =============")
            
    except Exception as e:
        print(f"[IMAGE-BG] ❌ ============= BACKGROUND IMAGE ERROR =============")
        print(f"[IMAGE-BG] ❌ Error type: {type(e).__name__}")
        print(f"[IMAGE-BG] ❌ Error message: {e}")
        import traceback
        traceback.print_exc()


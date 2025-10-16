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
    print(f"[PIPELINE] Starting for chat {chat_id}")
    
    # Create action manager for persistent indicators
    action_mgr = ChatActionManager(bot, tg_chat_id)
    
    try:
        # Show typing indicator
        await action_mgr.start("typing")
        
        # 1. Fetch data
        with get_db() as db:
            chat = crud.get_chat_by_id(db, chat_id)
            if not chat:
                raise ValueError(f"Chat {chat_id} not found")
                
            persona = crud.get_persona_by_id(db, chat.persona_id)
            if not persona:
                raise ValueError(f"Persona {chat.persona_id} not found")
                
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
        
        print(f"[PIPELINE] Data fetched: {len(chat_history)} history messages, persona={persona_data['name']}")
        
        # 2. Brain 1: State Resolver
        print(f"[PIPELINE] 🧠 Brain 1: Resolving state...")
        new_state = await resolve_state(
            previous_state=previous_state,
            chat_history=chat_history,
            user_message=batched_text,
            persona_name=persona_data["name"]
        )
        
        # 3. Brain 2: Dialogue Specialist
        print(f"[PIPELINE] 🧠 Brain 2: Generating dialogue...")
        dialogue_response = await generate_dialogue(
            state=new_state,
            chat_history=chat_history,
            user_message=batched_text,
            persona=persona_data
        )
        
        # 4. Save & send response immediately
        print(f"[PIPELINE] 💾 Saving and sending response...")
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
        
        # Send response to user
        await bot.send_message(tg_chat_id, dialogue_response, parse_mode="HTML")
        print(f"[PIPELINE] ✅ Response sent")
        
        # Stop typing, start upload_photo indicator
        await action_mgr.stop()
        await action_mgr.start("upload_photo")
        
        # 5. Brain 3 + Image dispatch (background, non-blocking)
        print(f"[PIPELINE] 🎨 Starting background image generation...")
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
        
    except Exception as e:
        print(f"[PIPELINE] ❌ Error: {e}")
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
    action_mgr: ChatActionManager
):
    """Non-blocking image generation"""
    try:
        print(f"[IMAGE-BG] Starting image generation...")
        
        # Brain 3: Generate image plan
        image_plan = await generate_image_plan(
            state=state,
            dialogue_response=dialogue_response,
            user_message=batched_text,
            persona=persona
        )
        
        # Assemble prompts
        positive, negative = assemble_final_prompt(
            image_plan,
            persona_prompt=persona.get("prompt", "")
        )
        
        print(f"[IMAGE-BG] Prompt assembled ({len(positive)} chars)")
        
        # Create job record
        with get_db() as db:
            job = crud.create_image_job(
                db, user_id, persona_id, positive, negative, chat_id
            )
            job_id = job.id
        
        # Dispatch to RunPod
        from app.core.img_runpod import dispatch_image_generation
        result = await dispatch_image_generation(
            job_id=job_id,
            prompt=positive,
            negative_prompt=negative,
            tg_chat_id=tg_chat_id
        )
        
        if result:
            print(f"[IMAGE-BG] ✅ Image dispatched successfully")
        else:
            print(f"[IMAGE-BG] ⚠️ Image dispatch returned no result")
            
    except Exception as e:
        print(f"[IMAGE-BG] ❌ Background image error: {e}")
    finally:
        # Stop upload_photo indicator when done (or failed)
        await action_mgr.stop()
        print(f"[IMAGE-BG] Stopped upload indicator")


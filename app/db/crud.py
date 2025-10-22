"""
CRUD operations for database models
"""
from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.db.models import User, Persona, Chat, Message, ImageJob
from datetime import datetime


# ========== USER OPERATIONS ==========

def get_or_create_user(db: Session, telegram_id: int, username: str = None, first_name: str = None) -> User:
    """Get existing user or create new one"""
    user = db.query(User).filter(User.id == telegram_id).first()
    if not user:
        user = User(
            id=telegram_id,
            username=username,
            first_name=first_name
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


# ========== PERSONA OPERATIONS ==========

def get_persona_by_key(db: Session, key: str) -> Optional[Persona]:
    """Get preset persona by key"""
    return db.query(Persona).filter(Persona.key == key, Persona.is_preset == True).first()


def get_persona_by_id(db: Session, persona_id: UUID) -> Optional[Persona]:
    """Get persona by ID"""
    return db.query(Persona).filter(Persona.id == persona_id).first()


def get_preset_personas(db: Session) -> List[Persona]:
    """Get all public personas"""
    return db.query(Persona).filter(Persona.visibility == 'public').all()


def get_user_personas(db: Session, user_id: int) -> List[Persona]:
    """Get user's custom personas"""
    return db.query(Persona).filter(
        Persona.owner_user_id == user_id, 
        Persona.visibility.in_(['private', 'custom'])
    ).all()


def create_persona(
    db: Session,
    name: str,
    prompt: str = None,
    badges: list = None,
    visibility: str = "custom",
    description: str = None,
    intro: str = None,
    owner_user_id: int = None,
    key: str = None
) -> Persona:
    """Create a new persona"""
    persona = Persona(
        name=name,
        prompt=prompt,
        badges=badges or [],
        visibility=visibility,
        description=description,
        intro=intro,
        owner_user_id=owner_user_id,
        key=key
    )
    db.add(persona)
    db.commit()
    db.refresh(persona)
    return persona


# ========== CHAT OPERATIONS ==========

def check_existing_chat(db: Session, tg_chat_id: int, user_id: int, persona_id: UUID) -> Optional[Chat]:
    """Check if chat exists for given tg_chat_id, user_id, and persona_id"""
    return db.query(Chat).filter(
        Chat.tg_chat_id == tg_chat_id,
        Chat.user_id == user_id,
        Chat.persona_id == persona_id
    ).first()


def get_or_create_chat(db: Session, tg_chat_id: int, user_id: int, persona_id: UUID) -> Chat:
    """Get existing chat or create new one"""
    chat = db.query(Chat).filter(
        Chat.tg_chat_id == tg_chat_id,
        Chat.user_id == user_id,
        Chat.persona_id == persona_id
    ).first()
    
    if not chat:
        chat = Chat(
            tg_chat_id=tg_chat_id,
            user_id=user_id,
            persona_id=persona_id,
            state_snapshot={}
        )
        db.add(chat)
        db.commit()
        db.refresh(chat)
    
    return chat


def create_new_chat(db: Session, tg_chat_id: int, user_id: int, persona_id: UUID) -> Chat:
    """Always create a new chat (even if one exists for this persona)"""
    chat = Chat(
        tg_chat_id=tg_chat_id,
        user_id=user_id,
        persona_id=persona_id,
        state_snapshot={}
    )
    db.add(chat)
    db.commit()
    db.refresh(chat)
    return chat


def get_active_chat(db: Session, tg_chat_id: int, user_id: int) -> Optional[Chat]:
    """Get most recent chat for this Telegram chat"""
    return db.query(Chat).filter(
        Chat.tg_chat_id == tg_chat_id,
        Chat.user_id == user_id
    ).order_by(desc(Chat.updated_at)).first()


def get_chat_by_tg_chat_id(db: Session, tg_chat_id: int) -> Optional[Chat]:
    """Get most recent chat by Telegram chat ID (without user_id filter)"""
    return db.query(Chat).filter(
        Chat.tg_chat_id == tg_chat_id
    ).order_by(desc(Chat.updated_at)).first()


def update_chat_state(db: Session, chat_id: UUID, state_snapshot: dict):
    """Update chat state snapshot"""
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if chat:
        chat.state_snapshot = state_snapshot
        chat.updated_at = datetime.utcnow()
        db.commit()


def clear_chat_history(db: Session, chat_id: UUID):
    """Clear all messages in a chat"""
    db.query(Message).filter(Message.chat_id == chat_id).delete()
    # Reset state
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if chat:
        chat.state_snapshot = {}
        chat.updated_at = datetime.utcnow()
    db.commit()


def delete_chat(db: Session, chat_id: UUID):
    """Delete a chat and all its messages"""
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        return False
    
    # Set chat_id to NULL for any image jobs associated with this chat
    # (preserves image job history but disconnects from deleted chat)
    db.query(ImageJob).filter(ImageJob.chat_id == chat_id).update(
        {"chat_id": None}, synchronize_session=False
    )
    
    # Messages will be deleted automatically due to cascade="all, delete-orphan"
    db.delete(chat)
    db.commit()
    return True


# ========== MESSAGE OPERATIONS ==========

def create_message(db: Session, chat_id: UUID, role: str, text: str, media: dict = None) -> Message:
    """Create a new message"""
    message = Message(
        chat_id=chat_id,
        role=role,
        text=text,
        media=media or {}
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def get_recent_messages(db: Session, chat_id: UUID, limit: int = 10) -> List[Message]:
    """Get recent messages for a chat"""
    return db.query(Message).filter(
        Message.chat_id == chat_id
    ).order_by(desc(Message.created_at)).limit(limit).all()


def get_chat_messages(db: Session, chat_id: UUID, limit: int = None) -> List[Message]:
    """Get all messages for a chat (ordered oldest first)
    
    If limit is specified, returns the LAST N messages (most recent)
    """
    if limit:
        # Get last N messages by ordering DESC and limiting, then reverse to chronological order
        messages = db.query(Message).filter(
            Message.chat_id == chat_id
        ).order_by(desc(Message.created_at)).limit(limit).all()
        return list(reversed(messages))  # Return in chronological order (oldest first)
    else:
        # Get all messages in chronological order
        return db.query(Message).filter(
            Message.chat_id == chat_id
        ).order_by(Message.created_at).all()


# ========== MESSAGE BATCHING OPERATIONS ==========

def get_unprocessed_user_messages(db: Session, chat_id: UUID) -> List[Message]:
    """Get all unprocessed user messages for batching"""
    return db.query(Message).filter(
        Message.chat_id == chat_id,
        Message.role == "user",
        Message.is_processed == False
    ).order_by(Message.created_at).all()


def mark_messages_processed(db: Session, message_ids: List[UUID]):
    """Mark messages as processed"""
    db.query(Message).filter(Message.id.in_(message_ids)).update(
        {"is_processed": True}, synchronize_session=False
    )
    db.commit()


def clear_unprocessed_messages(db: Session, chat_id: UUID):
    """Clear all unprocessed messages for a chat (on persona switch, timeout, etc.)"""
    db.query(Message).filter(
        Message.chat_id == chat_id,
        Message.role == "user",
        Message.is_processed == False
    ).update(
        {"is_processed": True}, synchronize_session=False
    )
    db.commit()


def get_last_assistant_message_time(db: Session, chat_id: UUID) -> Optional[datetime]:
    """Get timestamp of last assistant message"""
    last_msg = db.query(Message).filter(
        Message.chat_id == chat_id,
        Message.role == "assistant"
    ).order_by(Message.created_at.desc()).first()
    
    return last_msg.created_at if last_msg else None


def set_chat_processing(db: Session, chat_id: UUID, is_processing: bool):
    """Set chat processing lock to prevent overlapping pipeline executions"""
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if chat:
        chat.is_processing = is_processing
        chat.processing_started_at = datetime.utcnow() if is_processing else None
        db.commit()


def is_chat_processing(db: Session, chat_id: UUID) -> bool:
    """Check if chat is currently being processed"""
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        return False
    
    # If processing flag is set but it's been more than 10 minutes, clear it (stuck state)
    if chat.is_processing and chat.processing_started_at:
        elapsed = datetime.utcnow() - chat.processing_started_at
        if elapsed.total_seconds() > 600:  # 10 minutes
            print(f"[CRUD] ⚠️ Clearing stuck processing lock for chat {chat_id} (elapsed: {elapsed.total_seconds()}s)")
            chat.is_processing = False
            chat.processing_started_at = None
            db.commit()
            return False
    
    return chat.is_processing


# ========== PERSONA HISTORY START OPERATIONS ==========

def get_random_history_start(db: Session, persona_id: UUID):
    """Get random history start for persona"""
    from sqlalchemy.sql.expression import func
    from app.db.models import PersonaHistoryStart
    return db.query(PersonaHistoryStart).filter(
        PersonaHistoryStart.persona_id == persona_id
    ).order_by(func.random()).first()


# ========== CHAT TIMESTAMP OPERATIONS ==========

def update_chat_timestamps(db: Session, chat_id: UUID, user_at=None, assistant_at=None):
    """Update chat timestamp tracking"""
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        return
    
    if user_at:
        chat.last_user_message_at = user_at
    if assistant_at:
        chat.last_assistant_message_at = assistant_at
    
    db.commit()


def get_inactive_chats(db: Session, minutes: int = 5) -> List[Chat]:
    """Get chats where assistant spoke last and it's been >N minutes (for auto-messages)
    
    Only returns chats where we haven't already sent an auto-message since the last user reply.
    This prevents sending multiple auto-messages if the user doesn't respond.
    """
    from datetime import timedelta
    from sqlalchemy import or_, and_
    threshold = datetime.utcnow() - timedelta(minutes=minutes)
    
    return db.query(Chat).filter(
        Chat.last_assistant_message_at.isnot(None),  # Has assistant messages
        Chat.last_assistant_message_at < threshold,  # More than N minutes ago
        or_(
            Chat.last_user_message_at.is_(None),  # User never replied yet
            Chat.last_assistant_message_at > Chat.last_user_message_at  # Or assistant spoke last
        ),
        # Only send auto-message if we haven't sent one since the last user message
        or_(
            Chat.last_auto_message_at.is_(None),  # Never sent an auto-message
            and_(
                Chat.last_user_message_at.isnot(None),  # User has replied at some point
                Chat.last_auto_message_at < Chat.last_user_message_at  # Auto-msg was before last user msg
            )
        )
    ).all()


def get_inactive_chats_for_reengagement(db: Session, minutes: int = 1440) -> List[Chat]:
    """Get chats inactive for long periods (24h+) that need re-engagement
    
    This allows sending a follow-up even if we already sent an auto-message earlier
    (e.g., at 30min) and the user still hasn't responded. We only re-engage if:
    - It's been at least N minutes since our last auto-message attempt
    - The assistant spoke last (user hasn't replied)
    
    This prevents spam while allowing periodic re-engagement for very inactive chats.
    """
    from datetime import timedelta
    from sqlalchemy import or_
    threshold = datetime.utcnow() - timedelta(minutes=minutes)
    
    return db.query(Chat).filter(
        Chat.last_assistant_message_at.isnot(None),  # Has assistant messages
        or_(
            Chat.last_user_message_at.is_(None),  # User never replied yet
            Chat.last_assistant_message_at > Chat.last_user_message_at  # Or assistant spoke last
        ),
        # Either never sent auto-message, or last auto-message was more than N minutes ago
        or_(
            Chat.last_auto_message_at.is_(None),  # Never sent an auto-message
            Chat.last_auto_message_at < threshold  # Or last auto-message was long ago
        )
    ).all()


# ========== ENHANCED MESSAGE CREATION ==========

def create_message_with_state(
    db: Session, 
    chat_id: UUID, 
    role: str, 
    text: str, 
    media: dict = None,
    state_snapshot: dict = None,
    is_processed: bool = False
) -> Message:
    """Create a message with optional state snapshot"""
    message = Message(
        chat_id=chat_id,
        role=role,
        text=text,
        media=media or {},
        state_snapshot=state_snapshot,
        is_processed=is_processed
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def create_batch_messages(
    db: Session,
    chat_id: UUID,
    message_texts: List[str]
) -> List[Message]:
    """Create multiple user messages at once (from Redis batch)"""
    messages = []
    for text in message_texts:
        message = Message(
            chat_id=chat_id,
            role="user",
            text=text,
            media={},
            is_processed=True  # Already processed when saving from Redis
        )
        db.add(message)
        messages.append(message)
    
    db.commit()
    
    # Refresh all messages
    for msg in messages:
        db.refresh(msg)
    
    return messages


def get_chat_by_id(db: Session, chat_id: UUID) -> Optional[Chat]:
    """Get chat by ID"""
    return db.query(Chat).filter(Chat.id == chat_id).first()


# ========== IMAGE JOB OPERATIONS ==========

def create_image_job(
    db: Session,
    user_id: int,
    persona_id: UUID,
    prompt: str,
    negative_prompt: str,
    chat_id: UUID = None,
    ext: dict = None
) -> ImageJob:
    """Create a new image generation job"""
    job = ImageJob(
        user_id=user_id,
        persona_id=persona_id,
        chat_id=chat_id,
        prompt=prompt,
        negative_prompt=negative_prompt,
        status="queued",
        ext=ext or {}
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def get_image_job(db: Session, job_id: UUID) -> Optional[ImageJob]:
    """Get image job by ID"""
    return db.query(ImageJob).filter(ImageJob.id == job_id).first()


def get_last_completed_image_job(db: Session, chat_id: UUID) -> Optional[ImageJob]:
    """Get the last completed image job for a chat (to get previous image prompt)"""
    return db.query(ImageJob).filter(
        ImageJob.chat_id == chat_id,
        ImageJob.status == "completed"
    ).order_by(desc(ImageJob.created_at)).first()


def update_image_job_status(
    db: Session,
    job_id: UUID,
    status: str,
    result_url: str = None,
    result_file_id: str = None,
    error: str = None
):
    """Update image job status"""
    job = db.query(ImageJob).filter(ImageJob.id == job_id).first()
    if not job:
        return
    
    job.status = status
    if result_url:
        job.result_url = result_url
    if result_file_id:
        job.result_file_id = result_file_id
    if error:
        job.error = error
    if status in ("completed", "failed"):
        job.finished_at = datetime.utcnow()
    
    db.commit()


# ========== PERSONA HISTORY OPERATIONS ==========

def get_persona_histories(db: Session, persona_id: UUID):
    """Get all history starts for a persona"""
    from app.db.models import PersonaHistoryStart
    return db.query(PersonaHistoryStart).filter(
        PersonaHistoryStart.persona_id == persona_id
    ).all()


# ========== USER ENERGY OPERATIONS ==========

def get_user_energy(db: Session, user_id: int) -> dict:
    """Get user's current energy"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"energy": 0, "max_energy": 0}
    return {"energy": user.energy, "max_energy": user.max_energy}


def deduct_user_energy(db: Session, user_id: int, amount: int = 5) -> bool:
    """
    Deduct energy from user
    Returns True if successful, False if insufficient energy
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False
    
    if user.energy < amount:
        return False
    
    user.energy -= amount
    db.commit()
    return True


def add_user_energy(db: Session, user_id: int, amount: int) -> bool:
    """
    Add energy to user (up to max_energy)
    Returns True if successful
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False
    
    user.energy = min(user.energy + amount, user.max_energy)
    db.commit()
    return True


def check_user_energy(db: Session, user_id: int, required: int = 5) -> bool:
    """Check if user has enough energy"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False
    return user.energy >= required


def save_energy_upsell_message(db: Session, user_id: int, message_id: int, chat_id: int):
    """Save the last energy upsell message ID for this user"""
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.last_energy_upsell_message_id = message_id
        user.last_energy_upsell_chat_id = chat_id
        db.commit()


def get_and_clear_energy_upsell_message(db: Session, user_id: int) -> tuple:
    """
    Get and clear the last energy upsell message
    Returns: (message_id, chat_id)
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None, None
    
    message_id = user.last_energy_upsell_message_id
    chat_id = user.last_energy_upsell_chat_id
    
    # Clear the tracking
    user.last_energy_upsell_message_id = None
    user.last_energy_upsell_chat_id = None
    db.commit()
    
    return message_id, chat_id




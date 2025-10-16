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


def get_active_chat(db: Session, tg_chat_id: int, user_id: int) -> Optional[Chat]:
    """Get most recent chat for this Telegram chat"""
    return db.query(Chat).filter(
        Chat.tg_chat_id == tg_chat_id,
        Chat.user_id == user_id
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
    """Get all messages for a chat (ordered oldest first)"""
    query = db.query(Message).filter(Message.chat_id == chat_id).order_by(Message.created_at)
    if limit:
        query = query.limit(limit)
    return query.all()


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
    """Get chats inactive for N minutes (for auto-messages)"""
    from datetime import datetime, timedelta
    threshold = datetime.utcnow() - timedelta(minutes=minutes)
    
    return db.query(Chat).filter(
        Chat.last_user_message_at < threshold,
        Chat.last_assistant_message_at < Chat.last_user_message_at
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



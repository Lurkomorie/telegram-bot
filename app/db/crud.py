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
    """Get all preset personas"""
    return db.query(Persona).filter(Persona.is_preset == True).all()


def get_user_personas(db: Session, user_id: int) -> List[Persona]:
    """Get user's custom personas"""
    return db.query(Persona).filter(Persona.owner_user_id == user_id, Persona.is_preset == False).all()


def create_persona(
    db: Session,
    name: str,
    system_prompt: str,
    style: dict,
    negatives: str,
    appearance: dict,
    owner_user_id: int = None,
    key: str = None,
    is_preset: bool = False
) -> Persona:
    """Create a new persona"""
    persona = Persona(
        name=name,
        system_prompt=system_prompt,
        style=style,
        negatives=negatives,
        appearance=appearance,
        owner_user_id=owner_user_id,
        key=key,
        is_preset=is_preset
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



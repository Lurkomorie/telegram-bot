"""
CRUD operations for database models
"""
from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.db.models import User, Persona, Chat, Message, ImageJob, TgAnalyticsEvent, StartCode
from datetime import datetime, date


def apply_date_filter(query, model_field, start_date: Optional[str] = None, end_date: Optional[str] = None):
    """
    Apply date range filter to a query
    
    Args:
        query: SQLAlchemy query object
        model_field: The datetime field to filter on (e.g., TgAnalyticsEvent.created_at)
        start_date: Start date string in YYYY-MM-DD format
        end_date: End date string in YYYY-MM-DD format
    
    Returns:
        Filtered query
    """
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(model_field >= start_dt)
        except ValueError:
            pass  # Invalid date format, skip filter
    
    if end_date:
        try:
            # Add 1 day to include the entire end date
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            end_dt = end_dt.replace(hour=23, minute=59, second=59)
            query = query.filter(model_field <= end_dt)
        except ValueError:
            pass  # Invalid date format, skip filter
    
    return query


def apply_acquisition_source_filter(db: Session, query, acquisition_source: Optional[str] = None):
    """
    Apply acquisition source filter to a query that involves TgAnalyticsEvent
    
    Args:
        db: Database session
        query: SQLAlchemy query object
        acquisition_source: Acquisition source to filter by
    
    Returns:
        Filtered query
    """
    if not acquisition_source:
        return query
    
    # Use a subquery approach to filter by acquisition source
    # This is safer than trying to join User table
    user_ids_subquery = db.query(User.id).filter(
        User.acquisition_source == acquisition_source
    ).subquery()
    
    query = query.filter(TgAnalyticsEvent.client_id.in_(user_ids_subquery))
    
    return query


# ========== USER OPERATIONS ==========

def get_or_create_user(db: Session, telegram_id: int, username: str = None, first_name: str = None, acquisition_source: str = None) -> User:
    """Get existing user or create new one
    
    Args:
        telegram_id: Telegram user ID
        username: User's username
        first_name: User's first name
        acquisition_source: Deep-link payload for ads attribution (only set on first visit)
    
    Returns:
        User object
    """
    user = db.query(User).filter(User.id == telegram_id).first()
    if not user:
        # New user - set acquisition source if provided
        user = User(
            id=telegram_id,
            username=username,
            first_name=first_name,
            acquisition_source=acquisition_source if acquisition_source else None,
            acquisition_timestamp=datetime.utcnow() if acquisition_source else None
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # Existing user - only set acquisition source if not already set (first-touch attribution)
        if acquisition_source and not user.acquisition_source:
            user.acquisition_source = acquisition_source
            user.acquisition_timestamp = datetime.utcnow()
            db.commit()
            db.refresh(user)
    return user


def get_user(db: Session, telegram_id: int) -> Optional[User]:
    """Get user by telegram ID
    
    Args:
        telegram_id: Telegram user ID
    
    Returns:
        User object or None if not found
    """
    return db.query(User).filter(User.id == telegram_id).first()


def update_user_age_verified(db: Session, telegram_id: int) -> User:
    """Mark user as age verified
    
    Args:
        telegram_id: Telegram user ID
    
    Returns:
        Updated User object
    """
    user = db.query(User).filter(User.id == telegram_id).first()
    if user:
        user.age_verified = True
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


def archive_all_user_chats(db: Session, user_id: int):
    """Archive all chats for a telegram user (to stop scheduler auto-messages)"""
    db.query(Chat).filter(
        Chat.user_id == user_id
    ).update(
        {"status": "archived"}, synchronize_session=False
    )
    db.commit()


def archive_user_chats_except(db: Session, user_id: int, chat_id: UUID):
    """Archive all user chats except the specified one"""
    db.query(Chat).filter(
        Chat.user_id == user_id,
        Chat.id != chat_id
    ).update(
        {"status": "archived"}, synchronize_session=False
    )
    db.commit()


def activate_chat(db: Session, chat_id: UUID, user_id: int):
    """Reactivate a chat and archive all other chats for that user
    
    This is used when a user chooses to "continue" an existing conversation.
    We archive all their other chats to prevent scheduler messages.
    """
    # First, archive all user chats
    archive_all_user_chats(db, user_id)
    
    # Then activate the specified chat
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if chat:
        chat.status = "active"
        db.commit()


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
    """Always create a new chat (even if one exists for this persona)
    
    Archives all other chats for this telegram user to prevent scheduler
    from sending auto-messages to old conversations.
    """
    # Archive all other chats for this telegram user
    archive_all_user_chats(db, user_id)
    
    chat = Chat(
        tg_chat_id=tg_chat_id,
        user_id=user_id,
        persona_id=persona_id,
        state_snapshot={},
        status="active"
    )
    db.add(chat)
    db.commit()
    db.refresh(chat)
    return chat


def get_active_chat(db: Session, tg_chat_id: int, user_id: int) -> Optional[Chat]:
    """Get most recent active chat for this Telegram chat"""
    return db.query(Chat).filter(
        Chat.tg_chat_id == tg_chat_id,
        Chat.user_id == user_id,
        Chat.status == "active"
    ).order_by(desc(Chat.updated_at)).first()


def get_chat_by_tg_chat_id(db: Session, tg_chat_id: int) -> Optional[Chat]:
    """Get most recent active chat by Telegram chat ID (without user_id filter)"""
    return db.query(Chat).filter(
        Chat.tg_chat_id == tg_chat_id,
        Chat.status == "active"
    ).order_by(desc(Chat.updated_at)).first()


def update_chat_state(db: Session, chat_id: UUID, state_snapshot: dict):
    """Update chat state snapshot"""
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if chat:
        chat.state_snapshot = state_snapshot
        chat.updated_at = datetime.utcnow()
        db.commit()


def update_chat_memory(db: Session, chat_id: UUID, memory: str):
    """Update chat memory"""
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if chat:
        chat.memory = memory
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


def delete_all_user_chats(db: Session, user_id: int):
    """Delete all chats and messages for a user
    
    Args:
        user_id: Telegram user ID
    
    Returns:
        Number of chats deleted
    """
    # Get all chats for the user
    chats = db.query(Chat).filter(Chat.user_id == user_id).all()
    chat_ids = [chat.id for chat in chats]
    
    if not chat_ids:
        return 0
    
    # Set chat_id to NULL for any image jobs associated with these chats
    # (preserves image job history but disconnects from deleted chats)
    db.query(ImageJob).filter(ImageJob.chat_id.in_(chat_ids)).update(
        {"chat_id": None}, synchronize_session=False
    )
    
    # Delete all chats (messages will be deleted automatically due to cascade)
    deleted_count = db.query(Chat).filter(Chat.user_id == user_id).delete(synchronize_session=False)
    db.commit()
    
    return deleted_count


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


def get_inactive_chats(db: Session, minutes: int = 5, test_user_ids: Optional[List[int]] = None) -> List[Chat]:
    """Get chats where assistant spoke last and it's been >N minutes (for auto-messages)
    
    Only returns chats where we haven't already sent an auto-message since the last user reply.
    This prevents sending multiple auto-messages if the user doesn't respond.
    Only queries active chats to prevent messages to archived conversations.
    
    Args:
        db: Database session
        minutes: Number of minutes of inactivity required
        test_user_ids: Optional list of user IDs to restrict results to (for testing)
    """
    from datetime import timedelta
    from sqlalchemy import or_, and_
    threshold = datetime.utcnow() - timedelta(minutes=minutes)
    
    query = db.query(Chat).filter(
        Chat.status == "active",  # Only active chats
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
    )
    
    # Filter by test users if whitelist is provided
    if test_user_ids is not None:
        query = query.filter(Chat.user_id.in_(test_user_ids))
    
    return query.all()


def get_inactive_chats_for_reengagement(db: Session, minutes: int = 1440, test_user_ids: Optional[List[int]] = None) -> List[Chat]:
    """Get chats inactive for long periods (24h+) that need a single re-engagement message
    
    This allows sending ONE follow-up 24h after we already sent a 30min auto-message
    and the user still hasn't responded. We only re-engage if:
    - We already sent a 30min auto-message (last_auto_message_at is set)
    - It's been at least N minutes (typically 24h) since that auto-message
    - The assistant spoke last (user hasn't replied since the auto-message)
    - The chat is active (not archived)
    
    Sends only ONE 24h message. Stops until user replies, which resets the cycle.
    
    Args:
        db: Database session
        minutes: Number of minutes of inactivity required (default: 1440 = 24 hours)
        test_user_ids: Optional list of user IDs to restrict results to (for testing)
    """
    from datetime import timedelta
    from sqlalchemy import or_
    threshold = datetime.utcnow() - timedelta(minutes=minutes)
    
    query = db.query(Chat).filter(
        Chat.status == "active",  # Only active chats
        Chat.last_assistant_message_at.isnot(None),  # Has assistant messages
        or_(
            Chat.last_user_message_at.is_(None),  # User never replied yet
            Chat.last_assistant_message_at > Chat.last_user_message_at  # Or assistant spoke last
        ),
        # Must have sent a 30min message already
        Chat.last_auto_message_at.isnot(None),
        # That message was 24h ago
        Chat.last_auto_message_at < threshold,
        # User hasn't replied since that auto message (prevents infinite loop)
        or_(
            Chat.last_user_message_at.is_(None),  # User never replied
            Chat.last_auto_message_at > Chat.last_user_message_at  # Auto message sent after user's last reply
        )
    )
    
    # Filter by test users if whitelist is provided
    if test_user_ids is not None:
        query = query.filter(Chat.user_id.in_(test_user_ids))
    
    return query.all()


# ========== ENHANCED MESSAGE CREATION ==========

def increment_chat_message_count(db: Session, chat_id: UUID, increment_by: int = 1) -> int:
    """
    Increment message counter for a chat and return new count
    
    Args:
        db: Database session
        chat_id: Chat UUID
        increment_by: Number to increment by (default 1)
    
    Returns:
        New message count
    """
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if chat:
        chat.message_count += increment_by
        db.commit()
        db.refresh(chat)
        return chat.message_count
    return 0


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
    
    # Increment message counter (1 for each message saved)
    increment_chat_message_count(db, chat_id, increment_by=1)
    
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
    
    # Increment message counter by batch size
    increment_chat_message_count(db, chat_id, increment_by=len(messages))
    
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


def create_initial_image_job(
    db: Session,
    user_id: int,
    persona_id: UUID,
    chat_id: UUID,
    prompt: str,
    result_url: str = None
) -> ImageJob:
    """Create a completed initial image job for history_start continuity"""
    from datetime import datetime
    job = ImageJob(
        user_id=user_id,
        persona_id=persona_id,
        chat_id=chat_id,
        prompt=prompt,
        negative_prompt="",  # Not relevant for history images
        status="completed",
        result_url=result_url,
        finished_at=datetime.utcnow(),
        ext={"source": "history_start"}
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


# ========== PREMIUM SUBSCRIPTION OPERATIONS ==========

def check_user_premium(db: Session, user_id: int) -> bool:
    """
    Check if user has active premium subscription
    Returns True if user is premium and subscription hasn't expired
    """
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False
    
    # Check if premium and not expired
    if user.is_premium:
        if user.premium_until is None:
            return True  # Lifetime premium
        if user.premium_until > datetime.utcnow():
            return True  # Active subscription
        else:
            # Expired - clear premium status
            user.is_premium = False
            db.commit()
            return False
    
    return False


def activate_premium(db: Session, user_id: int, duration_days: int) -> bool:
    """
    Activate premium subscription for user
    duration_days: number of days to add to subscription
    Returns True if successful
    """
    from datetime import timedelta
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False
    
    # Set premium status
    user.is_premium = True
    
    # Calculate expiry date
    if user.premium_until and user.premium_until > datetime.utcnow():
        # Extend existing subscription
        user.premium_until = user.premium_until + timedelta(days=duration_days)
    else:
        # New subscription
        user.premium_until = datetime.utcnow() + timedelta(days=duration_days)
    
    db.commit()
    return True


def regenerate_user_energy(db: Session, user_id: int) -> bool:
    """
    Add 2 energy to user (hourly regeneration for free users)
    Only applies to non-premium users
    Returns True if energy was added
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False
    
    # Skip if user is premium
    if check_user_premium(db, user_id):
        return False
    
    # Add 2 energy, capped at max_energy
    old_energy = user.energy
    user.energy = min(user.energy + 2, user.max_energy)
    db.commit()
    
    return user.energy > old_energy


def regenerate_all_users_energy(db: Session) -> int:
    """
    Regenerate 2 energy for all non-premium users (runs every hour)
    Returns count of users who received energy
    """
    
    # Get all non-premium users
    users = db.query(User).filter(
        (User.is_premium == False) | 
        ((User.is_premium == True) & (User.premium_until < datetime.utcnow()))
    ).all()
    
    count = 0
    for user in users:
        # Update expired premium status
        if user.is_premium and user.premium_until and user.premium_until < datetime.utcnow():
            user.is_premium = False
        
        # Add energy if below max
        if user.energy < user.max_energy:
            user.energy = min(user.energy + 2, user.max_energy)
            count += 1
    
    db.commit()
    return count


# ========== ANALYTICS OPERATIONS ==========

def create_analytics_event(
    db: Session,
    client_id: int,
    event_name: str,
    persona_id: UUID = None,
    persona_name: str = None,
    message: str = None,
    prompt: str = None,
    negative_prompt: str = None,
    image_url: str = None,
    meta: dict = None
) -> TgAnalyticsEvent:
    """Create a new analytics event"""
    event = TgAnalyticsEvent(
        client_id=client_id,
        event_name=event_name,
        persona_id=persona_id,
        persona_name=persona_name,
        message=message,
        prompt=prompt,
        negative_prompt=negative_prompt,
        image_url=image_url,
        meta=meta or {}
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def get_analytics_events_by_user(db: Session, client_id: int, limit: int = 1000) -> List[TgAnalyticsEvent]:
    """Get all analytics events for a specific user, sorted by created_at ASC (oldest first, like chat)"""
    return db.query(TgAnalyticsEvent).filter(
        TgAnalyticsEvent.client_id == client_id
    ).order_by(TgAnalyticsEvent.created_at).limit(limit).all()


def get_all_analytics_events(db: Session, limit: int = 10000, offset: int = 0) -> List[TgAnalyticsEvent]:
    """Get all analytics events, sorted by created_at DESC"""
    return db.query(TgAnalyticsEvent).order_by(
        desc(TgAnalyticsEvent.created_at)
    ).limit(limit).offset(offset).all()


def get_analytics_stats(db: Session, start_date: Optional[str] = None, end_date: Optional[str] = None, acquisition_source: Optional[str] = None) -> dict:
    """Get analytics statistics
    
    Args:
        start_date: Filter from this date onwards (YYYY-MM-DD)
        end_date: Filter up to this date (YYYY-MM-DD)
        acquisition_source: Filter by acquisition source
    """
    from sqlalchemy import func, distinct
    from datetime import timedelta
    
    # Base queries with date filter
    base_query = db.query(TgAnalyticsEvent)
    base_query = apply_date_filter(base_query, TgAnalyticsEvent.created_at, start_date, end_date)
    base_query = apply_acquisition_source_filter(db, base_query, acquisition_source)
    
    # Total unique users
    total_users = db.query(func.count(distinct(TgAnalyticsEvent.client_id)))
    total_users = apply_date_filter(total_users, TgAnalyticsEvent.created_at, start_date, end_date)
    total_users = apply_acquisition_source_filter(db, total_users, acquisition_source)
    total_users = total_users.scalar()
    
    # Total events
    total_events = base_query.count()
    
    # Total messages (user + ai)
    total_messages = db.query(func.count(TgAnalyticsEvent.id)).filter(
        TgAnalyticsEvent.event_name.in_(['user_message', 'ai_message'])
    )
    total_messages = apply_date_filter(total_messages, TgAnalyticsEvent.created_at, start_date, end_date)
    total_messages = apply_acquisition_source_filter(db, total_messages, acquisition_source)
    total_messages = total_messages.scalar()
    
    # Total image generations
    total_images = db.query(func.count(TgAnalyticsEvent.id)).filter(
        TgAnalyticsEvent.event_name == 'image_generated'
    )
    total_images = apply_date_filter(total_images, TgAnalyticsEvent.created_at, start_date, end_date)
    total_images = apply_acquisition_source_filter(db, total_images, acquisition_source)
    total_images = total_images.scalar()
    
    # Active users (last 7 days)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    active_users = db.query(func.count(distinct(TgAnalyticsEvent.client_id))).filter(
        TgAnalyticsEvent.created_at >= seven_days_ago
    )
    active_users = apply_date_filter(active_users, TgAnalyticsEvent.created_at, start_date, end_date)
    active_users = apply_acquisition_source_filter(db, active_users, acquisition_source)
    active_users = active_users.scalar()
    
    # Most popular personas with unique user counts
    popular_personas_query = db.query(
        TgAnalyticsEvent.persona_name,
        func.count(TgAnalyticsEvent.id).label('interaction_count'),
        func.count(distinct(TgAnalyticsEvent.client_id)).label('user_count')
    ).filter(
        TgAnalyticsEvent.persona_name.isnot(None)
    )
    popular_personas_query = apply_date_filter(popular_personas_query, TgAnalyticsEvent.created_at, start_date, end_date)
    popular_personas_query = apply_acquisition_source_filter(db, popular_personas_query, acquisition_source)
    popular_personas = popular_personas_query.group_by(
        TgAnalyticsEvent.persona_name
    ).order_by(desc('interaction_count')).limit(10).all()
    
    # Average messages per user
    avg_messages_per_user = total_messages / total_users if total_users > 0 else 0
    
    # Image waiting time and failed images
    avg_image_waiting_time = get_avg_image_waiting_time(db, start_date=start_date, end_date=end_date, acquisition_source=acquisition_source)
    failed_images_count = get_failed_images_count(db, start_date=start_date, end_date=end_date, acquisition_source=acquisition_source)
    
    return {
        'total_users': total_users or 0,
        'total_events': total_events or 0,
        'total_messages': total_messages or 0,
        'total_images': total_images or 0,
        'active_users_7d': active_users or 0,
        'avg_messages_per_user': round(avg_messages_per_user, 2),
        'avg_image_waiting_time': round(avg_image_waiting_time, 2),
        'failed_images_count': failed_images_count,
        'popular_personas': [
            {
                'name': name,
                'interaction_count': interaction_count,
                'user_count': user_count
            } for name, interaction_count, user_count in popular_personas
        ]
    }


def get_all_users_from_analytics(db: Session, limit: int = 100, offset: int = 0) -> dict:
    """Get all users with their message counts and acquisition source (optimized with pagination)
    
    Args:
        db: Database session
        limit: Number of users to return (default 100)
        offset: Number of users to skip (default 0)
    
    Returns:
        Dict with 'users', 'total', 'limit', 'offset' keys
    """
    from sqlalchemy import func, cast, Date, case, and_, literal_column
    from datetime import datetime, timedelta
    
    # Get total count first
    total_users = db.query(func.count(func.distinct(TgAnalyticsEvent.client_id))).scalar() or 0
    
    # Get basic user stats with single query using window functions
    users_query = db.query(
        TgAnalyticsEvent.client_id,
        func.count(TgAnalyticsEvent.id).label('total_events'),
        func.max(TgAnalyticsEvent.created_at).label('last_activity'),
        func.min(TgAnalyticsEvent.created_at).label('first_activity'),
        func.sum(
            case((TgAnalyticsEvent.event_name == 'user_message', 1), else_=0)
        ).label('message_events_count'),
        func.max(
            case((TgAnalyticsEvent.event_name == 'user_message', TgAnalyticsEvent.created_at), else_=None)
        ).label('last_message_send')
    ).group_by(
        TgAnalyticsEvent.client_id
    ).order_by(desc('last_activity')).limit(limit).offset(offset).all()
    
    if not users_query:
        return {
            'users': [],
            'total': total_users,
            'limit': limit,
            'offset': offset
        }
    
    # Get all client IDs for batch queries
    client_ids = [u.client_id for u in users_query]
    
    # Batch fetch user info from User table
    user_objs = db.query(User).filter(User.id.in_(client_ids)).all()
    user_dict = {u.id: u for u in user_objs}
    
    # Batch fetch sparkline data for all users (last 14 days)
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=13)
    
    # Get all event counts by date for all users at once
    all_events_sparkline = db.query(
        TgAnalyticsEvent.client_id,
        cast(TgAnalyticsEvent.created_at, Date).label('date'),
        func.count(TgAnalyticsEvent.id).label('count')
    ).filter(
        TgAnalyticsEvent.client_id.in_(client_ids),
        cast(TgAnalyticsEvent.created_at, Date) >= start_date,
        cast(TgAnalyticsEvent.created_at, Date) <= end_date
    ).group_by(TgAnalyticsEvent.client_id, 'date').all()
    
    # Get message counts by date for all users at once
    message_sparkline = db.query(
        TgAnalyticsEvent.client_id,
        cast(TgAnalyticsEvent.created_at, Date).label('date'),
        func.count(TgAnalyticsEvent.id).label('count')
    ).filter(
        TgAnalyticsEvent.client_id.in_(client_ids),
        TgAnalyticsEvent.event_name == 'user_message',
        cast(TgAnalyticsEvent.created_at, Date) >= start_date,
        cast(TgAnalyticsEvent.created_at, Date) <= end_date
    ).group_by(TgAnalyticsEvent.client_id, 'date').all()
    
    # Organize sparkline data by client_id
    all_events_dict = {}
    for row in all_events_sparkline:
        if row.client_id not in all_events_dict:
            all_events_dict[row.client_id] = {}
        all_events_dict[row.client_id][row.date] = row.count
    
    message_dict = {}
    for row in message_sparkline:
        if row.client_id not in message_dict:
            message_dict[row.client_id] = {}
        message_dict[row.client_id][row.date] = row.count
    
    # Batch fetch consecutive days data
    message_dates_query = db.query(
        TgAnalyticsEvent.client_id,
        func.array_agg(
            func.distinct(cast(TgAnalyticsEvent.created_at, Date))
        ).label('dates')
    ).filter(
        TgAnalyticsEvent.client_id.in_(client_ids),
        TgAnalyticsEvent.event_name == 'user_message'
    ).group_by(TgAnalyticsEvent.client_id).all()
    
    consecutive_days_dict = {}
    today = datetime.utcnow().date()
    yesterday = today - timedelta(days=1)
    
    for row in message_dates_query:
        dates = sorted(row.dates, reverse=True) if row.dates else []
        if not dates:
            consecutive_days_dict[row.client_id] = 0
            continue
        
        # Check if user has activity today or yesterday
        if dates[0] not in (today, yesterday):
            consecutive_days_dict[row.client_id] = 0
            continue
        
        # Count consecutive days
        streak = 1
        expected_date = dates[0] - timedelta(days=1)
        for date in dates[1:]:
            if date == expected_date:
                streak += 1
                expected_date = date - timedelta(days=1)
            else:
                break
        consecutive_days_dict[row.client_id] = streak
    
    # Build result
    result = []
    for user in users_query:
        user_obj = user_dict.get(user.client_id)
        
        # Build sparkline arrays (14 days)
        sparkline_data = []
        message_sparkline_data = []
        current_date = start_date
        for _ in range(14):
            sparkline_data.append(all_events_dict.get(user.client_id, {}).get(current_date, 0))
            message_sparkline_data.append(message_dict.get(user.client_id, {}).get(current_date, 0))
            current_date += timedelta(days=1)
        
        result.append({
            'client_id': user.client_id,
            'username': user_obj.username if user_obj else None,
            'first_name': user_obj.first_name if user_obj else None,
            'total_events': user.total_events,
            'last_activity': user.last_activity.isoformat() if user.last_activity else None,
            'first_activity': user.first_activity.isoformat() if user.first_activity else None,
            'acquisition_source': user_obj.acquisition_source if user_obj else None,
            'acquisition_timestamp': user_obj.acquisition_timestamp.isoformat() if user_obj and user_obj.acquisition_timestamp else None,
            'sparkline_data': sparkline_data,
            'consecutive_days_streak': consecutive_days_dict.get(user.client_id, 0),
            'message_events_count': user.message_events_count or 0,
            'last_message_send': user.last_message_send.isoformat() if user.last_message_send else None,
            'message_sparkline_data': message_sparkline_data
        })
    
    return {
        'users': result,
        'total': total_users,
        'limit': limit,
        'offset': offset
    }


def get_user_activity_sparkline_data(db: Session, client_id: int, days: int = 14) -> List[int]:
    """Get user activity (all events) for the last N days as sparkline data"""
    from sqlalchemy import func, cast, Date
    from datetime import datetime, timedelta
    
    # Calculate date range
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=days - 1)
    
    # Query all events grouped by date
    daily_counts = db.query(
        cast(TgAnalyticsEvent.created_at, Date).label('date'),
        func.count(TgAnalyticsEvent.id).label('count')
    ).filter(
        TgAnalyticsEvent.client_id == client_id,
        cast(TgAnalyticsEvent.created_at, Date) >= start_date,
        cast(TgAnalyticsEvent.created_at, Date) <= end_date
    ).group_by('date').all()
    
    # Create a dict for quick lookup
    counts_dict = {row.date: row.count for row in daily_counts}
    
    # Build complete array with 0 for missing days
    sparkline = []
    current_date = start_date
    for _ in range(days):
        count = counts_dict.get(current_date, 0)
        sparkline.append(count)
        current_date += timedelta(days=1)
    
    return sparkline


def get_user_sparkline_data(db: Session, client_id: int, days: int = 14) -> List[int]:
    """Get user message activity for the last N days as sparkline data"""
    from sqlalchemy import func, cast, Date
    from datetime import datetime, timedelta
    
    # Calculate date range
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=days - 1)
    
    # Query user_message events grouped by date
    daily_counts = db.query(
        cast(TgAnalyticsEvent.created_at, Date).label('date'),
        func.count(TgAnalyticsEvent.id).label('count')
    ).filter(
        TgAnalyticsEvent.client_id == client_id,
        TgAnalyticsEvent.event_name == 'user_message',
        cast(TgAnalyticsEvent.created_at, Date) >= start_date,
        cast(TgAnalyticsEvent.created_at, Date) <= end_date
    ).group_by('date').all()
    
    # Create a dict for quick lookup
    counts_dict = {row.date: row.count for row in daily_counts}
    
    # Build complete array with 0 for missing days
    sparkline = []
    current_date = start_date
    for _ in range(days):
        count = counts_dict.get(current_date, 0)
        sparkline.append(count)
        current_date += timedelta(days=1)
    
    return sparkline


def get_user_consecutive_days(db: Session, client_id: int) -> int:
    """Calculate current active streak of consecutive days with user messages"""
    from sqlalchemy import cast, Date, distinct
    from datetime import datetime, timedelta
    
    # Get distinct dates with user messages, ordered descending
    message_dates = db.query(
        distinct(cast(TgAnalyticsEvent.created_at, Date)).label('date')
    ).filter(
        TgAnalyticsEvent.client_id == client_id,
        TgAnalyticsEvent.event_name == 'user_message'
    ).order_by(desc('date')).all()
    
    if not message_dates:
        return 0
    
    # Calculate streak from today going backwards
    today = datetime.utcnow().date()
    yesterday = today - timedelta(days=1)
    
    # Check if user has activity today or yesterday (to count as active streak)
    latest_date = message_dates[0].date
    if latest_date != today and latest_date != yesterday:
        return 0  # Streak is broken
    
    # Count consecutive days
    streak = 0
    expected_date = today if latest_date == today else yesterday
    
    for row in message_dates:
        if row.date == expected_date or row.date == expected_date - timedelta(days=1):
            streak += 1
            expected_date = row.date - timedelta(days=1)
        else:
            break
    
    return streak


def get_acquisition_source_stats(db: Session, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[dict]:
    """Get statistics grouped by acquisition source
    
    Args:
        start_date: Filter from this date onwards (YYYY-MM-DD)
        end_date: Filter up to this date (YYYY-MM-DD)
    """
    from sqlalchemy import func, cast, Date, case
    from datetime import datetime, timedelta
    
    # Calculate date range for sparklines (14 days)
    end_date_calc = datetime.utcnow().date()
    start_date_calc = end_date_calc - timedelta(days=13)
    
    # Get user counts by acquisition source (with date filter on acquisition_timestamp)
    user_counts_query = db.query(
        func.coalesce(User.acquisition_source, 'direct').label('source'),
        func.count(User.id).label('user_count')
    )
    # Apply date filter to user acquisition
    if start_date or end_date:
        user_counts_query = apply_date_filter(user_counts_query, User.acquisition_timestamp, start_date, end_date)
    user_counts_query = user_counts_query.group_by(
        func.coalesce(User.acquisition_source, 'direct')
    ).all()
    
    # Get event counts by acquisition source (with date filter on event created_at)
    event_counts_query = db.query(
        func.coalesce(User.acquisition_source, 'direct').label('source'),
        func.count(TgAnalyticsEvent.id).label('total_events')
    ).join(
        TgAnalyticsEvent, User.id == TgAnalyticsEvent.client_id
    )
    # Apply date filter to events
    if start_date or end_date:
        event_counts_query = apply_date_filter(event_counts_query, TgAnalyticsEvent.created_at, start_date, end_date)
    event_counts_query = event_counts_query.group_by(
        func.coalesce(User.acquisition_source, 'direct')
    ).all()
    
    # Build result dict with main stats
    source_stats = {}
    
    # First, populate with user counts
    for row in user_counts_query:
        source_stats[row.source] = {
            'source': row.source,
            'user_count': row.user_count,
            'total_events': 0,
            'avg_events_per_user': 0,
            'sparkline_data': []
        }
    
    # Then add event counts
    event_counts_dict = {row.source: row.total_events for row in event_counts_query}
    for source in source_stats.keys():
        total_events = event_counts_dict.get(source, 0)
        source_stats[source]['total_events'] = total_events
        source_stats[source]['avg_events_per_user'] = round(total_events / source_stats[source]['user_count'], 2) if source_stats[source]['user_count'] > 0 else 0
    
    # Get sparkline data (new users per day for last 14 days) in a single query
    # Create a subquery for each user's first activity date
    user_first_activity = db.query(
        User.id.label('user_id'),
        func.coalesce(User.acquisition_source, 'direct').label('source'),
        func.min(cast(TgAnalyticsEvent.created_at, Date)).label('first_activity_date')
    ).join(
        TgAnalyticsEvent, User.id == TgAnalyticsEvent.client_id
    ).group_by(User.id, func.coalesce(User.acquisition_source, 'direct')).subquery()
    
    # Get counts by source and date
    sparkline_data = db.query(
        user_first_activity.c.source,
        user_first_activity.c.first_activity_date,
        func.count(user_first_activity.c.user_id).label('count')
    ).filter(
        user_first_activity.c.first_activity_date >= start_date_calc,
        user_first_activity.c.first_activity_date <= end_date_calc
    ).group_by(
        user_first_activity.c.source,
        user_first_activity.c.first_activity_date
    ).all()
    
    # Build sparkline lookup dict
    sparkline_lookup = {}
    for row in sparkline_data:
        if row.source not in sparkline_lookup:
            sparkline_lookup[row.source] = {}
        sparkline_lookup[row.source][row.first_activity_date] = row.count
    
    # Fill in sparkline data for each source
    for source in source_stats.keys():
        sparkline = []
        current_date = start_date_calc
        
        for _ in range(14):
            count = sparkline_lookup.get(source, {}).get(current_date, 0)
            sparkline.append(count)
            current_date += timedelta(days=1)
        
        source_stats[source]['sparkline_data'] = sparkline
    
    # Convert to list and sort by user count
    result = list(source_stats.values())
    result.sort(key=lambda x: x['user_count'], reverse=True)
    
    return result


# ========== TIME-SERIES ANALYTICS FUNCTIONS ==========


def get_messages_over_time(db: Session, interval_minutes: int = 60, limit_hours: int = 24, start_date: Optional[str] = None, end_date: Optional[str] = None, acquisition_source: Optional[str] = None) -> List[dict]:
    """
    Get message counts over time bucketed by interval
    
    Args:
        start_date: Filter from this date onwards (YYYY-MM-DD)
        end_date: Filter up to this date (YYYY-MM-DD)
        acquisition_source: Filter by acquisition source
    
    Args:
        db: Database session
        interval_minutes: Time bucket size (1, 5, 15, 30, 60, 360, 720, 1440)
        limit_hours: How many hours of history to fetch - only used if start_date/end_date not provided
    
    Returns:
        List of {timestamp, count} dictionaries
    """
    from sqlalchemy import func, text
    from datetime import datetime, timedelta
    
    # Use PostgreSQL's date_trunc for time bucketing
    if interval_minutes == 1:
        trunc_spec = 'minute'
    elif interval_minutes < 60:
        # For 5, 15, 30 minutes, we'll use minute and group manually
        trunc_spec = 'minute'
    elif interval_minutes == 60:
        trunc_spec = 'hour'
    elif interval_minutes == 360:
        trunc_spec = 'hour'
    elif interval_minutes == 720:
        trunc_spec = 'hour'
    else:  # 1440 (1 day)
        trunc_spec = 'day'
    
    query = db.query(
        func.date_trunc(trunc_spec, TgAnalyticsEvent.created_at).label('time_bucket'),
        func.count(TgAnalyticsEvent.id).label('count')
    ).filter(
        TgAnalyticsEvent.event_name.in_(['user_message', 'ai_message'])
    )
    
    # Apply date filters (default to limit_hours if not provided)
    if not start_date and not end_date:
        cutoff_time = datetime.utcnow() - timedelta(hours=limit_hours)
        query = query.filter(TgAnalyticsEvent.created_at >= cutoff_time)
    else:
        query = apply_date_filter(query, TgAnalyticsEvent.created_at, start_date, end_date)
    
    query = apply_acquisition_source_filter(db, query, acquisition_source)
    query = query.group_by('time_bucket').order_by('time_bucket')
    
    results = query.all()
    
    # For intervals that don't align with date_trunc, we need to further group
    if interval_minutes in [5, 15, 30]:
        # Group by floor(minutes / interval) * interval
        from collections import defaultdict
        bucketed = defaultdict(int)
        
        for row in results:
            # Round down to nearest interval
            dt = row.time_bucket
            total_minutes = dt.hour * 60 + dt.minute
            bucket_num = total_minutes // interval_minutes
            bucket_minutes = bucket_num * interval_minutes
            bucket_time = dt.replace(hour=bucket_minutes // 60, minute=bucket_minutes % 60, second=0, microsecond=0)
            bucketed[bucket_time] += row.count
        
        return [{'timestamp': ts.isoformat(), 'count': count} for ts, count in sorted(bucketed.items())]
    elif interval_minutes == 360:
        # 6 hours: group by floor(hour / 6) * 6
        from collections import defaultdict
        bucketed = defaultdict(int)
        
        for row in results:
            dt = row.time_bucket
            bucket_hour = (dt.hour // 6) * 6
            bucket_time = dt.replace(hour=bucket_hour, minute=0, second=0, microsecond=0)
            bucketed[bucket_time] += row.count
        
        return [{'timestamp': ts.isoformat(), 'count': count} for ts, count in sorted(bucketed.items())]
    elif interval_minutes == 720:
        # 12 hours: group by floor(hour / 12) * 12
        from collections import defaultdict
        bucketed = defaultdict(int)
        
        for row in results:
            dt = row.time_bucket
            bucket_hour = (dt.hour // 12) * 12
            bucket_time = dt.replace(hour=bucket_hour, minute=0, second=0, microsecond=0)
            bucketed[bucket_time] += row.count
        
        return [{'timestamp': ts.isoformat(), 'count': count} for ts, count in sorted(bucketed.items())]
    
    return [{'timestamp': row.time_bucket.isoformat(), 'count': row.count} for row in results]


def get_user_messages_over_time(db: Session, interval_minutes: int = 60, limit_hours: int = 24, start_date: Optional[str] = None, end_date: Optional[str] = None, acquisition_source: Optional[str] = None) -> List[dict]:
    """
    Get user-sent message counts over time bucketed by interval
    
    Args:
        start_date: Filter from this date onwards (YYYY-MM-DD)
        end_date: Filter up to this date (YYYY-MM-DD)
        acquisition_source: Filter by acquisition source
    
    Args:
        db: Database session
        interval_minutes: Time bucket size (1, 5, 15, 30, 60, 360, 720, 1440)
        limit_hours: How many hours of history to fetch - only used if start_date/end_date not provided
    
    Returns:
        List of {timestamp, count} dictionaries
    """
    from sqlalchemy import func
    from datetime import datetime, timedelta
    
    # Use PostgreSQL's date_trunc for time bucketing
    if interval_minutes == 1:
        trunc_spec = 'minute'
    elif interval_minutes < 60:
        trunc_spec = 'minute'
    elif interval_minutes == 60:
        trunc_spec = 'hour'
    elif interval_minutes == 360:
        trunc_spec = 'hour'
    elif interval_minutes == 720:
        trunc_spec = 'hour'
    else:  # 1440 (1 day)
        trunc_spec = 'day'
    
    query = db.query(
        func.date_trunc(trunc_spec, TgAnalyticsEvent.created_at).label('time_bucket'),
        func.count(TgAnalyticsEvent.id).label('count')
    ).filter(
        TgAnalyticsEvent.event_name == 'user_message'
    )
    
    # Apply date filters (default to limit_hours if not provided)
    if not start_date and not end_date:
        cutoff_time = datetime.utcnow() - timedelta(hours=limit_hours)
        query = query.filter(TgAnalyticsEvent.created_at >= cutoff_time)
    else:
        query = apply_date_filter(query, TgAnalyticsEvent.created_at, start_date, end_date)
    
    query = apply_acquisition_source_filter(db, query, acquisition_source)
    query = query.group_by('time_bucket').order_by('time_bucket')
    
    results = query.all()
    
    # Apply same bucketing logic as get_messages_over_time
    if interval_minutes in [5, 15, 30]:
        from collections import defaultdict
        bucketed = defaultdict(int)
        
        for row in results:
            dt = row.time_bucket
            total_minutes = dt.hour * 60 + dt.minute
            bucket_num = total_minutes // interval_minutes
            bucket_minutes = bucket_num * interval_minutes
            bucket_time = dt.replace(hour=bucket_minutes // 60, minute=bucket_minutes % 60, second=0, microsecond=0)
            bucketed[bucket_time] += row.count
        
        return [{'timestamp': ts.isoformat(), 'count': count} for ts, count in sorted(bucketed.items())]
    elif interval_minutes == 360:
        from collections import defaultdict
        bucketed = defaultdict(int)
        
        for row in results:
            dt = row.time_bucket
            bucket_hour = (dt.hour // 6) * 6
            bucket_time = dt.replace(hour=bucket_hour, minute=0, second=0, microsecond=0)
            bucketed[bucket_time] += row.count
        
        return [{'timestamp': ts.isoformat(), 'count': count} for ts, count in sorted(bucketed.items())]
    elif interval_minutes == 720:
        from collections import defaultdict
        bucketed = defaultdict(int)
        
        for row in results:
            dt = row.time_bucket
            bucket_hour = (dt.hour // 12) * 12
            bucket_time = dt.replace(hour=bucket_hour, minute=0, second=0, microsecond=0)
            bucketed[bucket_time] += row.count
        
        return [{'timestamp': ts.isoformat(), 'count': count} for ts, count in sorted(bucketed.items())]
    
    return [{'timestamp': row.time_bucket.isoformat(), 'count': row.count} for row in results]


def get_scheduled_messages_over_time(db: Session, interval_minutes: int = 60, limit_hours: int = 24, start_date: Optional[str] = None, end_date: Optional[str] = None, acquisition_source: Optional[str] = None) -> List[dict]:
    """
    Get auto-followup message counts over time bucketed by interval
    
    Args:
        start_date: Filter from this date onwards (YYYY-MM-DD)
        end_date: Filter up to this date (YYYY-MM-DD)
        acquisition_source: Filter by acquisition source
    
    Args:
        db: Database session
        interval_minutes: Time bucket size (1, 5, 15, 30, 60, 360, 720, 1440)
        limit_hours: How many hours of history to fetch - only used if start_date/end_date not provided
    
    Returns:
        List of {timestamp, count} dictionaries
    """
    from sqlalchemy import func
    from datetime import datetime, timedelta
    
    # Use PostgreSQL's date_trunc for time bucketing
    if interval_minutes == 1:
        trunc_spec = 'minute'
    elif interval_minutes < 60:
        trunc_spec = 'minute'
    elif interval_minutes == 60:
        trunc_spec = 'hour'
    elif interval_minutes == 360:
        trunc_spec = 'hour'
    elif interval_minutes == 720:
        trunc_spec = 'hour'
    else:  # 1440 (1 day)
        trunc_spec = 'day'
    
    query = db.query(
        func.date_trunc(trunc_spec, TgAnalyticsEvent.created_at).label('time_bucket'),
        func.count(TgAnalyticsEvent.id).label('count')
    ).filter(
        TgAnalyticsEvent.event_name == 'auto_followup_message'
    )
    
    # Apply date filters (default to limit_hours if not provided)
    if not start_date and not end_date:
        cutoff_time = datetime.utcnow() - timedelta(hours=limit_hours)
        query = query.filter(TgAnalyticsEvent.created_at >= cutoff_time)
    else:
        query = apply_date_filter(query, TgAnalyticsEvent.created_at, start_date, end_date)
    
    query = apply_acquisition_source_filter(db, query, acquisition_source)
    query = query.group_by('time_bucket').order_by('time_bucket')
    
    results = query.all()
    
    # Apply same bucketing logic as get_messages_over_time
    if interval_minutes in [5, 15, 30]:
        from collections import defaultdict
        bucketed = defaultdict(int)
        
        for row in results:
            dt = row.time_bucket
            total_minutes = dt.hour * 60 + dt.minute
            bucket_num = total_minutes // interval_minutes
            bucket_minutes = bucket_num * interval_minutes
            bucket_time = dt.replace(hour=bucket_minutes // 60, minute=bucket_minutes % 60, second=0, microsecond=0)
            bucketed[bucket_time] += row.count
        
        return [{'timestamp': ts.isoformat(), 'count': count} for ts, count in sorted(bucketed.items())]
    elif interval_minutes == 360:
        from collections import defaultdict
        bucketed = defaultdict(int)
        
        for row in results:
            dt = row.time_bucket
            bucket_hour = (dt.hour // 6) * 6
            bucket_time = dt.replace(hour=bucket_hour, minute=0, second=0, microsecond=0)
            bucketed[bucket_time] += row.count
        
        return [{'timestamp': ts.isoformat(), 'count': count} for ts, count in sorted(bucketed.items())]
    elif interval_minutes == 720:
        from collections import defaultdict
        bucketed = defaultdict(int)
        
        for row in results:
            dt = row.time_bucket
            bucket_hour = (dt.hour // 12) * 12
            bucket_time = dt.replace(hour=bucket_hour, minute=0, second=0, microsecond=0)
            bucketed[bucket_time] += row.count
        
        return [{'timestamp': ts.isoformat(), 'count': count} for ts, count in sorted(bucketed.items())]
    
    return [{'timestamp': row.time_bucket.isoformat(), 'count': row.count} for row in results]


def get_active_users_over_time(db: Session, days: int = 7, start_date: Optional[str] = None, end_date: Optional[str] = None, acquisition_source: Optional[str] = None) -> List[dict]:
    """
    Get daily unique active user counts
    
    Args:
        start_date: Filter from this date onwards (YYYY-MM-DD)
        end_date: Filter up to this date (YYYY-MM-DD)
        acquisition_source: Filter by acquisition source
    
    Args:
        db: Database session
        days: Number of days to fetch (7, 30, or 90) - only used if start_date/end_date not provided
    
    Returns:
        List of {date, count} dictionaries
    """
    from sqlalchemy import func, cast, Date, distinct
    from datetime import datetime, timedelta
    
    # Use provided dates or calculate from days parameter
    if start_date and end_date:
        start_date_calc = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date_calc = datetime.strptime(end_date, '%Y-%m-%d').date()
        days = (end_date_calc - start_date_calc).days + 1
    else:
        end_date_calc = datetime.utcnow().date()
        start_date_calc = end_date_calc - timedelta(days=days - 1)
    
    # Query unique users per day
    query = db.query(
        cast(TgAnalyticsEvent.created_at, Date).label('date'),
        func.count(distinct(TgAnalyticsEvent.client_id)).label('count')
    ).filter(
        cast(TgAnalyticsEvent.created_at, Date) >= start_date_calc,
        cast(TgAnalyticsEvent.created_at, Date) <= end_date_calc
    )
    
    query = apply_acquisition_source_filter(db, query, acquisition_source)
    results = query.group_by('date').order_by('date').all()
    
    # Create a dict for quick lookup
    counts_dict = {row.date: row.count for row in results}
    
    # Fill in missing days with 0
    result_list = []
    current_date = start_date_calc
    for _ in range(days):
        count = counts_dict.get(current_date, 0)
        result_list.append({
            'date': current_date.isoformat(),
            'count': count
        })
        current_date += timedelta(days=1)
    
    return result_list


def get_messages_by_persona(db: Session, start_date: Optional[str] = None, end_date: Optional[str] = None, acquisition_source: Optional[str] = None) -> List[dict]:
    """
    Get message count distribution by persona
    
    Args:
        start_date: Filter from this date onwards (YYYY-MM-DD)
        end_date: Filter up to this date (YYYY-MM-DD)
        acquisition_source: Filter by acquisition source
    
    Returns:
        List of {persona_name, count} dictionaries
    """
    from sqlalchemy import func
    
    query = db.query(
        TgAnalyticsEvent.persona_name,
        func.count(TgAnalyticsEvent.id).label('count')
    ).filter(
        TgAnalyticsEvent.event_name.in_(['user_message', 'ai_message']),
        TgAnalyticsEvent.persona_name.isnot(None)
    )
    
    query = apply_date_filter(query, TgAnalyticsEvent.created_at, start_date, end_date)
    query = apply_acquisition_source_filter(db, query, acquisition_source)
    results = query.group_by(
        TgAnalyticsEvent.persona_name
    ).order_by(desc('count')).all()
    
    return [{'persona_name': row.persona_name, 'count': row.count} for row in results]


def get_images_over_time(db: Session, days: int = 7, start_date: Optional[str] = None, end_date: Optional[str] = None, acquisition_source: Optional[str] = None) -> List[dict]:
    """
    Get daily image generation counts
    
    Args:
        start_date: Filter from this date onwards (YYYY-MM-DD)
        end_date: Filter up to this date (YYYY-MM-DD)
        acquisition_source: Filter by acquisition source
    
    Args:
        db: Database session
        days: Number of days to fetch (7, 30, or 90) - only used if start_date/end_date not provided
    
    Returns:
        List of {date, count} dictionaries
    """
    from sqlalchemy import func, cast, Date
    from datetime import datetime, timedelta
    
    # Use provided dates or calculate from days parameter
    if start_date and end_date:
        start_date_calc = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date_calc = datetime.strptime(end_date, '%Y-%m-%d').date()
        days = (end_date_calc - start_date_calc).days + 1
    else:
        end_date_calc = datetime.utcnow().date()
        start_date_calc = end_date_calc - timedelta(days=days - 1)
    
    # Query image generations per day
    query = db.query(
        cast(TgAnalyticsEvent.created_at, Date).label('date'),
        func.count(TgAnalyticsEvent.id).label('count')
    ).filter(
        TgAnalyticsEvent.event_name == 'image_generated',
        cast(TgAnalyticsEvent.created_at, Date) >= start_date_calc,
        cast(TgAnalyticsEvent.created_at, Date) <= end_date_calc
    )
    
    query = apply_acquisition_source_filter(db, query, acquisition_source)
    results = query.group_by('date').order_by('date').all()
    
    # Create a dict for quick lookup
    counts_dict = {row.date: row.count for row in results}
    
    # Fill in missing days with 0
    result_list = []
    current_date = start_date_calc
    for _ in range(days):
        count = counts_dict.get(current_date, 0)
        result_list.append({
            'date': current_date.isoformat(),
            'count': count
        })
        current_date += timedelta(days=1)
    
    return result_list


def get_engagement_heatmap(db: Session, start_date: Optional[str] = None, end_date: Optional[str] = None, acquisition_source: Optional[str] = None) -> List[dict]:
    """
    Get message counts by hour of day and day of week
    
    Args:
        start_date: Filter from this date onwards (YYYY-MM-DD)
        end_date: Filter up to this date (YYYY-MM-DD)
        acquisition_source: Filter by acquisition source
    
    Returns:
        List of {hour, day_of_week, count} dictionaries
        hour: 0-23
        day_of_week: 0-6 (0=Monday, 6=Sunday)
    """
    from sqlalchemy import func, extract
    from datetime import datetime, timedelta
    
    query = db.query(
        extract('hour', TgAnalyticsEvent.created_at).label('hour'),
        extract('dow', TgAnalyticsEvent.created_at).label('day_of_week'),
        func.count(TgAnalyticsEvent.id).label('count')
    ).filter(
        TgAnalyticsEvent.event_name.in_(['user_message', 'ai_message'])
    )
    
    # Apply date filters (default to last 30 days if not provided)
    if not start_date and not end_date:
        cutoff_time = datetime.utcnow() - timedelta(days=30)
        query = query.filter(TgAnalyticsEvent.created_at >= cutoff_time)
    else:
        query = apply_date_filter(query, TgAnalyticsEvent.created_at, start_date, end_date)
    
    query = apply_acquisition_source_filter(db, query, acquisition_source)
    results = query.group_by('hour', 'day_of_week').all()
    
    return [
        {
            'hour': int(row.hour),
            'day_of_week': int(row.day_of_week),
            'count': row.count
        } 
        for row in results
    ]


def get_avg_image_waiting_time(db: Session, start_date: Optional[str] = None, end_date: Optional[str] = None, acquisition_source: Optional[str] = None) -> float:
    """
    Get average image generation waiting time in seconds
    
    Args:
        start_date: Filter from this date onwards (YYYY-MM-DD)
        end_date: Filter up to this date (YYYY-MM-DD)
        acquisition_source: Filter by acquisition source
    
    Returns:
        Average waiting time in seconds (float), or 0.0 if no completed images
    """
    from sqlalchemy import func, extract
    
    query = db.query(
        func.avg(
            extract('epoch', ImageJob.finished_at - ImageJob.created_at)
        ).label('avg_seconds')
    ).filter(
        ImageJob.status == 'completed',
        ImageJob.finished_at.isnot(None)
    )
    
    if acquisition_source:
        query = query.join(User, ImageJob.user_id == User.id).filter(User.acquisition_source == acquisition_source)
    
    query = apply_date_filter(query, ImageJob.created_at, start_date, end_date)
    result = query.scalar()
    
    return float(result) if result else 0.0


def get_failed_images_count(db: Session, start_date: Optional[str] = None, end_date: Optional[str] = None, acquisition_source: Optional[str] = None) -> int:
    """
    Get count of failed image generation jobs
    
    Args:
        start_date: Filter from this date onwards (YYYY-MM-DD)
        end_date: Filter up to this date (YYYY-MM-DD)
        acquisition_source: Filter by acquisition source
    
    Returns:
        Count of failed images (int)
    """
    from sqlalchemy import func
    
    query = db.query(func.count(ImageJob.id)).filter(
        ImageJob.status == 'failed'
    )
    
    if acquisition_source:
        query = query.join(User, ImageJob.user_id == User.id).filter(User.acquisition_source == acquisition_source)
    
    query = apply_date_filter(query, ImageJob.created_at, start_date, end_date)
    result = query.scalar()
    
    return result or 0


def get_premium_stats(db: Session, start_date: Optional[str] = None, end_date: Optional[str] = None, acquisition_source: Optional[str] = None) -> dict:
    """
    Get premium user statistics and metrics
    
    Args:
        start_date: Filter from this date onwards (YYYY-MM-DD)
        end_date: Filter up to this date (YYYY-MM-DD)
        acquisition_source: Filter by acquisition source
    
    Returns:
        Dictionary with premium statistics
    """
    from sqlalchemy import func, distinct, case
    from datetime import timedelta
    
    # Currently active premium users
    active_premium_query = db.query(func.count(User.id)).filter(
        User.is_premium == True,
        (User.premium_until.is_(None)) | (User.premium_until > datetime.utcnow())
    )
    if acquisition_source:
        active_premium_query = active_premium_query.filter(User.acquisition_source == acquisition_source)
    total_premium_users = active_premium_query.scalar() or 0
    
    # Total users who EVER bought premium (including expired)
    ever_premium_query = db.query(func.count(User.id)).filter(
        User.is_premium == True
    )
    if acquisition_source:
        ever_premium_query = ever_premium_query.filter(User.acquisition_source == acquisition_source)
    total_ever_premium_users = ever_premium_query.scalar() or 0
    
    # Free users (never bought premium)
    free_query = db.query(func.count(User.id)).filter(
        User.is_premium == False
    )
    if acquisition_source:
        free_query = free_query.filter(User.acquisition_source == acquisition_source)
    total_free_users = free_query.scalar() or 0
    
    # Conversion rate (based on ever bought premium)
    total_users = total_ever_premium_users + total_free_users
    conversion_rate = (total_ever_premium_users / total_users * 100) if total_users > 0 else 0
    
    # Premium activations over time (ALL time, not just last 30 days)
    # This shows when users became premium (joined while premium or upgraded)
    premium_users_over_time_query = db.query(
        func.date_trunc('day', User.created_at).label('date'),
        func.count(User.id).label('count')
    ).filter(
        User.is_premium == True
    )
    if acquisition_source:
        premium_users_over_time_query = premium_users_over_time_query.filter(User.acquisition_source == acquisition_source)
    premium_users_over_time = premium_users_over_time_query.group_by(func.date_trunc('day', User.created_at)).order_by('date').all()
    
    premium_users_over_time_data = [
        {'date': row.date.isoformat() if row.date else None, 'count': row.count}
        for row in premium_users_over_time
    ]
    
    # Premium vs Free image generation (with date filter)
    image_query = db.query(
        User.is_premium,
        func.count(ImageJob.id).label('image_count')
    ).join(User, ImageJob.user_id == User.id).filter(
        ImageJob.status == 'completed'
    )
    if acquisition_source:
        image_query = image_query.filter(User.acquisition_source == acquisition_source)
    
    image_query = apply_date_filter(image_query, ImageJob.created_at, start_date, end_date)
    image_results = image_query.group_by(User.is_premium).all()
    
    premium_images = 0
    free_images = 0
    for row in image_results:
        if row.is_premium:
            premium_images = row.image_count
        else:
            free_images = row.image_count
    
    # Premium vs Free engagement (messages, with date filter)
    message_query = db.query(
        TgAnalyticsEvent.client_id,
        func.count(TgAnalyticsEvent.id).label('message_count')
    ).filter(
        TgAnalyticsEvent.event_name.in_(['user_message', 'ai_message'])
    )
    
    message_query = apply_date_filter(message_query, TgAnalyticsEvent.created_at, start_date, end_date)
    message_query = apply_acquisition_source_filter(db, message_query, acquisition_source)
    message_results = message_query.group_by(TgAnalyticsEvent.client_id).subquery()
    
    engagement_query = db.query(
        User.is_premium,
        func.count(message_results.c.client_id).label('user_count'),
        func.avg(message_results.c.message_count).label('avg_messages')
    ).join(message_results, User.id == message_results.c.client_id)
    if acquisition_source:
        engagement_query = engagement_query.filter(User.acquisition_source == acquisition_source)
    engagement_results = engagement_query.group_by(User.is_premium).all()
    
    premium_engagement = {'user_count': 0, 'avg_messages': 0}
    free_engagement = {'user_count': 0, 'avg_messages': 0}
    
    for row in engagement_results:
        data = {
            'user_count': row.user_count,
            'avg_messages': float(row.avg_messages) if row.avg_messages else 0
        }
        if row.is_premium:
            premium_engagement = data
        else:
            free_engagement = data
    
    return {
        'total_premium_users': total_premium_users,  # Currently active premium
        'total_ever_premium_users': total_ever_premium_users,  # Total who ever bought premium
        'total_free_users': total_free_users,
        'conversion_rate': round(conversion_rate, 2),
        'premium_users_over_time': premium_users_over_time_data,
        'premium_vs_free_images': {
            'premium': premium_images,
            'free': free_images
        },
        'premium_vs_free_engagement': {
            'premium': premium_engagement,
            'free': free_engagement
        }
    }


def get_image_waiting_time_over_time(db: Session, interval_minutes: int = 60, limit_hours: int = 24, start_date: Optional[str] = None, end_date: Optional[str] = None, acquisition_source: Optional[str] = None) -> List[dict]:
    """
    Get average image generation waiting time over time with premium/free breakdown
    
    Args:
        start_date: Filter from this date onwards (YYYY-MM-DD)
        end_date: Filter up to this date (YYYY-MM-DD)
        acquisition_source: Filter by acquisition source
    
    Args:
        db: Database session
        interval_minutes: Time bucket size (1, 5, 15, 30, 60, 360, 720, 1440)
        limit_hours: How many hours of history to fetch - only used if start_date/end_date not provided
    
    Returns:
        List of {timestamp, avg_waiting_time, avg_premium, avg_free} dictionaries
        All times in seconds
    """
    from sqlalchemy import func, extract, case
    from datetime import datetime, timedelta
    
    # Use PostgreSQL's date_trunc for time bucketing
    if interval_minutes == 1:
        trunc_spec = 'minute'
    elif interval_minutes < 60:
        trunc_spec = 'minute'
    elif interval_minutes == 60:
        trunc_spec = 'hour'
    elif interval_minutes == 360:
        trunc_spec = 'hour'
    elif interval_minutes == 720:
        trunc_spec = 'hour'
    else:  # 1440 (1 day)
        trunc_spec = 'day'
    
    # Query with join to User table for premium status
    query = db.query(
        func.date_trunc(trunc_spec, ImageJob.created_at).label('time_bucket'),
        func.avg(
            extract('epoch', ImageJob.finished_at - ImageJob.created_at)
        ).label('avg_waiting_time'),
        func.avg(
            case(
                (User.is_premium == True, extract('epoch', ImageJob.finished_at - ImageJob.created_at)),
                else_=None
            )
        ).label('avg_premium'),
        func.avg(
            case(
                (User.is_premium == False, extract('epoch', ImageJob.finished_at - ImageJob.created_at)),
                else_=None
            )
        ).label('avg_free')
    ).join(
        User, ImageJob.user_id == User.id
    ).filter(
        ImageJob.status == 'completed',
        ImageJob.finished_at.isnot(None)
    )
    
    # Apply date filters (default to limit_hours if not provided)
    if not start_date and not end_date:
        cutoff_time = datetime.utcnow() - timedelta(hours=limit_hours)
        query = query.filter(ImageJob.created_at >= cutoff_time)
    else:
        query = apply_date_filter(query, ImageJob.created_at, start_date, end_date)
    
    if acquisition_source:
        query = query.filter(User.acquisition_source == acquisition_source)
    
    query = query.group_by('time_bucket').order_by('time_bucket')
    
    results = query.all()
    
    # For intervals that don't align with date_trunc, we need to further group
    if interval_minutes in [5, 15, 30]:
        from collections import defaultdict
        
        # Group data by bucket
        bucketed = defaultdict(lambda: {'total': [], 'premium': [], 'free': []})
        
        for row in results:
            dt = row.time_bucket
            total_minutes = dt.hour * 60 + dt.minute
            bucket_num = total_minutes // interval_minutes
            bucket_minutes = bucket_num * interval_minutes
            bucket_time = dt.replace(hour=bucket_minutes // 60, minute=bucket_minutes % 60, second=0, microsecond=0)
            
            if row.avg_waiting_time:
                bucketed[bucket_time]['total'].append(row.avg_waiting_time)
            if row.avg_premium:
                bucketed[bucket_time]['premium'].append(row.avg_premium)
            if row.avg_free:
                bucketed[bucket_time]['free'].append(row.avg_free)
        
        # Calculate averages for each bucket
        result_list = []
        for ts in sorted(bucketed.keys()):
            data = bucketed[ts]
            result_list.append({
                'timestamp': ts.isoformat(),
                'avg_waiting_time': sum(data['total']) / len(data['total']) if data['total'] else None,
                'avg_premium': sum(data['premium']) / len(data['premium']) if data['premium'] else None,
                'avg_free': sum(data['free']) / len(data['free']) if data['free'] else None
            })
        
        return result_list
    elif interval_minutes == 360:
        from collections import defaultdict
        bucketed = defaultdict(lambda: {'total': [], 'premium': [], 'free': []})
        
        for row in results:
            dt = row.time_bucket
            bucket_hour = (dt.hour // 6) * 6
            bucket_time = dt.replace(hour=bucket_hour, minute=0, second=0, microsecond=0)
            
            if row.avg_waiting_time:
                bucketed[bucket_time]['total'].append(row.avg_waiting_time)
            if row.avg_premium:
                bucketed[bucket_time]['premium'].append(row.avg_premium)
            if row.avg_free:
                bucketed[bucket_time]['free'].append(row.avg_free)
        
        result_list = []
        for ts in sorted(bucketed.keys()):
            data = bucketed[ts]
            result_list.append({
                'timestamp': ts.isoformat(),
                'avg_waiting_time': sum(data['total']) / len(data['total']) if data['total'] else None,
                'avg_premium': sum(data['premium']) / len(data['premium']) if data['premium'] else None,
                'avg_free': sum(data['free']) / len(data['free']) if data['free'] else None
            })
        
        return result_list
    elif interval_minutes == 720:
        from collections import defaultdict
        bucketed = defaultdict(lambda: {'total': [], 'premium': [], 'free': []})
        
        for row in results:
            dt = row.time_bucket
            bucket_hour = (dt.hour // 12) * 12
            bucket_time = dt.replace(hour=bucket_hour, minute=0, second=0, microsecond=0)
            
            if row.avg_waiting_time:
                bucketed[bucket_time]['total'].append(row.avg_waiting_time)
            if row.avg_premium:
                bucketed[bucket_time]['premium'].append(row.avg_premium)
            if row.avg_free:
                bucketed[bucket_time]['free'].append(row.avg_free)
        
        result_list = []
        for ts in sorted(bucketed.keys()):
            data = bucketed[ts]
            result_list.append({
                'timestamp': ts.isoformat(),
                'avg_waiting_time': sum(data['total']) / len(data['total']) if data['total'] else None,
                'avg_premium': sum(data['premium']) / len(data['premium']) if data['premium'] else None,
                'avg_free': sum(data['free']) / len(data['free']) if data['free'] else None
            })
        
        return result_list
    
    # Return direct results for 1min, 1hour, and 1day intervals
    return [{
        'timestamp': row.time_bucket.isoformat(),
        'avg_waiting_time': float(row.avg_waiting_time) if row.avg_waiting_time else None,
        'avg_premium': float(row.avg_premium) if row.avg_premium else None,
        'avg_free': float(row.avg_free) if row.avg_free else None
    } for row in results]


def get_all_images_paginated(db: Session, page: int = 1, per_page: int = 100) -> dict:
    """
    Get all generated images with pagination
    
    Args:
        db: Database session
        page: Page number (1-indexed)
        per_page: Number of items per page
    
    Returns:
        Dictionary with:
        - images: List of image records with user, persona, and source info
        - total: Total number of images
        - page: Current page number
        - per_page: Items per page
        - total_pages: Total number of pages
    """
    from sqlalchemy import func
    
    # Query image_generated events with user and persona info
    offset = (page - 1) * per_page
    
    # Get total count
    total = db.query(func.count(TgAnalyticsEvent.id)).filter(
        TgAnalyticsEvent.event_name == 'image_generated'
    ).scalar() or 0
    
    # Get paginated images
    images_query = db.query(TgAnalyticsEvent).filter(
        TgAnalyticsEvent.event_name == 'image_generated'
    ).order_by(desc(TgAnalyticsEvent.created_at)).limit(per_page).offset(offset).all()
    
    # Build response with user info
    images_list = []
    for img_event in images_query:
        # Get user info
        user = db.query(User).filter(User.id == img_event.client_id).first()
        
        # Determine source from meta field
        source = 'message_response'  # default
        if img_event.meta and isinstance(img_event.meta, dict):
            if img_event.meta.get('source') == 'history_start':
                source = 'history_start'
            elif img_event.meta.get('is_auto_followup'):
                source = 'scheduler'
        
        images_list.append({
            'id': str(img_event.id),
            'created_at': img_event.created_at.isoformat(),
            'image_url': img_event.image_url,
            'prompt': img_event.prompt,
            'negative_prompt': img_event.negative_prompt,
            'source': source,
            'user_id': img_event.client_id,
            'username': user.username if user else None,
            'first_name': user.first_name if user else None,
            'persona_id': str(img_event.persona_id) if img_event.persona_id else None,
            'persona_name': img_event.persona_name,
            'meta': img_event.meta
        })
    
    return {
        'images': images_list,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page  # Ceiling division
    }


# ========== START CODE OPERATIONS ==========

def get_start_code(db: Session, code: str) -> Optional[StartCode]:
    """Get start code by code
    
    Args:
        db: Database session
        code: 5-character alphanumeric code
    
    Returns:
        StartCode object or None if not found
    """
    return db.query(StartCode).filter(StartCode.code == code.upper()).first()


def get_all_start_codes(db: Session) -> List[StartCode]:
    """Get all start codes
    
    Args:
        db: Database session
    
    Returns:
        List of StartCode objects ordered by created_at desc
    """
    return db.query(StartCode).order_by(desc(StartCode.created_at)).all()


def create_start_code(
    db: Session,
    code: str,
    description: str = None,
    persona_id: str = None,
    history_id: str = None,
    is_active: bool = True
) -> StartCode:
    """Create new start code
    
    Args:
        db: Database session
        code: 5-character alphanumeric code
        description: Info text about this code
        persona_id: Optional persona UUID
        history_id: Optional history UUID
        is_active: Whether code is active
    
    Returns:
        Created StartCode object
    """
    # Convert code to uppercase for consistency
    code = code.upper()
    
    start_code = StartCode(
        code=code,
        description=description,
        persona_id=UUID(persona_id) if persona_id else None,
        history_id=UUID(history_id) if history_id else None,
        is_active=is_active
    )
    db.add(start_code)
    db.commit()
    db.refresh(start_code)
    return start_code


def update_start_code(
    db: Session,
    code: str,
    description: str = None,
    persona_id: str = None,
    history_id: str = None,
    is_active: bool = None
) -> Optional[StartCode]:
    """Update start code
    
    Args:
        db: Database session
        code: 5-character alphanumeric code
        description: Info text about this code
        persona_id: Optional persona UUID (None to clear)
        history_id: Optional history UUID (None to clear)
        is_active: Whether code is active
    
    Returns:
        Updated StartCode object or None if not found
    """
    start_code = get_start_code(db, code)
    if not start_code:
        return None
    
    if description is not None:
        start_code.description = description
    if persona_id is not None:
        start_code.persona_id = UUID(persona_id) if persona_id else None
    if history_id is not None:
        start_code.history_id = UUID(history_id) if history_id else None
    if is_active is not None:
        start_code.is_active = is_active
    
    start_code.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(start_code)
    return start_code


def delete_start_code(db: Session, code: str) -> bool:
    """Delete start code
    
    Args:
        db: Database session
        code: 5-character alphanumeric code
    
    Returns:
        True if deleted, False if not found
    """
    start_code = get_start_code(db, code)
    if not start_code:
        return False
    
    db.delete(start_code)
    db.commit()
    return True




"""
CRUD operations for database models
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.db.models import (
    User, Persona, Chat, Message, ImageJob, TgAnalyticsEvent, StartCode,
    PersonaTranslation, PersonaHistoryTranslation, SystemMessage, SystemMessageTemplate, SystemMessageDelivery
)
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

def get_or_create_user(
    db: Session, 
    telegram_id: int, 
    username: str = None, 
    first_name: str = None, 
    acquisition_source: str = None,
    language_code: str = None
) -> User:
    """Get existing user or create new one
    
    Args:
        telegram_id: Telegram user ID
        username: User's username
        first_name: User's first name
        acquisition_source: Deep-link payload for ads attribution (only set on first visit)
        language_code: Telegram user language code (e.g., 'en', 'ru', 'fr')
    
    Returns:
        User object
    """
    # Normalize and validate language code
    supported_languages = ['en', 'ru']
    normalized_locale = None
    if language_code:
        # Extract base language code (e.g., 'en-US' -> 'en')
        base_lang = language_code.lower().split('-')[0]
        normalized_locale = base_lang if base_lang in supported_languages else 'en'
    
    user = db.query(User).filter(User.id == telegram_id).first()
    if not user:
        # New user - set acquisition source and locale if provided
        user = User(
            id=telegram_id,
            username=username,
            first_name=first_name,
            locale=normalized_locale or 'en',
            locale_manually_set=False,  # Default to Telegram language
            acquisition_source=acquisition_source if acquisition_source else None,
            acquisition_timestamp=datetime.utcnow() if acquisition_source else None,
            settings={"voice_buttons_hidden": True}  # Voice disabled by default for new users
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # Existing user - only update locale from Telegram if NOT manually set
        if normalized_locale and user.locale != normalized_locale and not user.locale_manually_set:
            user.locale = normalized_locale
            db.commit()
            db.refresh(user)
        
        # Only set acquisition source if not already set (first-touch attribution)
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


def set_user_locale(db: Session, telegram_id: int, locale: str) -> User:
    """Set user's locale preference manually
    
    Args:
        telegram_id: Telegram user ID
        locale: Language code (e.g., 'en', 'ru')
    
    Returns:
        Updated User object
    """
    user = db.query(User).filter(User.id == telegram_id).first()
    if user:
        user.locale = locale
        user.locale_manually_set = True
        db.commit()
        db.refresh(user)
    return user


def mark_user_bot_blocked(db: Session, telegram_id: int) -> Optional[User]:
    """Mark user as having blocked the bot
    
    Args:
        telegram_id: Telegram user ID
    
    Returns:
        Updated User object or None if not found
    """
    user = db.query(User).filter(User.id == telegram_id).first()
    if user:
        user.bot_blocked = True
        user.bot_blocked_at = datetime.utcnow()
        db.commit()
        db.refresh(user)
    return user


def save_pending_deep_link(db: Session, telegram_id: int, deep_link: str):
    """Save deep link to user settings to execute after age verification
    
    Args:
        telegram_id: Telegram user ID
        deep_link: The deep link parameter
    """
    user = db.query(User).filter(User.id == telegram_id).first()
    if user:
        if user.settings is None:
            user.settings = {}
        
        # Create a copy of settings to ensure SQLAlchemy detects the change
        settings = dict(user.settings)
        settings["pending_deep_link"] = deep_link
        user.settings = settings
        
        db.commit()


def get_and_clear_pending_deep_link(db: Session, telegram_id: int) -> Optional[str]:
    """Get and clear pending deep link from user settings
    
    Args:
        telegram_id: Telegram user ID
        
    Returns:
        Pending deep link or None
    """
    user = db.query(User).filter(User.id == telegram_id).first()
    if user and user.settings and "pending_deep_link" in user.settings:
        settings = dict(user.settings)
        deep_link = settings.pop("pending_deep_link")
        user.settings = settings
        db.commit()
        return deep_link
    
    return None


def get_user_language(db: Session, telegram_id: int) -> str:
    """Get user's language preference
    
    Args:
        telegram_id: Telegram user ID
    
    Returns:
        Language code (e.g., 'en', 'ru', 'fr', 'de', 'es'), defaults to 'en'
    """
    user = db.query(User).filter(User.id == telegram_id).first()
    if user and user.locale:
        return user.locale
    return 'en'


# ========== PERSONA OPERATIONS ==========

def get_persona_by_key(db: Session, key: str) -> Optional[Persona]:
    """Get preset persona by key"""
    return db.query(Persona).filter(Persona.key == key).first()


def get_persona_by_id(db: Session, persona_id: UUID) -> Optional[Persona]:
    """Get persona by ID"""
    return db.query(Persona).filter(Persona.id == persona_id).first()


def get_preset_personas(db: Session, main_menu_only: bool = False) -> List[Persona]:
    """Get all public personas, optionally filtered by main_menu
    
    Args:
        db: Database session
        main_menu_only: If True, only return personas with main_menu=True
    
    Returns:
        List of personas ordered by 'order' field ascending
    """
    query = db.query(Persona).filter(Persona.visibility == 'public')
    
    if main_menu_only:
        query = query.filter(Persona.main_menu == True)
    
    # Order by 'order' field (lower numbers appear first), with NULL values last
    return query.order_by(Persona.order.asc().nullslast()).all()


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
    key: str = None,
    order: int = 999,
    main_menu: bool = True
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
        key=key,
        order=order,
        main_menu=main_menu
    )
    db.add(persona)
    db.commit()
    db.refresh(persona)
    return persona


# ========== PERSONA TRANSLATION OPERATIONS ==========

def get_persona_translations(db: Session, persona_id: UUID, language: str = None) -> Dict[str, PersonaTranslation]:
    """Get translations for a persona
    
    Args:
        persona_id: Persona UUID
        language: Optional language filter (e.g., 'ru', 'fr')
    
    Returns:
        Dictionary mapping language codes to translation objects
    """
    query = db.query(PersonaTranslation).filter(PersonaTranslation.persona_id == persona_id)
    
    if language:
        query = query.filter(PersonaTranslation.language == language)
    
    translations = query.all()
    return {t.language: t for t in translations}


def get_persona_history_translations(db: Session, history_id: UUID, language: str = None) -> Dict[str, PersonaHistoryTranslation]:
    """Get translations for a persona history start
    
    Args:
        history_id: PersonaHistoryStart UUID
        language: Optional language filter (e.g., 'ru', 'fr')
    
    Returns:
        Dictionary mapping language codes to translation objects
    """
    query = db.query(PersonaHistoryTranslation).filter(PersonaHistoryTranslation.history_id == history_id)
    
    if language:
        query = query.filter(PersonaHistoryTranslation.language == language)
    
    translations = query.all()
    return {t.language: t for t in translations}


def create_or_update_persona_translation(
    db: Session,
    persona_id: UUID,
    language: str,
    description: str = None,
    small_description: str = None,
    intro: str = None
) -> PersonaTranslation:
    """Create or update a persona translation"""
    translation = db.query(PersonaTranslation).filter(
        PersonaTranslation.persona_id == persona_id,
        PersonaTranslation.language == language
    ).first()
    
    if translation:
        # Update existing
        if description is not None:
            translation.description = description
        if small_description is not None:
            translation.small_description = small_description
        if intro is not None:
            translation.intro = intro
        translation.updated_at = datetime.utcnow()
    else:
        # Create new
        translation = PersonaTranslation(
            persona_id=persona_id,
            language=language,
            description=description,
            small_description=small_description,
            intro=intro
        )
        db.add(translation)
    
    db.commit()
    db.refresh(translation)
    return translation


def create_or_update_persona_history_translation(
    db: Session,
    history_id: UUID,
    language: str,
    name: str = None,
    small_description: str = None,
    description: str = None,
    text: str = None
) -> PersonaHistoryTranslation:
    """Create or update a persona history translation"""
    translation = db.query(PersonaHistoryTranslation).filter(
        PersonaHistoryTranslation.history_id == history_id,
        PersonaHistoryTranslation.language == language
    ).first()
    
    if translation:
        # Update existing
        if name is not None:
            translation.name = name
        if small_description is not None:
            translation.small_description = small_description
        if description is not None:
            translation.description = description
        if text is not None:
            translation.text = text
        translation.updated_at = datetime.utcnow()
    else:
        # Create new
        translation = PersonaHistoryTranslation(
            history_id=history_id,
            language=language,
            name=name,
            small_description=small_description,
            description=description,
            text=text
        )
        db.add(translation)
    
    db.commit()
    db.refresh(translation)
    return translation
  
def get_all_personas(db: Session) -> List[Persona]:
    """Get all personas (public and private) for admin management"""
    return db.query(Persona).order_by(Persona.created_at.desc()).all()


def update_persona(
    db: Session,
    persona_id: UUID,
    name: str = None,
    key: str = None,
    prompt: str = None,
    image_prompt: str = None,
    badges: list = None,
    visibility: str = None,
    description: str = None,
    small_description: str = None,
    emoji: str = None,
    intro: str = None,
    avatar_url: str = None,
    order: int = None,
    main_menu: bool = None,
    voice_id: str = None
) -> Optional[Persona]:
    """Update an existing persona"""
    persona = db.query(Persona).filter(Persona.id == persona_id).first()
    if not persona:
        return None
    
    if name is not None:
        persona.name = name
    if key is not None:
        persona.key = key
    if prompt is not None:
        persona.prompt = prompt
    if image_prompt is not None:
        persona.image_prompt = image_prompt
    if badges is not None:
        persona.badges = badges
    if visibility is not None:
        persona.visibility = visibility
    if description is not None:
        persona.description = description
    if small_description is not None:
        persona.small_description = small_description
    if emoji is not None:
        persona.emoji = emoji
    if intro is not None:
        persona.intro = intro
    if avatar_url is not None:
        persona.avatar_url = avatar_url
    if order is not None:
        persona.order = order
    if main_menu is not None:
        persona.main_menu = main_menu
    if voice_id is not None:
        persona.voice_id = voice_id
    
    db.commit()
    db.refresh(persona)
    return persona


def delete_persona(db: Session, persona_id: UUID) -> bool:
    """Delete a persona by ID (with cascade deletion of related records)"""
    persona = db.query(Persona).filter(Persona.id == persona_id).first()
    if not persona:
        return False
    
    # Delete in correct order to avoid foreign key constraints:
    # 1. Image jobs (references persona and chat)
    # 2. History starts (references persona)
    # 3. Chats (references persona)
    # 4. Persona
    
    from app.db.models import ImageJob, Chat, PersonaHistoryStart
    
    # Delete all image jobs for this persona
    db.query(ImageJob).filter(ImageJob.persona_id == persona_id).delete(synchronize_session='fetch')
    
    # Delete all history starts for this persona
    db.query(PersonaHistoryStart).filter(PersonaHistoryStart.persona_id == persona_id).delete(synchronize_session='fetch')
    
    # Delete all chats for this persona (cascade will delete messages)
    db.query(Chat).filter(Chat.persona_id == persona_id).delete(synchronize_session='fetch')
    
    # Now safe to delete the persona
    db.delete(persona)
    db.commit()
    return True


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


def get_user_chat_with_persona(db: Session, user_id: int, persona_id: UUID) -> Optional[Chat]:
    """Get most recent chat for a user with a specific persona (any tg_chat_id)"""
    return db.query(Chat).filter(
        Chat.user_id == user_id,
        Chat.persona_id == persona_id
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


def get_message_by_id(db: Session, message_id: UUID) -> Message | None:
    """Get a message by its ID"""
    return db.query(Message).filter(Message.id == message_id).first()


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
    from sqlalchemy import or_, and_, cast, Integer, func
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
        ),
        # EXCLUDE if auto_message_count >= 1 (prevent infinite loop if timestamp check fails)
        # Use COALESCE to handle NULL ext or missing key - treat as 0
        func.coalesce(
            Chat.ext['auto_message_count'].astext.cast(Integer),
            0
        ) == 0
    )
    
    # Filter by test users if whitelist is provided
    if test_user_ids is not None:
        query = query.filter(Chat.user_id.in_(test_user_ids))
    
    return query.all()


def get_inactive_chats_for_reengagement(db: Session, minutes: int = 1440, test_user_ids: Optional[List[int]] = None, required_count: Optional[int] = None) -> List[Chat]:
    """Get chats inactive for long periods (24h+) that need a single re-engagement message
    
    This allows sending ONE follow-up 24h after we already sent a 30min auto-message
    and the user still hasn't responded. We only re-engage if:
    - We already sent a 30min auto-message (last_auto_message_at is set)
    - It's been at least N minutes (typically 24h) since that auto-message
    - The assistant spoke last (user hasn't replied since the auto-message)
    - The chat is active (not archived)
    - The auto_message_count matches required_count (if specified)
    
    Sends only ONE 24h message. Stops until user replies, which resets the cycle.
    
    Args:
        db: Database session
        minutes: Number of minutes of inactivity required (default: 1440 = 24 hours)
        test_user_ids: Optional list of user IDs to restrict results to (for testing)
        required_count: Optional required auto_message_count (1 for 24h check, 2 for 3day check)
    """
    from datetime import timedelta
    from sqlalchemy import or_, cast, Integer, func
    threshold = datetime.utcnow() - timedelta(minutes=minutes)
    
    filters = [
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
    ]
    
    # Filter by auto_message_count if required
    # Use COALESCE to handle NULL ext or missing key - treat as 0
    # Flow: 3min (count=1) → 30min (count=2) → 24h (count=3) → 3day (count=4)
    if required_count is not None:
        if required_count == 1:
            # For 30min check: accept exactly count=1 (3min was sent)
            filters.append(
                func.coalesce(Chat.ext['auto_message_count'].astext.cast(Integer), 0) == 1
            )
        elif required_count == 2:
            # For 24h check: accept count=2 (new 30min) OR count=1 (legacy 30min)
            filters.append(
                or_(
                    func.coalesce(Chat.ext['auto_message_count'].astext.cast(Integer), 0) == 2,
                    func.coalesce(Chat.ext['auto_message_count'].astext.cast(Integer), 0) == 1
                )
            )
        elif required_count == 3:
            # For 3day check: accept count=3 (new 24h) OR count=2 (legacy 24h)
            filters.append(
                or_(
                    func.coalesce(Chat.ext['auto_message_count'].astext.cast(Integer), 0) == 3,
                    func.coalesce(Chat.ext['auto_message_count'].astext.cast(Integer), 0) == 2
                )
            )
        else:
            # For any other count, require exact match
            filters.append(
                func.coalesce(Chat.ext['auto_message_count'].astext.cast(Integer), 0) == required_count
            )
            
    query = db.query(Chat).filter(*filters)
    
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


def create_persona_history(
    db: Session,
    persona_id: UUID,
    text: str,
    name: str = None,
    small_description: str = None,
    description: str = None,
    image_url: str = None,
    wide_menu_image_url: str = None,
    image_prompt: str = None
):
    """Create a new persona history start"""
    from app.db.models import PersonaHistoryStart
    
    history = PersonaHistoryStart(
        persona_id=persona_id,
        text=text,
        name=name,
        small_description=small_description,
        description=description,
        image_url=image_url,
        wide_menu_image_url=wide_menu_image_url,
        image_prompt=image_prompt
    )
    db.add(history)
    db.commit()
    db.refresh(history)
    return history


def update_persona_history(
    db: Session,
    history_id: UUID,
    text: str = None,
    name: str = None,
    small_description: str = None,
    description: str = None,
    image_url: str = None,
    wide_menu_image_url: str = None,
    image_prompt: str = None
):
    """Update an existing persona history start"""
    from app.db.models import PersonaHistoryStart
    
    history = db.query(PersonaHistoryStart).filter(PersonaHistoryStart.id == history_id).first()
    if not history:
        return None
    
    if text is not None:
        history.text = text
    if name is not None:
        history.name = name
    if small_description is not None:
        history.small_description = small_description
    if description is not None:
        history.description = description
    if image_url is not None:
        history.image_url = image_url
    if wide_menu_image_url is not None:
        history.wide_menu_image_url = wide_menu_image_url
    if image_prompt is not None:
        history.image_prompt = image_prompt
    
    db.commit()
    db.refresh(history)
    return history


def delete_persona_history(db: Session, history_id: UUID) -> bool:
    """Delete a persona history start by ID"""
    from app.db.models import PersonaHistoryStart
    
    history = db.query(PersonaHistoryStart).filter(PersonaHistoryStart.id == history_id).first()
    if not history:
        return False
    
    db.delete(history)
    db.commit()
    return True


# ========== USER ENERGY OPERATIONS ==========

def get_user_energy(db: Session, user_id: int) -> dict:
    """Get user's current token balance (combined temp_energy + regular energy)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"tokens": 0, "premium_tier": "free"}
    total_tokens = (user.temp_energy or 0) + user.energy
    return {"tokens": total_tokens, "premium_tier": user.premium_tier}


def deduct_user_energy(db: Session, user_id: int, amount: int = 5) -> bool:
    """
    Deduct tokens from user (all users including premium tiers consume tokens)
    Deducts from temp_energy first, then regular energy
    Returns True if successful, False if insufficient tokens
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False
    
    # Check if user has enough total energy
    total_energy = (user.temp_energy or 0) + user.energy
    if total_energy < amount:
        return False
    
    # Deduct from temp_energy first
    if user.temp_energy >= amount:
        # Sufficient temp energy to cover the cost
        user.temp_energy -= amount
    else:
        # Use all temp energy and deduct the rest from regular energy
        remaining = amount - user.temp_energy
        user.temp_energy = 0
        user.energy -= remaining
    
    db.commit()
    return True


def add_user_energy(db: Session, user_id: int, amount: int) -> bool:
    """
    Add tokens to user (no cap - tokens are purchased)
    Returns True if successful
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False
    
    # Simply add tokens - no max_energy cap for purchased tokens
    user.energy += amount
    db.commit()
    return True


def check_user_energy(db: Session, user_id: int, required: int = 5) -> bool:
    """Check if user has enough energy (checks temp_energy + regular energy combined)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False
    total_energy = (user.temp_energy or 0) + user.energy
    return total_energy >= required


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

def check_user_premium(db: Session, user_id: int) -> dict:
    """
    Check if user has active premium subscription and return tier information
    Returns: {"is_premium": bool, "tier": str}
    """
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"is_premium": False, "tier": "free"}
    
    # Check if premium and not expired
    if user.is_premium:
        if user.premium_until is None or user.premium_until > datetime.utcnow():
            # Active subscription - ensure tier is set
            if user.premium_tier == "free":
                user.premium_tier = "premium"  # Default tier
                db.commit()
            return {"is_premium": True, "tier": user.premium_tier}
        else:
            # Expired - downgrade to free
            user.is_premium = False
            user.premium_tier = "free"
            db.commit()
            return {"is_premium": False, "tier": "free"}
    
    return {"is_premium": False, "tier": user.premium_tier}


def activate_premium(db: Session, user_id: int, duration_days: int, tier: str = "premium") -> bool:
    """
    Activate premium subscription for user with specific tier
    duration_days: number of days to add to subscription
    tier: premium tier (always "premium" in unified subscription system)
    Returns True if successful
    
    NOTE: In unified subscription system, premium users get unlimited energy.
    No bonus tokens are granted - premium status itself removes energy costs.
    """
    from datetime import timedelta
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False
    
    # Set premium status and tier
    user.is_premium = True
    user.premium_tier = tier
    
    # Calculate expiry date
    if user.premium_until and user.premium_until > datetime.utcnow():
        # Extend existing subscription (time stacks)
        user.premium_until = user.premium_until + timedelta(days=duration_days)
    else:
        # New subscription
        user.premium_until = datetime.utcnow() + timedelta(days=duration_days)
    
    # NO bonus tokens granted - premium users don't need tokens
    # Premium = unlimited energy for messages, photos, blur removal
    
    db.commit()
    return True


def add_daily_tokens_by_tier(db: Session) -> int:
    """
    Reset temporary daily energy for premium tier users based on their subscription level
    Runs every day via scheduler
    Returns count of users who received their daily refill
    """
    from datetime import timedelta
    
    # Tier temporary daily energy amounts
    TIER_DAILY_TEMP_ENERGY = {
        "plus": 50,
        "premium": 75,
        "pro": 100,
        "legendary": 150
    }
    
    # Get all premium tier users whose subscription hasn't expired
    users = db.query(User).filter(
        User.premium_tier.in_(["plus", "premium", "pro", "legendary"]),
        (User.premium_until.is_(None)) | (User.premium_until > datetime.utcnow())
    ).all()
    
    count = 0
    now = datetime.utcnow()
    
    for user in users:
        # Check if 24 hours have passed since last refill
        if user.last_temp_energy_refill:
            time_since_last = now - user.last_temp_energy_refill
            if time_since_last < timedelta(hours=24):
                continue  # Skip if less than 24 hours
        
        # Reset temp_energy to tier amount (doesn't accumulate)
        temp_energy_amount = TIER_DAILY_TEMP_ENERGY.get(user.premium_tier, 0)
        if temp_energy_amount > 0:
            user.temp_energy = temp_energy_amount  # Reset, not add
            user.last_temp_energy_refill = now
            count += 1
    
    db.commit()
    return count


# ========== DAILY BONUS OPERATIONS ==========

def can_claim_daily_bonus(db: Session, user_id: int) -> dict:
    """
    Check if user can claim daily bonus
    Returns: {can_claim: bool, next_claim_seconds: int}
    """
    from datetime import timedelta
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"can_claim": False, "next_claim_seconds": 0}
    
    # If never claimed, can claim now
    if not user.last_daily_bonus_claim:
        return {"can_claim": True, "next_claim_seconds": 0}
    
    # Check if 24 hours have passed
    now = datetime.utcnow()
    time_since_last = now - user.last_daily_bonus_claim
    
    if time_since_last >= timedelta(hours=24):
        return {"can_claim": True, "next_claim_seconds": 0}
    else:
        # Calculate seconds until next claim
        time_until_next = timedelta(hours=24) - time_since_last
        seconds_until_next = int(time_until_next.total_seconds())
        # Cap at 23h 59m (86340 seconds) to avoid showing 24h 0m
        # This ensures we never display 24h 0m, max is 23h 59m
        if seconds_until_next > 86340:  # 23 hours 59 minutes
            seconds_until_next = 86340
        return {"can_claim": False, "next_claim_seconds": seconds_until_next}


def claim_daily_bonus(db: Session, user_id: int) -> dict:
    """
    Claim daily bonus (10 tokens)
    Returns: {success: bool, tokens: int, message: str, streak: int}
    """
    from datetime import timedelta
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"success": False, "tokens": 0, "message": "User not found", "streak": 0}
    
    # Check if can claim
    if user.last_daily_bonus_claim:
        time_since_last = datetime.utcnow() - user.last_daily_bonus_claim
        if time_since_last < timedelta(hours=24):
            time_until_next = timedelta(hours=24) - time_since_last
            hours = int(time_until_next.total_seconds() // 3600)
            minutes = int((time_until_next.total_seconds() % 3600) // 60)
            return {
                "success": False,
                "tokens": user.energy,
                "message": f"Already claimed today. Next bonus in {hours}h {minutes}m",
                "streak": user.daily_bonus_streak or 0
            }
        
        # Check if streak should be reset (more than 48 hours)
        if time_since_last > timedelta(hours=48):
            user.daily_bonus_streak = 0
    
    # Award 10 tokens and increment streak
    user.energy += 10
    user.last_daily_bonus_claim = datetime.utcnow()
    user.daily_bonus_streak = (user.daily_bonus_streak or 0) + 1
    db.commit()
    db.refresh(user)
    
    return {
        "success": True,
        "tokens": user.energy,
        "message": f"Claimed 10 tokens! Day {user.daily_bonus_streak} streak!",
        "streak": user.daily_bonus_streak
    }


# ========== REFERRAL OPERATIONS ==========

def track_referral(db: Session, referrer_id: int, new_user_id: int) -> bool:
    """
    Track that a new user was referred by an existing user
    Returns True if successfully tracked
    """
    new_user = db.query(User).filter(User.id == new_user_id).first()
    if not new_user:
        return False
    
    # Only set referrer if not already set
    if not new_user.referred_by_user_id:
        new_user.referred_by_user_id = referrer_id
        db.commit()
        return True
    
    return False


def award_referral_tokens(db: Session, referrer_id: int, new_user_id: int) -> bool:
    """
    Award 50 tokens to referrer when their referred user completes onboarding
    Returns True if tokens were awarded
    """
    # Check that new user was referred by this referrer
    new_user = db.query(User).filter(User.id == new_user_id).first()
    if not new_user or new_user.referred_by_user_id != referrer_id:
        return False
    
    # Check if tokens already awarded
    if new_user.referral_tokens_awarded:
        return False
    
    # Award tokens to referrer
    referrer = db.query(User).filter(User.id == referrer_id).first()
    if not referrer:
        return False
    
    referrer.energy += 50
    new_user.referral_tokens_awarded = True
    
    db.commit()
    return True


# ========== PAYMENT TRANSACTION OPERATIONS ==========

def create_payment_transaction(
    db: Session,
    user_id: int,
    transaction_type: str,
    product_id: str,
    amount_stars: int,
    tokens_received: int = None,
    tier_granted: str = None,
    subscription_days: int = None,
    telegram_payment_charge_id: str = None,
    status: str = "completed"
) -> 'PaymentTransaction':
    """
    Create a payment transaction record
    """
    from app.db.models import PaymentTransaction
    
    transaction = PaymentTransaction(
        user_id=user_id,
        transaction_type=transaction_type,
        product_id=product_id,
        amount_stars=amount_stars,
        tokens_received=tokens_received,
        tier_granted=tier_granted,
        subscription_days=subscription_days,
        telegram_payment_charge_id=telegram_payment_charge_id,
        status=status
    )
    
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    
    return transaction


def get_user_transactions(db: Session, user_id: int, limit: int = 50) -> list:
    """
    Get user's payment transaction history
    """
    from app.db.models import PaymentTransaction
    
    transactions = db.query(PaymentTransaction).filter(
        PaymentTransaction.user_id == user_id
    ).order_by(PaymentTransaction.created_at.desc()).limit(limit).all()
    
    return transactions


def get_user_purchase_count(db: Session, user_id: int) -> int:
    """
    Get the total number of completed purchases for a user
    """
    from app.db.models import PaymentTransaction
    
    count = db.query(PaymentTransaction).filter(
        PaymentTransaction.user_id == user_id,
        PaymentTransaction.status == 'completed'
    ).count()
    
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
    
    # Total voice generations
    total_voices = db.query(func.count(TgAnalyticsEvent.id)).filter(
        TgAnalyticsEvent.event_name == 'voice_generated'
    )
    total_voices = apply_date_filter(total_voices, TgAnalyticsEvent.created_at, start_date, end_date)
    total_voices = apply_acquisition_source_filter(db, total_voices, acquisition_source)
    total_voices = total_voices.scalar()
    
    # Total voice characters used (ElevenLabs billing)
    from sqlalchemy import cast, Integer
    from sqlalchemy.dialects.postgresql import JSONB
    total_voice_characters_query = db.query(
        func.coalesce(
            func.sum(
                cast(TgAnalyticsEvent.meta['characters_used'].astext, Integer)
            ), 0
        )
    ).filter(
        TgAnalyticsEvent.event_name == 'voice_generated',
        TgAnalyticsEvent.meta['characters_used'].isnot(None)
    )
    total_voice_characters_query = apply_date_filter(total_voice_characters_query, TgAnalyticsEvent.created_at, start_date, end_date)
    total_voice_characters_query = apply_acquisition_source_filter(db, total_voice_characters_query, acquisition_source)
    total_voice_characters = total_voice_characters_query.scalar() or 0
    
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
        'total_voices': total_voices or 0,
        'total_voice_characters': total_voice_characters,
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
    from app.db.models import PaymentTransaction
    
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
    
    # Get purchase stats by acquisition source
    purchase_stats_query = db.query(
        func.coalesce(User.acquisition_source, 'direct').label('source'),
        func.count(PaymentTransaction.id).label('purchase_count'),
        func.coalesce(func.sum(PaymentTransaction.amount_stars), 0).label('total_stars')
    ).join(
        PaymentTransaction, User.id == PaymentTransaction.user_id
    ).filter(
        PaymentTransaction.status == 'completed'
    )
    # Apply date filter to purchases
    if start_date or end_date:
        purchase_stats_query = apply_date_filter(purchase_stats_query, PaymentTransaction.created_at, start_date, end_date)
    purchase_stats_query = purchase_stats_query.group_by(
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
            'total_purchases': 0,
            'total_stars': 0,
            'sparkline_data': []
        }
    
    # Then add event counts
    event_counts_dict = {row.source: row.total_events for row in event_counts_query}
    for source in source_stats.keys():
        total_events = event_counts_dict.get(source, 0)
        source_stats[source]['total_events'] = total_events
        source_stats[source]['avg_events_per_user'] = round(total_events / source_stats[source]['user_count'], 2) if source_stats[source]['user_count'] > 0 else 0
    
    # Add purchase stats
    purchase_stats_dict = {row.source: {'count': row.purchase_count, 'stars': int(row.total_stars)} for row in purchase_stats_query}
    for source in source_stats.keys():
        purchase_data = purchase_stats_dict.get(source, {'count': 0, 'stars': 0})
        source_stats[source]['total_purchases'] = purchase_data['count']
        source_stats[source]['total_stars'] = purchase_data['stars']
    
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


def get_voices_over_time(db: Session, days: int = 7, start_date: Optional[str] = None, end_date: Optional[str] = None, acquisition_source: Optional[str] = None) -> List[dict]:
    """
    Get daily voice generation counts
    
    Args:
        start_date: Filter from this date onwards (YYYY-MM-DD)
        end_date: Filter up to this date (YYYY-MM-DD)
        acquisition_source: Filter by acquisition source
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
    
    # Query voice generations per day
    query = db.query(
        cast(TgAnalyticsEvent.created_at, Date).label('date'),
        func.count(TgAnalyticsEvent.id).label('count')
    ).filter(
        TgAnalyticsEvent.event_name == 'voice_generated',
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
    Get premium user statistics, revenue metrics, and payment transaction data
    
    Args:
        start_date: Filter from this date onwards (YYYY-MM-DD)
        end_date: Filter up to this date (YYYY-MM-DD)
        acquisition_source: Filter by acquisition source
    
    Returns:
        Dictionary with premium and revenue statistics
    """
    from sqlalchemy import func, distinct, case
    from datetime import timedelta
    from app.db.models import PaymentTransaction
    
    # ========== USER STATS ==========
    
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
    
    # ========== REVENUE STATS (from PaymentTransaction) ==========
    
    # Base query for completed transactions
    base_tx_query = db.query(PaymentTransaction).join(
        User, PaymentTransaction.user_id == User.id
    ).filter(PaymentTransaction.status == 'completed')
    
    if acquisition_source:
        base_tx_query = base_tx_query.filter(User.acquisition_source == acquisition_source)
    
    # Apply date filter to transactions
    if start_date or end_date:
        base_tx_query = apply_date_filter(base_tx_query, PaymentTransaction.created_at, start_date, end_date)
    
    # Total revenue stats
    revenue_query = db.query(
        func.count(PaymentTransaction.id).label('total_purchases'),
        func.coalesce(func.sum(PaymentTransaction.amount_stars), 0).label('total_stars'),
        func.count(distinct(PaymentTransaction.user_id)).label('unique_paying_users')
    ).join(User, PaymentTransaction.user_id == User.id).filter(
        PaymentTransaction.status == 'completed'
    )
    if acquisition_source:
        revenue_query = revenue_query.filter(User.acquisition_source == acquisition_source)
    if start_date or end_date:
        revenue_query = apply_date_filter(revenue_query, PaymentTransaction.created_at, start_date, end_date)
    
    revenue_result = revenue_query.first()
    total_purchases = revenue_result.total_purchases if revenue_result else 0
    total_stars = int(revenue_result.total_stars) if revenue_result else 0
    unique_paying_users = revenue_result.unique_paying_users if revenue_result else 0
    
    # Token packages stats
    token_query = db.query(
        func.count(PaymentTransaction.id).label('count'),
        func.coalesce(func.sum(PaymentTransaction.amount_stars), 0).label('stars'),
        func.coalesce(func.sum(PaymentTransaction.tokens_received), 0).label('tokens')
    ).join(User, PaymentTransaction.user_id == User.id).filter(
        PaymentTransaction.status == 'completed',
        PaymentTransaction.transaction_type == 'token_package'
    )
    if acquisition_source:
        token_query = token_query.filter(User.acquisition_source == acquisition_source)
    if start_date or end_date:
        token_query = apply_date_filter(token_query, PaymentTransaction.created_at, start_date, end_date)
    
    token_result = token_query.first()
    token_packages_count = token_result.count if token_result else 0
    token_packages_stars = int(token_result.stars) if token_result else 0
    tokens_sold = int(token_result.tokens) if token_result else 0
    
    # Tier subscriptions stats
    tier_query = db.query(
        func.count(PaymentTransaction.id).label('count'),
        func.coalesce(func.sum(PaymentTransaction.amount_stars), 0).label('stars')
    ).join(User, PaymentTransaction.user_id == User.id).filter(
        PaymentTransaction.status == 'completed',
        PaymentTransaction.transaction_type == 'tier_subscription'
    )
    if acquisition_source:
        tier_query = tier_query.filter(User.acquisition_source == acquisition_source)
    if start_date or end_date:
        tier_query = apply_date_filter(tier_query, PaymentTransaction.created_at, start_date, end_date)
    
    tier_result = tier_query.first()
    tier_subscriptions_count = tier_result.count if tier_result else 0
    tier_subscriptions_stars = int(tier_result.stars) if tier_result else 0
    
    # Product breakdown
    breakdown_query = db.query(
        PaymentTransaction.product_id,
        PaymentTransaction.transaction_type,
        func.count(PaymentTransaction.id).label('count'),
        func.coalesce(func.sum(PaymentTransaction.amount_stars), 0).label('total_stars')
    ).join(User, PaymentTransaction.user_id == User.id).filter(
        PaymentTransaction.status == 'completed'
    )
    if acquisition_source:
        breakdown_query = breakdown_query.filter(User.acquisition_source == acquisition_source)
    if start_date or end_date:
        breakdown_query = apply_date_filter(breakdown_query, PaymentTransaction.created_at, start_date, end_date)
    
    breakdown_results = breakdown_query.group_by(
        PaymentTransaction.product_id, 
        PaymentTransaction.transaction_type
    ).order_by(func.sum(PaymentTransaction.amount_stars).desc()).all()
    
    packages_breakdown = [
        {
            'product_id': row.product_id,
            'transaction_type': row.transaction_type,
            'count': row.count,
            'total_stars': int(row.total_stars)
        }
        for row in breakdown_results
    ]
    
    # Average purchase value
    avg_purchase_value = round(total_stars / total_purchases, 2) if total_purchases > 0 else 0
    
    # Revenue over time (daily) - always calculate if we have date filters
    revenue_over_time = []
    revenue_time_query = db.query(
        func.date(PaymentTransaction.created_at).label('date'),
        func.count(PaymentTransaction.id).label('purchases'),
        func.coalesce(func.sum(PaymentTransaction.amount_stars), 0).label('stars')
    ).join(User, PaymentTransaction.user_id == User.id).filter(
        PaymentTransaction.status == 'completed'
    )
    if acquisition_source:
        revenue_time_query = revenue_time_query.filter(User.acquisition_source == acquisition_source)
    if start_date or end_date:
        revenue_time_query = apply_date_filter(revenue_time_query, PaymentTransaction.created_at, start_date, end_date)
    
    revenue_time_results = revenue_time_query.group_by(func.date(PaymentTransaction.created_at)).order_by(func.date(PaymentTransaction.created_at)).all()
    
    STARS_TO_USD = 0.013
    revenue_over_time = [
        {
            'date': row.date.isoformat(),
            'purchases': row.purchases,
            'revenue_stars': int(row.stars),
            'revenue_usd': round(int(row.stars) * STARS_TO_USD, 2)
        }
        for row in revenue_time_results
    ]
    
    # Revenue by plan
    by_plan_query = db.query(
        PaymentTransaction.product_id,
        func.count(PaymentTransaction.id).label('count'),
        func.coalesce(func.sum(PaymentTransaction.amount_stars), 0).label('stars')
    ).join(User, PaymentTransaction.user_id == User.id).filter(
        PaymentTransaction.status == 'completed'
    )
    if acquisition_source:
        by_plan_query = by_plan_query.filter(User.acquisition_source == acquisition_source)
    if start_date or end_date:
        by_plan_query = apply_date_filter(by_plan_query, PaymentTransaction.created_at, start_date, end_date)
    
    by_plan_results = by_plan_query.group_by(PaymentTransaction.product_id).all()
    
    STARS_TO_USD = 0.013
    by_plan = [
        {
            'plan_name': row.product_id or 'Unknown',
            'count': row.count,
            'revenue_stars': int(row.stars),
            'revenue_usd': round(int(row.stars) * STARS_TO_USD, 2)
        }
        for row in by_plan_results
    ]
    
    # Calculate total revenue in USD
    total_revenue_usd = round(total_stars * STARS_TO_USD, 2)
    
    return {
        # User stats
        'total_premium_users': total_premium_users,
        'total_ever_premium_users': total_ever_premium_users,
        'total_free_users': total_free_users,
        'conversion_rate': round(conversion_rate, 2),
        'unique_paying_users': unique_paying_users,
        # Revenue stats
        'total_purchases': total_purchases,
        'total_stars': total_stars,
        'total_revenue_stars': total_stars,
        'total_revenue_usd': total_revenue_usd,
        'paying_users': unique_paying_users,
        'avg_purchase_value': avg_purchase_value,
        # Token packages
        'token_packages_count': token_packages_count,
        'token_packages_stars': token_packages_stars,
        'tokens_sold': tokens_sold,
        # Tier subscriptions
        'tier_subscriptions_count': tier_subscriptions_count,
        'tier_subscriptions_stars': tier_subscriptions_stars,
        # Breakdown
        'packages_breakdown': packages_breakdown,
        # Time series
        'revenue_over_time': revenue_over_time,
        'by_plan': by_plan
    }


def get_premium_users_with_spending(db: Session) -> dict:
    """
    Get all premium users with their spending statistics and usage costs
    
    Returns:
        Dictionary with users list and aggregate stats including LLM and image costs
    """
    from sqlalchemy import func
    from app.db.models import PaymentTransaction, Message, ImageJob
    
    # Cost constants
    COST_PER_MESSAGE = 0.0013
    COST_PER_IMAGE = 0.003
    STARS_TO_USD = 0.013
    
    # Get all users who ever had premium
    premium_users_query = db.query(User).filter(User.is_premium == True)
    
    # Get spending stats per user (revenue from purchases)
    spending_stats = db.query(
        PaymentTransaction.user_id,
        func.count(PaymentTransaction.id).label('purchase_count'),
        func.coalesce(func.sum(PaymentTransaction.amount_stars), 0).label('total_spent_stars'),
        func.max(PaymentTransaction.created_at).label('last_purchase_date')
    ).filter(
        PaymentTransaction.status == 'completed'
    ).group_by(PaymentTransaction.user_id).all()
    
    # Create a dict for quick lookup
    spending_dict = {
        stat.user_id: {
            'purchase_count': stat.purchase_count,
            'total_spent_stars': int(stat.total_spent_stars),
            'last_purchase_date': stat.last_purchase_date
        }
        for stat in spending_stats
    }
    
    # Get usage stats per user (messages and images)
    message_stats = db.query(
        Message.client_id,
        func.count(Message.id).label('message_count')
    ).filter(
        Message.role == 'assistant'
    ).group_by(Message.client_id).all()
    
    message_dict = {stat.client_id: stat.message_count for stat in message_stats}
    
    image_stats = db.query(
        ImageJob.user_id,
        func.count(ImageJob.id).label('image_count')
    ).filter(
        ImageJob.status == 'completed'
    ).group_by(ImageJob.user_id).all()
    
    image_dict = {stat.user_id: stat.image_count for stat in image_stats}
    
    # Build user list with spending and usage info
    users = []
    for user in premium_users_query.all():
        spending = spending_dict.get(user.id, {
            'purchase_count': 0,
            'total_spent_stars': 0,
            'last_purchase_date': None
        })
        
        messages = message_dict.get(user.id, 0)
        images = image_dict.get(user.id, 0)
        
        llm_cost = messages * COST_PER_MESSAGE
        image_cost = images * COST_PER_IMAGE
        total_cost = llm_cost + image_cost
        
        users.append({
            'id': user.id,
            'username': user.username,
            'first_name': user.first_name,
            'acquisition_source': user.acquisition_source,
            'is_premium': user.is_premium,
            'premium_until': user.premium_until.isoformat() if user.premium_until else None,
            'purchase_count': spending['purchase_count'],
            'total_spent_stars': spending['total_spent_stars'],
            'last_purchase_date': spending['last_purchase_date'].isoformat() if spending['last_purchase_date'] else None,
            'messages': messages,
            'images': images,
            'llm_cost': round(llm_cost, 2),
            'image_cost': round(image_cost, 2),
            'total_cost': round(total_cost, 2)
        })
    
    # Calculate aggregate stats
    total_premium_users = len(users)
    active_premium_users = sum(1 for u in users if not u['premium_until'] or datetime.fromisoformat(u['premium_until']) > datetime.utcnow())
    total_revenue_stars = sum(u['total_spent_stars'] for u in users)
    total_purchases = sum(u['purchase_count'] for u in users)
    total_messages = sum(u['messages'] for u in users)
    total_images = sum(u['images'] for u in users)
    total_llm_cost = sum(u['llm_cost'] for u in users)
    total_image_cost = sum(u['image_cost'] for u in users)
    total_usage_cost = total_llm_cost + total_image_cost
    
    total_revenue_usd = round(total_revenue_stars * STARS_TO_USD, 2)
    avg_spent_per_user = round(total_revenue_usd / total_premium_users, 2) if total_premium_users > 0 else 0
    avg_purchases_per_user = round(total_purchases / total_premium_users, 2) if total_premium_users > 0 else 0
    avg_cost_per_user = round(total_usage_cost / total_premium_users, 2) if total_premium_users > 0 else 0
    
    return {
        'users': users,
        'stats': {
            'total_premium_users': total_premium_users,
            'active_premium_users': active_premium_users,
            'total_revenue_stars': total_revenue_stars,
            'total_revenue_usd': total_revenue_usd,
            'total_purchases': total_purchases,
            'avg_spent_per_user': avg_spent_per_user,
            'avg_purchases_per_user': avg_purchases_per_user,
            'total_messages': total_messages,
            'total_images': total_images,
            'total_llm_cost': round(total_llm_cost, 2),
            'total_image_cost': round(total_image_cost, 2),
            'total_usage_cost': round(total_usage_cost, 2),
            'avg_cost_per_user': avg_cost_per_user
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
    is_active: bool = True,
    ad_price: float = None
) -> StartCode:
    """Create new start code
    
    Args:
        db: Database session
        code: 5-character alphanumeric code
        description: Info text about this code
        persona_id: Optional persona UUID
        history_id: Optional history UUID
        is_active: Whether code is active
        ad_price: Advertisement price in USD for ROI calculations
    
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
        is_active=is_active,
        ad_price=ad_price
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
    is_active: bool = None,
    ad_price: float = None
) -> Optional[StartCode]:
    """Update start code
    
    Args:
        db: Database session
        code: 5-character alphanumeric code
        description: Info text about this code
        persona_id: Optional persona UUID (None to clear)
        history_id: Optional history UUID (None to clear)
        is_active: Whether code is active
        ad_price: Advertisement price in USD for ROI calculations
    
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
    if ad_price is not None:
        start_code.ad_price = ad_price if ad_price > 0 else None
    
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


# ========== SYSTEM MESSAGE OPERATIONS ==========

def create_system_message(
    db: Session,
    title: str = None,
    text: str = None,
    text_ru: str = None,
    media_type: str = "none",
    media_url: str = None,
    audio_url: str = None,
    buttons: dict = None,
    target_type: str = None,
    target_user_ids: List[int] = None,
    target_group: str = None,
    send_immediately: bool = False,
    scheduled_at: datetime = None,
    created_by: str = None,
    ext: dict = None,
    template_id: UUID = None
) -> SystemMessage:
    """Create a new system message"""
    # Determine initial status
    if send_immediately:
        status = "sending"
    elif scheduled_at:
        status = "scheduled"
    else:
        status = "draft"
    
    message = SystemMessage(
        title=title,
        text=text,
        text_ru=text_ru,
        media_type=media_type,
        media_url=media_url,
        audio_url=audio_url,
        buttons=buttons or [],
        target_type=target_type,
        target_user_ids=target_user_ids,
        target_group=target_group,
        status=status,
        send_immediately=send_immediately,
        scheduled_at=scheduled_at,
        created_by=created_by,
        ext=ext or {},
        template_id=template_id
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def get_system_message(db: Session, message_id: UUID) -> Optional[SystemMessage]:
    """Get system message by ID"""
    return db.query(SystemMessage).filter(SystemMessage.id == message_id).first()


def list_system_messages(
    db: Session,
    page: int = 1,
    per_page: int = 50,
    status: str = None,
    target_type: str = None,
    date_from: datetime = None,
    date_to: datetime = None
) -> dict:
    """List system messages with pagination and filters"""
    query = db.query(SystemMessage)
    
    if status:
        query = query.filter(SystemMessage.status == status)
    if target_type:
        query = query.filter(SystemMessage.target_type == target_type)
    if date_from:
        query = query.filter(SystemMessage.created_at >= date_from)
    if date_to:
        query = query.filter(SystemMessage.created_at <= date_to)
    
    total = query.count()
    messages = query.order_by(desc(SystemMessage.created_at)).offset((page - 1) * per_page).limit(per_page).all()
    
    return {
        'messages': messages,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page
    }


def update_system_message(
    db: Session,
    message_id: UUID,
    title: str = None,
    text: str = None,
    text_ru: str = None,
    media_type: str = None,
    media_url: str = None,
    audio_url: str = None,
    buttons: dict = None,
    target_type: str = None,
    target_user_ids: List[int] = None,
    target_group: str = None,
    send_immediately: bool = None,
    scheduled_at: datetime = None,
    ext: dict = None
) -> Optional[SystemMessage]:
    """Update system message (only if status is 'draft' or 'scheduled')"""
    message = db.query(SystemMessage).filter(SystemMessage.id == message_id).first()
    if not message:
        return None
    
    if message.status not in ('draft', 'scheduled'):
        raise ValueError(f"Cannot update message with status '{message.status}'")
    
    if title is not None:
        message.title = title
    if text is not None:
        message.text = text
    if text_ru is not None:
        message.text_ru = text_ru
    if media_type is not None:
        message.media_type = media_type
    if media_url is not None:
        message.media_url = media_url
    if audio_url is not None:
        message.audio_url = audio_url
    if buttons is not None:
        message.buttons = buttons
    if target_type is not None:
        message.target_type = target_type
    if target_user_ids is not None:
        message.target_user_ids = target_user_ids
    if target_group is not None:
        message.target_group = target_group
    if send_immediately is not None:
        message.send_immediately = send_immediately
    if scheduled_at is not None:
        message.scheduled_at = scheduled_at
    if ext is not None:
        message.ext = ext
    
    # Update status based on send_immediately and scheduled_at
    if message.send_immediately:
        message.status = "sending"
    elif message.scheduled_at:
        message.status = "scheduled"
    else:
        message.status = "draft"
    
    db.commit()
    db.refresh(message)
    return message


def delete_system_message(db: Session, message_id: UUID) -> bool:
    """Delete system message (only if status is 'draft', 'scheduled', or 'cancelled')"""
    message = db.query(SystemMessage).filter(SystemMessage.id == message_id).first()
    if not message:
        return False
    
    if message.status not in ('draft', 'scheduled', 'cancelled'):
        raise ValueError(f"Cannot delete message with status '{message.status}'")
    
    db.delete(message)
    db.commit()
    return True


# ========== TRANSLATION OPERATIONS ==========

def get_translation(db: Session, key: str, lang: str):
    """Get a single translation by key and language
    
    Args:
        db: Database session
        key: Translation key (e.g., "airi.name", "welcome.title")
        lang: Language code (e.g., 'en', 'ru', 'fr', 'de', 'es')
    
    Returns:
        Translation object or None if not found
    """
    from app.db.models import Translation
    return db.query(Translation).filter(
        Translation.key == key,
        Translation.lang == lang
    ).first()


def get_translations_by_prefix(db: Session, prefix: str, lang: str) -> List:
    """Get all translations with keys starting with a prefix
    
    Args:
        db: Database session
        prefix: Key prefix (e.g., "airi.", "welcome.")
        lang: Language code
    
    Returns:
        List of Translation objects
    """
    from app.db.models import Translation
    return db.query(Translation).filter(
        Translation.key.like(f"{prefix}%"),
        Translation.lang == lang
    ).all()


def get_all_translations(db: Session, lang: Optional[str] = None) -> List:
    """Get all translations, optionally filtered by language
    
    Args:
        db: Database session
        lang: Optional language code filter
    
    Returns:
        List of Translation objects
    """
    from app.db.models import Translation
    query = db.query(Translation)
    
    if lang:
        query = query.filter(Translation.lang == lang)
    
    return query.all()


# ========== SYSTEM MESSAGE DELIVERY & SCHEDULING ==========

def get_scheduled_messages(db: Session) -> List[SystemMessage]:
    """
    Get messages that are scheduled and ready to send
    
    Uses SELECT FOR UPDATE SKIP LOCKED for concurrency safety:
    - Multiple scheduler instances won't process the same message
    - Locked rows are skipped, not blocked
    - Status is immediately updated to 'sending' within transaction
    """
    from sqlalchemy import select
    
    now = datetime.utcnow()
    
    # Use FOR UPDATE SKIP LOCKED for distributed lock-free concurrency
    stmt = select(SystemMessage).filter(
        SystemMessage.status == "scheduled",
        SystemMessage.scheduled_at <= now
    ).with_for_update(skip_locked=True)
    
    messages = db.execute(stmt).scalars().all()
    
    # Immediately update status to 'sending' to prevent other instances from picking them up
    for message in messages:
        message.status = "sending"
    
    if messages:
        db.commit()
        # Refresh to ensure we have latest data
        for message in messages:
            db.refresh(message)
    
    return messages


def get_users_by_group(db: Session, group_name: str) -> List[User]:
    """Get users by group name"""
    now = datetime.utcnow()
    
    if group_name == "premium":
        return db.query(User).filter(
            User.is_premium == True,
            User.premium_until > now
        ).all()
    
    elif group_name == "inactive_7d":
        from datetime import timedelta
        cutoff = now - timedelta(days=7)
        # Users with no messages or image generations in last 7 days
        # Check last_user_message_at from chats
        active_user_ids = db.query(Chat.user_id).filter(
            Chat.last_user_message_at >= cutoff
        ).distinct().all()
        active_user_ids = [uid[0] for uid in active_user_ids]
        
        # Also check image generation events
        active_image_user_ids = db.query(TgAnalyticsEvent.client_id).filter(
            TgAnalyticsEvent.event_name == "image_generated",
            TgAnalyticsEvent.created_at >= cutoff
        ).distinct().all()
        active_image_user_ids = [uid[0] for uid in active_image_user_ids]
        
        all_active_ids = set(active_user_ids + active_image_user_ids)
        if all_active_ids:
            return db.query(User).filter(~User.id.in_(all_active_ids)).all()
        else:
            return db.query(User).all()
    
    elif group_name == "inactive_30d":
        from datetime import timedelta
        cutoff = now - timedelta(days=30)
        active_user_ids = db.query(Chat.user_id).filter(
            Chat.last_user_message_at >= cutoff
        ).distinct().all()
        active_user_ids = [uid[0] for uid in active_user_ids]
        
        active_image_user_ids = db.query(TgAnalyticsEvent.client_id).filter(
            TgAnalyticsEvent.event_name == "image_generated",
            TgAnalyticsEvent.created_at >= cutoff
        ).distinct().all()
        active_image_user_ids = [uid[0] for uid in active_image_user_ids]
        
        all_active_ids = set(active_user_ids + active_image_user_ids)
        if all_active_ids:
            return db.query(User).filter(~User.id.in_(all_active_ids)).all()
        else:
            return db.query(User).all()
    
    elif group_name == "has_acquisition_source":
        return db.query(User).filter(User.acquisition_source.isnot(None)).all()
    
    elif group_name.startswith("acquisition_source:"):
        source = group_name.replace("acquisition_source:", "")
        return db.query(User).filter(User.acquisition_source == source).all()
    
    else:
        return []


# ========== SYSTEM MESSAGE TEMPLATE OPERATIONS ==========

def create_template(
    db: Session,
    name: str,
    title: str = None,
    text: str = None,
    media_type: str = "none",
    media_url: str = None,
    audio_url: str = None,
    buttons: dict = None,
    created_by: str = None
) -> SystemMessageTemplate:
    """Create a new system message template"""
    template = SystemMessageTemplate(
        name=name,
        title=title,
        text=text,
        media_type=media_type,
        media_url=media_url,
        audio_url=audio_url,
        buttons=buttons or [],
        created_by=created_by
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


def get_template(db: Session, template_id: UUID) -> Optional[SystemMessageTemplate]:
    """Get template by ID"""
    return db.query(SystemMessageTemplate).filter(SystemMessageTemplate.id == template_id).first()


def list_templates(
    db: Session,
    page: int = 1,
    per_page: int = 50,
    is_active: bool = None
) -> dict:
    """List templates with pagination"""
    query = db.query(SystemMessageTemplate)
    
    if is_active is not None:
        query = query.filter(SystemMessageTemplate.is_active == is_active)
    
    total = query.count()
    templates = query.order_by(desc(SystemMessageTemplate.created_at)).offset((page - 1) * per_page).limit(per_page).all()
    
    return {
        'templates': templates,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page
    }


def get_active_templates(db: Session) -> List[SystemMessageTemplate]:
    """Get all active templates"""
    return db.query(SystemMessageTemplate).filter(SystemMessageTemplate.is_active == True).all()


def update_template(
    db: Session,
    template_id: UUID,
    name: str = None,
    title: str = None,
    text: str = None,
    media_type: str = None,
    media_url: str = None,
    audio_url: str = None,
    buttons: dict = None,
    is_active: bool = None
) -> Optional[SystemMessageTemplate]:
    """Update template"""
    template = db.query(SystemMessageTemplate).filter(SystemMessageTemplate.id == template_id).first()
    if not template:
        return None
    
    if name is not None:
        template.name = name
    if title is not None:
        template.title = title
    if text is not None:
        template.text = text
    if media_type is not None:
        template.media_type = media_type
    if media_url is not None:
        template.media_url = media_url
    if audio_url is not None:
        template.audio_url = audio_url
    if buttons is not None:
        template.buttons = buttons
    if is_active is not None:
        template.is_active = is_active
    
    db.commit()
    db.refresh(template)
    return template


def delete_template(db: Session, template_id: UUID) -> bool:
    """Delete template"""
    template = db.query(SystemMessageTemplate).filter(SystemMessageTemplate.id == template_id).first()
    if not template:
        return False
    
    db.delete(template)
    db.commit()
    return True


# ========== SYSTEM MESSAGE DELIVERY OPERATIONS ==========

def create_delivery_records(db: Session, system_message_id: UUID, user_ids: List[int], max_retries: int = 3) -> List[SystemMessageDelivery]:
    """Create delivery records for all target users"""
    deliveries = []
    for user_id in user_ids:
        delivery = SystemMessageDelivery(
            system_message_id=system_message_id,
            user_id=user_id,
            max_retries=max_retries
        )
        db.add(delivery)
        deliveries.append(delivery)
    
    db.commit()
    for delivery in deliveries:
        db.refresh(delivery)
    return deliveries


def get_delivery_record(db: Session, delivery_id: UUID) -> Optional[SystemMessageDelivery]:
    """Get delivery record by ID"""
    return db.query(SystemMessageDelivery).filter(SystemMessageDelivery.id == delivery_id).first()


def update_delivery_status(
    db: Session,
    delivery_id: UUID,
    status: str = None,
    error: str = None,
    sent_at: datetime = None,
    message_id: int = None,
    retry_count: int = None
) -> Optional[SystemMessageDelivery]:
    """Update delivery status"""
    delivery = db.query(SystemMessageDelivery).filter(SystemMessageDelivery.id == delivery_id).first()
    if not delivery:
        return None
    
    if status is not None:
        delivery.status = status
    if error is not None:
        delivery.error = error
    if sent_at is not None:
        delivery.sent_at = sent_at
    if message_id is not None:
        delivery.message_id = message_id
    if retry_count is not None:
        delivery.retry_count = retry_count
    
    db.commit()
    db.refresh(delivery)
    return delivery


def get_failed_deliveries(db: Session, system_message_id: UUID = None) -> List[SystemMessageDelivery]:
    """Get failed deliveries that can be retried"""
    query = db.query(SystemMessageDelivery).filter(
        SystemMessageDelivery.status == "failed",
        SystemMessageDelivery.retry_count < SystemMessageDelivery.max_retries
    )
    
    if system_message_id:
        query = query.filter(SystemMessageDelivery.system_message_id == system_message_id)
    
    return query.all()


# ========== TRANSLATION OPERATIONS (CONTINUED) ==========

def create_or_update_translation(
    db: Session,
    key: str,
    lang: str,
    value: str,
    category: Optional[str] = None
):
    """Create or update a translation
    
    Args:
        db: Database session
        key: Translation key
        lang: Language code
        value: Translated text
        category: Optional category ('ui', 'persona', 'history')
    
    Returns:
        Translation object
    """
    from app.db.models import Translation
    
    # Try to find existing translation
    translation = db.query(Translation).filter(
        Translation.key == key,
        Translation.lang == lang
    ).first()
    
    if translation:
        # Update existing
        translation.value = value
        if category is not None:
            translation.category = category
        translation.updated_at = datetime.utcnow()
    else:
        # Create new
        translation = Translation(
            key=key,
            lang=lang,
            value=value,
            category=category
        )
        db.add(translation)
    
    db.commit()
    db.refresh(translation)
    return translation


def delete_translation(db: Session, key: str, lang: Optional[str] = None) -> int:
    """Delete translation(s) by key and optionally language
    
    Args:
        db: Database session
        key: Translation key
        lang: Optional language code (if None, deletes all languages for this key)
    
    Returns:
        Number of translations deleted
    """
    from app.db.models import Translation
    
    query = db.query(Translation).filter(Translation.key == key)
    
    if lang:
        query = query.filter(Translation.lang == lang)
    
    count = query.delete(synchronize_session=False)
    db.commit()
    
    return count


def bulk_create_translations(db: Session, translations_list: List[Dict[str, str]]) -> int:
    """Bulk create translations efficiently
    
    Args:
        db: Database session
        translations_list: List of dicts with keys: 'key', 'lang', 'value', 'category' (optional)
    
    Returns:
        Number of translations created
    """
    from app.db.models import Translation
    
    translation_objects = []
    for trans_data in translations_list:
        translation = Translation(
            key=trans_data['key'],
            lang=trans_data['lang'],
            value=trans_data['value'],
            category=trans_data.get('category')
        )
        translation_objects.append(translation)
    
    db.bulk_save_objects(translation_objects)
    db.commit()
    
    return len(translation_objects)


def get_daily_user_stats(db: Session, target_date: datetime.date) -> List[Dict[str, Any]]:
    """
    Get aggregated stats per user for a specific date
    """
    from sqlalchemy import func, cast, Float
    
    # Date range for the day
    start_time = datetime.combine(target_date, datetime.min.time())
    end_time = datetime.combine(target_date, datetime.max.time())
    
    # 1. User Messages count
    user_msgs = db.query(
        Chat.user_id,
        func.count(Message.id).label('count')
    ).join(
        Chat, Message.chat_id == Chat.id
    ).filter(
        Message.role == 'user',
        Message.created_at >= start_time,
        Message.created_at <= end_time
    ).group_by(Chat.user_id).all()
    
    user_msg_map = {r.user_id: r.count for r in user_msgs}
    
    # 2. Scheduled Messages count
    sched_msgs = db.query(
        TgAnalyticsEvent.client_id,
        func.count(TgAnalyticsEvent.id).label('count')
    ).filter(
        TgAnalyticsEvent.event_name == 'auto_followup_message',
        TgAnalyticsEvent.created_at >= start_time,
        TgAnalyticsEvent.created_at <= end_time
    ).group_by(TgAnalyticsEvent.client_id).all()
    
    sched_msg_map = {r.client_id: r.count for r in sched_msgs}
    
    # 3. Cost from events
    # Note: JSONB operator ->> returns text, cast to float
    cost_events = db.query(
        TgAnalyticsEvent.client_id,
        func.sum(cast(TgAnalyticsEvent.meta['cost_usd'].astext, Float)).label('cost')
    ).filter(
        TgAnalyticsEvent.event_name == 'llm_cost',
        TgAnalyticsEvent.created_at >= start_time,
        TgAnalyticsEvent.created_at <= end_time
    ).group_by(TgAnalyticsEvent.client_id).all()
    
    cost_map = {r.client_id: (r.cost or 0.0) for r in cost_events}
    
    # 4. Fallback Cost (Estimated from assistant messages if no cost events)
    # Assume ~$10/1M chars input+output mix? Or simple per char.
    # Price: Let's assume avg $5/1M tokens => $5/4M chars => 0.00000125 per char
    
    fallback_cost_msgs = db.query(
        Chat.user_id,
        func.sum(func.length(Message.text)).label('chars')
    ).join(
        Chat, Message.chat_id == Chat.id
    ).filter(
        Message.role == 'assistant',
        Message.created_at >= start_time,
        Message.created_at <= end_time
    ).group_by(Chat.user_id).all()
    
    fallback_cost_map = {}
    PRICE_PER_CHAR = 0.000002 # Rough estimate ($8/1M tokens approx)
    for r in fallback_cost_msgs:
        fallback_cost_map[r.user_id] = (r.chars or 0) * PRICE_PER_CHAR
        
    # 5. Get all relevant users (union of keys)
    all_user_ids = set(user_msg_map.keys()) | set(sched_msg_map.keys()) | set(cost_map.keys()) | set(fallback_cost_map.keys())
    
    if not all_user_ids:
        return []

    # Fetch user details
    users = db.query(User).filter(User.id.in_(all_user_ids)).all()
    user_details = {u.id: u for u in users}
    
    stats = []
    for uid in all_user_ids:
        user = user_details.get(uid)
        cost = cost_map.get(uid, 0.0)
        if cost == 0.0:
            cost = fallback_cost_map.get(uid, 0.0)
            
        stats.append({
            "user_id": uid,
            "username": user.username if user else None,
            "first_name": user.first_name if user else None,
            "is_premium": user.is_premium if user else False,
            "user_messages": user_msg_map.get(uid, 0),
            "scheduled_messages": sched_msg_map.get(uid, 0),
            "estimated_cost": round(cost, 4)
        })
        
    # Sort by cost desc
    stats.sort(key=lambda x: x["estimated_cost"], reverse=True)
    
    return stats


# ========== SYSTEM MESSAGE DELIVERY STATISTICS ==========

def get_delivery_stats(db: Session, system_message_id: UUID) -> dict:
    """Get delivery statistics for a system message"""
    deliveries = db.query(SystemMessageDelivery).filter(
        SystemMessageDelivery.system_message_id == system_message_id
    ).all()
    
    total = len(deliveries)
    sent = sum(1 for d in deliveries if d.status == "sent")
    failed = sum(1 for d in deliveries if d.status == "failed")
    blocked = sum(1 for d in deliveries if d.status == "blocked")
    pending = sum(1 for d in deliveries if d.status == "pending")
    
    success_rate = (sent / total * 100) if total > 0 else 0
    
    return {
        'total': total,
        'sent': sent,
        'failed': failed,
        'blocked': blocked,
        'pending': pending,
        'success_rate': round(success_rate, 2)
    }


def get_deliveries_by_message(
    db: Session,
    system_message_id: UUID,
    page: int = 1,
    per_page: int = 100,
    status: str = None
) -> dict:
    """Get deliveries for a system message with pagination"""
    query = db.query(SystemMessageDelivery).filter(
        SystemMessageDelivery.system_message_id == system_message_id
    )
    
    if status:
        query = query.filter(SystemMessageDelivery.status == status)
    
    total = query.count()
    deliveries = query.order_by(desc(SystemMessageDelivery.created_at)).offset((page - 1) * per_page).limit(per_page).all()
    
    return {
        'deliveries': deliveries,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page
    }




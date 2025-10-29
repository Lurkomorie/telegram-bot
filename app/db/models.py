"""
SQLAlchemy database models
"""
from datetime import datetime
from uuid import uuid4
from sqlalchemy import BigInteger, Boolean, CheckConstraint, Column, DateTime, ForeignKey, Index, String, Text, ARRAY
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class User(Base):
    """Telegram users"""
    __tablename__ = "users"
    
    id = Column(BigInteger, primary_key=True)  # Telegram user ID
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    locale = Column(String(10), default="en")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Settings
    settings = Column(JSONB, default={})
    
    # Energy system
    energy = Column(BigInteger, default=100, nullable=False)
    max_energy = Column(BigInteger, default=100, nullable=False)
    last_energy_upsell_message_id = Column(BigInteger, nullable=True)
    last_energy_upsell_chat_id = Column(BigInteger, nullable=True)
    
    # Premium subscription
    is_premium = Column(Boolean, default=False, nullable=False)
    premium_until = Column(DateTime, nullable=True)
    
    # Relationships
    chats = relationship("Chat", back_populates="user")
    personas = relationship("Persona", back_populates="owner")


class Persona(Base):
    """AI girl personas (public or user-created)"""
    __tablename__ = "personas"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    owner_user_id = Column(BigInteger, ForeignKey("users.id"), nullable=True)  # NULL = public persona
    key = Column(String(100), nullable=True, unique=True)  # e.g., "sweet_girlfriend" for public personas
    name = Column(String(255), nullable=False)
    
    # Simplified schema - separate prompts for dialogue and images
    prompt = Column(Text, nullable=True)  # Custom personality prompt for dialogue
    image_prompt = Column(Text, nullable=True)  # Custom prompt for image generation (SDXL tags)
    badges = Column(ARRAY(String), default=[])  # UI display badges like ["Popular", "New", "NSFW"]
    visibility = Column(
        String(20), 
        CheckConstraint("visibility IN ('public', 'private', 'custom')"), 
        default="custom",
        nullable=False
    )
    description = Column(Text, nullable=True)  # Short description for UI
    small_description = Column(Text, nullable=True)  # Short one-line description for persona selection
    emoji = Column(String(10), nullable=True)  # Emoji for persona (e.g., "💕", "🌟")
    intro = Column(Text, nullable=True)  # Introduction message
    avatar_url = Column(Text, nullable=True)  # Avatar image for gallery display
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    owner = relationship("User", back_populates="personas")
    chats = relationship("Chat", back_populates="persona")
    history_starts = relationship("PersonaHistoryStart", back_populates="persona")
    
    __table_args__ = (
        Index("ix_personas_owner_user_id", "owner_user_id"),
        Index("ix_personas_key", "key"),
        Index("ix_personas_visibility", "visibility"),
    )


class PersonaHistoryStart(Base):
    """Initial greeting messages with images for personas"""
    __tablename__ = "persona_history_starts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=False)
    name = Column(String(255), nullable=True)  # Story name (e.g., "The Dairy Queen")
    small_description = Column(Text, nullable=True)  # Short story description for menu
    description = Column(Text, nullable=True)  # Scene-setting description (sent before greeting)
    text = Column(Text, nullable=False)  # Greeting message
    image_url = Column(Text, nullable=True)  # Pre-generated image URL (portrait)
    wide_menu_image_url = Column(Text, nullable=True)  # Wide image for menu display
    image_prompt = Column(Text, nullable=True)  # SDXL prompt used for the greeting image (for continuity)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    persona = relationship("Persona", back_populates="history_starts")
    
    __table_args__ = (
        Index("ix_persona_history_starts_persona_id", "persona_id"),
    )


class Chat(Base):
    """Chat sessions between user and persona"""
    __tablename__ = "chats"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tg_chat_id = Column(BigInteger, nullable=False)  # Telegram chat ID
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=False)
    mode = Column(String(20), CheckConstraint("mode IN ('dm', 'group')"), default="dm", nullable=False)
    status = Column(String(20), CheckConstraint("status IN ('active', 'archived')"), default="active", nullable=False)
    
    # Chat-specific settings
    settings = Column(JSONB, default={})  # Can override persona style per chat
    ext = Column(JSONB, default={})  # Extended metadata
    
    # Conversation state (mirrors FullState from schemas)
    state_snapshot = Column(JSONB, default={})
    
    # Memory system - stores important conversation facts
    memory = Column(Text, nullable=True)
    
    # Timestamps for auto-message tracking
    last_user_message_at = Column(DateTime, nullable=True)
    last_assistant_message_at = Column(DateTime, nullable=True)
    last_auto_message_at = Column(DateTime, nullable=True)  # Track auto-follow-ups to prevent spam
    
    # Processing lock to prevent overlapping pipeline executions
    is_processing = Column(Boolean, default=False, nullable=False)
    processing_started_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="chats")
    persona = relationship("Persona", back_populates="chats")
    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("ix_chats_tg_chat_id", "tg_chat_id"),
        Index("ix_chats_user_persona", "user_id", "persona_id"),
        Index("ix_chats_last_user_message_at", "last_user_message_at"),
        Index("ix_chats_status", "status"),
    )


class Message(Base):
    """Chat messages"""
    __tablename__ = "messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    chat_id = Column(UUID(as_uuid=True), ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), CheckConstraint("role IN ('user', 'assistant', 'system')"), nullable=False)
    text = Column(Text, nullable=True)
    media = Column(JSONB, default={})  # {"type": "photo", "file_id": "...", "url": "..."}
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Processing tracking for message batching
    is_processed = Column(Boolean, default=False, nullable=False)
    
    # State snapshot (stored with assistant messages)
    state_snapshot = Column(JSONB, default=None, nullable=True)
    
    # Relationships
    chat = relationship("Chat", back_populates="messages")
    
    __table_args__ = (
        Index("ix_messages_chat_created", "chat_id", "created_at"),
        Index("ix_messages_unprocessed", "chat_id", "is_processed"),
    )


class ImageJob(Base):
    """Image generation jobs (Runpod)"""
    __tablename__ = "image_jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    chat_id = Column(UUID(as_uuid=True), ForeignKey("chats.id"), nullable=True)
    persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    
    # Prompts
    prompt = Column(Text, nullable=False)
    negative_prompt = Column(Text, nullable=True)
    
    # Status
    status = Column(
        String(20),
        CheckConstraint("status IN ('queued', 'running', 'completed', 'failed')"),
        default="queued",
        nullable=False
    )
    
    # Results
    result_url = Column(Text, nullable=True)
    result_file_id = Column(String(255), nullable=True)  # Telegram file_id for caching
    error = Column(Text, nullable=True)
    
    # Extra metadata
    ext = Column(JSONB, default={})  # {"width": 832, "height": 1216, "seed": 123456, ...}
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    finished_at = Column(DateTime, nullable=True)
    
    # Relationships
    persona = relationship("Persona")
    user = relationship("User")
    chat = relationship("Chat")
    
    __table_args__ = (
        Index("ix_image_jobs_status", "status"),
        Index("ix_image_jobs_chat_id", "chat_id"),
    )


class TgAnalyticsEvent(Base):
    """Analytics events for tracking all user interactions"""
    __tablename__ = "tg_analytics_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    client_id = Column(BigInteger, nullable=False)  # Telegram user ID
    event_name = Column(String(100), nullable=False)
    
    # Optional persona information
    persona_id = Column(UUID(as_uuid=True), nullable=True)
    persona_name = Column(String(255), nullable=True)
    
    # Event data
    message = Column(Text, nullable=True)
    prompt = Column(Text, nullable=True)
    negative_prompt = Column(Text, nullable=True)
    image_url = Column(Text, nullable=True)  # Cloudflare URL for analytics
    
    # Additional metadata
    meta = Column(JSONB, default={}, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index("ix_tg_analytics_client_id", "client_id"),
        Index("ix_tg_analytics_event_name", "event_name"),
        Index("ix_tg_analytics_created_at", "created_at"),
        Index("ix_tg_analytics_client_created", "client_id", "created_at"),
    )

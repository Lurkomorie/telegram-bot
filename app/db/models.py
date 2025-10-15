"""
SQLAlchemy database models
"""
from datetime import datetime
from uuid import uuid4
from sqlalchemy import BigInteger, Boolean, CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, String, Text, text
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
    
    # Relationships
    chats = relationship("Chat", back_populates="user")
    personas = relationship("Persona", back_populates="owner")


class Persona(Base):
    """AI girl personas (preset or user-created)"""
    __tablename__ = "personas"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    owner_user_id = Column(BigInteger, ForeignKey("users.id"), nullable=True)  # NULL = preset
    key = Column(String(100), nullable=True, unique=True)  # e.g., "sweet_girlfriend" for presets
    name = Column(String(255), nullable=False)
    system_prompt = Column(Text, nullable=False)
    style = Column(JSONB, default={})  # {"temperature": 0.8, "tone": "sweet", "max_tokens": 400}
    negatives = Column(Text, nullable=True)  # Comma-separated negative prompts for images
    appearance = Column(JSONB, default={})  # Physical appearance for image generation
    is_preset = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    owner = relationship("User", back_populates="personas")
    chats = relationship("Chat", back_populates="persona")
    
    __table_args__ = (
        Index("ix_personas_owner_user_id", "owner_user_id"),
        Index("ix_personas_key", "key"),
    )


class Chat(Base):
    """Chat sessions between user and persona"""
    __tablename__ = "chats"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tg_chat_id = Column(BigInteger, nullable=False)  # Telegram chat ID
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=False)
    mode = Column(String(20), CheckConstraint("mode IN ('dm', 'group')"), default="dm", nullable=False)
    
    # Chat-specific settings
    settings = Column(JSONB, default={})  # Can override persona style per chat
    
    # Conversation state (mirrors your FullState from Sexsplicit)
    state_snapshot = Column(JSONB, default={})
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="chats")
    persona = relationship("Persona", back_populates="chats")
    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("ix_chats_tg_chat_id", "tg_chat_id"),
        Index("ix_chats_user_persona", "user_id", "persona_id"),
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
    
    # Relationships
    chat = relationship("Chat", back_populates="messages")
    
    __table_args__ = (
        Index("ix_messages_chat_created", "chat_id", "created_at"),
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
    
    __table_args__ = (
        Index("ix_image_jobs_status", "status"),
        Index("ix_image_jobs_chat_id", "chat_id"),
    )



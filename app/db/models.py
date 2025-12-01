"""
SQLAlchemy database models
"""
from datetime import datetime
from uuid import uuid4
from sqlalchemy import BigInteger, Boolean, CheckConstraint, Column, DateTime, ForeignKey, Index, String, Text, ARRAY, UniqueConstraint
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
    locale_manually_set = Column(Boolean, default=False, nullable=False)  # True if user manually changed language in miniapp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Settings
    settings = Column(JSONB, default={})
    
    # Token system (formerly energy)
    energy = Column(BigInteger, default=100, nullable=False)  # Now represents token balance
    max_energy = Column(BigInteger, default=100, nullable=False)  # Maximum energy/tokens a user can have
    temp_energy = Column(BigInteger, default=0, nullable=False)  # Temporary daily energy (resets daily, consumed first)
    last_energy_upsell_message_id = Column(BigInteger, nullable=True)
    last_energy_upsell_chat_id = Column(BigInteger, nullable=True)
    
    # Premium tiers and subscription
    is_premium = Column(Boolean, default=False, nullable=False)
    premium_until = Column(DateTime, nullable=True)
    premium_tier = Column(String(20), default="free", nullable=False)  # free, plus, premium, pro, legendary
    last_daily_token_addition = Column(DateTime, nullable=True)  # Last automatic tier-based token addition
    last_temp_energy_refill = Column(DateTime, nullable=True)  # Last temporary energy refill (daily)
    last_daily_bonus_claim = Column(DateTime, nullable=True)  # Last manual daily bonus claim
    daily_bonus_streak = Column(BigInteger, default=0, nullable=False)  # Consecutive days of claiming daily bonus
    
    # Referral system
    referred_by_user_id = Column(BigInteger, ForeignKey("users.id"), nullable=True)
    referral_tokens_awarded = Column(Boolean, default=False, nullable=False)
    
    # Global message counter (for priority queue logic)
    global_message_count = Column(BigInteger, default=0, nullable=False)
    
    # Acquisition tracking (for ads attribution)
    acquisition_source = Column(String(64), nullable=True)  # First deep-link payload
    acquisition_timestamp = Column(DateTime, nullable=True)  # When user first arrived
    
    # Age verification
    age_verified = Column(Boolean, default=False, nullable=False)  # Whether user confirmed 18+
    
    # Character creation tracking
    char_created = Column(Boolean, default=False, nullable=False)  # Whether user has created their first character (first is free)
    
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
    
    # Ordering and menu visibility
    order = Column(BigInteger, nullable=True, default=999)  # Sort order (lower appears first)
    main_menu = Column(Boolean, nullable=True, default=True)  # Show in chat main menu
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    owner = relationship("User", back_populates="personas")
    chats = relationship("Chat", back_populates="persona", cascade="all, delete-orphan")
    history_starts = relationship("PersonaHistoryStart", back_populates="persona", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("ix_personas_owner_user_id", "owner_user_id"),
        Index("ix_personas_key", "key"),
        Index("ix_personas_visibility", "visibility"),
        Index("ix_personas_order", "order"),
    )


class PersonaHistoryStart(Base):
    """Initial greeting messages with images for personas"""
    __tablename__ = "persona_history_starts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="CASCADE"), nullable=False)
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


class PersonaTranslation(Base):
    """Translations for persona descriptions"""
    __tablename__ = "persona_translations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="CASCADE"), nullable=False)
    language = Column(String(10), nullable=False)  # 'en', 'ru', 'fr', 'de', 'es'
    description = Column(Text, nullable=True)
    small_description = Column(Text, nullable=True)
    intro = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    persona = relationship("Persona")
    
    __table_args__ = (
        Index("ix_persona_translations_persona_id", "persona_id"),
        Index("ix_persona_translations_language", "language"),
        UniqueConstraint("persona_id", "language", name="uq_persona_translations_persona_language"),
    )


class PersonaHistoryTranslation(Base):
    """Translations for persona history start descriptions"""
    __tablename__ = "persona_history_translations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    history_id = Column(UUID(as_uuid=True), ForeignKey("persona_history_starts.id", ondelete="CASCADE"), nullable=False)
    language = Column(String(10), nullable=False)  # 'en', 'ru', 'fr', 'de', 'es'
    name = Column(String(255), nullable=True)  # Story name
    small_description = Column(Text, nullable=True)  # Short story description
    description = Column(Text, nullable=True)  # Scene-setting description
    text = Column(Text, nullable=True)  # Greeting message
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    history = relationship("PersonaHistoryStart")
    
    __table_args__ = (
        Index("ix_persona_history_translations_history_id", "history_id"),
        Index("ix_persona_history_translations_language", "language"),
        UniqueConstraint("history_id", "language", name="uq_persona_history_translations_history_language"),
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
    
    # Message counter for image generation decisions
    message_count = Column(BigInteger, default=0, nullable=False)
    
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


class StartCode(Base):
    """Start codes for bot acquisition tracking and onboarding"""
    __tablename__ = "start_codes"
    
    code = Column(String(5), primary_key=True)  # 5-character alphanumeric code
    description = Column(Text, nullable=True)  # Info text about this code
    persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True)  # Optional persona
    history_id = Column(UUID(as_uuid=True), ForeignKey("persona_history_starts.id"), nullable=True)  # Optional history
    is_active = Column(Boolean, default=True, nullable=False)  # Active/inactive toggle
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    persona = relationship("Persona")
    history = relationship("PersonaHistoryStart")
    
    __table_args__ = (
        Index("ix_start_codes_is_active", "is_active"),
    )


class Translation(Base):
    """Unified translation table for all localizable content"""
    __tablename__ = "translations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    key = Column(String(255), nullable=False, index=True)  # Dot notation: "airi.name", "welcome.title", "airi.history.title-0"
    lang = Column(String(10), nullable=False, index=True)  # 'en', 'ru', 'fr', 'de', 'es'
    value = Column(Text, nullable=False)  # The translated content
    category = Column(String(50), nullable=True)  # 'ui', 'persona', 'history' for filtering/organization
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint("key", "lang", name="uq_translations_key_lang"),
        Index("ix_translations_key_lang", "key", "lang"),
        Index("ix_translations_category", "category"),
    )


class PaymentTransaction(Base):
    """Payment transactions for tracking all token purchases and tier subscriptions"""
    __tablename__ = "payment_transactions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    transaction_type = Column(
        String(20),
        CheckConstraint("transaction_type IN ('token_package', 'tier_subscription')"),
        nullable=False
    )
    product_id = Column(String(50), nullable=False)  # e.g., "tokens_100", "premium_month"
    amount_stars = Column(BigInteger, nullable=False)  # Stars paid
    tokens_received = Column(BigInteger, nullable=True)  # For token packages
    tier_granted = Column(String(20), nullable=True)  # For subscriptions: plus, premium, pro, legendary
    subscription_days = Column(BigInteger, nullable=True)  # For subscriptions
    telegram_payment_charge_id = Column(String(255), nullable=True)  # Telegram's payment ID
    status = Column(
        String(20),
        CheckConstraint("status IN ('completed', 'pending', 'failed', 'refunded')"),
        default="completed",
        nullable=False
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User")
    
    __table_args__ = (
        Index("ix_payment_transactions_user_id", "user_id"),
        Index("ix_payment_transactions_created_at", "created_at"),
        Index("ix_payment_transactions_status", "status"),
    )


class SystemMessageTemplate(Base):
    """Templates for system messages"""
    __tablename__ = "system_message_templates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    title = Column(String(255), nullable=True)
    text = Column(Text, nullable=False)
    media_type = Column(
        String(20),
        CheckConstraint("media_type IN ('none', 'photo', 'video', 'animation')"),
        default="none",
        nullable=False
    )
    media_url = Column(Text, nullable=True)
    buttons = Column(JSONB, default=[], nullable=True)
    created_by = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    system_messages = relationship("SystemMessage", back_populates="template")
    
    __table_args__ = (
        Index("ix_system_message_templates_is_active", "is_active"),
        Index("ix_system_message_templates_created_at", "created_at"),
    )


class SystemMessage(Base):
    """System messages sent to users"""
    __tablename__ = "system_messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    title = Column(String(255), nullable=True)
    text = Column(Text, nullable=False)
    media_type = Column(
        String(20),
        CheckConstraint("media_type IN ('none', 'photo', 'video', 'animation')"),
        default="none",
        nullable=False
    )
    media_url = Column(Text, nullable=True)
    buttons = Column(JSONB, default=[], nullable=True)
    target_type = Column(
        String(20),
        CheckConstraint("target_type IN ('all', 'user', 'users', 'group')"),
        nullable=False
    )
    target_user_ids = Column(ARRAY(BigInteger), nullable=True)
    target_group = Column(String(255), nullable=True)
    status = Column(
        String(20),
        CheckConstraint("status IN ('draft', 'scheduled', 'sending', 'completed', 'failed', 'cancelled')"),
        default="draft",
        nullable=False
    )
    send_immediately = Column(Boolean, default=False, nullable=False)
    scheduled_at = Column(DateTime, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    created_by = Column(String(255), nullable=True)
    ext = Column(JSONB, default={}, nullable=True)
    template_id = Column(UUID(as_uuid=True), ForeignKey("system_message_templates.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    template = relationship("SystemMessageTemplate", back_populates="system_messages")
    deliveries = relationship("SystemMessageDelivery", back_populates="system_message", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("ix_system_messages_status", "status"),
        Index("ix_system_messages_target_type", "target_type"),
        Index("ix_system_messages_scheduled_at", "scheduled_at"),
        Index("ix_system_messages_created_at", "created_at"),
        Index("ix_system_messages_template_id", "template_id"),
    )


class SystemMessageDelivery(Base):
    """Delivery tracking for system messages"""
    __tablename__ = "system_message_deliveries"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    system_message_id = Column(UUID(as_uuid=True), ForeignKey("system_messages.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    status = Column(
        String(20),
        CheckConstraint("status IN ('pending', 'sent', 'failed', 'blocked')"),
        default="pending",
        nullable=False
    )
    error = Column(Text, nullable=True)
    retry_count = Column(BigInteger, default=0, nullable=False)
    max_retries = Column(BigInteger, default=3, nullable=False)
    sent_at = Column(DateTime, nullable=True)
    message_id = Column(BigInteger, nullable=True)  # Telegram message ID
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    system_message = relationship("SystemMessage", back_populates="deliveries")
    user = relationship("User")
    
    __table_args__ = (
        Index("ix_system_message_deliveries_system_message_id", "system_message_id"),
        Index("ix_system_message_deliveries_user_id", "user_id"),
        Index("ix_system_message_deliveries_status", "status"),
        Index("ix_system_message_deliveries_retry_count", "retry_count"),
    )

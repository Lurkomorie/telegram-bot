"""
Application constants and enums
"""
from enum import Enum


class MessageRole(str, Enum):
    """Message role types"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ImageJobStatus(str, Enum):
    """Image generation job statuses"""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class PersonaVisibility(str, Enum):
    """Persona visibility levels"""
    PUBLIC = "public"
    PRIVATE = "private"
    CUSTOM = "custom"


class RelationshipStage(str, Enum):
    """Relationship progression stages"""
    STRANGER = "stranger"
    ACQUAINTANCE = "acquaintance"
    FRIEND = "friend"
    CRUSH = "crush"
    LOVER = "lover"
    PARTNER = "partner"
    EX = "ex"


class ChatMode(str, Enum):
    """Chat modes"""
    DM = "dm"
    GROUP = "group"


# Chat action types
class ChatAction(str, Enum):
    """Telegram chat action types"""
    TYPING = "typing"
    UPLOAD_PHOTO = "upload_photo"
    UPLOAD_VIDEO = "upload_video"
    RECORD_VIDEO = "record_video"
    UPLOAD_DOCUMENT = "upload_document"


# Error messages
ERROR_MESSAGES = {
    "no_persona": "Please select an AI girl first using /start",
    "persona_not_found": "Persona not found. Please start over with /start",
    "rate_limit": "⚠️ You're sending messages too fast! Please wait a moment.",
    "rate_limit_image": "⚠️ Slow down! Please wait before requesting another image.",
    "processing_error": "Sorry, I'm having trouble responding right now. Please try again in a moment.",
    "chat_not_found": "Chat session not found. Please use /start to begin.",
    "image_generating": "🎨 Generating your image... This may take a minute.",
    "image_failed": "❌ Sorry, image generation failed. Please try again.",
    "history_cleared": "✅ Conversation history cleared. Starting fresh!",
}


# Pipeline constants
MAX_HISTORY_MESSAGES = 20
MAX_CONTEXT_MESSAGES = 10
AUTO_MESSAGE_THRESHOLD_MINUTES = 5
CHAT_ACTION_INTERVAL_SECONDS = 4.5


# Retry configuration
STATE_RESOLVER_MAX_RETRIES = 2
DIALOGUE_SPECIALIST_MAX_RETRIES = 3
IMAGE_ENGINEER_MAX_RETRIES = 3
IMAGE_ENGINEER_BASE_DELAY = 1  # seconds, will be exponentially increased


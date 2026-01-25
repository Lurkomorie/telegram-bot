"""
Application settings and configuration loader.
Loads ENV vars, validates YAML/JSON configs against schemas.
"""
import os
import json
import yaml
from pathlib import Path
from typing import Optional, Any
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Environment variables configuration"""
    
    # Telegram
    BOT_TOKEN: str
    WEBHOOK_SECRET: str
    PUBLIC_BASE_URL: Optional[str] = None  # Auto-constructed from RAILWAY_PUBLIC_DOMAIN if not set
    
    # Railway variables
    RAILWAY_PUBLIC_DOMAIN: Optional[str] = None
    RAILWAY_PRIVATE_DOMAIN: Optional[str] = None
    
    # Database
    DATABASE_URL: str
    TEST_DATABASE_URL: Optional[str] = None
    USE_TEST_DB: bool = False
    REDIS_URL: str
    
    # AI Services
    OPENROUTER_API_KEY: str
    RUNPOD_API_KEY_POD: str
    RUNPOD_ENDPOINT: str
    
    # ElevenLabs TTS
    ELEVENLABS_API_KEY: Optional[str] = None
    ELEVENLABS_VOICE_ID: str = "BpjGufoPiobT79j2vtj4"  # Priyanka voice
    ELEVENLABS_MODEL_ID: str = "eleven_v3"
    
    # Security
    IMAGE_CALLBACK_SECRET: str
    
    # Cloudflare (for analytics image storage)
    CLOUDFLARE_API_TOKEN: Optional[str] = None
    CLOUDFLARE_ACCOUNT_ID: Optional[str] = None
    CLOUDFLARE_ACCOUNT_HASH: Optional[str] = None
    
    # Langfuse (observability/tracing)
    LANGFUSE_SECRET_KEY: Optional[str] = None
    LANGFUSE_PUBLIC_KEY: Optional[str] = None
    LANGFUSE_BASE_URL: Optional[str] = None
    
    # App
    ENV: str = "production"
    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: Optional[str] = "production"  # For verbose logging (development/dev/local or production)
    SERVE_LOCAL_STATIC: bool = True
    
    # Frontend base URLs (CDN/Pages)
    MINIAPP_BASE_URL: Optional[str] = None
    ANALYTICS_BASE_URL: Optional[str] = None
    
    # Upload storage
    UPLOADS_BACKEND: str = "local"  # local | r2
    R2_ACCESS_KEY_ID: Optional[str] = None
    R2_SECRET_ACCESS_KEY: Optional[str] = None
    R2_BUCKET_NAME: Optional[str] = None
    R2_ENDPOINT_URL: Optional[str] = None
    R2_PUBLIC_BASE_URL: Optional[str] = None
    R2_SIGNED_URLS: bool = True
    R2_URL_EXPIRES_SECONDS: int = 3600
    R2_UPLOADS_PREFIX: str = "uploads"
    
    # Feature flags
    ENABLE_BOT: bool = True  # Set to False to disable bot (useful for local testing of APIs)
    ENABLE_FOLLOWUPS: bool = True  # Set to False to disable auto follow-up messages
    ENABLE_IMAGES_IN_FOLLOWUP: bool = False  # Set to True to generate images during 30min auto follow-ups
    ENABLE_IMAGES_24HOURS: bool = False  # Set to True to generate images during 24h re-engagement follow-ups
    ENABLE_IMAGES_3DAYS: bool = False  # Set to True to generate images during 3day re-engagement follow-ups
    SERVICE_UNAVAILABLE: bool = False  # Set to True to show maintenance message to users
    FORCE_IMAGES_ALWAYS: bool = False  # Debug flag to force images every message (bypasses AI decision)
    CONCURRENT_IMAGE_LIMIT_ENABLED: bool = False  # Set to True to enable concurrent image limit per user
    CONCURRENT_IMAGE_LIMIT_NUMBER: int = 2  # Maximum number of images a user can generate simultaneously (only if CONCURRENT_IMAGE_LIMIT_ENABLED=True)
    SIMULATE_PAYMENTS: bool = False  # Set to True to simulate successful payments in development (no real Telegram Stars charged)

    # CORS
    CORS_ALLOW_ORIGINS: Optional[str] = None  # Comma-separated origins
    ENABLE_EGRESS_LOGGING: bool = False
    
    # Notifications
    PAYMENT_NOTIFICATION_CHAT_ID: Optional[int] = None  # Telegram group/channel ID for payment notifications
    
    # Testing/Development
    FOLLOWUP_TEST_USERS: Optional[str] = None  # Comma-separated user IDs to restrict followups to (e.g., "123456,789012")
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    @property
    def public_url(self) -> str:
        """Get public URL, auto-construct from Railway domain if needed"""
        if self.PUBLIC_BASE_URL:
            return self.PUBLIC_BASE_URL
        elif self.RAILWAY_PUBLIC_DOMAIN:
            return f"https://{self.RAILWAY_PUBLIC_DOMAIN}"
        else:
            raise ValueError("Either PUBLIC_BASE_URL or RAILWAY_PUBLIC_DOMAIN must be set")

    @property
    def miniapp_url(self) -> str:
        """Get Mini App URL (external base if configured)."""
        if self.MINIAPP_BASE_URL:
            return self.MINIAPP_BASE_URL.rstrip("/")
        return f"{self.public_url}/miniapp"

    @property
    def analytics_url(self) -> Optional[str]:
        """Get Analytics URL (external base if configured)."""
        if self.ANALYTICS_BASE_URL:
            return self.ANALYTICS_BASE_URL.rstrip("/")
        return f"{self.public_url}/analytics"

    @property
    def cors_allow_origins(self) -> list[str]:
        if not self.CORS_ALLOW_ORIGINS:
            return []
        return [origin.strip() for origin in self.CORS_ALLOW_ORIGINS.split(",") if origin.strip()]
    
    @property
    def followup_test_user_ids(self) -> Optional[list[int]]:
        """Parse comma-separated test user IDs for followup whitelist"""
        if not self.FOLLOWUP_TEST_USERS:
            return None
        try:
            return [int(uid.strip()) for uid in self.FOLLOWUP_TEST_USERS.split(',') if uid.strip()]
        except ValueError:
            print(f"⚠️  Warning: Invalid FOLLOWUP_TEST_USERS format: {self.FOLLOWUP_TEST_USERS}")
            return None
    
    @property
    def active_database_url(self) -> str:
        """Get the active database URL based on USE_TEST_DB flag"""
        if self.USE_TEST_DB and self.TEST_DATABASE_URL:
            print("🔄 Using TEST database")
            return self.TEST_DATABASE_URL
        print("📊 Using MAIN database")
        return self.DATABASE_URL


# Global settings instance
settings = Settings()

# Config storage
_app_config: Optional[dict] = None
_ui_texts: Optional[dict] = None


def get_config_path(filename: str) -> Path:
    """Get absolute path to config file"""
    base = Path(__file__).parent.parent
    return base / "config" / filename


def load_configs():
    """Load and validate app.yaml and all language-specific ui_texts files at startup"""
    global _app_config, _ui_texts
    
    # Load app.yaml
    app_path = get_config_path("app.yaml")
    with open(app_path, 'r') as f:
        _app_config = yaml.safe_load(f)
    
    # Substitute env vars in YAML (simple ${VAR} replacement)
    _app_config = _substitute_env_vars(_app_config)
    
    print(f"✅ Loaded app.yaml config ({len(_app_config)} keys)")
    
    # Load all language-specific UI text files
    supported_languages = ['en', 'ru']
    _ui_texts = {}
    
    for lang in supported_languages:
        ui_texts_path = get_config_path(f"ui_texts_{lang}.yaml")
        try:
            with open(ui_texts_path, 'r', encoding='utf-8') as f:
                _ui_texts[lang] = yaml.safe_load(f)
            print(f"✅ Loaded ui_texts_{lang}.yaml ({len(_ui_texts[lang])} keys)")
        except FileNotFoundError:
            print(f"⚠️  Warning: ui_texts_{lang}.yaml not found, skipping")
        except Exception as e:
            print(f"⚠️  Warning: Error loading ui_texts_{lang}.yaml: {e}")
    
    # Ensure English is loaded (fallback language)
    if 'en' not in _ui_texts:
        raise RuntimeError("English UI texts (ui_texts_en.yaml) must be present as fallback language")


def _substitute_env_vars(obj):
    """Recursively substitute ${VAR} in config values"""
    if isinstance(obj, dict):
        return {k: _substitute_env_vars(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_substitute_env_vars(item) for item in obj]
    elif isinstance(obj, str) and obj.startswith("${") and obj.endswith("}"):
        var_name = obj[2:-1]
        return os.environ.get(var_name, obj)
    return obj


def get_app_config() -> dict:
    """Get loaded app.yaml config"""
    if _app_config is None:
        raise RuntimeError("Configs not loaded. Call load_configs() first.")
    return _app_config


def get_ui_text(key_path: str, language: str = "en", **kwargs) -> str:
    """
    Get UI text by dot-notation key path in specified language and format with kwargs
    
    Now uses TranslationService for unified translation management.
    
    Examples:
        get_ui_text("welcome.title", language="en")
        get_ui_text("chat_options.title", language="ru", persona_name="Jane")
        get_ui_text("energy.insufficient_description", language="fr", required=5, current=2)
    
    Args:
        key_path: Dot-separated path (e.g., "welcome.title" or "errors.persona_not_found")
        language: Language code (e.g., 'en', 'ru', 'fr', 'de', 'es'), defaults to 'en'
        **kwargs: Format variables to substitute in the text
    
    Returns:
        Formatted text string
    """
    from app.core.translation_service import translation_service
    
    # Normalize language code
    language = language.lower() if language else 'en'
    
    # Get translation from service (with fallback to English)
    text = translation_service.get(key_path, language, fallback=True)
    
    # Format with kwargs if any
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, ValueError) as e:
            # If formatting fails, return unformatted text
            print(f"[UI-TEXT] Warning: Failed to format text '{key_path}': {e}")
            return text
    
    return text


def get_ui_texts() -> dict:
    """Get all loaded UI texts (for debugging or bulk access)"""
    if _ui_texts is None:
        raise RuntimeError("UI texts not loaded. Call load_configs() first.")
    return _ui_texts

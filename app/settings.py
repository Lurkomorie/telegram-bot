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
    REDIS_URL: str
    
    # AI Services
    OPENROUTER_API_KEY: str
    RUNPOD_API_KEY_POD: str
    RUNPOD_ENDPOINT: str = "https://aa9yxd4ap6p47w-8000.proxy.runpod.net/run"
    
    # Security
    IMAGE_CALLBACK_SECRET: str
    
    # Cloudflare (for analytics image storage)
    CLOUDFLARE_API_TOKEN: str
    CLOUDFLARE_ACCOUNT_ID: str
    CLOUDFLARE_ACCOUNT_HASH: str
    
    # App
    ENV: str = "production"
    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: Optional[str] = "production"  # For verbose logging (development/dev/local or production)
    
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
    """Load and validate app.yaml and ui_texts.yaml at startup"""
    global _app_config, _ui_texts
    
    # Load app.yaml
    app_path = get_config_path("app.yaml")
    with open(app_path, 'r') as f:
        _app_config = yaml.safe_load(f)
    
    # Substitute env vars in YAML (simple ${VAR} replacement)
    _app_config = _substitute_env_vars(_app_config)
    
    print(f"✅ Loaded app.yaml config ({len(_app_config)} keys)")
    
    # Load ui_texts.yaml
    ui_texts_path = get_config_path("ui_texts.yaml")
    with open(ui_texts_path, 'r') as f:
        _ui_texts = yaml.safe_load(f)
    
    print(f"✅ Loaded ui_texts.yaml config ({len(_ui_texts)} keys)")


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


def get_ui_text(key_path: str, **kwargs) -> str:
    """
    Get UI text by dot-notation key path and format with kwargs
    
    Examples:
        get_ui_text("welcome.title")
        get_ui_text("chat_options.title", persona_name="Jane")
        get_ui_text("energy.insufficient_description", required=5, current=2)
    
    Args:
        key_path: Dot-separated path (e.g., "welcome.title" or "errors.persona_not_found")
        **kwargs: Format variables to substitute in the text
    
    Returns:
        Formatted text string
    """
    if _ui_texts is None:
        raise RuntimeError("UI texts not loaded. Call load_configs() first.")
    
    # Navigate through nested dict using dot notation
    keys = key_path.split('.')
    value = _ui_texts
    
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            raise KeyError(f"UI text key not found: {key_path}")
    
    # Format with kwargs if any
    if kwargs and isinstance(value, str):
        return value.format(**kwargs)
    
    return value


def get_ui_texts() -> dict:
    """Get all loaded UI texts (for debugging or bulk access)"""
    if _ui_texts is None:
        raise RuntimeError("UI texts not loaded. Call load_configs() first.")
    return _ui_texts

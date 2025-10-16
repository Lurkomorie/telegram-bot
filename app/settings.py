"""
Application settings and configuration loader.
Loads ENV vars, validates YAML/JSON configs against schemas.
"""
import os
import json
import yaml
from pathlib import Path
from typing import Optional
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
    
    # Admin Panel
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str
    ADMIN_SECRET_KEY: str
    
    # App
    ENV: str = "production"
    LOG_LEVEL: str = "INFO"
    
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


def get_config_path(filename: str) -> Path:
    """Get absolute path to config file"""
    base = Path(__file__).parent.parent
    return base / "config" / filename


def load_configs():
    """Load and validate app.yaml at startup"""
    global _app_config
    
    # Load app.yaml
    app_path = get_config_path("app.yaml")
    with open(app_path, 'r') as f:
        _app_config = yaml.safe_load(f)
    
    # Substitute env vars in YAML (simple ${VAR} replacement)
    _app_config = _substitute_env_vars(_app_config)
    
    print(f"✅ Loaded app.yaml config ({len(_app_config)} keys)")


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



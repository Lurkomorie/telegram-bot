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
    PUBLIC_BASE_URL: str
    
    # Database
    DATABASE_URL: str
    REDIS_URL: str
    
    # AI Services
    OPENROUTER_API_KEY: str
    RUNPOD_API_KEY_POD: str
    RUNPOD_ENDPOINT: str = "https://aa9yxd4ap6p47w-8000.proxy.runpod.net/run"
    
    # Security
    IMAGE_CALLBACK_SECRET: str
    
    # App
    ENV: str = "production"
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()

# Config storage
_app_config: Optional[dict] = None
_prompts_config: Optional[dict] = None


def get_config_path(filename: str) -> Path:
    """Get absolute path to config file"""
    base = Path(__file__).parent.parent
    return base / "config" / filename


def load_configs():
    """Load and validate app.yaml and prompts.json at startup"""
    global _app_config, _prompts_config
    
    # Load app.yaml
    app_path = get_config_path("app.yaml")
    with open(app_path, 'r') as f:
        _app_config = yaml.safe_load(f)
    
    # Substitute env vars in YAML (simple ${VAR} replacement)
    _app_config = _substitute_env_vars(_app_config)
    
    # Load prompts.json
    prompts_path = get_config_path("prompts.json")
    with open(prompts_path, 'r') as f:
        _prompts_config = json.load(f)
    
    # TODO: Validate against JSON schemas
    print(f"✅ Loaded configs: app.yaml ({len(_app_config)} keys), prompts.json ({len(_prompts_config['personas'])} personas)")


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


def get_prompts_config() -> dict:
    """Get loaded prompts.json config"""
    if _prompts_config is None:
        raise RuntimeError("Configs not loaded. Call load_configs() first.")
    return _prompts_config



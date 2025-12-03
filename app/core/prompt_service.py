"""
Centralized prompt management service with Langfuse integration.
Fetches prompts from Langfuse Prompt Management with fallback to local prompts.
"""
from config.prompts import (
    CHAT_GPT,
    IMAGE_TAG_GENERATOR_GPT,
    CONVERSATION_STATE_GPT,
    MEMORY_EXTRACTOR_GPT,
    IMAGE_DECISION_GPT
)
from app.core.langfuse_client import get_prompt as langfuse_get_prompt


# Mapping of prompt names to Langfuse names and local fallbacks
_PROMPT_CONFIG = {
    "CHAT_GPT": {
        "langfuse_name": "dialogue-specialist",
        "local_fallback": CHAT_GPT,
    },
    "IMAGE_TAG_GENERATOR_GPT": {
        "langfuse_name": "image-prompt-engineer",
        "local_fallback": IMAGE_TAG_GENERATOR_GPT,
    },
    "CONVERSATION_STATE_GPT": {
        "langfuse_name": "state-resolver",
        "local_fallback": CONVERSATION_STATE_GPT,
    },
    "MEMORY_EXTRACTOR_GPT": {
        "langfuse_name": "memory-extractor",
        "local_fallback": MEMORY_EXTRACTOR_GPT,
    },
    "IMAGE_DECISION_GPT": {
        "langfuse_name": "image-decision",
        "local_fallback": IMAGE_DECISION_GPT,
    },
}

# Cache for prompts (to avoid hitting Langfuse on every request)
_prompt_cache = {}
_cache_enabled = True


def clear_prompt_cache():
    """Clear the prompt cache to force refresh from Langfuse"""
    global _prompt_cache  # noqa: PLW0603
    _prompt_cache = {}
    print("[PROMPT] 🗑️  Prompt cache cleared")


def set_cache_enabled(enabled: bool):
    """Enable or disable prompt caching"""
    global _cache_enabled  # noqa: PLW0603
    _cache_enabled = enabled
    if not enabled:
        clear_prompt_cache()
    print(f"[PROMPT] {'✅' if enabled else '⚠️'} Prompt caching {'enabled' if enabled else 'disabled'}")


class PromptService:
    """Centralized prompt management with Langfuse integration"""
    
    @classmethod
    def get(cls, name: str, force_refresh: bool = False) -> str:
        """
        Get prompt by name.
        
        Attempts to fetch from Langfuse first, falls back to local prompt if:
        - Langfuse is not configured
        - Prompt not found in Langfuse
        - Langfuse API error
        
        Args:
            name: Prompt identifier (e.g., "CHAT_GPT", "STATE_RESOLVER_GPT")
            force_refresh: If True, bypass cache and fetch fresh from Langfuse
        
        Returns:
            Prompt string
        
        Raises:
            ValueError: If prompt name is unknown
        """
        config = _PROMPT_CONFIG.get(name)
        if not config:
            raise ValueError(f"Unknown prompt: {name}")
        
        # Check cache first (unless force_refresh)
        if _cache_enabled and not force_refresh and name in _prompt_cache:
            return _prompt_cache[name]
        
        # Try Langfuse first
        langfuse_name = config["langfuse_name"]
        local_fallback = config["local_fallback"]
        
        prompt = langfuse_get_prompt(
            name=langfuse_name,
            fallback=local_fallback
        )
        
        # If we got the prompt from Langfuse, log it
        if prompt != local_fallback:
            print(f"[PROMPT] 📡 Fetched '{name}' from Langfuse (name: {langfuse_name})")
        
        # Cache the prompt
        if _cache_enabled:
            _prompt_cache[name] = prompt
        
        return prompt
    
    @classmethod
    def get_local(cls, name: str) -> str:
        """
        Get local prompt only (bypass Langfuse).
        Useful for testing or when you need guaranteed local version.
        """
        config = _PROMPT_CONFIG.get(name)
        if not config:
            raise ValueError(f"Unknown prompt: {name}")
        return config["local_fallback"]
    
    @classmethod
    def get_all_names(cls) -> list:
        """Get list of all available prompt names"""
        return list(_PROMPT_CONFIG.keys())
    
    @classmethod
    def get_langfuse_mapping(cls) -> dict:
        """Get mapping of local names to Langfuse names"""
        return {
            name: config["langfuse_name"] 
            for name, config in _PROMPT_CONFIG.items()
        }

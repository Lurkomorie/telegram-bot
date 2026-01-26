"""
Centralized prompt management service
"""
from config.prompts import (
    CHAT_GPT_EN,
    CHAT_GPT_RU,
    IMAGE_TAG_GENERATOR_GPT,
    CONVERSATION_STATE_GPT,
    MEMORY_EXTRACTOR_GPT,
    IMAGE_DECISION_GPT,
    VOICE_PROCESSOR_GPT,
    CONTEXT_SUMMARY_GPT
)


class PromptService:
    """Centralized prompt management"""
    
    _PROMPTS = {
        "CHAT_GPT_EN": CHAT_GPT_EN,
        "CHAT_GPT_RU": CHAT_GPT_RU,
        "IMAGE_TAG_GENERATOR_GPT": IMAGE_TAG_GENERATOR_GPT,
        "CONVERSATION_STATE_GPT": CONVERSATION_STATE_GPT,
        "MEMORY_EXTRACTOR_GPT": MEMORY_EXTRACTOR_GPT,
        "IMAGE_DECISION_GPT": IMAGE_DECISION_GPT,
        "VOICE_PROCESSOR_GPT": VOICE_PROCESSOR_GPT,
        "CONTEXT_SUMMARY_GPT": CONTEXT_SUMMARY_GPT,
    }
    
    # Language-specific prompt mapping
    _LANGUAGE_PROMPTS = {
        "CHAT_GPT": {
            "en": "CHAT_GPT_EN",
            "ru": "CHAT_GPT_RU",
        }
    }
    
    @classmethod
    def get(cls, name: str, language: str = "en") -> str:
        """Get prompt by name, optionally selecting language-specific version.
        
        Args:
            name: Prompt name (e.g., "CHAT_GPT", "IMAGE_TAG_GENERATOR_GPT")
            language: Language code (e.g., "en", "ru"). Defaults to "en".
        
        Returns:
            The prompt string, selecting language-specific version if available.
        """
        # Check if this prompt has language-specific versions
        if name in cls._LANGUAGE_PROMPTS:
            lang_mapping = cls._LANGUAGE_PROMPTS[name]
            # Get the language-specific prompt name, defaulting to English
            prompt_name = lang_mapping.get(language, lang_mapping.get("en"))
            prompt = cls._PROMPTS.get(prompt_name)
            if prompt:
                return prompt
        
        # Fall back to direct lookup
        prompt = cls._PROMPTS.get(name)
        if not prompt:
            raise ValueError(f"Unknown prompt: {name}")
        return prompt



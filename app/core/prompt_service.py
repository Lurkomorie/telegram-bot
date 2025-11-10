"""
Centralized prompt management service
"""
from config.prompts import (
    CHAT_GPT,
    IMAGE_TAG_GENERATOR_GPT,
    CONVERSATION_STATE_GPT,
    MEMORY_EXTRACTOR_GPT,
    IMAGE_DECISION_GPT
)


class PromptService:
    """Centralized prompt management"""
    
    _PROMPTS = {
        "CHAT_GPT": CHAT_GPT,
        "IMAGE_TAG_GENERATOR_GPT": IMAGE_TAG_GENERATOR_GPT,
        "CONVERSATION_STATE_GPT": CONVERSATION_STATE_GPT,
        "MEMORY_EXTRACTOR_GPT": MEMORY_EXTRACTOR_GPT,
        "IMAGE_DECISION_GPT": IMAGE_DECISION_GPT,
    }
    
    @classmethod
    def get(cls, name: str) -> str:
        """Get prompt by name"""
        prompt = cls._PROMPTS.get(name)
        if not prompt:
            raise ValueError(f"Unknown prompt: {name}")
        return prompt



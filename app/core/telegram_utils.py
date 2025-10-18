"""
Telegram-specific utility functions
"""
import re


def escape_markdown_v2(text: str) -> str:
    """
    Escape special characters for Telegram MarkdownV2 while preserving formatting.
    
    This function:
    - Converts literal \n to actual newlines
    - Preserves *bold* and _italic_ markdown formatting
    - Escapes special characters: [ ] ( ) ~ ` > # + - = | { } . !
    - Does NOT escape * and _ as they're used for formatting
    """
    if not text:
        return text
    
    # Convert literal \n to actual newlines
    text = text.replace('\\n', '\n')
    
    # Characters that need escaping (excluding * and _ which are used for formatting)
    special_chars = ['[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    
    return text


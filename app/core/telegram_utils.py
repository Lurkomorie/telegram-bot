"""
Telegram-specific utility functions
"""


def escape_markdown_v2(text: str) -> str:
    """
    Escape special characters for Telegram MarkdownV2 while preserving formatting.
    
    This function:
    - Converts literal \n to actual newlines
    - Validates and balances *bold* and _italic_ markdown formatting
    - Escapes special characters: [ ] ( ) ~ ` > # + - = | { } . !
    - Strips unbalanced formatting to prevent Telegram errors
    """
    if not text:
        return text
    
    # Convert literal \n to actual newlines
    text = text.replace('\\n', '\n')
    
    # Balance markdown formatting to prevent Telegram parsing errors
    text = _balance_markdown(text)
    
    # Characters that need escaping (excluding * and _ which are used for formatting)
    special_chars = ['[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    
    return text


def _balance_markdown(text: str) -> str:
    """
    Balance markdown formatting by ensuring all * and _ have matching pairs.
    If they don't match, strip them entirely to prevent Telegram errors.
    """
    # Count asterisks and underscores
    asterisk_count = text.count('*')
    underscore_count = text.count('_')
    
    # If unbalanced, strip all formatting
    if asterisk_count % 2 != 0:
        # Remove all asterisks to prevent unbalanced bold
        text = text.replace('*', '')
    
    if underscore_count % 2 != 0:
        # Remove all underscores to prevent unbalanced italic
        text = text.replace('_', '')
    
    return text


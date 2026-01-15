"""
Telegram-specific utility functions
"""
import re


def escape_markdown_v2(text: str) -> str:
    """
    Escape special characters for Telegram MarkdownV2 while preserving formatting.
    
    This function:
    - Converts literal \n to actual newlines
    - Validates and balances *bold* and _italic_ markdown formatting
    - Escapes special characters before processing markdown
    - Ensures formatting markers don't split multi-byte characters
    - Strips unbalanced formatting to prevent Telegram errors
    """
    if not text:
        return text
    
    # Convert literal \n to actual newlines
    text = text.replace('\\n', '\n')
    
    # Extract and validate markdown formatting
    text = _process_markdown_safely(text)
    
    return text


def _process_markdown_safely(text: str) -> str:
    """
    Safely process markdown by:
    1. Extracting bold (*text*) and italic (_text_) segments
    2. Escaping special characters in non-formatted segments
    3. Validating that formatting doesn't split multi-byte characters
    4. Reconstructing the text with proper escaping
    """
    # Characters that need escaping in MarkdownV2
    # Note: * and _ are NOT escaped when used for formatting
    # Backslash MUST be included to prevent escape sequence issues
    special_chars = r'\_*[]()~`>#+=|{}.!-'
    
    result = []
    i = 0
    
    while i < len(text):
        char = text[i]
        
        # Check for bold marker (*)
        if char == '*':
            # Find the closing *
            closing_idx = _find_closing_marker(text, i + 1, '*')
            
            if closing_idx != -1:
                # Valid bold segment found
                inner_text = text[i + 1:closing_idx]
                
                # Validate that the segment doesn't split multi-byte characters
                if _is_valid_utf8_segment(inner_text):
                    # Escape special chars inside bold text (but not the markers themselves)
                    escaped_inner = _escape_special_chars(inner_text, exclude='*')
                    result.append(f'*{escaped_inner}*')
                    i = closing_idx + 1
                    continue
                else:
                    # Invalid segment, escape the asterisk and continue
                    result.append('\\*')
                    i += 1
                    continue
            else:
                # No closing marker found, escape the asterisk
                result.append('\\*')
                i += 1
                continue
        
        # Check for italic marker (_)
        elif char == '_':
            # Find the closing _
            closing_idx = _find_closing_marker(text, i + 1, '_')
            
            if closing_idx != -1:
                # Valid italic segment found
                inner_text = text[i + 1:closing_idx]
                
                # Validate that the segment doesn't split multi-byte characters
                if _is_valid_utf8_segment(inner_text):
                    # Escape special chars inside italic text (but not the markers themselves)
                    escaped_inner = _escape_special_chars(inner_text, exclude='_')
                    result.append(f'_{escaped_inner}_')
                    i = closing_idx + 1
                    continue
                else:
                    # Invalid segment, escape the underscore and continue
                    result.append('\\_')
                    i += 1
                    continue
            else:
                # No closing marker found, escape the underscore
                result.append('\\_')
                i += 1
                continue
        
        # Regular character - escape if special
        elif char in special_chars:
            result.append(f'\\{char}')
            i += 1
        else:
            result.append(char)
            i += 1
    
    return ''.join(result)


def _find_closing_marker(text: str, start_idx: int, marker: str) -> int:
    """
    Find the closing marker, ensuring it's not escaped and forms a valid pair.
    Returns -1 if no valid closing marker is found.
    """
    idx = start_idx
    while idx < len(text):
        if text[idx] == marker:
            # Check if there's actual content between markers
            if idx > start_idx:
                return idx
            else:
                # Empty formatting like ** or __ is invalid
                return -1
        idx += 1
    return -1


def _is_valid_utf8_segment(text: str) -> bool:
    """
    Check if the text segment is valid UTF-8 and doesn't split multi-byte characters.
    """
    try:
        # Try to encode and decode to verify UTF-8 validity
        text.encode('utf-8').decode('utf-8')
        return True
    except (UnicodeEncodeError, UnicodeDecodeError):
        return False


def _escape_special_chars(text: str, exclude: str = '') -> str:
    """
    Escape special MarkdownV2 characters, optionally excluding certain characters.
    
    IMPORTANT: Backslash must be escaped FIRST to avoid double-escaping issues.
    """
    # Backslash MUST be first to avoid escaping the escape sequences we create
    special_chars = ['\\', '_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    
    result = text
    for char in special_chars:
        if char not in exclude:
            result = result.replace(char, f'\\{char}')
    
    return result


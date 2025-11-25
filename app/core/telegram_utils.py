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
    - Escapes special characters: [ ] ( ) ~ ` > # + - = | { } . !
    - Strips unbalanced formatting to prevent Telegram errors
    
    Process order:
    1. Convert literal newlines
    2. Balance markdown (remove unbalanced formatting)
    3. Escape special chars INSIDE text (not inside markdown markers)
    4. Return the properly formatted text
    """
    if not text:
        return text
    
    # Convert literal \n to actual newlines
    text = text.replace('\\n', '\n')
    
    # Balance markdown formatting to prevent Telegram parsing errors
    text = _balance_markdown(text)
    
    # Escape special characters while preserving markdown
    text = _escape_special_chars_preserve_markdown(text)
    
    return text


def _balance_markdown(text: str) -> str:
    """
    Balance markdown formatting by ensuring all * and _ have proper matching pairs.
    
    For MarkdownV2:
    - *text* = bold (must not contain spaces at boundaries)
    - _text_ = italic (must not contain spaces at boundaries)
    - Markdown cannot span across certain boundaries improperly
    
    If markers are unbalanced or improperly formatted, strip them entirely.
    """
    # Process asterisks (bold)
    text = _balance_marker(text, '*')
    
    # Process underscores (italic)  
    text = _balance_marker(text, '_')
    
    return text


def _balance_marker(text: str, marker: str) -> str:
    """
    Balance a specific markdown marker (* or _).
    
    Strategy:
    1. Find all occurrences of the marker
    2. Validate that they form proper pairs (no leading/trailing spaces inside)
    3. If count is odd or formatting is invalid, remove all markers
    
    Valid MarkdownV2 formatting rules:
    - Must not start with space after opening marker
    - Must not end with space before closing marker
    - Must contain at least one character between markers
    """
    count = text.count(marker)
    
    # If odd count, definitely unbalanced - strip all
    if count % 2 != 0:
        return text.replace(marker, '')
    
    # If no markers, nothing to do
    if count == 0:
        return text
    
    # If even count, check if they form valid pairs
    # Valid pair: marker + non-space + (text without trailing space) + marker
    # This regex finds potentially valid formatted segments
    # Pattern: marker, then non-whitespace, then any chars (non-greedy), then non-whitespace, then marker
    pattern = re.escape(marker) + r'([^\s' + re.escape(marker) + r'](?:[^' + re.escape(marker) + r']*[^\s' + re.escape(marker) + r'])?)' + re.escape(marker)
    
    # Find all valid pairs
    valid_pairs = re.findall(pattern, text)
    expected_pairs = count // 2
    
    # If we don't find the expected number of valid pairs, strip all markers
    if len(valid_pairs) != expected_pairs:
        return text.replace(marker, '')
    
    return text


def _escape_special_chars_preserve_markdown(text: str) -> str:
    """
    Escape special MarkdownV2 characters while preserving * and _ for formatting.
    
    Characters to escape: _ * [ ] ( ) ~ ` > # + - = | { } . !
    But we preserve * and _ when they're used for formatting (already validated).
    
    Strategy:
    1. Split text into segments: markdown-formatted and plain text
    2. Escape special chars only in plain text segments
    3. Reassemble
    """
    # Characters that always need escaping (excluding * and _ which are formatting)
    always_escape = ['[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    
    # Find all markdown formatted segments: *text* or _text_
    # We'll process the text in parts
    result = []
    last_end = 0
    
    # Find all bold (*) and italic (_) segments
    # Pattern: (marker)(non-space)(anything)(marker)
    markdown_pattern = r'([*_])([^\s\1][^\1]*?)\1'
    
    for match in re.finditer(markdown_pattern, text):
        # Add plain text before this match (with escaping)
        plain_text = text[last_end:match.start()]
        escaped_plain = plain_text
        for char in always_escape:
            escaped_plain = escaped_plain.replace(char, f'\\{char}')
        result.append(escaped_plain)
        
        # Add the markdown segment
        # Escape special chars INSIDE the markdown but keep the markers
        marker = match.group(1)
        content = match.group(2)
        
        # Escape special chars in the content
        for char in always_escape:
            content = content.replace(char, f'\\{char}')
        
        result.append(f'{marker}{content}{marker}')
        last_end = match.end()
    
    # Add remaining plain text
    plain_text = text[last_end:]
    escaped_plain = plain_text
    for char in always_escape:
        escaped_plain = escaped_plain.replace(char, f'\\{char}')
    result.append(escaped_plain)
    
    return ''.join(result)


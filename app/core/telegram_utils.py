"""
Telegram-specific utility functions
"""
import re


def normalize_roleplay_layout(text: str) -> str:
    """Give every action and every spoken line its own paragraph.

    The model alternates freely — sometimes it writes one tidy block per beat,
    sometimes it strings "*speech* _action_ *speech*" onto a single line, which
    is where readers lose track of what she actually said. It also closes a
    segment with the wrong marker now and then (`_action.*`), which turns the
    whole reply into one broken run. Both are fixed here rather than hoped away
    in the prompt, so the layout is the same on every message.
    """
    if not text:
        return text

    text = text.replace("\r\n", "\n")

    # Repair a segment opened with one marker and closed with the other.
    text = re.sub(r"_([^_*\n]{2,}?)\*", r"_\1_", text)
    text = re.sub(r"\*([^_*\n]{2,}?)_(?=\s|$)", r"*\1*", text)

    # Split the reply into its action / speech segments, in order. The two
    # unterminated alternatives keep a trailing "*she said…" marked as speech
    # instead of silently demoting it to plain text.
    segments = []
    for raw in re.findall(r"_[^_]+_|\*[^*]+\*|_[^_]*$|\*[^*]*$|[^_*]+", text):
        chunk = raw.strip()
        if chunk:
            segments.append(chunk)

    # A trailing unclosed segment ("*Take me…" with no closer) keeps its marker.
    fixed = []
    for seg in segments:
        if seg.startswith("_") and not seg.endswith("_") and len(seg) > 1:
            seg += "_"
        elif seg.startswith("*") and not seg.endswith("*") and len(seg) > 1:
            seg += "*"
        fixed.append(seg)

    return "\n\n".join(fixed).strip()


async def send_roleplay_reply(bot, chat_id: int, text: str) -> None:
    """Send a reply as two messages: what she does, then what she says.

    Two bubbles arriving back to back read like someone reacting and then
    answering, instead of one narrated paragraph. Falls back to a single
    message when the reply is all action or all speech.
    """
    actions, speech = split_action_and_speech(text)
    parts = [p for p in (actions, speech) if p]
    if not parts:
        parts = [text]
    for part in parts:
        await bot.send_message(chat_id, escape_markdown_v2(part), parse_mode="MarkdownV2")


def split_action_and_speech(text: str) -> tuple:
    """Split a reply into what she does and what she says, in that order.

    Sent as two consecutive messages this reads like a real person: the room
    moves first, then she answers. Segments keep their original order inside
    each part, so an alternating reply still tells its story straight.

    Returns (actions, speech); either side may be empty, in which case the
    caller should send only the other one.
    """
    if not text:
        return "", ""

    layout = normalize_roleplay_layout(text)
    actions, speech = [], []
    for block in layout.split("\n\n"):
        block = block.strip()
        if not block:
            continue
        if block.startswith("*") and block.endswith("*"):
            speech.append(block)
        elif block.startswith("_") and block.endswith("_"):
            actions.append(block)
        else:
            # Unmarked prose is narration unless she has already started talking.
            (speech if speech else actions).append(block)

    return "\n\n".join(actions).strip(), "\n\n".join(speech).strip()


def format_roleplay_reply(text: str) -> str:
    """Lay out a roleplay reply, then escape it for Telegram.

    Use this for anything the character says; plain system copy should keep
    calling escape_markdown_v2 directly so its own line breaks survive.
    """
    return escape_markdown_v2(normalize_roleplay_layout(text))


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


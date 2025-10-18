# History Description Feature Implementation

## Overview

Added support for scene-setting descriptions to persona history starts. These descriptions appear before the greeting message, formatted in italic using Telegram MarkdownV2, and are stored as system messages in the database for context in AI conversations.

## Changes Made

### 1. Database Schema Updates

#### Model Changes (`app/db/models.py`)

- Added `description` field to `PersonaHistoryStart` model
- Field type: `Text`, nullable
- Purpose: Store scene-setting descriptions that appear before greeting messages

#### Migration (`app/db/migrations/versions/005_add_history_description.py`)

- Created migration to add `description` column to `persona_history_starts` table
- Migration ID: 005
- Status: ✅ Successfully applied

### 2. Handler Updates (`app/bot/handlers/start.py`)

#### Functionality Added

1. **Extract Description**: When selecting a persona, extracts description from history start if available
2. **Save as System Message**: Stores description as a system message in the database with role="system"
3. **Format for Telegram**: Escapes special characters for MarkdownV2 and wraps in underscores for italic formatting
4. **Send to User**: Sends description before the greeting message

#### Helper Function

```python
def escape_markdown_v2(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2"""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text
```

#### Message Flow

1. Description sent first (if exists) → MarkdownV2 italic format
2. Greeting message sent second → HTML format
3. Both stored in database for AI context

### 3. AI Integration

#### Chat History Inclusion

- System messages (descriptions) are automatically included in chat history
- Sent to AI models alongside user and assistant messages
- Provides context for:
  - State resolution (Brain 1)
  - Dialogue generation (Brain 2)
  - Image prompt engineering (Brain 3)

#### Pipeline Integration (`app/core/multi_brain_pipeline.py`)

- Line 84-88: Chat history extraction includes all message roles (user, assistant, system)
- Descriptions appear in conversation context sent to LLMs

### 4. Seed Script Updates

#### Updated Scripts

1. `scripts/quick_admin_setup.py`
2. `scripts/seed_persona_histories.py`

#### Example Descriptions Added

**Sweet Girlfriend (Mia)**

- "You open your phone to see a notification from Mia. She's sitting on her cozy couch at home, wearing comfortable pajamas and looking at her phone with a bright smile."
- "It's a quiet evening. Mia has been curled up on her bed, checking her phone every few minutes, hoping to hear from you."

**Tsundere (Rei)**

- "Rei is in her room after school, still in her uniform. She's been pretending not to care, but she's been glancing at her phone all afternoon."
- "It's late afternoon. Rei is sitting by her window, trying to look disinterested, but she's been checking her messages repeatedly."

**Seductive (Scarlett)**

- "You receive a message from Scarlett. She's lounging on a luxurious red velvet couch in her dimly lit apartment, wearing an elegant silk dress."
- "The evening light filters through sheer curtains. Scarlett is relaxing on her bed in comfortable yet alluring loungewear, a playful smile on her lips."

## Usage

### For Developers

#### Adding Descriptions to New History Starts

```python
from app.db.models import PersonaHistoryStart

history = PersonaHistoryStart(
    persona_id=persona.id,
    description="Scene-setting description here...",
    text="Greeting message here...",
    image_url=None
)
db.add(history)
db.commit()
```

#### Telegram Message Format

- **Description**: Sent in italic using `_escaped text_` with MarkdownV2
- **Greeting**: Sent in HTML format as before

### For Users

When selecting a persona:

1. First message appears in _italic_ (description)
2. Second message is the greeting (normal format)
3. Optional image may accompany the greeting

## Technical Details

### Database Structure

```sql
CREATE TABLE persona_history_starts (
    id UUID PRIMARY KEY,
    persona_id UUID REFERENCES personas(id),
    description TEXT,  -- NEW FIELD
    text TEXT NOT NULL,
    image_url TEXT,
    created_at TIMESTAMP
);
```

### Message Roles

- `system`: Scene descriptions, context messages
- `user`: User messages
- `assistant`: AI persona responses

### MarkdownV2 Escaping

Special characters that need escaping: `_*[]()~`>#+\-=|{}.!`

All these characters are escaped with a backslash before sending to Telegram.

## Testing

### Migration Test

```bash
python -m alembic upgrade head
```

✅ Successfully applied migration 005

### Seed Data Test

```bash
python scripts/quick_admin_setup.py
```

✅ Creates personas with descriptions

### Integration Points Verified

- ✅ Database schema updated
- ✅ Messages stored with system role
- ✅ Messages sent in italic format
- ✅ Chat history includes system messages
- ✅ AI receives descriptions in context
- ✅ Seed scripts updated with examples

## Future Enhancements

### Potential Additions

1. Admin panel UI for editing descriptions
2. Rich formatting support (bold, links, etc.)
3. Multiple descriptions per language/locale
4. Dynamic description generation based on time of day
5. User preference for showing/hiding descriptions

## Files Modified

1. `app/db/models.py` - Added description field
2. `app/db/migrations/versions/005_add_history_description.py` - New migration
3. `app/bot/handlers/start.py` - Handler updates for description flow
4. `scripts/quick_admin_setup.py` - Added example descriptions
5. `scripts/seed_persona_histories.py` - Added example descriptions

## Compatibility

- ✅ Backward compatible (description is nullable)
- ✅ Existing history starts work without descriptions
- ✅ No breaking changes to API or handlers
- ✅ Gracefully handles missing descriptions

## Notes

- Descriptions are optional (nullable field)
- If no description exists, only greeting is sent
- MarkdownV2 format only for descriptions
- HTML format maintained for greetings
- System messages appear in AI context automatically

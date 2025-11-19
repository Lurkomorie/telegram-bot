# Persona Translations Implementation Guide

## ✅ Implementation Complete

The persona translation system is now fully implemented with separate database tables for translations.

## 🗄️ Database Schema

### Tables Created

1. **`persona_translations`** - Translations for persona descriptions
   - `persona_id` (FK to personas)
   - `language` (en, ru, fr, de, es)
   - `description` - Full description
   - `small_description` - One-liner for selection menu
   - `intro` - Introduction/greeting message
   - Unique constraint on (persona_id, language)

2. **`persona_history_translations`** - Translations for story descriptions
   - `history_id` (FK to persona_history_starts)
   - `language` (en, ru, fr, de, es)
   - `name` - Story name
   - `small_description` - Short story description
   - `description` - Scene-setting description
   - `text` - Greeting message
   - Unique constraint on (history_id, language)

## 📦 How It Works

### 1. Cache Loading
The persona cache (`app/core/persona_cache.py`) now loads all translations at startup:
```python
persona_dict["translations"] = {
    "ru": {
        "description": "...",
        "small_description": "...",
        "intro": "..."
    },
    "fr": {...},
    # etc
}
```

### 2. Translation Retrieval
Use helper functions to get translated content:
```python
from app.core.persona_cache import get_persona_field, get_history_field

# Get translated persona description
desc = get_persona_field(persona_dict, 'small_description', language='ru')

# Get translated history greeting
greeting = get_history_field(history_dict, 'text', language='fr')
```

### 3. Automatic Fallback
- If translation doesn't exist for requested language → fallback to English
- If field is None in translation → fallback to English
- Always graceful, never crashes

## 📝 Adding Translations

### Method 1: Using the Seeding Script

Edit `scripts/seed_persona_translations.py` and add your translations:

```python
PERSONA_TRANSLATIONS = {
    "your_persona_key": {
        "ru": {
            "small_description": "Краткое описание",
            "description": "Полное описание персонажа...",
            "intro": "Привет! Приятно познакомиться!"
        },
        "fr": {
            "small_description": "Brève description",
            "description": "Description complète du personnage...",
            "intro": "Salut ! Ravi de te rencontrer !"
        },
        "de": {...},
        "es": {...}
    }
}

HISTORY_TRANSLATIONS = {
    "your_persona_key": {
        0: {  # First story (index 0)
            "ru": {
                "name": "Название истории",
                "small_description": "Краткое описание",
                "description": "Описание сцены...",
                "text": "Приветственное сообщение..."
            }
        }
    }
}
```

Then run:
```bash
python3 scripts/seed_persona_translations.py
```

### Method 2: Direct Database Insert

```sql
-- Insert persona translation
INSERT INTO persona_translations (persona_id, language, description, small_description, intro)
VALUES (
    '12345678-1234-1234-1234-123456789012',  -- persona UUID
    'ru',
    'Полное описание на русском',
    'Краткое описание',
    'Привет! Я рада тебя видеть!'
);

-- Insert history translation
INSERT INTO persona_history_translations (history_id, language, name, small_description, description, text)
VALUES (
    '87654321-4321-4321-4321-210987654321',  -- history UUID
    'ru',
    'Название истории',
    'Краткое описание истории',
    'Описание сцены...',
    'Приветственное сообщение персонажа...'
);
```

### Method 3: Python Script (Programmatic)

```python
from app.db.base import get_db
from app.db import crud

with get_db() as db:
    # Get persona by key
    persona = crud.get_persona_by_key(db, "your_persona_key")
    
    if persona:
        # Add Russian translation
        crud.create_or_update_persona_translation(
            db,
            persona_id=persona.id,
            language='ru',
            small_description='Краткое описание',
            description='Полное описание персонажа на русском',
            intro='Привет! Рада тебя видеть!'
        )
```

## 🔄 Cache Updates

After adding/updating translations:

1. **Restart the bot** - Translations are loaded at startup into memory cache
2. OR **Reload cache programmatically** (if you have a reload endpoint)

## 🌍 Where Translations Are Used

### Telegram Bot
- ✅ Persona selection menu (`/start`) - shows translated `small_description`
- ✅ Story selection menu - shows translated story `name` and `small_description`
- ✅ Greeting messages - uses translated `text` from history
- ✅ Scene descriptions - uses translated `description` from history
- ✅ All automatically match user's Telegram language setting

### Mini App
- ✅ Persona gallery (`/api/miniapp/personas`) - returns translated descriptions
- ✅ History selection (`/api/miniapp/personas/{id}/histories`) - returns translated story info
- ✅ Automatically detects user language from Telegram Web App init data

## 📋 Important Notes

### What IS Translated
- ✅ Persona descriptions (full and short)
- ✅ Persona intro messages
- ✅ Story names
- ✅ Story descriptions (short and scene-setting)
- ✅ Story greeting messages

### What is NOT Translated
- ❌ Persona names (kept in original language - character names are universal)
- ❌ Persona keys (internal identifiers)
- ❌ Image URLs (images are language-independent)

## 🚀 Current Status

- ✅ Database tables created
- ✅ ORM models added
- ✅ CRUD functions implemented
- ✅ Cache loading with translations
- ✅ Helper functions for translated content
- ✅ Telegram bot handlers updated
- ✅ Mini App API updated
- ✅ Migrations applied to database
- ⏳ Translations need to be added to database (use seeding script)

## 📊 Performance

- **Cache-based**: All translations loaded at startup (O(1) lookup)
- **No runtime DB calls**: Translations served from memory
- **Minimal overhead**: ~5-10KB per persona across all languages
- **Fallback**: Always graceful degradation to English

## 🔧 Troubleshooting

### Translations not showing?
1. Check if translations exist in database: `SELECT * FROM persona_translations WHERE language = 'ru';`
2. Restart bot to reload cache
3. Verify user language is set: `SELECT id, locale FROM users WHERE id = YOUR_USER_ID;`
4. Check logs for cache loading: Look for `[CACHE] 🌐 Loaded X persona translations`

### Database out of sync?
Run migrations:
```bash
alembic upgrade head
```

### Need to update translations?
1. Update via seeding script
2. OR update database directly
3. Restart bot to reload cache


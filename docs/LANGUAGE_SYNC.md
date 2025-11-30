# Language Synchronization System

## Overview

This document explains how language detection and synchronization works between the Telegram bot and miniapp to ensure consistency.

## Translation Storage

**Source of Truth**: JSON files in [`config/translations/`](../config/translations/)

- [`config/translations/en.json`](../config/translations/en.json) - English translations
- [`config/translations/ru.json`](../config/translations/ru.json) - Russian translations

These files contain:

- UI texts (buttons, messages, errors)
- Persona names and descriptions
- History scenario texts

**Miniapp**: Uses its own copies at [`miniapp/src/locales/en.json`](../miniapp/src/locales/en.json) and [`ru.json`](../miniapp/src/locales/ru.json)

## Language Detection Flow

### Telegram Bot

**File**: [`app/bot/handlers/start.py`](../app/bot/handlers/start.py) - `get_and_update_user_language()`

1. User sends `/start` or any message
2. System extracts `telegram_user.language_code` from Telegram API
3. Calls [`app/db/crud.py`](../app/db/crud.py) `get_or_create_user()` with language code
4. Database logic (lines 119-122):
   ```python
   # Only update locale from Telegram if NOT manually set
   if normalized_locale and user.locale != normalized_locale and not user.locale_manually_set:
       user.locale = normalized_locale
   ```
5. Returns `user.locale` for rendering UI texts

**Key Point**: Bot respects `locale_manually_set` flag. If user manually changed language in miniapp, bot won't override it.

### Miniapp

**File**: [`miniapp/src/i18n/TranslationContext.jsx`](../miniapp/src/i18n/TranslationContext.jsx) - `initializeLanguage()`

1. User opens miniapp
2. Priority order:
   - First: `localStorage.getItem('manualLanguageOverride')` (set when user changes language in settings)
   - Second: `WebApp.initDataUnsafe?.user?.language_code` from Telegram
   - Third: Cached `localStorage.getItem('userLanguage')`
   - Default: `'en'`
3. Calls API `/api/miniapp/user/language` to get/sync with database
4. Backend returns `user.locale` from database
5. Uses this language to render UI

**Key Point**: Manual language selection is stored in localStorage AND database.

## Language Change Behavior

### User Changes Language in Miniapp Settings

**File**: [`app/api/miniapp.py`](../app/api/miniapp.py) - `/api/miniapp/user/update-language` endpoint

When user selects a language in miniapp settings:

```python
user.locale = request.language
user.locale_manually_set = True  # Mark as manually set
```

**Result**:

- ✅ Miniapp immediately uses new language
- ✅ Database stores `locale` and sets `locale_manually_set=True`
- ✅ Bot will use same language (reads from `user.locale`)
- ✅ Future Telegram language changes WON'T override this choice

### User Changes Telegram App Language

When user changes their phone/Telegram language:

1. Next time they interact with bot, `telegram_user.language_code` is different
2. Bot checks `locale_manually_set` flag
3. If `True`: **No change** (respects manual choice)
4. If `False`: **Updates** to new Telegram language

### User Clears Browser Data

If user clears localStorage:

1. Miniapp loses `manualLanguageOverride` flag
2. Falls back to checking API `/api/miniapp/user/language`
3. Gets `user.locale` from database (still correct)
4. Syncs with database value

## Consistency Matrix

| User Action             | Bot Language   | Miniapp Language | Database State                             |
| ----------------------- | -------------- | ---------------- | ------------------------------------------ |
| New user (Telegram: ru) | ru (auto)      | ru (auto)        | `locale='ru'`, `locale_manually_set=False` |
| Change to en in miniapp | en (from DB)   | en (manual)      | `locale='en'`, `locale_manually_set=True`  |
| Change phone to fr      | en (no change) | en (no change)   | `locale='en'`, `locale_manually_set=True`  |
| Clear localStorage      | en (from DB)   | en (from DB)     | `locale='en'`, `locale_manually_set=True`  |

## Database Schema

**Table**: `users`

```sql
locale VARCHAR(10) DEFAULT 'en'  -- User's current language
locale_manually_set BOOLEAN DEFAULT FALSE  -- True if user manually selected language in miniapp
```

## Translation Service

**File**: [`app/core/translation_service.py`](../app/core/translation_service.py)

- Loads translations from JSON files at startup
- Caches in memory for fast access
- API: `translation_service.get(key, lang, fallback=True)`
- Example: `translation_service.get("welcome.title", "ru")`

## Persona Translations

**File**: [`app/core/persona_cache.py`](../app/core/persona_cache.py)

Functions:

- `get_persona_field(persona_dict, field, language)` - Get translated persona field
- `get_history_field(history_dict, field, language)` - Get translated history field

Translation keys:

- Personas: `{persona.key}.name`, `{persona.key}.description`
- Histories: `{persona.key}.history.name-{index}`, `{persona.key}.history.text-{index}`

Example:

```python
from app.core.persona_cache import get_persona_field

name = get_persona_field(persona, 'name', language='ru')
# Looks up "airi.name" in ru.json
```

## Testing Scenarios

### Scenario 1: New User

1. User with Telegram language=ru opens bot
2. Expected: Bot shows Russian text
3. User opens miniapp
4. Expected: Miniapp shows Russian text

### Scenario 2: Language Change

1. User changes language to English in miniapp settings
2. Expected: Miniapp immediately switches to English
3. User sends message to bot
4. Expected: Bot responds in English
5. User checks persona names
6. Expected: Persona names in English

### Scenario 3: Telegram Language Change (After Manual Override)

1. User has manually selected English in miniapp
2. User changes phone language to Russian
3. User interacts with bot
4. Expected: Bot STAYS in English (respects manual choice)
5. Expected: Miniapp STAYS in English

## Troubleshooting

### Bot and Miniapp Show Different Languages

**Check**:

1. Database: `SELECT id, locale, locale_manually_set FROM users WHERE id=<user_id>`
2. Miniapp localStorage: Open DevTools → Application → Local Storage → Check `manualLanguageOverride` and `userLanguage`
3. Verify translation files exist: `config/translations/en.json` and `ru.json`

**Common Causes**:

- Race condition during manual language change
- LocalStorage and database out of sync
- Translation service not loaded properly

**Solution**:

- Clear localStorage and reload miniapp
- Or manually update database: `UPDATE users SET locale='en', locale_manually_set=True WHERE id=<user_id>`

### Persona Names Always in English

**Check**:

1. Verify translation keys exist in JSON: Look for `{persona_key}.name` in `config/translations/ru.json`
2. Check if persona cache is loaded: `app.core.persona_cache.is_cache_loaded()`
3. Verify `get_persona_field()` is being called with correct language

**Solution**:

- Run export and merge scripts again to update translations
- Restart service to reload translation cache

## Maintaining Translations

### Adding New Translations

1. Edit JSON files directly:

   - Bot: [`config/translations/en.json`](../config/translations/en.json), [`ru.json`](../config/translations/ru.json)
   - Miniapp: [`miniapp/src/locales/en.json`](../miniapp/src/locales/en.json), [`ru.json`](../miniapp/src/locales/ru.json)

2. Use flat key structure:

   ```json
   {
     "welcome.title": "Welcome to AI Girls",
     "premium.features.energy": "Unlimited energy",
     "airi.name": "Airi",
     "airi.description": "Sweet and caring girlfriend"
   }
   ```

3. Commit changes to git

4. Restart service to reload translations

### Re-syncing From Database

If you need to re-export from database:

```bash
# Export from database
python scripts/export_db_translations.py

# Merge with miniapp JSONs
python scripts/merge_translations.py

# Restart service
# (Railway/production will auto-restart on git push)
```

## Future Improvements

- Add language change notification to bot when changed in miniapp
- Support more languages (fr, de, es)
- Add translation validation script
- Create admin UI for editing translations

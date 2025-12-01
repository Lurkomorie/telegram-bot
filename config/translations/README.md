# Translation Files

This directory contains all translations for the Telegram bot in JSON format.

## Files

- `en.json` - English translations
- `ru.json` - Russian translations

## Structure

The JSON files use a **nested structure** for better organization:

```json
{
  "welcome": {
    "title": "Choose your companion:",
    "subtitle": "Select a character to start chatting"
  },
  "premium": {
    "features": {
      "energy": "Infinite energy",
      "ai": "Advanced AI models"
    }
  },
  "amazon": {
    "name": "Zenara",
    "description": "Confident Amazon warrior...",
    "intro": "Kneel... or fight me...",
    "history": {
      "name-0": "Highland Dawn",
      "text-0": "Zenara turns slowly...",
      "description-0": "The sun rises..."
    }
  }
}
```

The translation service automatically flattens these to dot-notation keys internally:
- `welcome.title`
- `premium.features.energy`
- `amazon.name`
- `amazon.history.name-0`

## How To Add/Edit Translations

### 1. Edit JSON Files Directly

Simply edit the JSON files in your text editor:

```bash
# Edit bot translations
nano config/translations/en.json
nano config/translations/ru.json

# Or edit miniapp translations
nano miniapp/src/locales/en.json
nano miniapp/src/locales/ru.json
```

### 2. Follow the Structure

**UI Texts** (buttons, messages, errors):
```json
{
  "settings": {
    "language": {
      "title": "Language"
    }
  }
}
```

**Persona Translations** (names, descriptions):
```json
{
  "eva": {
    "name": "Eva",
    "description": "Sweet and caring girlfriend...",
    "small_description": "Your loving companion",
    "intro": "Hi! I'm Eva..."
  }
}
```

**History Scenarios** (greeting scenes):
```json
{
  "eva": {
    "history": {
      "name-0": "Morning Coffee",
      "name-1": "Beach Sunset",
      "small_description-0": "Cozy morning at home",
      "small_description-1": "Romantic evening walk",
      "description-0": "The kitchen smells of fresh coffee...",
      "description-1": "The waves crash softly...",
      "text-0": "Good morning! Want some coffee?",
      "text-1": "The sunset is beautiful tonight..."
    }
  }
}
```

### 3. Deployment

**For Development:**
```bash
# Restart the bot service
# Translations are loaded on startup
```

**For Production (Railway):**
```bash
git add config/translations/
git commit -m "Update translations"
git push origin main
# Railway will auto-deploy and restart
```

## Re-syncing From Database

If you need to pull translations from the database again:

```bash
# Step 1: Export from database
python scripts/export_db_translations.py

# Step 2: Merge with miniapp JSONs
python scripts/merge_translations.py

# Step 3: Restart service
```

This creates:
- `_db_export_en.json` (temporary)
- `_db_export_ru.json` (temporary)
- `config/translations/en.json` (merged result)
- `config/translations/ru.json` (merged result)

**Note**: Miniapp JSON files (`miniapp/src/locales/*.json`) are the source of truth and won't be overwritten.

## Testing

Test that translations load correctly:

```bash
python scripts/test_translation_service.py
```

This will:
- Load translations from JSON files
- Test retrieval of UI texts
- Test retrieval of persona translations
- Test fallback mechanism
- Show statistics

## Translation Key Naming Conventions

### For UI Elements:
- Use descriptive, hierarchical keys
- Use lowercase with underscores for multi-word components
- Example: `age_verification.confirm_button`, `premium.features.energy`

### For Personas:
- Use persona key as prefix (e.g., `eva`, `amazon`, `kiki`)
- Required fields: `name`, `description`, `small_description`, `intro`
- Example: `eva.name`, `eva.description`

### For History Scenarios:
- Use format: `{persona_key}.history.{field}-{index}`
- Fields: `name`, `small_description`, `description`, `text`
- Index starts at 0
- Example: `eva.history.name-0`, `eva.history.text-0`

## Language Consistency

The same `user.locale` field in the database controls both:
1. **Telegram Bot** - Loaded from `config/translations/*.json`
2. **Miniapp** - Loaded from `miniapp/src/locales/*.json`

See [`docs/LANGUAGE_SYNC.md`](../../docs/LANGUAGE_SYNC.md) for detailed information about how language detection and synchronization works.

## File Format Notes

- Use UTF-8 encoding
- Use 2-space indentation
- Keep keys sorted alphabetically (for git diffs)
- No trailing commas
- Escape special characters in strings (quotes, backslashes)

## Supported Languages

Currently supported:
- `en` - English
- `ru` - Russian

To add more languages:
1. Create `config/translations/{lang}.json`
2. Create `miniapp/src/locales/{lang}.json`
3. Update `app/core/translation_service.py` supported languages
4. Update `miniapp/src/i18n/TranslationContext.jsx` supported languages





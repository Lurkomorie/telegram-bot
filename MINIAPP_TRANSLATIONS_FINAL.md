# Miniapp Translations - Final Architecture ✅

## Overview

Miniapp translations use a **hybrid approach**: stored in database, generated as static JSON files.

## Architecture

```
Database (Source of Truth)
    ↓
Generate Script (scripts/generate_miniapp_translations.py)
    ↓
Static JSON Files (miniapp/src/locales/*.json)
    ↓
Frontend Bundle (static imports, zero runtime cost)
```

## Why This Approach?

✅ **No runtime API calls** - translations bundled with app  
✅ **Instant loading** - zero latency, no loading states  
✅ **CDN cacheable** - static files cached aggressively  
✅ **Database managed** - edit via admin dashboard  
✅ **Simple workflow** - regenerate + rebuild when needed  

## Files

### Scripts
- `scripts/migrate_miniapp_translations.py` - Initial migration JSON → DB (one-time)
- `scripts/generate_miniapp_translations.py` - Generate JSON from DB (run after edits)

### Output
- `miniapp/src/locales/en.json` - English translations (generated)
- `miniapp/src/locales/ru.json` - Russian translations (generated)
- `miniapp/src/locales/fr.json` - French translations (generated)
- `miniapp/src/locales/de.json` - German translations (generated)
- `miniapp/src/locales/es.json` - Spanish translations (generated)

## Workflow

### 1. Edit Translations

**Via Admin Dashboard:**
```
1. Open analytics dashboard
2. Navigate to Translations section
3. Filter by category: "miniapp"
4. Edit translations inline
5. Save changes
```

**Via Database:**
```python
from app.db.base import get_db
from app.db import crud

with get_db() as db:
    crud.create_or_update_translation(
        db,
        key='miniapp.app.header.characters',
        lang='en',
        value='Characters',
        category='miniapp'
    )
    db.commit()
```

### 2. Regenerate JSON Files

```bash
python scripts/generate_miniapp_translations.py
```

This reads all `miniapp.*` translations from database and generates JSON files.

### 3. Rebuild Miniapp

```bash
cd miniapp
npm run build
```

### 4. Deploy

Deploy updated miniapp build with new translations.

## Database Schema

All miniapp translations stored with:
- **key**: `miniapp.{dotted.path}` (e.g., `miniapp.app.header.characters`)
- **lang**: Language code (`en`, `ru`, `fr`, `de`, `es`)
- **value**: Translated text
- **category**: `miniapp`

## Migration History

1. ✅ Started with static JSON files
2. ✅ Created unified `translations` table in DB
3. ✅ Migrated all JSON → DB (215 translations)
4. ✅ Added generation script DB → JSON
5. ✅ Kept frontend using static JSON imports (best performance)

## Why Not Dynamic API Loading?

We considered loading translations via API (`GET /api/miniapp/translations?lang={lang}`) but decided against it:

❌ Extra HTTP request on every app load  
❌ Loading states and error handling needed  
❌ Slower initial render  
❌ Can't be cached by CDN  
❌ Unnecessary complexity  

**Static files are simply better for this use case.**

## Commands Reference

```bash
# Migrate JSON to database (one-time, already done)
python scripts/migrate_miniapp_translations.py

# Generate JSON from database (after editing translations)
python scripts/generate_miniapp_translations.py

# Build miniapp
cd miniapp && npm run build

# Dev server (uses JSON files directly)
cd miniapp && npm run dev
```

## Supported Languages

- `en` - English
- `ru` - Russian (Русский)
- `fr` - French (Français)
- `de` - German (Deutsch)
- `es` - Spanish (Español)

## Key Benefits

1. **Performance**: Zero runtime overhead
2. **Simplicity**: Standard JSON imports, no special loading logic
3. **Maintainability**: Edit in database, regenerate files
4. **Caching**: Static files cached by CDN and browser
5. **Reliability**: No API failures, always available
6. **Bundle size**: Minimal impact, only ~2KB per language

## Integration with Translation Service

Miniapp translations are part of the unified translation system:
- Backend uses `TranslationService` for in-memory caching
- Bot accesses translations via `TranslationService`
- Analytics dashboard manages all translations
- Miniapp uses generated static JSON files

This gives us the best of both worlds: centralized management + optimal frontend performance.



# How to Translate Persona Descriptions

## Current State
- Persona descriptions are stored in the **database** (`personas` and `persona_history_starts` tables)
- They are currently in English
- These need to be stored in a language-specific format

## Options for Implementation

### Option 1: Store Translations as JSON in Existing Fields (Recommended)
Store multilingual text as JSON in the current database fields.

**Example:**
```sql
-- Instead of:
name = "Sweet Emily"

-- Use:
name = '{"en": "Sweet Emily", "ru": "Милая Эмили", "fr": "Douce Emily", "de": "Süße Emily", "es": "Dulce Emily"}'
```

**Pros:**
- No schema changes needed
- All translations in one place
- Easy to add more languages

**Cons:**
- Requires updating CRUD functions to handle JSON
- Need to update persona cache logic

---

### Option 2: Separate Translation Tables
Create new tables like `persona_translations` and `persona_history_translations`.

**Schema:**
```sql
CREATE TABLE persona_translations (
    id UUID PRIMARY KEY,
    persona_id UUID REFERENCES personas(id),
    language VARCHAR(10), -- 'en', 'ru', 'fr', etc.
    name VARCHAR(255),
    description TEXT,
    small_description TEXT,
    intro TEXT
);
```

**Pros:**
- Clean separation
- Easy to query specific language
- Standard i18n pattern

**Cons:**
- Requires migration
- More complex queries (JOIN operations)

---

### Option 3: Hybrid Approach (Quick Win)
Keep English as default in current fields, add a JSON `translations` column.

**Schema:**
```sql
ALTER TABLE personas ADD COLUMN translations JSONB;

-- Example data:
translations = {
  "ru": {
    "name": "Милая Эмили",
    "description": "...",
    "small_description": "..."
  },
  "fr": {
    "name": "Douce Emily",
    ...
  }
}
```

**Pros:**
- English stays as fallback
- Flexible JSON structure
- Single migration

**Cons:**
- Duplicates English (once in field, once in JSON)

---

## Recommended Implementation Steps

### 1. Add Translation Support to Database

```python
# Migration file
def upgrade():
    # Add translations column to personas
    op.add_column('personas', 
        sa.Column('translations', postgresql.JSONB(), nullable=True))
    
    # Add translations column to persona_history_starts
    op.add_column('persona_history_starts',
        sa.Column('translations', postgresql.JSONB(), nullable=True))
```

### 2. Update CRUD Functions

```python
def get_persona_translated(db: Session, persona_id: UUID, language: str = 'en'):
    """Get persona with translated fields"""
    persona = db.query(Persona).filter(Persona.id == persona_id).first()
    if not persona:
        return None
    
    # If translations available for requested language, use them
    if persona.translations and language in persona.translations:
        trans = persona.translations[language]
        persona.name = trans.get('name', persona.name)
        persona.description = trans.get('description', persona.description)
        persona.small_description = trans.get('small_description', persona.small_description)
        persona.intro = trans.get('intro', persona.intro)
    
    return persona
```

### 3. Update Persona Cache

The persona cache (`app/core/persona_cache.py`) would need to load translations and return them based on language.

### 4. Update Mini App API

The mini app API endpoints (`app/api/miniapp.py`) would need to:
- Detect user language from request
- Return translated persona data

---

## Quick Script to Add Translations

Here's a script to manually add translations to existing personas:

```python
#!/usr/bin/env python3
"""
Add translations to personas
"""
from app.db.base import get_db
from app.db.models import Persona

translations = {
    "your-persona-key": {
        "ru": {
            "name": "Русское имя",
            "small_description": "Краткое описание",
            "description": "Полное описание"
        },
        "fr": {
            "name": "Nom français",
            "small_description": "Brève description",
            "description": "Description complète"
        }
        # ... add more languages
    }
}

with get_db() as db:
    for key, trans_data in translations.items():
        persona = db.query(Persona).filter(Persona.key == key).first()
        if persona:
            persona.translations = trans_data
            db.commit()
            print(f"✅ Updated {persona.name}")
```

---

## Current Workaround (Immediate Solution)

**For now, personas remain in English** since:
1. They're stored in the database (not config files)
2. Implementing persona translations requires schema changes
3. Most persona content is visual/character-specific (names are international)

**Priority should be:**
1. ✅ UI text translations (Done!)
2. ⚠️ Mini app language detection (API level)
3. 🔄 Persona translations (future enhancement)

The bot will show Russian UI text, but persona names/descriptions will stay English until you implement one of the options above.


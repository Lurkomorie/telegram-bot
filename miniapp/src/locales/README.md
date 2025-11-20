# Miniapp Translations

## System Architecture ✅

Translations are stored in database and **generated as static JSON files** for optimal performance.

### How it works:
1. **Source of Truth**: Translations stored in `translations` table (category: `miniapp`)
2. **Static Generation**: JSON files generated from DB via `scripts/generate_miniapp_translations.py`
3. **Frontend**: Imports static JSON files (no API calls, instant loading)
4. **Performance**: Zero runtime overhead, all translations bundled with app

### Workflow:

**1. Edit translations:**
- Via analytics dashboard at `/admin/translations`
- Filter by category: `miniapp`
- Or use CRUD operations in `app/db/crud.py`

**2. Regenerate JSON files:**
```bash
python scripts/generate_miniapp_translations.py
```

**3. Rebuild miniapp:**
```bash
cd miniapp && npm run build
```

### File Structure:
```
miniapp/src/locales/
├── en.json          # Generated from DB
├── ru.json          # Generated from DB
├── fr.json          # Generated from DB
├── de.json          # Generated from DB
├── es.json          # Generated from DB
├── backup/          # Original JSON backups
└── README.md        # This file
```

### Supported Languages:
- English (en)
- Russian (ru)
- French (fr)  
- German (de)
- Spanish (es)

### Benefits:
- ⚡ **Fast**: No API calls, translations bundled with app
- 📦 **Simple**: Standard JSON imports, no complexity
- 🔄 **Manageable**: Edit in database, regenerate files
- 💾 **Cacheable**: Static files cached by CDN/browser


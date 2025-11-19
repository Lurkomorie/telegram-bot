#!/usr/bin/env python3
"""
Seed persona name translations into the database
Since persona names are proper nouns, they typically stay the same across languages
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.base import get_db
from app.db import crud
from app.db.models import Persona, Translation


def seed_persona_name_translations():
    """Add name translations for all personas in all supported languages"""
    print("=" * 70)
    print("PERSONA NAME TRANSLATIONS SEEDER")
    print("=" * 70)
    print("\nAdding persona name translations for all languages...\n")
    
    with get_db() as db:
        # Get all personas with keys
        personas = db.query(Persona).filter(Persona.key.isnot(None)).all()
        
        if not personas:
            print("❌ No personas with keys found in database")
            return
        
        languages = ['en', 'ru', 'fr', 'de', 'es']
        total_created = 0
        total_updated = 0
        
        for persona in personas:
            persona_key = persona.key
            translation_key = f"{persona_key}.name"
            
            # Get the English translation (which should already exist)
            english_trans = db.query(Translation).filter(
                Translation.key == translation_key,
                Translation.lang == 'en'
            ).first()
            
            if not english_trans:
                print(f"⚠️  No English translation found for {persona_key}, skipping")
                continue
            
            english_name = english_trans.value
            print(f"📝 {persona_key}: {english_name}")
            
            # Add translations for all languages
            for lang in languages:
                # Check if translation already exists
                existing = db.query(Translation).filter(
                    Translation.key == translation_key,
                    Translation.lang == lang
                ).first()
                
                if existing:
                    if existing.value != english_name:
                        print(f"   ✏️  Updating {lang}: {existing.value} → {english_name}")
                        existing.value = english_name
                        total_updated += 1
                    else:
                        print(f"   ✓  {lang}: {english_name} (already exists)")
                else:
                    print(f"   ✨ Creating {lang}: {english_name}")
                    crud.create_or_update_translation(
                        db,
                        key=translation_key,
                        lang=lang,
                        value=english_name,
                        category='persona'
                    )
                    total_created += 1
        
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"✅ Translations created: {total_created}")
        print(f"✅ Translations updated: {total_updated}")
        print(f"✅ Total operations: {total_created + total_updated}")
        print("\n💡 Next steps:")
        print("   1. Restart your application to reload the translation cache")
        print("   2. Test persona names in different languages")
        print("   3. Update code to use get_persona_field(persona, 'name', language)")
        print("=" * 70)


if __name__ == "__main__":
    try:
        seed_persona_name_translations()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


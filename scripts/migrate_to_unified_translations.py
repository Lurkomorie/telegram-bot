"""
Migration script to populate the unified Translation table
Migrates data from:
1. PersonaTranslation table
2. PersonaHistoryTranslation table
3. UI texts YAML files
4. Persona names
"""
import sys
import os
from pathlib import Path
import yaml

# Add parent directory to path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.base import get_db
from app.db import crud
from app.db.models import Persona, PersonaHistoryStart, PersonaTranslation, PersonaHistoryTranslation


def flatten_dict(d, parent_key='', sep='.'):
    """Flatten nested dictionary into dot notation
    
    Example: {'welcome': {'title': 'Hello'}} -> {'welcome.title': 'Hello'}
    """
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def migrate_persona_translations():
    """Migrate PersonaTranslation data to Translation table"""
    print("\n[MIGRATE] 📝 Migrating persona translations...")
    
    with get_db() as db:
        # Get all personas with translations
        personas = db.query(Persona).filter(Persona.key.isnot(None)).all()
        
        translation_count = 0
        for persona in personas:
            persona_key = persona.key
            
            # Migrate persona name translations
            print(f"[MIGRATE]   Processing persona: {persona_key} (name: {persona.name})")
            
            # Add name translations for all languages
            for lang in ['en', 'ru']:
                # For English, use the persona's base name
                if lang == 'en':
                    crud.create_or_update_translation(
                        db,
                        key=f"{persona_key}.name",
                        lang=lang,
                        value=persona.name,
                        category='persona'
                    )
                    translation_count += 1
                
            # Get existing persona translations
            persona_translations = db.query(PersonaTranslation).filter(
                PersonaTranslation.persona_id == persona.id
            ).all()
            
            for trans in persona_translations:
                lang = trans.language
                
                # Migrate description
                if trans.description:
                    crud.create_or_update_translation(
                        db,
                        key=f"{persona_key}.description",
                        lang=lang,
                        value=trans.description,
                        category='persona'
                    )
                    translation_count += 1
                
                # Migrate small_description
                if trans.small_description:
                    crud.create_or_update_translation(
                        db,
                        key=f"{persona_key}.small_description",
                        lang=lang,
                        value=trans.small_description,
                        category='persona'
                    )
                    translation_count += 1
                
                # Migrate intro
                if trans.intro:
                    crud.create_or_update_translation(
                        db,
                        key=f"{persona_key}.intro",
                        lang=lang,
                        value=trans.intro,
                        category='persona'
                    )
                    translation_count += 1
        
        print(f"[MIGRATE] ✅ Migrated {translation_count} persona translations")
        return translation_count


def migrate_history_translations():
    """Migrate PersonaHistoryTranslation data to Translation table"""
    print("\n[MIGRATE] 📖 Migrating persona history translations...")
    
    with get_db() as db:
        # Get all personas with keys
        personas = db.query(Persona).filter(Persona.key.isnot(None)).all()
        
        translation_count = 0
        for persona in personas:
            persona_key = persona.key
            
            # Get histories for this persona
            histories = db.query(PersonaHistoryStart).filter(
                PersonaHistoryStart.persona_id == persona.id
            ).order_by(PersonaHistoryStart.created_at).all()
            
            if not histories:
                continue
            
            print(f"[MIGRATE]   Processing {len(histories)} histories for persona: {persona_key}")
            
            for index, history in enumerate(histories):
                # Get translations for this history
                history_translations = db.query(PersonaHistoryTranslation).filter(
                    PersonaHistoryTranslation.history_id == history.id
                ).all()
                
                for trans in history_translations:
                    lang = trans.language
                    
                    # Migrate name
                    if trans.name:
                        crud.create_or_update_translation(
                            db,
                            key=f"{persona_key}.history.name-{index}",
                            lang=lang,
                            value=trans.name,
                            category='history'
                        )
                        translation_count += 1
                    
                    # Migrate small_description
                    if trans.small_description:
                        crud.create_or_update_translation(
                            db,
                            key=f"{persona_key}.history.small_description-{index}",
                            lang=lang,
                            value=trans.small_description,
                            category='history'
                        )
                        translation_count += 1
                    
                    # Migrate description
                    if trans.description:
                        crud.create_or_update_translation(
                            db,
                            key=f"{persona_key}.history.description-{index}",
                            lang=lang,
                            value=trans.description,
                            category='history'
                        )
                        translation_count += 1
                    
                    # Migrate text (greeting)
                    if trans.text:
                        crud.create_or_update_translation(
                            db,
                            key=f"{persona_key}.history.text-{index}",
                            lang=lang,
                            value=trans.text,
                            category='history'
                        )
                        translation_count += 1
        
        print(f"[MIGRATE] ✅ Migrated {translation_count} history translations")
        return translation_count


def migrate_ui_texts():
    """Migrate UI texts from YAML files to Translation table"""
    print("\n[MIGRATE] 🎨 Migrating UI texts from YAML files...")
    
    config_dir = Path(__file__).parent.parent / "config"
    languages = ['en', 'ru']
    
    translation_count = 0
    with get_db() as db:
        for lang in languages:
            yaml_file = config_dir / f"ui_texts_{lang}.yaml"
            
            if not yaml_file.exists():
                print(f"[MIGRATE]   ⚠️  File not found: {yaml_file}")
                continue
            
            print(f"[MIGRATE]   Processing {lang} UI texts...")
            
            # Load YAML file
            with open(yaml_file, 'r', encoding='utf-8') as f:
                ui_texts = yaml.safe_load(f)
            
            if not ui_texts:
                print(f"[MIGRATE]   ⚠️  Empty or invalid YAML: {yaml_file}")
                continue
            
            # Flatten nested structure to dot notation
            flat_texts = flatten_dict(ui_texts)
            
            # Create translations
            for key, value in flat_texts.items():
                if isinstance(value, str):  # Only migrate string values
                    crud.create_or_update_translation(
                        db,
                        key=key,
                        lang=lang,
                        value=value,
                        category='ui'
                    )
                    translation_count += 1
            
            print(f"[MIGRATE]     ✅ Migrated {len(flat_texts)} {lang} UI texts")
    
    print(f"[MIGRATE] ✅ Total UI texts migrated: {translation_count}")
    return translation_count


def verify_migration():
    """Verify migration was successful"""
    print("\n[VERIFY] 🔍 Verifying migration...")
    
    with get_db() as db:
        from app.db.models import Translation
        
        # Count translations by category
        total = db.query(Translation).count()
        ui_count = db.query(Translation).filter(Translation.category == 'ui').count()
        persona_count = db.query(Translation).filter(Translation.category == 'persona').count()
        history_count = db.query(Translation).filter(Translation.category == 'history').count()
        
        print(f"[VERIFY] Total translations: {total}")
        print(f"[VERIFY]   UI texts: {ui_count}")
        print(f"[VERIFY]   Persona: {persona_count}")
        print(f"[VERIFY]   History: {history_count}")
        
        # Count by language
        for lang in ['en', 'ru']:
            lang_count = db.query(Translation).filter(Translation.lang == lang).count()
            print(f"[VERIFY]   {lang.upper()}: {lang_count}")
        
        # Sample some translations
        print("\n[VERIFY] Sample translations:")
        samples = db.query(Translation).limit(5).all()
        for sample in samples:
            print(f"[VERIFY]   {sample.lang} | {sample.category} | {sample.key}: {sample.value[:50]}...")
    
    print("\n[VERIFY] ✅ Verification complete")


def main():
    """Run all migrations"""
    print("=" * 60)
    print("TRANSLATION MIGRATION SCRIPT")
    print("=" * 60)
    print("\nThis script will migrate all translations to the unified Translation table.")
    print("Old tables (PersonaTranslation, PersonaHistoryTranslation) will NOT be dropped.")
    print()
    
    try:
        # Run migrations
        persona_count = migrate_persona_translations()
        history_count = migrate_history_translations()
        ui_count = migrate_ui_texts()
        
        # Verify
        verify_migration()
        
        print("\n" + "=" * 60)
        print("MIGRATION SUMMARY")
        print("=" * 60)
        print(f"Persona translations: {persona_count}")
        print(f"History translations: {history_count}")
        print(f"UI text translations: {ui_count}")
        print(f"Total: {persona_count + history_count + ui_count}")
        print()
        print("✅ Migration completed successfully!")
        print()
        print("Next steps:")
        print("1. Restart the application to load translations into cache")
        print("2. Test the bot in different languages")
        print("3. Use the analytics UI to manage translations")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()


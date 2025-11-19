"""
Migration script to move persona and history texts to translation keys

This script will:
1. Take actual text from persona fields (name, description, small_description, intro)
2. Create English translation entries in the translations table
3. Replace the text in persona fields with translation keys (e.g., "airi.name")
4. Do the same for persona_history_start fields
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.base import get_db
from app.db import crud
from app.db.models import Persona, PersonaHistoryStart


def migrate_personas():
    """Migrate persona fields to use translation keys"""
    print("\n[MIGRATE] 📝 Migrating persona text fields to keys...")
    
    with get_db() as db:
        personas = db.query(Persona).filter(Persona.key.isnot(None)).all()
        
        migrated_count = 0
        for persona in personas:
            persona_key = persona.key
            print(f"[MIGRATE]   Processing persona: {persona_key}")
            
            # Migrate name field
            if persona.name and persona.name != f"{persona_key}.name":
                # Store actual name as English translation
                crud.create_or_update_translation(
                    db,
                    key=f"{persona_key}.name",
                    lang='en',
                    value=persona.name,
                    category='persona'
                )
                print(f"[MIGRATE]     Created translation: {persona_key}.name = {persona.name}")
                
                # Replace with key
                persona.name = f"{persona_key}.name"
                migrated_count += 1
            
            # Migrate description field
            if persona.description and not persona.description.startswith(f"{persona_key}."):
                # Store actual description as English translation
                crud.create_or_update_translation(
                    db,
                    key=f"{persona_key}.description",
                    lang='en',
                    value=persona.description,
                    category='persona'
                )
                print(f"[MIGRATE]     Created translation: {persona_key}.description")
                
                # Replace with key
                persona.description = f"{persona_key}.description"
                migrated_count += 1
            
            # Migrate small_description field
            if persona.small_description and not persona.small_description.startswith(f"{persona_key}."):
                # Store actual small_description as English translation
                crud.create_or_update_translation(
                    db,
                    key=f"{persona_key}.small_description",
                    lang='en',
                    value=persona.small_description,
                    category='persona'
                )
                print(f"[MIGRATE]     Created translation: {persona_key}.small_description")
                
                # Replace with key
                persona.small_description = f"{persona_key}.small_description"
                migrated_count += 1
            
            # Migrate intro field
            if persona.intro and not persona.intro.startswith(f"{persona_key}."):
                # Store actual intro as English translation
                crud.create_or_update_translation(
                    db,
                    key=f"{persona_key}.intro",
                    lang='en',
                    value=persona.intro,
                    category='persona'
                )
                print(f"[MIGRATE]     Created translation: {persona_key}.intro")
                
                # Replace with key
                persona.intro = f"{persona_key}.intro"
                migrated_count += 1
        
        db.commit()
        print(f"[MIGRATE] ✅ Migrated {migrated_count} persona text fields to keys")
        return migrated_count


def migrate_persona_histories():
    """Migrate persona history fields to use translation keys"""
    print("\n[MIGRATE] 📖 Migrating persona history text fields to keys...")
    
    with get_db() as db:
        personas = db.query(Persona).filter(Persona.key.isnot(None)).all()
        
        migrated_count = 0
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
                # Migrate name field
                if history.name and not history.name.startswith(f"{persona_key}.history."):
                    # Store actual name as English translation
                    crud.create_or_update_translation(
                        db,
                        key=f"{persona_key}.history.name-{index}",
                        lang='en',
                        value=history.name,
                        category='history'
                    )
                    print(f"[MIGRATE]     Created translation: {persona_key}.history.name-{index}")
                    
                    # Replace with key
                    history.name = f"{persona_key}.history.name-{index}"
                    migrated_count += 1
                
                # Migrate small_description field
                if history.small_description and not history.small_description.startswith(f"{persona_key}.history."):
                    # Store actual small_description as English translation
                    crud.create_or_update_translation(
                        db,
                        key=f"{persona_key}.history.small_description-{index}",
                        lang='en',
                        value=history.small_description,
                        category='history'
                    )
                    print(f"[MIGRATE]     Created translation: {persona_key}.history.small_description-{index}")
                    
                    # Replace with key
                    history.small_description = f"{persona_key}.history.small_description-{index}"
                    migrated_count += 1
                
                # Migrate description field
                if history.description and not history.description.startswith(f"{persona_key}.history."):
                    # Store actual description as English translation
                    crud.create_or_update_translation(
                        db,
                        key=f"{persona_key}.history.description-{index}",
                        lang='en',
                        value=history.description,
                        category='history'
                    )
                    print(f"[MIGRATE]     Created translation: {persona_key}.history.description-{index}")
                    
                    # Replace with key
                    history.description = f"{persona_key}.history.description-{index}"
                    migrated_count += 1
                
                # Migrate text field (greeting)
                if history.text and not history.text.startswith(f"{persona_key}.history."):
                    # Store actual text as English translation
                    crud.create_or_update_translation(
                        db,
                        key=f"{persona_key}.history.text-{index}",
                        lang='en',
                        value=history.text,
                        category='history'
                    )
                    print(f"[MIGRATE]     Created translation: {persona_key}.history.text-{index}")
                    
                    # Replace with key
                    history.text = f"{persona_key}.history.text-{index}"
                    migrated_count += 1
        
        db.commit()
        print(f"[MIGRATE] ✅ Migrated {migrated_count} history text fields to keys")
        return migrated_count


def verify_migration():
    """Verify migration was successful"""
    print("\n[VERIFY] 🔍 Verifying migration...")
    
    with get_db() as db:
        # Check personas
        personas = db.query(Persona).filter(Persona.key.isnot(None)).all()
        
        persona_keys_found = 0
        for persona in personas:
            persona_key = persona.key
            
            # Check if fields are now keys
            if persona.name and persona.name == f"{persona_key}.name":
                persona_keys_found += 1
            if persona.description and persona.description == f"{persona_key}.description":
                persona_keys_found += 1
            if persona.small_description and persona.small_description == f"{persona_key}.small_description":
                persona_keys_found += 1
            if persona.intro and persona.intro == f"{persona_key}.intro":
                persona_keys_found += 1
        
        print(f"[VERIFY] Found {persona_keys_found} persona fields using translation keys")
        
        # Check histories
        histories = db.query(PersonaHistoryStart).all()
        history_keys_found = 0
        for history in histories:
            if history.name and ".history.name-" in history.name:
                history_keys_found += 1
            if history.description and ".history.description-" in history.description:
                history_keys_found += 1
            if history.small_description and ".history.small_description-" in history.small_description:
                history_keys_found += 1
            if history.text and ".history.text-" in history.text:
                history_keys_found += 1
        
        print(f"[VERIFY] Found {history_keys_found} history fields using translation keys")
        
        # Check translations exist
        from app.db.models import Translation
        persona_translations = db.query(Translation).filter(
            Translation.category == 'persona',
            Translation.lang == 'en'
        ).count()
        
        history_translations = db.query(Translation).filter(
            Translation.category == 'history',
            Translation.lang == 'en'
        ).count()
        
        print(f"[VERIFY] English persona translations: {persona_translations}")
        print(f"[VERIFY] English history translations: {history_translations}")
    
    print("\n[VERIFY] ✅ Verification complete")


def main():
    """Run migration"""
    print("=" * 60)
    print("PERSONA TEXT TO KEY MIGRATION SCRIPT")
    print("=" * 60)
    print("\nThis script will:")
    print("1. Move actual text from persona fields to translations table")
    print("2. Replace text in persona tables with translation keys")
    print("3. Preserve all existing translations")
    print()
    
    try:
        # Run migrations
        persona_count = migrate_personas()
        history_count = migrate_persona_histories()
        
        # Verify
        verify_migration()
        
        print("\n" + "=" * 60)
        print("MIGRATION SUMMARY")
        print("=" * 60)
        print(f"Persona text fields migrated: {persona_count}")
        print(f"History text fields migrated: {history_count}")
        print(f"Total: {persona_count + history_count}")
        print()
        print("✅ Migration completed successfully!")
        print()
        print("Next steps:")
        print("1. Restart the application to reload caches")
        print("2. Test persona display in all languages")
        print("3. Verify translation keys are working correctly")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()


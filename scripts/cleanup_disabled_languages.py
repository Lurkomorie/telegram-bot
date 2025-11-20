#!/usr/bin/env python3
"""
Cleanup script to remove data for disabled languages (fr, de, es)
This script will:
1. Delete translations for unsupported languages
2. Reset user locales to 'en' if they are set to unsupported languages
"""
import sys
import os
from pathlib import Path

# Add parent directory to path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.base import get_db
from app.db.models import Translation, User, PersonaTranslation, PersonaHistoryTranslation

def cleanup_disabled_languages():
    print("=" * 60)
    print("DISABLED LANGUAGES CLEANUP")
    print("=" * 60)
    print("\nThis script will remove data for: fr, de, es")
    print("Supported languages: en, ru")
    
    confirm = input("\nAre you sure you want to proceed? (y/N): ")
    if confirm.lower() != 'y':
        print("Operation cancelled.")
        return

    with get_db() as db:
        # 1. Clean up Translation table
        print("\n[1/4] Cleaning up Translation table...")
        deleted = db.query(Translation).filter(
            Translation.lang.notin_(['en', 'ru'])
        ).delete(synchronize_session=False)
        print(f"   ✅ Deleted {deleted} rows")

        # 2. Clean up PersonaTranslation table
        print("\n[2/4] Cleaning up PersonaTranslation table...")
        deleted = db.query(PersonaTranslation).filter(
            PersonaTranslation.language.notin_(['en', 'ru'])
        ).delete(synchronize_session=False)
        print(f"   ✅ Deleted {deleted} rows")

        # 3. Clean up PersonaHistoryTranslation table
        print("\n[3/4] Cleaning up PersonaHistoryTranslation table...")
        deleted = db.query(PersonaHistoryTranslation).filter(
            PersonaHistoryTranslation.language.notin_(['en', 'ru'])
        ).delete(synchronize_session=False)
        print(f"   ✅ Deleted {deleted} rows")

        # 4. Reset User locales
        print("\n[4/4] Resetting unsupported user locales to 'en'...")
        users = db.query(User).filter(
            User.locale.notin_(['en', 'ru'])
        ).all()
        
        updated_count = 0
        for user in users:
            print(f"   🔄 User {user.id}: {user.locale} -> en")
            user.locale = 'en'
            updated_count += 1
        
        if updated_count > 0:
            db.commit()
        print(f"   ✅ Updated {updated_count} users")

        # Commit all deletions
        db.commit()
        print("\n✨ Cleanup completed successfully!")

if __name__ == "__main__":
    try:
        cleanup_disabled_languages()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


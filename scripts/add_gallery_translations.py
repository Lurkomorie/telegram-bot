#!/usr/bin/env python3
"""
Add missing gallery translations to the database

New translations:
- gallery.arrivingSoon: "Arriving soon" / "Скоро прибудет"
- gallery.deleteConfirm: "Delete {name}? This cannot be undone." / "Удалить {name}? Это действие нельзя отменить."
- gallery.deleteSuccess: "{name} deleted successfully" / "{name} успешно удалена"
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.base import get_db
from app.db.models import Translation
from sqlalchemy import and_


def add_gallery_translations():
    """Add missing gallery translations"""
    print("=" * 70)
    print("ADDING MISSING GALLERY TRANSLATIONS")
    print("=" * 70)
    
    translations_to_add = [
        # English
        {
            'category': 'miniapp',
            'key': 'miniapp.gallery.arrivingSoon',
            'lang': 'en',
            'value': 'Arriving soon'
        },
        {
            'category': 'miniapp',
            'key': 'miniapp.gallery.deleteConfirm',
            'lang': 'en',
            'value': 'Delete {name}? This cannot be undone.'
        },
        {
            'category': 'miniapp',
            'key': 'miniapp.gallery.deleteSuccess',
            'lang': 'en',
            'value': '{name} deleted successfully'
        },
        # Russian
        {
            'category': 'miniapp',
            'key': 'miniapp.gallery.arrivingSoon',
            'lang': 'ru',
            'value': 'Скоро прибудет'
        },
        {
            'category': 'miniapp',
            'key': 'miniapp.gallery.deleteConfirm',
            'lang': 'ru',
            'value': 'Удалить {name}? Это действие нельзя отменить.'
        },
        {
            'category': 'miniapp',
            'key': 'miniapp.gallery.deleteSuccess',
            'lang': 'ru',
            'value': '{name} успешно удалена'
        },
    ]
    
    with get_db() as db:
        added_count = 0
        updated_count = 0
        
        for trans_data in translations_to_add:
            # Check if translation already exists
            existing = db.query(Translation).filter(
                and_(
                    Translation.key == trans_data['key'],
                    Translation.lang == trans_data['lang'],
                    Translation.category == trans_data['category']
                )
            ).first()
            
            if existing:
                # Update if exists
                existing.value = trans_data['value']
                updated_count += 1
                print(f"   ✏️  Updated: {trans_data['key']} ({trans_data['lang']})")
            else:
                # Create new
                new_translation = Translation(**trans_data)
                db.add(new_translation)
                added_count += 1
                print(f"   ✅ Added: {trans_data['key']} ({trans_data['lang']})")
        
        db.commit()
        
        print("\n" + "=" * 70)
        print(f"✨ COMPLETE!")
        print(f"   Added: {added_count} translations")
        print(f"   Updated: {updated_count} translations")
        print("=" * 70)
        print("\n💡 Next step: Run generate_miniapp_translations.py to export to JSON")
        print()


def main():
    try:
        add_gallery_translations()
    except Exception as e:
        print(f"\n❌ Error adding translations: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()






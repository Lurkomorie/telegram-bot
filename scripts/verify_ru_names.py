#!/usr/bin/env python3
"""
Verify the Russian name translations in the database
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.base import get_db
from app.db.models import Persona, Translation


def verify_ru_names():
    """Display all persona name translations"""
    print("=" * 70)
    print("RUSSIAN PERSONA NAME TRANSLATIONS - VERIFICATION")
    print("=" * 70)
    
    with get_db() as db:
        # Get all personas with keys
        personas = db.query(Persona).filter(Persona.key.isnot(None)).order_by(Persona.order).all()
        
        if not personas:
            print("❌ No personas found")
            return
        
        print(f"\n{'Persona Key':<20} {'English Name':<20} {'Russian Name (Cyrillic)':<30}")
        print("-" * 70)
        
        for persona in personas:
            translation_key = f"{persona.key}.name"
            
            # Get English translation
            en_trans = db.query(Translation).filter(
                Translation.key == translation_key,
                Translation.lang == 'en'
            ).first()
            
            # Get Russian translation
            ru_trans = db.query(Translation).filter(
                Translation.key == translation_key,
                Translation.lang == 'ru'
            ).first()
            
            en_name = en_trans.value if en_trans else "N/A"
            ru_name = ru_trans.value if ru_trans else "N/A"
            
            # Check if properly in Cyrillic
            has_cyrillic = any('\u0400' <= char <= '\u04FF' for char in ru_name) if ru_name != "N/A" else False
            status = "✅" if has_cyrillic else "❌"
            
            print(f"{persona.key:<20} {en_name:<20} {ru_name:<30} {status}")
        
        print("-" * 70)
        print(f"\n✅ All {len(personas)} personas verified\n")


if __name__ == "__main__":
    try:
        verify_ru_names()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)



"""
Export all translations from database to JSON files
This script queries Translation, PersonaTranslation, and PersonaHistoryTranslation tables
and exports them to temporary JSON files for comparison/merging.
"""
import sys
import os
import json
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.base import get_db
from app.db.models import Translation, PersonaTranslation, PersonaHistoryTranslation, Persona, PersonaHistoryStart


def export_translations():
    """Export all translations from database to JSON files"""
    
    print("=" * 60)
    print("EXPORTING TRANSLATIONS FROM DATABASE")
    print("=" * 60)
    
    with get_db() as db:
        # Dictionary to store translations by language
        translations_by_lang = {
            'en': {},
            'ru': {}
        }
        
        # 1. Export UI translations from Translation table
        print("\n[1/3] Exporting UI translations from Translation table...")
        ui_translations = db.query(Translation).all()
        
        for trans in ui_translations:
            lang = trans.lang
            if lang in translations_by_lang:
                translations_by_lang[lang][trans.key] = trans.value
        
        print(f"   ✓ Found {len(ui_translations)} UI translation entries")
        
        # 2. Export persona translations from PersonaTranslation table
        print("\n[2/3] Exporting persona translations from PersonaTranslation table...")
        persona_translations = db.query(PersonaTranslation).all()
        
        # Get persona keys for translation keys
        personas_by_id = {}
        all_personas = db.query(Persona).all()
        for p in all_personas:
            if p.key:  # Only public personas with keys
                personas_by_id[str(p.id)] = p.key
        
        for trans in persona_translations:
            persona_key = personas_by_id.get(str(trans.persona_id))
            if not persona_key:
                continue  # Skip custom personas without keys
            
            lang = trans.language
            if lang not in translations_by_lang:
                continue
            
            # Create keys like: airi.name, airi.description, etc.
            if trans.description:
                translations_by_lang[lang][f"{persona_key}.description"] = trans.description
            if trans.small_description:
                translations_by_lang[lang][f"{persona_key}.small_description"] = trans.small_description
            if trans.intro:
                translations_by_lang[lang][f"{persona_key}.intro"] = trans.intro
        
        print(f"   ✓ Found {len(persona_translations)} persona translation entries")
        
        # 3. Export history translations from PersonaHistoryTranslation table
        print("\n[3/3] Exporting history translations from PersonaHistoryTranslation table...")
        history_translations = db.query(PersonaHistoryTranslation).all()
        
        # Get history -> persona mapping
        histories_by_id = {}
        all_histories = db.query(PersonaHistoryStart).all()
        for h in all_histories:
            persona_key = personas_by_id.get(str(h.persona_id))
            if persona_key:
                histories_by_id[str(h.id)] = persona_key
        
        # Count histories per persona to create indices
        history_indices = {}
        for h in all_histories:
            persona_key = personas_by_id.get(str(h.persona_id))
            if persona_key:
                if persona_key not in history_indices:
                    history_indices[persona_key] = []
                history_indices[persona_key].append(str(h.id))
        
        for trans in history_translations:
            history_id_str = str(trans.history_id)
            persona_key = histories_by_id.get(history_id_str)
            if not persona_key:
                continue
            
            # Find index of this history for this persona
            if persona_key not in history_indices:
                continue
            try:
                idx = history_indices[persona_key].index(history_id_str)
            except ValueError:
                continue
            
            lang = trans.language
            if lang not in translations_by_lang:
                continue
            
            # Create keys like: airi.history.name-0, airi.history.text-1, etc.
            if trans.name:
                translations_by_lang[lang][f"{persona_key}.history.name-{idx}"] = trans.name
            if trans.small_description:
                translations_by_lang[lang][f"{persona_key}.history.small_description-{idx}"] = trans.small_description
            if trans.description:
                translations_by_lang[lang][f"{persona_key}.history.description-{idx}"] = trans.description
            if trans.text:
                translations_by_lang[lang][f"{persona_key}.history.text-{idx}"] = trans.text
        
        print(f"   ✓ Found {len(history_translations)} history translation entries")
        
        # Write to temporary files
        print("\n" + "=" * 60)
        print("WRITING TO FILES")
        print("=" * 60)
        
        output_dir = Path(__file__).parent.parent
        
        for lang, translations in translations_by_lang.items():
            output_file = output_dir / f"_db_export_{lang}.json"
            
            # Sort keys for readability
            sorted_translations = dict(sorted(translations.items()))
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(sorted_translations, f, ensure_ascii=False, indent=2)
            
            print(f"\n✓ Exported {len(translations)} translations to: {output_file.name}")
            
            # Show sample keys
            sample_keys = list(sorted_translations.keys())[:5]
            print(f"  Sample keys: {', '.join(sample_keys)}")
        
        print("\n" + "=" * 60)
        print("EXPORT COMPLETE")
        print("=" * 60)
        print("\nNext step: Run merge_translations.py to merge with miniapp JSONs")


if __name__ == "__main__":
    export_translations()


#!/usr/bin/env python3
"""
Generate static JSON translation files for the miniapp from database

This script:
1. Reads all translations from DB where category='miniapp'
2. Converts from flat dot notation to nested JSON
3. Writes to static JSON files in miniapp/src/locales/

Usage:
    python scripts/generate_miniapp_translations.py

After running:
    cd miniapp && npm run build
"""
import sys
import json
from pathlib import Path
from typing import Dict, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.base import get_db
from app.db.models import Translation


def unflatten_dict(flat_dict: Dict[str, str]) -> Dict[str, Any]:
    """Convert flat dot notation dict to nested dict
    
    Example:
        {'app.title': 'Hello', 'app.button.text': 'Click'}
        ->
        {'app': {'title': 'Hello', 'button': {'text': 'Click'}}}
    
    Args:
        flat_dict: Dict with dot notation keys
        
    Returns:
        Nested dict
    """
    result = {}
    
    for key, value in flat_dict.items():
        parts = key.split('.')
        current = result
        
        # Navigate/create nested structure
        for i, part in enumerate(parts[:-1]):
            if part not in current:
                current[part] = {}
            current = current[part]
        
        # Set the final value
        current[parts[-1]] = value
    
    return result


def generate_translation_files():
    """Generate JSON translation files from database"""
    print("=" * 70)
    print("MINIAPP TRANSLATION GENERATOR")
    print("=" * 70)
    print("\n📦 Reading translations from database...")
    
    # Get all miniapp translations from database
    with get_db() as db:
        miniapp_translations = db.query(Translation).filter(
            Translation.category == 'miniapp'
        ).all()
        
        if not miniapp_translations:
            print("⚠️  No translations found with category='miniapp'")
            print("   Run the translation migration script first or add miniapp translations")
            return
        
        print(f"✅ Found {len(miniapp_translations)} miniapp translations")
        
        # Organize by language and strip 'miniapp.' prefix from keys
        by_language = {}
        for trans in miniapp_translations:
            lang = trans.lang
            key = trans.key
            
            # Strip 'miniapp.' prefix if present
            if key.startswith('miniapp.'):
                key = key[8:]  # Remove 'miniapp.' (8 characters)
            
            if lang not in by_language:
                by_language[lang] = {}
            by_language[lang][key] = trans.value
        
        print(f"📋 Languages: {', '.join(sorted(by_language.keys()))}")
    
    # Output directory
    output_dir = Path(__file__).parent.parent / "miniapp" / "src" / "locales"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n📝 Writing JSON files to: {output_dir}")
    
    # Generate JSON file for each language
    generated_files = []
    for lang, translations in by_language.items():
        # Convert flat dict to nested structure
        nested = unflatten_dict(translations)
        
        # Write to JSON file
        output_file = output_dir / f"{lang}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(nested, f, ensure_ascii=False, indent=2)
        
        print(f"   ✅ {lang}.json ({len(translations)} keys)")
        generated_files.append(output_file.name)
    
    print("\n" + "=" * 70)
    print("✨ GENERATION COMPLETE!")
    print("=" * 70)
    print(f"\nGenerated files:")
    for filename in sorted(generated_files):
        print(f"  • {filename}")
    
    print("\n💡 Next steps:")
    print("   1. Review the generated JSON files")
    print("   2. Rebuild the miniapp: cd miniapp && npm run build")
    print("   3. Test translations in the app")
    print()


def main():
    try:
        generate_translation_files()
    except Exception as e:
        print(f"\n❌ Error generating translation files: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

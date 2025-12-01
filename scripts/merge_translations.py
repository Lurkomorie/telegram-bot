"""
Merge database translations with miniapp JSON files
This script:
1. Loads miniapp JSONs (these are correct, the source of truth)
2. Loads DB export JSONs
3. Finds translations in DB that are NOT in miniapp (bot-specific UI, persona translations)
4. Merges them and saves to config/translations/
5. Keeps miniapp JSONs unchanged
"""
import sys
import json
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def deep_merge(base_dict, new_dict):
    """
    Recursively merge new_dict into base_dict
    Only adds keys that don't exist in base_dict
    """
    result = base_dict.copy()
    
    for key, value in new_dict.items():
        if key not in result:
            # Key doesn't exist in base, add it
            result[key] = value
        elif isinstance(result[key], dict) and isinstance(value, dict):
            # Both are dicts, merge recursively
            result[key] = deep_merge(result[key], value)
        # If key exists and is not dict, keep base value (miniapp is source of truth)
    
    return result


def flatten_dict(d, parent_key='', sep='.'):
    """Flatten nested dict to dot-notation keys"""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def unflatten_dict(flat_dict, sep='.'):
    """Convert flat dict with dot-notation keys to nested dict"""
    result = {}
    for key, value in flat_dict.items():
        parts = key.split(sep)
        d = result
        for part in parts[:-1]:
            if part not in d:
                d[part] = {}
            elif not isinstance(d[part], dict):
                # Conflict: key already exists as a value, keep flat structure
                # This happens when we have both "key" and "key.subkey"
                continue
            d = d[part]
        
        # Only set if the parent is a dict
        if isinstance(d, dict):
            d[parts[-1]] = value
    return result


def merge_translations():
    """Merge database exports with miniapp JSONs"""
    
    print("=" * 60)
    print("MERGING TRANSLATIONS")
    print("=" * 60)
    
    root_dir = Path(__file__).parent.parent
    miniapp_locales_dir = root_dir / "miniapp" / "src" / "locales"
    config_dir = root_dir / "config"
    config_translations_dir = config_dir / "translations"
    
    # Create config/translations directory if it doesn't exist
    config_translations_dir.mkdir(parents=True, exist_ok=True)
    
    languages = ['en', 'ru']
    
    for lang in languages:
        print(f"\n{'=' * 60}")
        print(f"Processing {lang.upper()}")
        print('=' * 60)
        
        # 1. Load miniapp JSON (source of truth)
        miniapp_file = miniapp_locales_dir / f"{lang}.json"
        print(f"\n[1/4] Loading miniapp JSON: {miniapp_file.relative_to(root_dir)}")
        
        with open(miniapp_file, 'r', encoding='utf-8') as f:
            miniapp_translations = json.load(f)
        
        # Flatten for easier comparison
        miniapp_flat = flatten_dict(miniapp_translations)
        print(f"   ✓ Loaded {len(miniapp_flat)} miniapp translations")
        
        # 2. Load DB export
        db_export_file = root_dir / f"_db_export_{lang}.json"
        print(f"\n[2/4] Loading DB export: {db_export_file.name}")
        
        if not db_export_file.exists():
            print(f"   ✗ File not found! Run export_db_translations.py first")
            continue
        
        with open(db_export_file, 'r', encoding='utf-8') as f:
            db_translations = json.load(f)
        
        print(f"   ✓ Loaded {len(db_translations)} database translations")
        
        # 3. Find translations in DB that are NOT in miniapp
        print(f"\n[3/4] Finding translations to merge...")
        
        new_translations = {}
        for key, value in db_translations.items():
            if key not in miniapp_flat:
                new_translations[key] = value
        
        print(f"   ✓ Found {len(new_translations)} new translations from database")
        
        if new_translations:
            # Show samples of what's being added
            sample_keys = list(new_translations.keys())[:10]
            print(f"\n   Sample keys being added:")
            for key in sample_keys:
                print(f"     - {key}")
            if len(new_translations) > 10:
                print(f"     ... and {len(new_translations) - 10} more")
        
        # 4. Merge and save
        print(f"\n[4/4] Merging and saving to config/translations/...")
        
        # Combine: miniapp (priority) + new DB translations
        merged_flat = {**new_translations, **miniapp_flat}  # miniapp overwrites DB
        
        # Convert back to nested structure for better readability
        merged_nested = unflatten_dict(merged_flat)
        
        # Sort top-level keys
        merged_sorted = dict(sorted(merged_nested.items()))
        
        # Save to config/translations/
        output_file = config_translations_dir / f"{lang}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(merged_sorted, f, ensure_ascii=False, indent=2)
        
        print(f"   ✓ Saved {len(merged_flat)} total translations to: {output_file.relative_to(root_dir)}")
        
        # Statistics
        print(f"\n   Statistics:")
        print(f"     - Miniapp translations: {len(miniapp_flat)}")
        print(f"     - New from database: {len(new_translations)}")
        print(f"     - Total merged: {len(merged_flat)}")
    
    print("\n" + "=" * 60)
    print("MERGE COMPLETE")
    print("=" * 60)
    print("\nCreated files:")
    print(f"  - config/translations/en.json")
    print(f"  - config/translations/ru.json")
    print("\nNext step: Update translation_service.py to load from these files")


if __name__ == "__main__":
    merge_translations()


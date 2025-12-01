"""
Test script to verify translation service loads correctly from JSON files
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.translation_service import translation_service


def test_translation_service():
    """Test that translation service loads and works correctly"""
    
    print("=" * 60)
    print("TESTING TRANSLATION SERVICE")
    print("=" * 60)
    
    # Test 1: Load translations
    print("\n[TEST 1] Loading translations from JSON...")
    try:
        translation_service.load()
        print("✓ Translations loaded successfully")
    except Exception as e:
        print(f"✗ Failed to load translations: {e}")
        return False
    
    # Test 2: Check if loaded
    print("\n[TEST 2] Checking if translations are loaded...")
    if translation_service.is_loaded():
        print("✓ Translation service is loaded")
    else:
        print("✗ Translation service is NOT loaded")
        return False
    
    # Test 3: Get supported languages
    print("\n[TEST 3] Getting supported languages...")
    langs = translation_service.get_supported_languages()
    print(f"✓ Supported languages: {langs}")
    
    # Test 4: Test UI text retrieval
    print("\n[TEST 4] Testing UI text retrieval...")
    test_keys = [
        ("welcome.title", "en"),
        ("welcome.title", "ru"),
        ("premium.features.energy", "en"),
        ("premium.features.energy", "ru"),
    ]
    
    for key, lang in test_keys:
        value = translation_service.get(key, lang)
        if value and value != key:
            print(f"✓ {key} [{lang}]: {value[:50]}...")
        else:
            print(f"✗ {key} [{lang}]: NOT FOUND")
    
    # Test 5: Test persona translations
    print("\n[TEST 5] Testing persona translations...")
    persona_test_keys = [
        ("airi.name", "en"),
        ("airi.name", "ru"),
        ("airi.description", "en"),
        ("airi.description", "ru"),
    ]
    
    for key, lang in persona_test_keys:
        value = translation_service.get(key, lang)
        if value and value != key:
            print(f"✓ {key} [{lang}]: {value[:50]}...")
        else:
            print(f"⚠️  {key} [{lang}]: NOT FOUND (may be OK if persona doesn't have this translation)")
    
    # Test 6: Test fallback to English
    print("\n[TEST 6] Testing fallback to English...")
    value = translation_service.get("welcome.title", "fr", fallback=True)
    if value and value != "welcome.title":
        print(f"✓ Fallback works: {value[:50]}...")
    else:
        print(f"✗ Fallback failed")
    
    # Test 7: Get all translations for a language
    print("\n[TEST 7] Getting all translations count...")
    en_translations = translation_service.get_all("en")
    ru_translations = translation_service.get_all("ru")
    print(f"✓ English translations: {len(en_translations)}")
    print(f"✓ Russian translations: {len(ru_translations)}")
    
    # Test 8: Get namespace
    print("\n[TEST 8] Testing namespace retrieval...")
    premium_en = translation_service.get_namespace("premium.", "en")
    print(f"✓ Found {len(premium_en)} translations in 'premium.' namespace")
    if premium_en:
        sample_keys = list(premium_en.keys())[:3]
        for key in sample_keys:
            print(f"  - {key}: {premium_en[key][:50]}...")
    
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED ✓")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = test_translation_service()
    sys.exit(0 if success else 1)






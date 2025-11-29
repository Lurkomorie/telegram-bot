#!/usr/bin/env python3
"""
Check and update persona name translations that should be in Cyrillic
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.base import get_db
from app.db import crud
from app.db.models import Persona, Translation
from app.settings import settings
import requests


# Proper Russian translations/transliterations
PROPER_RU_TRANSLATIONS = {
    "Zenara": "Зенара",
    "Emilia": "Эмилия", 
    "Isabella": "Изабелла",
    "Talia": "Талия",
    "Sparkle": "Спаркл",
    "Airi": "Айри",
    "Lumi": "Луми",
    "Inferra": "Инферра",
    "Ekaterina": "Екатерина",
    "Eva": "Ева",
}


def translate_with_ai(name: str, openrouter_key: str) -> str:
    """Translate a name to Russian using OpenRouter API"""
    
    prompt = f"""Translate this female character name to Russian Cyrillic: "{name}"

Rules:
1. If it's a common international name, use the standard Russian transliteration (e.g., Emma → Эмма, Sophia → София)
2. If it's a Japanese name, use katakana-to-Cyrillic transliteration (e.g., Airi → Айри, Yuki → Юки)
3. If it's already a Russian name in Latin script, convert to Cyrillic (e.g., Ekaterina → Екатерина)
4. If it's a fantasy/fictional name, transliterate it phonetically to Cyrillic
5. Return ONLY the Russian Cyrillic name, nothing else

Name to translate: {name}
Russian name:"""
    
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {openrouter_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/yourusername/telegram-bot"
            },
            json={
                "model": "anthropic/claude-3.5-sonnet",
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 50
            },
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        translated = result['choices'][0]['message']['content'].strip()
        
        # Clean up any quotes or extra text
        translated = translated.strip('"\'').strip()
        
        return translated
        
    except Exception as e:
        print(f"   ⚠️  API translation failed: {e}")
        return None


def check_and_update_ru_names():
    """Check persona names and update those that aren't properly transliterated to Cyrillic"""
    print("=" * 70)
    print("CHECK AND UPDATE RUSSIAN PERSONA NAME TRANSLATIONS")
    print("=" * 70)
    print("\nChecking persona name translations for proper Cyrillic...\n")
    
    # Get OpenRouter API key from settings
    try:
        openrouter_key = settings.OPENROUTER_API_KEY
        if not openrouter_key:
            raise ValueError("OPENROUTER_API_KEY is empty")
    except Exception as e:
        print(f"❌ OPENROUTER_API_KEY not found in environment: {e}")
        return
    
    with get_db() as db:
        # Get all personas with keys
        personas = db.query(Persona).filter(Persona.key.isnot(None)).all()
        
        if not personas:
            print("❌ No personas with keys found in database")
            return
        
        print(f"📊 Found {len(personas)} personas with keys\n")
        
        needs_update = []
        
        for persona in personas:
            persona_key = persona.key
            translation_key = f"{persona_key}.name"
            
            # Get English and Russian translations
            en_trans = db.query(Translation).filter(
                Translation.key == translation_key,
                Translation.lang == 'en'
            ).first()
            
            ru_trans = db.query(Translation).filter(
                Translation.key == translation_key,
                Translation.lang == 'ru'
            ).first()
            
            if not en_trans or not ru_trans:
                print(f"⚠️  {persona_key}: Missing translations")
                continue
            
            en_name = en_trans.value
            ru_name = ru_trans.value
            
            # Check if Russian name contains only Latin characters (needs Cyrillic)
            has_cyrillic = any('\u0400' <= char <= '\u04FF' for char in ru_name)
            
            if not has_cyrillic:
                print(f"❌ {persona_key}: {en_name} → {ru_name} (NOT in Cyrillic!)")
                needs_update.append({
                    'persona_key': persona_key,
                    'translation_key': translation_key,
                    'english_name': en_name,
                    'current_ru_name': ru_name
                })
            else:
                print(f"✓  {persona_key}: {en_name} → {ru_name} (properly in Cyrillic)")
        
        if not needs_update:
            print("\n✅ All persona names are properly in Cyrillic!")
            return
        
        print(f"\n{'=' * 70}")
        print(f"UPDATING {len(needs_update)} NAMES TO CYRILLIC")
        print(f"{'=' * 70}\n")
        
        updated_count = 0
        
        for item in needs_update:
            english_name = item['english_name']
            persona_key = item['persona_key']
            translation_key = item['translation_key']
            current_ru = item['current_ru_name']
            
            # Check if we have a predefined translation
            if english_name in PROPER_RU_TRANSLATIONS:
                russian_name = PROPER_RU_TRANSLATIONS[english_name]
                print(f"📝 {persona_key}: {current_ru} → {russian_name} (from predefined list)")
            else:
                print(f"🤖 {persona_key}: {english_name} → translating with AI...")
                russian_name = translate_with_ai(english_name, openrouter_key)
                
                if russian_name:
                    print(f"   ✨ Result: {russian_name}")
                else:
                    print(f"   ❌ Failed to translate, keeping as: {current_ru}")
                    continue
            
            # Update the translation
            crud.create_or_update_translation(
                db,
                key=translation_key,
                lang='ru',
                value=russian_name,
                category='persona'
            )
            updated_count += 1
            print(f"   ✅ Updated in database\n")
        
        print("=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"✅ Total personas checked: {len(personas)}")
        print(f"✅ Already in Cyrillic: {len(personas) - len(needs_update)}")
        print(f"✅ Updated to Cyrillic: {updated_count}")
        print("\n💡 Next steps:")
        print("   1. Restart your application to reload the translation cache")
        print("   2. Test persona names in Russian language")
        print("=" * 70)


if __name__ == "__main__":
    try:
        check_and_update_ru_names()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)



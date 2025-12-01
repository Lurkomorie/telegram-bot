#!/usr/bin/env python3
"""
Find personas without Russian name translations and add them.
Uses OpenRouter to translate persona names from English to Russian.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.base import get_db
from app.db import crud
from app.db.models import Persona, Translation
from app.settings import settings
import json
import requests


# Common female names that typically stay the same or have known Russian equivalents
KNOWN_TRANSLATIONS = {
    "Airi": "Айри",
    "Yuki": "Юки",
    "Mika": "Мика",
    "Sakura": "Сакура",
    "Eva": "Ева",
    "Emma": "Эмма",
    "Sophia": "София",
    "Olivia": "Оливия",
    "Isabella": "Изабелла",
    "Ava": "Ава",
    "Mia": "Миа",
    "Luna": "Луна",
    "Aria": "Ария",
    "Elena": "Елена",
    "Nina": "Нина",
    "Victoria": "Виктория",
    "Diana": "Диана",
    "Anastasia": "Анастасия",
    "Maria": "Мария",
    "Anna": "Анна",
    "Natasha": "Наташа",
    "Katya": "Катя",
    "Dasha": "Даша",
    "Lena": "Лена",
    "Julia": "Юлия",
    "Veronika": "Вероника",
}


def translate_name_with_ai(name: str, openrouter_key: str) -> str:
    """Translate a name to Russian using OpenRouter API"""
    
    prompt = f"""Translate this female character name to Russian Cyrillic: "{name}"

Rules:
1. If it's a common international name, use the standard Russian transliteration (e.g., Emma → Эмма, Sophia → София)
2. If it's a Japanese name, use katakana-to-Cyrillic transliteration (e.g., Airi → Айри, Yuki → Юки)
3. If it's already a Russian name, return it as-is
4. If it's a fantasy/fictional name, transliterate it phonetically to Cyrillic
5. Return ONLY the Russian name, nothing else

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
        # Fallback: use phonetic transliteration
        return transliterate_phonetic(name)


def transliterate_phonetic(name: str) -> str:
    """Simple phonetic transliteration fallback"""
    # Basic Latin-to-Cyrillic mapping
    mapping = {
        'a': 'а', 'b': 'б', 'c': 'к', 'd': 'д', 'e': 'е', 'f': 'ф',
        'g': 'г', 'h': 'х', 'i': 'и', 'j': 'дж', 'k': 'к', 'l': 'л',
        'm': 'м', 'n': 'н', 'o': 'о', 'p': 'п', 'q': 'к', 'r': 'р',
        's': 'с', 't': 'т', 'u': 'у', 'v': 'в', 'w': 'в', 'x': 'кс',
        'y': 'й', 'z': 'з',
        'A': 'А', 'B': 'Б', 'C': 'К', 'D': 'Д', 'E': 'Е', 'F': 'Ф',
        'G': 'Г', 'H': 'Х', 'I': 'И', 'J': 'Дж', 'K': 'К', 'L': 'Л',
        'M': 'М', 'N': 'Н', 'O': 'О', 'P': 'П', 'Q': 'К', 'R': 'Р',
        'S': 'С', 'T': 'Т', 'U': 'У', 'V': 'В', 'W': 'В', 'X': 'Кс',
        'Y': 'Й', 'Z': 'З',
    }
    
    result = []
    for char in name:
        result.append(mapping.get(char, char))
    
    return ''.join(result)


def find_and_localize_missing_ru_names():
    """Find personas without Russian name translations and add them"""
    print("=" * 70)
    print("LOCALIZE MISSING RUSSIAN PERSONA NAMES")
    print("=" * 70)
    print("\nFinding personas without Russian name translations...\n")
    
    # Get OpenRouter API key from settings
    try:
        openrouter_key = settings.OPENROUTER_API_KEY
        if not openrouter_key:
            raise ValueError("OPENROUTER_API_KEY is empty")
    except Exception as e:
        print(f"❌ OPENROUTER_API_KEY not found in environment: {e}")
        return
    
    with get_db() as db:
        # Get all personas with keys (public personas)
        personas = db.query(Persona).filter(Persona.key.isnot(None)).all()
        
        if not personas:
            print("❌ No personas with keys found in database")
            return
        
        print(f"📊 Found {len(personas)} personas with keys\n")
        
        missing_translations = []
        
        for persona in personas:
            persona_key = persona.key
            translation_key = f"{persona_key}.name"
            
            # Check if Russian translation exists
            ru_trans = db.query(Translation).filter(
                Translation.key == translation_key,
                Translation.lang == 'ru'
            ).first()
            
            if ru_trans:
                print(f"✓  {persona_key}: {persona.name} → {ru_trans.value} (already exists)")
            else:
                # Check if English translation exists first
                en_trans = db.query(Translation).filter(
                    Translation.key == translation_key,
                    Translation.lang == 'en'
                ).first()
                
                if not en_trans:
                    print(f"⚠️  {persona_key}: No English translation found, using persona.name: {persona.name}")
                    english_name = persona.name
                else:
                    english_name = en_trans.value
                
                missing_translations.append({
                    'persona_key': persona_key,
                    'persona_id': persona.id,
                    'english_name': english_name,
                    'translation_key': translation_key
                })
                print(f"❌ {persona_key}: {english_name} (NO RUSSIAN TRANSLATION)")
        
        if not missing_translations:
            print("\n✅ All personas already have Russian name translations!")
            return
        
        print(f"\n{'=' * 70}")
        print(f"TRANSLATING {len(missing_translations)} NAMES TO RUSSIAN")
        print(f"{'=' * 70}\n")
        
        created_count = 0
        
        for item in missing_translations:
            english_name = item['english_name']
            persona_key = item['persona_key']
            translation_key = item['translation_key']
            
            # Check if we have a known translation
            if english_name in KNOWN_TRANSLATIONS:
                russian_name = KNOWN_TRANSLATIONS[english_name]
                print(f"📝 {persona_key}: {english_name} → {russian_name} (from known list)")
            else:
                print(f"🤖 {persona_key}: {english_name} → translating with AI...")
                russian_name = translate_name_with_ai(english_name, openrouter_key)
                print(f"   ✨ Result: {russian_name}")
            
            # Create the translation
            crud.create_or_update_translation(
                db,
                key=translation_key,
                lang='ru',
                value=russian_name,
                category='persona'
            )
            created_count += 1
            print(f"   ✅ Saved to database\n")
        
        print("=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"✅ Total personas checked: {len(personas)}")
        print(f"✅ Already had Russian translations: {len(personas) - len(missing_translations)}")
        print(f"✅ New Russian translations created: {created_count}")
        print("\n💡 Next steps:")
        print("   1. Restart your application to reload the translation cache")
        print("   2. Test persona names in Russian language")
        print("=" * 70)


if __name__ == "__main__":
    try:
        find_and_localize_missing_ru_names()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


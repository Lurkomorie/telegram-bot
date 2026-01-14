"""
Script to populate button_name for existing stories and add translations
Based on screenshots from the design specification
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.base import get_db
from app.db.models import Persona, PersonaHistoryStart, PersonaHistoryTranslation, Translation


# Button name mappings based on screenshots and actual DB story names
# Format: {partial_story_name: {button_name_ru, button_name_en}}
BUTTON_NAMES = {
    # Airi (shy_romantic)
    "Secret Cove": {"ru": "Бухта 🏖️", "en": "Cove 🏖️"},
    "Hidden Grove": {"ru": "Роща 🌿", "en": "Grove 🌿"},
    "Moonlit Lick": {"ru": "Луна 🥛", "en": "Moon 🥛"},
    "Dawn Stroll": {"ru": "Рассвет 🌅", "en": "Dawn 🌅"},
    
    # Sparkle
    "London Streets": {"ru": "Лондон 🌃", "en": "London 🌃"},
    "Gym Glow": {"ru": "Зал ⚡", "en": "Gym ⚡"},
    "Steamy Awakening": {"ru": "Душ 💦", "en": "Shower 💦"},
    
    # Lumi (sweet_girlfriend)
    "Angel's Glow": {"ru": "Ангел 😇", "en": "Angel 😇"},
    "Misty Haven": {"ru": "Туман 💧", "en": "Mist 💧"},
    "Rooftop Whisper": {"ru": "Крыша 🌟", "en": "Roof 🌟"},
    
    # Eva
    "Roadside": {"ru": "Дорога 🚗", "en": "Road 🚗"},
    "Rainy Night": {"ru": "Гостья 💕", "en": "Guest 💕"},
    "City Move-In": {"ru": "Город💖", "en": "City💖"},
    
    # Nyxa
    "Velvet Dominion": {"ru": "Бархат 🖤", "en": "Velvet 🖤"},
    "Masked Masquerade": {"ru": "Маска 🎭", "en": "Mask 🎭"},
    "Scarlet Chamber": {"ru": "Алый 🩸", "en": "Scarlet 🩸"},
    
    # Ekaterina
    "After-Class Stay": {"ru": "Занятия🏫", "en": "Class🏫"},
    "Cozy Evening Study": {"ru": "Вечер 📚", "en": "Evening 📚"},
    "Forgotten Privacy": {"ru": "В душе 🚿", "en": "Shower 🚿"},
    
    # Inferra
    "Steamy Shadows": {"ru": "Тени 🛁", "en": "Bath 🛁"},
    "Cellar Flames": {"ru": "Подвал 🍷", "en": "Cellar 🍷"},
    "Fiery Depths": {"ru": "Глубины🔥", "en": "Depths🔥"},
    
    # Zenara (amazon)
    "Highland Dawn": {"ru": "Горы 💧", "en": "Highland 💧"},
    "Dawn Peak Shadow": {"ru": "Пик 🏔️", "en": "Peak 🏔️"},
    "Desert Sentinel": {"ru": "Пустыня 🌅", "en": "Desert 🌅"},
    
    # Talia (hacker)
    "Whispering Rails": {"ru": "Поезд 🚂", "en": "Train 🚂"},
    "Balcony Secrets": {"ru": "Балкон 🌃", "en": "Balcony 🌃"},
    "Code in the Clouds": {"ru": "Код 🚀", "en": "Code 🚀"},
    
    # Emilia
    "Beach Yoga Dawn": {"ru": "Йога 🌅", "en": "Yoga 🌅"},
    "Sunset Lakeside": {"ru": "Озеро 🏖️", "en": "Lake 🏖️"},
    "Whispering Woods": {"ru": "Лес 🌲", "en": "Woods 🌲"},
    
    # Isabella
    "Dawn Office Intrigue": {"ru": "Офис 🌅", "en": "Office 🌅"},
    "Seaside Launch": {"ru": "Море 🌅", "en": "Sea 🌅"},
    "Vineyard Glow": {"ru": "Вино 🍷", "en": "Wine 🍷"},
}


def find_button_name(story_name: str) -> dict | None:
    """Find button name mapping based on story name"""
    if not story_name:
        return None
    
    story_lower = story_name.lower()
    for key, value in BUTTON_NAMES.items():
        if key.lower() in story_lower or story_lower in key.lower():
            return value
    return None


def seed_button_names():
    """Populate button_name for all stories"""
    with get_db() as db:
        # Get all personas with their histories
        personas = db.query(Persona).filter(Persona.visibility == 'public').all()
        
        print(f"Found {len(personas)} public personas")
        
        for persona in personas:
            print(f"\n📦 Processing persona: {persona.name} (key: {persona.key})")
            
            histories = db.query(PersonaHistoryStart).filter(
                PersonaHistoryStart.persona_id == persona.id
            ).all()
            
            for idx, history in enumerate(histories):
                print(f"  📖 Story {idx}: {history.name}")
                
                # Find button name based on story name
                button_mapping = find_button_name(history.name)
                
                if button_mapping:
                    # Update the main history record with English button_name
                    history.button_name = button_mapping["en"]
                    print(f"     ✅ Set button_name: {button_mapping['en']}")
                    
                    # Update or create Russian translation
                    ru_translation = db.query(PersonaHistoryTranslation).filter(
                        PersonaHistoryTranslation.history_id == history.id,
                        PersonaHistoryTranslation.language == 'ru'
                    ).first()
                    
                    if ru_translation:
                        ru_translation.button_name = button_mapping["ru"]
                        print(f"     ✅ Updated RU translation button_name: {button_mapping['ru']}")
                    else:
                        # Create new translation record if needed
                        new_translation = PersonaHistoryTranslation(
                            history_id=history.id,
                            language='ru',
                            button_name=button_mapping["ru"]
                        )
                        db.add(new_translation)
                        print(f"     ➕ Created RU translation with button_name: {button_mapping['ru']}")
                    
                    # Also add to unified translations table
                    if persona.key:
                        # Russian button_name
                        trans_key_ru = f"{persona.key}.history.button_name-{idx}"
                        existing_ru = db.query(Translation).filter(
                            Translation.key == trans_key_ru,
                            Translation.lang == 'ru'
                        ).first()
                        
                        if existing_ru:
                            existing_ru.value = button_mapping["ru"]
                        else:
                            new_trans_ru = Translation(
                                key=trans_key_ru,
                                lang='ru',
                                value=button_mapping["ru"],
                                category='history'
                            )
                            db.add(new_trans_ru)
                        
                        # English button_name
                        trans_key_en = f"{persona.key}.history.button_name-{idx}"
                        existing_en = db.query(Translation).filter(
                            Translation.key == trans_key_en,
                            Translation.lang == 'en'
                        ).first()
                        
                        if existing_en:
                            existing_en.value = button_mapping["en"]
                        else:
                            new_trans_en = Translation(
                                key=trans_key_en,
                                lang='en',
                                value=button_mapping["en"],
                                category='history'
                            )
                            db.add(new_trans_en)
                        
                        print(f"     ✅ Added translations table entries")
                else:
                    print(f"     ⚠️ No button_name mapping found for: {history.name}")
        
        db.commit()
        print("\n✅ All button_names populated successfully!")


if __name__ == "__main__":
    seed_button_names()

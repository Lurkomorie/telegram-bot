"""
Add character creation translations to database
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.db.base import get_db
from app.db import crud


# Character creation translations
CHARACTER_CREATION_TRANSLATIONS = {
    # Hair colors
    'characterCreation.hairColor.title': {
        'en': 'Hair Color',
        'ru': 'Цвет волос'
    },
    'characterCreation.hairColor.black': {
        'en': 'Black',
        'ru': 'Черный'
    },
    'characterCreation.hairColor.brown': {
        'en': 'Brunette',
        'ru': 'Брюнетка'
    },
    'characterCreation.hairColor.blonde': {
        'en': 'Blonde',
        'ru': 'Блондинка'
    },
    'characterCreation.hairColor.red': {
        'en': 'Redhead',
        'ru': 'Рыжая'
    },
    'characterCreation.hairColor.white': {
        'en': 'White',
        'ru': 'Белый'
    },
    'characterCreation.hairColor.pink': {
        'en': 'Pink',
        'ru': 'Розовый'
    },
    'characterCreation.hairColor.blue': {
        'en': 'Blue',
        'ru': 'Синий'
    },
    'characterCreation.hairColor.green': {
        'en': 'Green',
        'ru': 'Зеленый'
    },
    'characterCreation.hairColor.purple': {
        'en': 'Purple',
        'ru': 'Фиолетовый'
    },
    'characterCreation.hairColor.multicolor': {
        'en': 'Multicolor',
        'ru': 'Разноцветный'
    },
    
    # Hair styles
    'characterCreation.hairStyle.title': {
        'en': 'Hair Style',
        'ru': 'Прическа'
    },
    'characterCreation.hairStyle.longStraight': {
        'en': 'Long Straight',
        'ru': 'Длинные прямые'
    },
    'characterCreation.hairStyle.longWavy': {
        'en': 'Long Wavy',
        'ru': 'Длинные волнистые'
    },
    'characterCreation.hairStyle.short': {
        'en': 'Short',
        'ru': 'Короткие'
    },
    'characterCreation.hairStyle.ponytail': {
        'en': 'Ponytail',
        'ru': 'Хвост'
    },
    'characterCreation.hairStyle.braided': {
        'en': 'Braided',
        'ru': 'Косы'
    },
    'characterCreation.hairStyle.curly': {
        'en': 'Curly',
        'ru': 'Кудрявые'
    },
    
    # Eye colors
    'characterCreation.eyeColor.title': {
        'en': 'Eye Color',
        'ru': 'Цвет глаз'
    },
    'characterCreation.eyeColor.brown': {
        'en': 'Brown',
        'ru': 'Карие'
    },
    'characterCreation.eyeColor.blue': {
        'en': 'Blue',
        'ru': 'Голубые'
    },
    'characterCreation.eyeColor.green': {
        'en': 'Green',
        'ru': 'Зеленые'
    },
    'characterCreation.eyeColor.hazel': {
        'en': 'Hazel',
        'ru': 'Ореховые'
    },
    'characterCreation.eyeColor.gray': {
        'en': 'Gray',
        'ru': 'Серые'
    },
    
    # Body types
    'characterCreation.bodyType.title': {
        'en': 'Body Type',
        'ru': 'Тип тела'
    },
    'characterCreation.bodyType.slim': {
        'en': 'Slim',
        'ru': 'Стройная'
    },
    'characterCreation.bodyType.athletic': {
        'en': 'Athletic',
        'ru': 'Спортивная'
    },
    'characterCreation.bodyType.curvy': {
        'en': 'Curvy',
        'ru': 'Пышная'
    },
    'characterCreation.bodyType.voluptuous': {
        'en': 'Voluptuous',
        'ru': 'Полная'
    },
    
    # Proportions
    'characterCreation.proportions.title': {
        'en': 'Proportions',
        'ru': 'Пропорции'
    },
    'characterCreation.proportions.breastSize': {
        'en': 'Breast Size',
        'ru': 'Размер груди'
    },
    'characterCreation.proportions.buttSize': {
        'en': 'Butt Size',
        'ru': 'Размер ягодиц'
    },
    'characterCreation.proportions.small': {
        'en': 'Small',
        'ru': 'Маленький'
    },
    'characterCreation.proportions.medium': {
        'en': 'Medium',
        'ru': 'Средний'
    },
    'characterCreation.proportions.large': {
        'en': 'Large',
        'ru': 'Большой'
    },
    'characterCreation.proportions.nextButton': {
        'en': 'NEXT',
        'ru': 'ДАЛЕЕ'
    },
    
    # Final details
    'characterCreation.final.title': {
        'en': 'Final Details',
        'ru': 'Финальные детали'
    },
    'characterCreation.final.namePlaceholder': {
        'en': 'Enter her name...',
        'ru': 'Введите её имя...'
    },
    'characterCreation.final.nameCounter': {
        'en': '{current}/20',
        'ru': '{current}/20'
    },
    'characterCreation.final.personalityLabel': {
        'en': 'Personality & Relationship',
        'ru': 'Личность и отношения'
    },
    'characterCreation.final.premiumBadge': {
        'en': 'Premium',
        'ru': 'Премиум'
    },
    'characterCreation.final.descriptionHint': {
        'en': 'Describe her personality, your relationship, background...',
        'ru': 'Опишите её личность, ваши отношения, биографию...'
    },
    'characterCreation.final.descriptionPlaceholder': {
        'en': "Example: You're my caring girlfriend who loves gaming and coffee. We've been dating for 2 years...",
        'ru': 'Пример: Ты моя заботливая девушка, которая любит игры и кофе. Мы встречаемся уже 2 года...'
    },
    'characterCreation.final.descriptionCounter': {
        'en': '{current}/{max}',
        'ru': '{current}/{max}'
    },
    'characterCreation.final.createButton': {
        'en': 'Create Girlfriend',
        'ru': 'Создать девушку'
    },
    'characterCreation.final.creating': {
        'en': 'Creating...',
        'ru': 'Создание...'
    },
    
    # Errors
    'characterCreation.errors.nameRequired': {
        'en': 'Please enter a name',
        'ru': 'Пожалуйста, введите имя'
    },
    'characterCreation.errors.descriptionRequired': {
        'en': 'Please describe your girlfriend',
        'ru': 'Пожалуйста, опишите свою девушку'
    },
    'characterCreation.errors.insufficientTokens': {
        'en': 'Insufficient tokens. Need {cost}, have {have}',
        'ru': 'Недостаточно токенов. Нужно {cost}, есть {have}'
    },
    'characterCreation.errors.creationFailed': {
        'en': 'Failed to create character. Please try again.',
        'ru': 'Не удалось создать персонажа. Пожалуйста, попробуйте еще раз.'
    },
    'characterCreation.success': {
        'en': '{name} created successfully! 💕\nGenerating portrait...',
        'ru': '{name} успешно создана! 💕\nГенерация портрета...'
    },
}


def add_translations():
    """Add character creation translations to database"""
    with get_db() as db:
        total_added = 0
        total_updated = 0
        
        print("📝 Adding character creation translations...\n")
        
        for key, translations in CHARACTER_CREATION_TRANSLATIONS.items():
            print(f"   {key}")
            
            for lang, value in translations.items():
                # Check if translation already exists
                existing = crud.get_translation(db, key, lang)
                
                if existing:
                    # Update existing
                    crud.create_or_update_translation(db, key, lang, value, category='miniapp')
                    total_updated += 1
                else:
                    # Create new
                    crud.create_or_update_translation(db, key, lang, value, category='miniapp')
                    total_added += 1
        
        print(f"\n✅ Translations: {total_added} created, {total_updated} updated")
        print(f"   Total keys: {len(CHARACTER_CREATION_TRANSLATIONS)}")
        print(f"   Languages: en, ru")


if __name__ == "__main__":
    add_translations()
    print("\n✨ Done! Now:")
    print("1. Export translations: python scripts/export_translations.py")
    print("2. Rebuild miniapp: cd miniapp && npm run build")


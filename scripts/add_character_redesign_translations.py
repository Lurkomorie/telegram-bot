"""
Add translations for character redesign feature
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.base import get_db
from app.db import crud

# Translation keys for character redesign feature
TRANSLATIONS = {
    "gallery.createCharacter.title": {
        "en": "Your character",
        "ru": "Ваш персонаж",
        "fr": "Votre personnage",
        "de": "Dein Charakter",
        "es": "Tu personaje"
    },
    "gallery.createCharacter.subtitle": {
        "en": "Will become anyone you want",
        "ru": "Станет кем угодно",
        "fr": "Deviendra qui vous voulez",
        "de": "Wird zu jedem, den du willst",
        "es": "Se convertirá en quien quieras"
    },
    "gallery.createCharacter.free": {
        "en": "Create free",
        "ru": "Создать бесплатно",
        "fr": "Créer gratuitement",
        "de": "Kostenlos erstellen",
        "es": "Crear gratis"
    },
    "gallery.customTag": {
        "en": "Yours",
        "ru": "Ваш",
        "fr": "Vôtre",
        "de": "Dein",
        "es": "Tuyo"
    },
    "characterPage.selectLocation": {
        "en": "Choose where to start",
        "ru": "Выберите место",
        "fr": "Choisissez où commencer",
        "de": "Wähle, wo du beginnen möchtest",
        "es": "Elige dónde empezar"
    },
    "characterPage.locations.home": {
        "en": "Home",
        "ru": "Дома",
        "fr": "Maison",
        "de": "Zuhause",
        "es": "Casa"
    },
    "characterPage.locations.office": {
        "en": "Office",
        "ru": "Офис",
        "fr": "Bureau",
        "de": "Büro",
        "es": "Oficina"
    },
    "characterPage.locations.school": {
        "en": "School",
        "ru": "Школа",
        "fr": "École",
        "de": "Schule",
        "es": "Escuela"
    },
    "characterPage.locations.cafe": {
        "en": "Cafe",
        "ru": "Кафе",
        "fr": "Café",
        "de": "Café",
        "es": "Cafetería"
    },
    "characterPage.locations.gym": {
        "en": "Gym",
        "ru": "Спортзал",
        "fr": "Salle de sport",
        "de": "Fitnessstudio",
        "es": "Gimnasio"
    },
    "characterPage.locations.park": {
        "en": "Park",
        "ru": "Парк",
        "fr": "Parc",
        "de": "Park",
        "es": "Parque"
    },
    "characterPage.createCustomButton": {
        "en": "Create custom",
        "ru": "Своя история",
        "fr": "Créer une histoire personnalisée",
        "de": "Eigene Geschichte erstellen",
        "es": "Crear personalizado"
    },
    "customStory.title": {
        "en": "Create your story with {name}",
        "ru": "Создайте свою историю с {name}",
        "fr": "Créez votre histoire avec {name}",
        "de": "Erstelle deine Geschichte mit {name}",
        "es": "Crea tu historia con {name}"
    },
    "customStory.startButton": {
        "en": "Start story",
        "ru": "Начать историю",
        "fr": "Commencer l'histoire",
        "de": "Geschichte beginnen",
        "es": "Comenzar historia"
    },
    "customStory.placeholder": {
        "en": "Describe the scenario you want to experience with {name}. Where are you? What's happening? What's the mood? Be creative! (e.g., 'We're hiking in the mountains when we find a hidden waterfall...')",
        "ru": "Опишите сценарий, который хотите пережить с {name}. Где вы? Что происходит? Какое настроение? Будьте креативны! (например, 'Мы идем в горы и находим скрытый водопад...')",
        "fr": "Décrivez le scénario que vous souhaitez vivre avec {name}. Où êtes-vous ? Que se passe-t-il ? Quelle est l'ambiance ? Soyez créatif ! (par exemple, 'Nous faisons de la randonnée en montagne quand nous trouvons une cascade cachée...')",
        "de": "Beschreibe das Szenario, das du mit {name} erleben möchtest. Wo bist du? Was passiert? Welche Stimmung herrscht? Sei kreativ! (z.B. 'Wir wandern in den Bergen und finden einen versteckten Wasserfall...')",
        "es": "Describe el escenario que quieres experimentar con {name}. ¿Dónde estás? ¿Qué está pasando? ¿Cuál es el ambiente? ¡Sé creativo! (por ejemplo, 'Estamos haciendo senderismo en las montañas cuando encontramos una cascada oculta...')"
    },
    "characterPage.deleteMenu": {
        "en": "Delete",
        "ru": "Удалить",
        "fr": "Supprimer",
        "de": "Löschen",
        "es": "Eliminar"
    },
    "characterPage.deleteConfirm.title": {
        "en": "Delete {name}?",
        "ru": "Удалить {name}?",
        "fr": "Supprimer {name} ?",
        "de": "{name} löschen?",
        "es": "¿Eliminar {name}?"
    },
    "characterPage.deleteConfirm.message": {
        "en": "This will permanently delete this character. This cannot be undone.",
        "ru": "Это навсегда удалит персонажа. Это действие нельзя отменить.",
        "fr": "Cela supprimera définitivement ce personnage. Cette action ne peut pas être annulée.",
        "de": "Dies wird diesen Charakter dauerhaft löschen. Dies kann nicht rückgängig gemacht werden.",
        "es": "Esto eliminará permanentemente este personaje. Esta acción no se puede deshacer."
    },
    "characterPage.deleteConfirm.cancel": {
        "en": "Cancel",
        "ru": "Отмена",
        "fr": "Annuler",
        "de": "Abbrechen",
        "es": "Cancelar"
    },
    "characterPage.deleteConfirm.confirm": {
        "en": "Delete",
        "ru": "Удалить",
        "fr": "Supprimer",
        "de": "Löschen",
        "es": "Eliminar"
    }
}


def main():
    """Add all translations to database"""
    print("Adding character redesign translations to database...")
    
    with get_db() as db:
        for key, translations in TRANSLATIONS.items():
            for lang, value in translations.items():
                crud.create_or_update_translation(
                    db,
                    key=key,
                    lang=lang,
                    value=value,
                    category="miniapp"
                )
                print(f"  ✓ Added {key} ({lang})")
    
    print(f"\n✅ Successfully added {len(TRANSLATIONS)} translation keys across 5 languages")
    print("\nNext steps:")
    print("1. Run: python scripts/generate_miniapp_translations.py")
    print("2. Rebuild miniapp: cd miniapp && npm run build")


if __name__ == "__main__":
    main()



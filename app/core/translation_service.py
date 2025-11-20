"""
Translation Service - Unified translation management with in-memory caching
Provides a clean API for accessing all translations (UI texts, personas, histories)
"""
from typing import Dict, Optional
from threading import Lock


class TranslationService:
    """Singleton service for managing translations with in-memory cache"""
    
    def __init__(self):
        self._cache: Dict[str, Dict[str, str]] = {}  # {lang: {key: value}}
        self._loaded = False
        self._lock = Lock()  # Thread-safe cache updates
    
    def load(self):
        """Load all translations from database into memory cache"""
        from app.db.base import get_db
        from app.db import crud
        
        print("[TRANSLATION-SERVICE] 📦 Loading translations from database...")
        
        with self._lock:
            # Clear existing cache
            self._cache = {}
            
            # Load all translations from DB
            with get_db() as db:
                all_translations = crud.get_all_translations(db)
                
                # Organize by language
                for translation in all_translations:
                    lang = translation.lang
                    key = translation.key
                    value = translation.value
                    
                    if lang not in self._cache:
                        self._cache[lang] = {}
                    
                    self._cache[lang][key] = value
            
            self._loaded = True
            
            # Log statistics
            total_translations = sum(len(keys) for keys in self._cache.values())
            languages = list(self._cache.keys())
            print(f"[TRANSLATION-SERVICE] ✅ Loaded {total_translations} translations across {len(languages)} languages: {languages}")
    
    def get(self, key: str, lang: str = 'en', fallback: bool = True) -> str:
        """Get single translation with optional fallback to English
        
        Args:
            key: Translation key (e.g., "airi.name", "welcome.title")
            lang: Language code (default: 'en')
            fallback: If True and translation not found in requested language, try English
        
        Returns:
            Translated text or the key itself if not found
        """
        if not self._loaded:
            print(f"[TRANSLATION-SERVICE] ⚠️  Cache not loaded, returning key: {key}")
            return key
        
        # Try requested language
        if lang in self._cache and key in self._cache[lang]:
            return self._cache[lang][key]
        
        # Fallback to English if enabled
        if fallback and lang != 'en' and 'en' in self._cache and key in self._cache['en']:
            return self._cache['en'][key]
        
        # Return key itself if not found (makes missing translations obvious)
        return key
    
    def get_all(self, lang: str) -> Dict[str, str]:
        """Get all translations for a language
        
        Args:
            lang: Language code
        
        Returns:
            Dictionary of {key: value} for the language, or empty dict if not found
        """
        if not self._loaded:
            return {}
        
        return self._cache.get(lang, {}).copy()
    
    def get_namespace(self, prefix: str, lang: str) -> Dict[str, str]:
        """Get all translations with keys starting with a prefix
        
        Args:
            prefix: Key prefix (e.g., "airi.", "welcome.")
            lang: Language code
        
        Returns:
            Dictionary of {key: value} for keys matching the prefix
        """
        if not self._loaded:
            return {}
        
        if lang not in self._cache:
            return {}
        
        return {
            key: value
            for key, value in self._cache[lang].items()
            if key.startswith(prefix)
        }
    
    def reload(self):
        """Refresh cache from database
        
        This is called when translations are updated via the admin UI
        """
        print("[TRANSLATION-SERVICE] 🔄 Reloading translations...")
        self.load()
    
    def is_loaded(self) -> bool:
        """Check if cache is populated
        
        Returns:
            True if translations have been loaded
        """
        return self._loaded
    
    def get_supported_languages(self) -> list:
        """Get list of supported language codes
        
        Returns:
            List of language codes
        """
        return ['en', 'ru']


# Global singleton instance
translation_service = TranslationService()


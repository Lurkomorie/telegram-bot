import { createContext, useContext, useState, useEffect } from 'react';
import WebApp from '@twa-dev/sdk';
import { fetchUserLanguage, updateUserLanguage } from '../api';

// Import translation files
import en from '../locales/en.json';
import ru from '../locales/ru.json';
import fr from '../locales/fr.json';
import de from '../locales/de.json';
import es from '../locales/es.json';

const translations = {
  en,
  ru,
  fr,
  de,
  es,
};

const SUPPORTED_LANGUAGES = ['en', 'ru', 'fr', 'de', 'es'];
const DEFAULT_LANGUAGE = 'en';

const TranslationContext = createContext();

/**
 * TranslationProvider
 * Manages language state and provides translation function to all components
 */
export function TranslationProvider({ children }) {
  const [language, setLanguage] = useState(DEFAULT_LANGUAGE);
  const [isLoading, setIsLoading] = useState(true);
  const [languageChangeListeners, setLanguageChangeListeners] = useState([]);

  useEffect(() => {
    initializeLanguage();
  }, []);

  async function initializeLanguage() {
    try {
      // Check for manual language override first (user selected from dropdown)
      const manualOverride = localStorage.getItem('manualLanguageOverride');
      if (manualOverride && SUPPORTED_LANGUAGES.includes(manualOverride)) {
        console.log(`✅ Language from manual override: ${manualOverride}`);
        setLanguage(manualOverride);
        setIsLoading(false);
        return; // Use manual selection, skip everything else
      }

      // Get fresh language from Telegram (instant, no API call)
      const telegramLanguage = WebApp.initDataUnsafe?.user?.language_code;
      const normalizedTelegramLanguage = normalizeLanguage(telegramLanguage);
      
      // Get cached language
      const cachedLanguage = localStorage.getItem('userLanguage');
      
      // If Telegram language matches cache, use cache immediately (skip API call)
      if (cachedLanguage === normalizedTelegramLanguage) {
        console.log(`✅ Language from cache: ${cachedLanguage}`);
        setLanguage(cachedLanguage);
        setIsLoading(false);
        return; // Skip API call - cache is correct
      }
      
      // Language changed or no cache - update from backend
      console.log(`🌐 Language update needed: ${cachedLanguage || 'none'} → ${normalizedTelegramLanguage}`);
      
      const initData = WebApp.initData;
      if (initData) {
        try {
          // Call API to update user language in DB and get confirmation
          const { language: userLanguage } = await fetchUserLanguage(initData);
          const normalizedLanguage = normalizeLanguage(userLanguage);
          setLanguage(normalizedLanguage);
          localStorage.setItem('userLanguage', normalizedLanguage);
          console.log(`✅ Language updated: ${normalizedLanguage}`);
        } catch (error) {
          // API failed, use Telegram language directly
          console.warn('API call failed, using Telegram language directly:', error);
          setLanguage(normalizedTelegramLanguage);
          localStorage.setItem('userLanguage', normalizedTelegramLanguage);
        }
      } else {
        // No initData (development), use Telegram SDK
        setLanguage(normalizedTelegramLanguage);
        localStorage.setItem('userLanguage', normalizedTelegramLanguage);
      }
    } catch (error) {
      console.error('Failed to initialize language:', error);
      // Fallback: Try Telegram language, then cache, then default
      const telegramLanguage = WebApp.initDataUnsafe?.user?.language_code;
      const normalizedTelegramLanguage = normalizeLanguage(telegramLanguage);
      
      if (normalizedTelegramLanguage !== DEFAULT_LANGUAGE) {
        setLanguage(normalizedTelegramLanguage);
      } else {
        const cachedLanguage = localStorage.getItem('userLanguage');
        setLanguage(cachedLanguage && SUPPORTED_LANGUAGES.includes(cachedLanguage) ? cachedLanguage : DEFAULT_LANGUAGE);
      }
    } finally {
      setIsLoading(false);
    }
  }

  function normalizeLanguage(languageCode) {
    if (!languageCode) return DEFAULT_LANGUAGE;
    
    // Extract base language code (e.g., 'en-US' -> 'en')
    const baseLang = languageCode.toLowerCase().split('-')[0];
    
    // Return if supported, otherwise default
    return SUPPORTED_LANGUAGES.includes(baseLang) ? baseLang : DEFAULT_LANGUAGE;
  }

  /**
   * Manually change language (user selected from dropdown)
   * @param {string} newLanguage - Language code (e.g., 'en', 'ru', 'fr')
   */
  async function changeLanguage(newLanguage) {
    if (!SUPPORTED_LANGUAGES.includes(newLanguage)) {
      console.warn(`Unsupported language: ${newLanguage}`);
      return;
    }

    console.log(`🌐 Manual language change: ${language} → ${newLanguage}`);
    
    // Set manual override flag
    localStorage.setItem('manualLanguageOverride', newLanguage);
    localStorage.setItem('userLanguage', newLanguage);
    setLanguage(newLanguage);

    // Update backend (important for bot to also use new language)
    const initData = WebApp.initData;
    if (initData) {
      try {
        await updateUserLanguage(newLanguage, initData);
        console.log(`✅ Backend updated to: ${newLanguage}`);
      } catch (err) {
        console.warn('Failed to update language in backend:', err);
      }
    }

    // Notify all listeners that language has changed
    console.log(`📢 Notifying ${languageChangeListeners.length} language change listeners`);
    languageChangeListeners.forEach(listener => listener(newLanguage));
  }

  /**
   * Subscribe to language changes
   * @param {Function} callback - Called when language changes
   * @returns {Function} Unsubscribe function
   */
  function onLanguageChange(callback) {
    setLanguageChangeListeners(prev => [...prev, callback]);
    // Return unsubscribe function
    return () => {
      setLanguageChangeListeners(prev => prev.filter(cb => cb !== callback));
    };
  }

  /**
   * Get translated text by dot-notation key path
   * @param {string} keyPath - Dot-separated path (e.g., 'app.ageVerification.title')
   * @returns {string} Translated text
   */
  function t(keyPath) {
    const keys = keyPath.split('.');
    let value = translations[language];

    for (const key of keys) {
      if (value && typeof value === 'object' && key in value) {
        value = value[key];
      } else {
        // Fallback to English if key not found
        console.warn(`Translation key not found: ${keyPath} for language ${language}, falling back to English`);
        value = translations[DEFAULT_LANGUAGE];
        for (const k of keys) {
          if (value && typeof value === 'object' && k in value) {
            value = value[k];
          } else {
            console.error(`Translation key not found even in fallback: ${keyPath}`);
            return keyPath; // Return key path as fallback
          }
        }
        break;
      }
    }

    return value;
  }

  const value = {
    language,
    changeLanguage,
    onLanguageChange,
    t,
    isLoading,
    supportedLanguages: SUPPORTED_LANGUAGES,
  };

  return (
    <TranslationContext.Provider value={value}>
      {children}
    </TranslationContext.Provider>
  );
}

/**
 * useTranslation hook
 * Provides access to translation function and current language
 * @returns {{ t: Function, language: string, isLoading: boolean }}
 */
export function useTranslation() {
  const context = useContext(TranslationContext);
  if (!context) {
    throw new Error('useTranslation must be used within a TranslationProvider');
  }
  return context;
}


import { useTranslation } from '../i18n/TranslationContext';
import './LanguagePage.css';

/**
 * LanguagePage Component
 * Displays language selection options
 */
export default function LanguagePage() {
  const { language, changeLanguage, supportedLanguages, t } = useTranslation();

  // Language display names
  const languageDisplayNames = {
    en: { native: 'English', english: 'English' },
    ru: { native: 'Русский', english: 'Russian' },
  };

  return (
    <div className="language-page">
      <div className="language-list">
        {supportedLanguages.map((lang) => (
          <button
            key={lang}
            className={`language-item ${language === lang ? 'active' : ''}`}
            onClick={() => changeLanguage(lang)}
          >
            <div className="language-text">
              <div className="language-name-english">{languageDisplayNames[lang].english}</div>
              <div className="language-name-native">{languageDisplayNames[lang].native}</div>
            </div>
            <div className="language-selector">
              {language === lang && (
                <svg className="checkmark-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                  <polyline points="20 6 9 17 4 12"></polyline>
                </svg>
              )}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}


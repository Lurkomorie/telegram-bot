import { useTranslation } from '../i18n/TranslationContext';
import './SettingsPage.css';

/**
 * SettingsPage Component
 * Shows current plan status, language selector button, and upgrade button
 */
export default function SettingsPage({ energy, onNavigate }) {
  const { t, language } = useTranslation();

  const currentPlanName = energy.is_premium ? t('settings.currentPlan.premium') : t('settings.currentPlan.free');
  const currentLanguageName = t(`settings.languageNames.${language}`);

  return (
    <div className="settings-page">
      {/* Current Plan Section */}
      <div className="settings-section">
        <h3 className="section-title">{t('settings.plan.title')}</h3>
        <div className="plan-display">
          <div className="plan-badge">
            {energy.is_premium && <span className="premium-icon">💎</span>}
            <span className="plan-name">{currentPlanName}</span>
          </div>
          {!energy.is_premium && (
            <button className="upgrade-plans-button" onClick={() => onNavigate('plans')}>
              {t('settings.plan.upgradePlans')}
            </button>
          )}
        </div>
      </div>

      {/* Language Section */}
      <div className="settings-section">
        <h3 className="section-title">{t('settings.language.title')}</h3>
        <button className="language-selector-button" onClick={() => onNavigate('language')}>
          <span className="language-name">{currentLanguageName}</span>
          <svg className="chevron-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M9 18l6-6-6-6"/>
          </svg>
        </button>
      </div>
    </div>
  );
}





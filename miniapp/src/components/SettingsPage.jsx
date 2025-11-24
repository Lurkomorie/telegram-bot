import lightningIcon from '../assets/lightning.png';
import premiumIcon from '../assets/premium.png';
import { useTranslation } from '../i18n/TranslationContext';
import './SettingsPage.css';

/**
 * SettingsPage Component
 * Shows current plan status, language selector button, and upgrade button
 */
export default function SettingsPage({ tokens, onNavigate }) {
  const { t, language } = useTranslation();

  // Map tier to display name
  const tierNames = {
    'free': t('settings.currentPlan.free'),
    'plus': 'Plus',
    'premium': 'Premium', 
    'pro': 'Pro',
    'legendary': 'Legendary'
  };
  
  const currentPlanName = tokens?.is_premium ? tierNames[tokens.premium_tier] || 'Premium' : t('settings.currentPlan.free');
  const currentLanguageName = t(`settings.languageNames.${language}`);

  return (
    <div className="settings-page">
      {/* Current Plan Section */}
      <div className="settings-section">
        <h3 className="section-title">
          <img src={premiumIcon} alt="premium" className="section-title-icon" />
          {t('settings.plan.title')}
        </h3>
        <div className="plan-display">
          <div className="plan-badge">
            {tokens?.is_premium && <span className="premium-icon">💎</span>}
            <span className="plan-name">{currentPlanName}</span>
          </div>
        </div>
        <button className="upgrade-plans-button" onClick={() => onNavigate('premium')}>
          Премиум подписки
        </button>
      </div>

      {/* Tokens Button */}
      <div className="settings-section">
        <button className="settings-action-button tokens-button" onClick={() => onNavigate('tokens')}>
          <img src={lightningIcon} alt="energy" className="button-icon" />
          <span className="button-text">Купить энергию</span>
          <svg className="chevron-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M9 18l6-6-6-6"/>
          </svg>
        </button>
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






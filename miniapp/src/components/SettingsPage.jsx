// import WebApp from '@twa-dev/sdk';  // VOICE DISABLED
// import { Mic } from 'lucide-react';  // VOICE DISABLED
import { useTranslation } from '../i18n/TranslationContext';
import giftIcon from '../assets/gift.webp';
import lightningIcon from '../assets/lightning.webp';
import premiumIcon from '../assets/premium.webp';
import './SettingsPage.css';

// API base URL
// const API_BASE = import.meta.env.VITE_API_URL || '';  // VOICE DISABLED

/**
 * SettingsPage Component
 * Shows current plan status, language selector button, and upgrade button
 */
export default function SettingsPage({ tokens, onNavigate /*, hasVoiceSupport = false */ }) {
  const { t, language } = useTranslation();
  
  // VOICE DISABLED - all voice-related state and handlers commented out
  // const [voiceEnabled, setVoiceEnabled] = useState(tokens?.voice_enabled ?? false);
  // useEffect(() => {
  //   if (tokens?.voice_enabled !== undefined) {
  //     setVoiceEnabled(tokens.voice_enabled);
  //   }
  // }, [tokens?.voice_enabled]);
  // const handleVoiceToggle = () => {
  //   const newValue = !voiceEnabled;
  //   setVoiceEnabled(newValue);
  //   fetch(`${API_BASE}/api/miniapp/user/update-voice-settings`, {
  //     method: 'POST',
  //     headers: {
  //       'Content-Type': 'application/json',
  //       'X-Telegram-Init-Data': WebApp.initData,
  //     },
  //     body: JSON.stringify({ voice_enabled: newValue }),
  //   }).catch(err => console.error('Failed to sync voice settings:', err));
  // };

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
          {t('settings.premiumSubscriptions')}
        </button>
      </div>

      {/* Energy & Friends Section */}
      <div className="settings-section">
        <button className="settings-action-button friends-button" onClick={() => onNavigate('referrals')}>
          <img src={giftIcon} alt="gift" className="button-icon" />
          <span className="button-text">{t('settings.friends')}</span>
          <svg className="chevron-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M9 18l6-6-6-6"/>
          </svg>
        </button>
        <button className="settings-action-button tokens-button" onClick={() => onNavigate('tokens')}>
          <img src={lightningIcon} alt="energy" className="button-icon" />
          <span className="button-text">{t('settings.buyEnergy')}</span>
          <svg className="chevron-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M9 18l6-6-6-6"/>
          </svg>
        </button>
        {/* VOICE DISABLED
        {hasVoiceSupport && (
          <div className="voice-row">
            <Mic size={20} className="voice-icon" />
            <span className="voice-label">{t('settings.voice.title')}</span>
            <div 
              className={`toggle ${voiceEnabled ? 'on' : 'off'}`}
              onClick={handleVoiceToggle}
            >
              <div className="toggle-knob" />
            </div>
          </div>
        )}
        */}
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






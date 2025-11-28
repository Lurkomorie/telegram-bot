import WebApp from '@twa-dev/sdk';
import { useCallback, useEffect, useState } from 'react';
import { checkAgeVerification, claimDailyBonus, fetchPersonaHistories, fetchPersonas, fetchUserEnergy, selectScenario, trackEvent, verifyAge } from './api';
import './App.css';
import clockIcon from './assets/clock.svg';
import giftIcon from './assets/gift.png';
import lightningIcon from './assets/lightning.png';
import premiumIcon from './assets/premium.png';
import BottomNav from './components/BottomNav';
import CheckoutPage from './components/CheckoutPage';
import HistorySelection from './components/HistorySelection';
import LanguagePage from './components/LanguagePage';
import PersonasGallery from './components/PersonasGallery';
import PlansPage from './components/PlansPage';
import PremiumPage from './components/PremiumPage';
import ReferralsPage from './components/ReferralsPage';
import SettingsPage from './components/SettingsPage';
import TokensPage from './components/TokensPage';
import CustomStoryCreation from './components/CustomStoryCreation';
import { useTranslation } from './i18n/TranslationContext';

/**
 * Main App Component
 * Initializes Telegram Web App SDK and manages navigation between pages
 */
function App() {
  const { t, isLoading: isLoadingLanguage, onLanguageChange } = useTranslation();
  const [currentPage, setCurrentPage] = useState('gallery'); // 'gallery' | 'history' | 'custom-story' | 'settings' | 'language' | 'plans' | 'premium' | 'checkout' | 'tokens' | 'referrals'
  const [userName, setUserName] = useState('User');
  const [userId, setUserId] = useState(null);
  const [userPhotoUrl, setUserPhotoUrl] = useState(null);
  const [subscriptionText, setSubscriptionText] = useState('');
  const [dailyBonusDay, setDailyBonusDay] = useState(1);
  const [showBonusAnimation, setShowBonusAnimation] = useState(false);
  const [isClaimingBonus, setIsClaimingBonus] = useState(false);
  const [personas, setPersonas] = useState([]);
  const [selectedPersona, setSelectedPersona] = useState(null);
  const [selectedTier, setSelectedTier] = useState(null);
  const [histories, setHistories] = useState([]);
  const [tokens, setTokens] = useState({ tokens: 100, premium_tier: 'free', is_premium: false, can_claim_daily_bonus: false, next_bonus_in_seconds: 0, daily_bonus_streak: 0 });
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingHistories, setIsLoadingHistories] = useState(false);
  const [error, setError] = useState(null);
  const [showAgeVerification, setShowAgeVerification] = useState(false);
  const [isVerifyingAge, setIsVerifyingAge] = useState(false);

  useEffect(() => {
    // Initialize Telegram Web App
    WebApp.ready();
    WebApp.expand();
    
    // Set modern dark background color for Telegram container
    WebApp.setBackgroundColor('#0a0a0a');
    WebApp.setHeaderColor('#0a0a0a');
    
    // Disable vertical swipes to prevent accidental closes
    WebApp.disableVerticalSwipes();
    
    // Get user info from Telegram
    const telegramUser = WebApp.initDataUnsafe?.user;
    if (telegramUser) {
      setUserName(telegramUser.first_name || 'User');
      setUserId(telegramUser.id);
      
      // Get user photo if available
      if (telegramUser.photo_url) {
        setUserPhotoUrl(telegramUser.photo_url);
      }
    }
    
    // Set random subscription text (will be translated)
    const subscriptionTextKeys = ['coolFeatures', 'recommendBuy', 'tryIt'];
    const randomKey = subscriptionTextKeys[Math.floor(Math.random() * subscriptionTextKeys.length)];
    setSubscriptionText(randomKey);
    
    // Track mini app opened
    try {
      const initData = WebApp.initData;
      trackEvent('miniapp_opened', {}, initData).catch(err => {
        console.error('Failed to track miniapp opened:', err);
      });
    } catch (err) {
      console.error('Error tracking miniapp opened:', err);
    }
    
    // Wait for language to load before checking age status
    if (!isLoadingLanguage) {
      checkAgeStatus();
    }
  }, [isLoadingLanguage]);

  async function checkAgeStatus() {
    try {
      const initData = WebApp.initData;
      const result = await checkAgeVerification(initData);
      
      if (!result.age_verified) {
        // User hasn't verified age - show blocking modal
        setShowAgeVerification(true);
        setIsLoading(false);
      } else {
        // User is verified - proceed to load app
        // Check URL parameters for routing
        const urlParams = new URLSearchParams(window.location.search);
        const page = urlParams.get('page');
        if (page === 'premium' || page === 'plans') {
          setCurrentPage('plans');
        }
        
        // Load initial data
        loadPersonas();
        loadEnergy();
      }
    } catch (err) {
      console.error('Failed to check age verification:', err);
      // On error, assume not verified for safety
      setShowAgeVerification(true);
      setIsLoading(false);
    }
  }

  async function handleAgeConfirmation() {
    try {
      setIsVerifyingAge(true);
      const initData = WebApp.initData;
      await verifyAge(initData);
      
      // Age verified successfully
      setShowAgeVerification(false);
      
      // Check URL parameters for routing
      const urlParams = new URLSearchParams(window.location.search);
      const page = urlParams.get('page');
      if (page === 'premium' || page === 'plans') {
        setCurrentPage('plans');
      }
      
      // Load initial data
      loadPersonas();
      loadEnergy();
    } catch (err) {
      console.error('Failed to verify age:', err);
      WebApp.showAlert('Failed to verify age. Please try again.');
    } finally {
      setIsVerifyingAge(false);
    }
  }

  // Scroll to top whenever page changes
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [currentPage]);

  // Subscribe to language changes and refetch personas
  useEffect(() => {
    if (!onLanguageChange) return;
    
    const unsubscribe = onLanguageChange((newLanguage) => {
      console.log(`🔄 Language changed to ${newLanguage}, refetching personas and histories...`);
      
      // Refetch personas with new language
      loadPersonas();
      
      // If viewing histories, refetch those too
      if (currentPage === 'history' && selectedPersona) {
        handlePersonaClick(selectedPersona);
      }
    });
    
    return unsubscribe;
  }, [currentPage, selectedPersona, onLanguageChange]);

  async function loadPersonas(silent = false) {
    try {
      if (!silent) {
        setIsLoading(true);
      }
      setError(null);
      
      const initData = WebApp.initData;
      const data = await fetchPersonas(initData);
      setPersonas(data);
    } catch (err) {
      console.error('Failed to load personas:', err);
      if (!silent) {
        const errorMsg = t('app.errors.loadFailed');
        setError(errorMsg);
        WebApp.showAlert(errorMsg);
      }
    } finally {
      if (!silent) {
        setIsLoading(false);
      }
    }
  }

  async function loadEnergy() {
    try {
      const initData = WebApp.initData;
      const data = await fetchUserEnergy(initData);
      setTokens(data);
      // Update daily bonus day from streak
      if (data.daily_bonus_streak) {
        setDailyBonusDay(data.daily_bonus_streak + 1); // Next day to claim
      }
    } catch (err) {
      console.error('Failed to load tokens:', err);
      // Don't show error for tokens, just use default
    }
  }

  async function handlePersonaClick(persona) {
    setSelectedPersona(persona);
    setCurrentPage('history');
    setIsLoadingHistories(true);
    
    try {
      const initData = WebApp.initData;
      const data = await fetchPersonaHistories(persona.id, initData);
      setHistories(data);
    } catch (err) {
      console.error('Failed to load histories:', err);
      setHistories([]);
    } finally {
      setIsLoadingHistories(false);
    }
  }

  async function handleHistoryClick(history) {
    // Close immediately - optimistic UI
    WebApp.close();
    
    // Fire the API call in the background
    try {
      const initData = WebApp.initData;
      // Extract location if present (for custom character location selection)
      const location = history?.location || null;
      selectScenario(
        selectedPersona.id,
        history ? history.id : null,
        initData,
        location
      ).catch(err => {
        console.error('Failed to select scenario:', err);
      });
    } catch (err) {
      console.error('Failed to initiate scenario selection:', err);
    }
  }

  const handleBackToGallery = useCallback(() => {
    setCurrentPage('gallery');
    setSelectedPersona(null);
    setHistories([]);
  }, []);

  const handleBackToPrevious = useCallback(() => {
    if (currentPage === 'checkout') {
      setCurrentPage('premium');
    } else if (currentPage === 'custom-story') {
      setCurrentPage('history');
    } else if (currentPage === 'language' || currentPage === 'plans' || currentPage === 'premium' || currentPage === 'tokens') {
      setCurrentPage('settings');
    } else if (currentPage === 'referrals') {
      setCurrentPage('gallery');
    } else if (currentPage === 'settings') {
      setCurrentPage('gallery');
    } else {
      handleBackToGallery();
    }
  }, [currentPage, handleBackToGallery]);

  function handleNavigate(page) {
    if (page === 'gallery' && currentPage !== 'gallery') {
      setCurrentPage('gallery');
      setSelectedPersona(null);
      setHistories([]);
    } else if (page === 'settings') {
      setCurrentPage('settings');
    } else if (page === 'language') {
      setCurrentPage('language');
    } else if (page === 'plans') {
      setCurrentPage('plans');
    } else if (page === 'premium') {
      setCurrentPage('premium');
    } else if (page === 'checkout') {
      setCurrentPage('checkout');
    } else if (page === 'tokens') {
      setCurrentPage('tokens');
    } else if (page === 'referrals') {
      setCurrentPage('referrals');
    }
  }

  function handleNavigateToCheckout(tier) {
    setSelectedTier(tier);
    setCurrentPage('checkout');
  }

  function formatTimeUntilBonus(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${hours}${t('app.time.hours')} ${minutes}${t('app.time.minutes')}`;
  }

  async function handleClaimDailyBonus() {
    if (isClaimingBonus) return;
    
    // Check if can claim
    if (!tokens.can_claim_daily_bonus) {
      const hours = Math.floor(tokens.next_bonus_in_seconds / 3600);
      const minutes = Math.floor((tokens.next_bonus_in_seconds % 3600) / 60);
      WebApp.showAlert(t('app.dailyBonus.alreadyClaimed', { hours, minutes }));
      return;
    }
    
    setIsClaimingBonus(true);
    
    try {
      const initData = WebApp.initData;
      const result = await claimDailyBonus(initData);
      
      if (result.success) {
        // Show animation
        setShowBonusAnimation(true);
        
        // Update tokens after a short delay (for animation)
        setTimeout(() => {
          setTokens(prev => ({
            ...prev,
            tokens: result.tokens,
            can_claim_daily_bonus: false,
            next_bonus_in_seconds: 86400,
            daily_bonus_streak: result.streak || prev.daily_bonus_streak + 1
          }));
          
          // Update daily bonus day
          setDailyBonusDay((result.streak || 0) + 1);
          
          // Hide animation
          setTimeout(() => {
            setShowBonusAnimation(false);
          }, 1000);
        }, 800);
      } else {
        WebApp.showAlert(result.message || t('app.dailyBonus.claimFailed'));
      }
    } catch (error) {
      console.error('Failed to claim daily bonus:', error);
      WebApp.showAlert(t('app.dailyBonus.claimError'));
    } finally {
      setIsClaimingBonus(false);
    }
  }

  // Determine if bottom nav should be shown (only on gallery page)
  const showBottomNav = currentPage === 'gallery';

  // Get page title
  const getPageTitle = () => {
    if (currentPage === 'gallery') return t('app.header.characters');
    if (currentPage === 'settings') return t('app.header.settings');
    if (currentPage === 'language') return t('settings.language.title');
    if (currentPage === 'plans') return t('app.header.settings');
    if (currentPage === 'premium') return t('app.header.premium');
    if (currentPage === 'checkout' && selectedTier) return t('app.header.checkoutTitle', { icon: selectedTier.icon, name: selectedTier.name });
    if (currentPage === 'tokens') return t('app.header.energy');
    if (currentPage === 'referrals') return t('app.header.referrals');
    if (currentPage === 'history' && selectedPersona) return selectedPersona.name;
    return '';
  };

  // Determine if back button should be shown
  const showBackButton = currentPage === 'settings' || currentPage === 'language' || currentPage === 'plans' || currentPage === 'premium' || currentPage === 'checkout' || currentPage === 'tokens' || currentPage === 'referrals' || currentPage === 'history' || currentPage === 'custom-story';

  // Handle Telegram BackButton
  useEffect(() => {
    const backHandler = () => {
      handleBackToPrevious();
    };
    
    if (showBackButton) {
      WebApp.BackButton.show();
      WebApp.BackButton.onClick(backHandler);
    } else {
      WebApp.BackButton.hide();
    }
    
    return () => {
      WebApp.BackButton.offClick(backHandler);
    };
  }, [showBackButton, handleBackToPrevious]);

  // Show loading screen while language is initializing
  if (isLoadingLanguage) {
    return (
      <div className="app" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh' }}>
        <div className="loading">
          <div className="spinner"></div>
        </div>
      </div>
    );
  }

  return (
    <div className={`app ${showBottomNav ? 'app-with-nav' : ''}`}>
      {/* Age Verification Modal - Blocking overlay */}
      {showAgeVerification && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: '#0a0a0a',
          zIndex: 9999,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '20px',
        }}>
          <div style={{
            backgroundColor: '#1a1a1a',
            borderRadius: '16px',
            padding: '32px 24px',
            maxWidth: '400px',
            width: '100%',
            textAlign: 'center',
          }}>
            <div style={{ fontSize: '48px', marginBottom: '16px' }}>🔞</div>
            <h2 style={{ 
              color: '#ffffff', 
              fontSize: '24px', 
              fontWeight: '600', 
              marginBottom: '16px',
              lineHeight: '1.3',
            }}>
              {t('app.ageVerification.title')}
            </h2>
            <p style={{ 
              color: '#888888', 
              fontSize: '16px', 
              marginBottom: '24px',
              lineHeight: '1.5',
            }}>
              {t('app.ageVerification.description')}
            </p>
            <button
              onClick={handleAgeConfirmation}
              disabled={isVerifyingAge}
              style={{
                width: '100%',
                padding: '16px',
                backgroundColor: isVerifyingAge ? '#333333' : '#007AFF',
                color: '#ffffff',
                border: 'none',
                borderRadius: '12px',
                fontSize: '16px',
                fontWeight: '600',
                cursor: isVerifyingAge ? 'not-allowed' : 'pointer',
                transition: 'background-color 0.2s',
              }}
              onMouseEnter={(e) => {
                if (!isVerifyingAge) e.target.style.backgroundColor = '#0051D5';
              }}
              onMouseLeave={(e) => {
                if (!isVerifyingAge) e.target.style.backgroundColor = '#007AFF';
              }}
            >
              {isVerifyingAge ? t('app.ageVerification.verifying') : t('app.ageVerification.confirmButton')}
            </button>
          </div>
        </div>
      )}

      {currentPage === 'gallery' ? (
        <header className="app-header gallery-header">
          <div className="gallery-header-content">
            <div className="user-profile-section">
              <div className={`user-avatar ${!userPhotoUrl ? 'skeleton-wave' : ''}`}>
                {userPhotoUrl && <img src={userPhotoUrl} alt={userName} className="avatar-image" />}
              </div>
              <div className="user-info-column">
                <div className="user-name">{userName}</div>
                <div className="user-energy-display">
                  <img src={lightningIcon} alt="energy" className="energy-icon-small" />
                  <span className={`energy-value-small ${showBonusAnimation ? 'energy-boost' : ''}`}>
                    {tokens.tokens.toLocaleString()}
                  </span>
                  <button className="plus-button-small" onClick={() => handleNavigate('tokens')}>
                    +
                  </button>
                </div>
              </div>
            </div>
            <button className="referral-bonus-button" onClick={() => handleNavigate('referrals')}>
              <span className="bonus-icon">🎁</span>
              <span className="bonus-text">{t('app.dailyBonus.referralBonus')}</span>
            </button>
          </div>
          <div className="action-buttons">
            <button 
              className={`action-button gift-button ${isClaimingBonus ? 'claiming' : ''} ${!tokens.can_claim_daily_bonus ? 'claimed' : ''}`}
              onClick={handleClaimDailyBonus}
              disabled={isClaimingBonus}
            >
              <div className="button-content">
                <img 
                  src={tokens.can_claim_daily_bonus ? giftIcon : clockIcon} 
                  alt={tokens.can_claim_daily_bonus ? 'gift' : 'clock'} 
                  className="gift-button-icon" 
                />
                <span className="button-label">{t('app.dailyBonus.gift')}</span>
                <span className="gift-button-day">{t('app.dailyBonus.day', { day: dailyBonusDay })}</span>
              </div>
              {tokens.can_claim_daily_bonus ? (
                <div className="button-subtitle gift-button-action">{t('app.dailyBonus.clickToClaim')}</div>
              ) : (
                <div className="button-subtitle">{formatTimeUntilBonus(tokens.next_bonus_in_seconds)}</div>
              )}
            </button>
            <button className="action-button subscription-button" onClick={() => handleNavigate('premium')}>
              <div className="button-content">
                <img src={premiumIcon} alt="premium" className="button-icon-large" />
                <span className="button-label">{t('app.dailyBonus.subscription')}</span>
              </div>
              <div className="button-subtitle">{t(`app.subscriptionTexts.${subscriptionText}`)}</div>
            </button>
          </div>
          {showBonusAnimation && (
            <div className="bonus-animation">
              <span className="bonus-amount">+10</span>
            </div>
          )}
        </header>
      ) : (
        <header className="app-header">
          <div className="header-content">
            <h1 className="page-title">{getPageTitle()}</h1>
            {currentPage !== 'history' && currentPage !== 'referrals' && currentPage !== 'checkout' && (
              <div className="energy-display">
                <div className="energy-content">
                  <span className="energy-icon">
                    <img src={lightningIcon} alt="energy" />
                  </span>
                  <div className="energy-info">
                    <span className="energy-value">
                      {tokens.tokens.toLocaleString()}
                    </span>
                  </div>
                </div>
                <button className="plus-button" onClick={() => handleNavigate('tokens')}>
                  +
                </button>
              </div>
            )}
          </div>
        </header>
      )}
      
      <main className="app-main">
        {error ? (
          <div className="error-state">
            <p>{error}</p>
            <button onClick={loadPersonas} className="retry-button">
              {t('app.errors.retryButton')}
            </button>
          </div>
        ) : currentPage === 'gallery' ? (
          <PersonasGallery
            personas={personas}
            onPersonaClick={handlePersonaClick}
            isLoading={isLoading}
            tokens={tokens}
            onRefresh={() => loadPersonas(true)}
            onNavigateToTokens={() => setCurrentPage('tokens')}
          />
        ) : currentPage === 'history' ? (
          <HistorySelection
            persona={selectedPersona}
            histories={histories}
            onHistoryClick={handleHistoryClick}
            onBack={handleBackToGallery}
            isLoading={isLoadingHistories}
            onNavigateToCustomStory={() => setCurrentPage('custom-story')}
            onCharacterDeleted={() => {
              setCurrentPage('gallery');
              setSelectedPersona(null);
              loadPersonas(true);
            }}
          />
        ) : currentPage === 'custom-story' ? (
          <CustomStoryCreation
            persona={selectedPersona}
            onBack={() => setCurrentPage('history')}
            onStoryCreated={handleHistoryClick}
          />
        ) : currentPage === 'settings' ? (
          <SettingsPage
            tokens={tokens}
            onNavigate={handleNavigate}
          />
        ) : currentPage === 'language' ? (
          <LanguagePage />
        ) : currentPage === 'plans' ? (
          <PlansPage />
        ) : currentPage === 'premium' ? (
          <PremiumPage onNavigateToCheckout={handleNavigateToCheckout} />
        ) : currentPage === 'checkout' ? (
          <CheckoutPage tier={selectedTier} onBack={handleBackToPrevious} />
        ) : currentPage === 'tokens' ? (
          <TokensPage tokens={tokens} />
        ) : currentPage === 'referrals' ? (
          <ReferralsPage userId={userId} />
        ) : null}
      </main>

      {showBottomNav && (
        <BottomNav
          currentPage={currentPage}
          onNavigate={handleNavigate}
        />
      )}
    </div>
  );
}

export default App;

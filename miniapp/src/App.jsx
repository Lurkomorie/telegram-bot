import WebApp from '@twa-dev/sdk';
import { useEffect, useState } from 'react';
import { fetchPersonaHistories, fetchPersonas, fetchUserEnergy, selectScenario, checkAgeVerification, verifyAge } from './api';
import './App.css';
import BottomNav from './components/BottomNav';
import HistorySelection from './components/HistorySelection';
import PersonasGallery from './components/PersonasGallery';
import SettingsPage from './components/SettingsPage';
import LanguagePage from './components/LanguagePage';
import PlansPage from './components/PlansPage';
import { useTranslation } from './i18n/TranslationContext';

/**
 * Main App Component
 * Initializes Telegram Web App SDK and manages navigation between pages
 */
function App() {
  const { t, isLoading: isLoadingLanguage, onLanguageChange } = useTranslation();
  const [currentPage, setCurrentPage] = useState('gallery'); // 'gallery' | 'history' | 'settings' | 'language' | 'plans'
  const [personas, setPersonas] = useState([]);
  const [selectedPersona, setSelectedPersona] = useState(null);
  const [histories, setHistories] = useState([]);
  const [energy, setEnergy] = useState({ energy: 100, max_energy: 100, is_premium: false });
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingHistories, setIsLoadingHistories] = useState(false);
  const [error, setError] = useState(null);
  const [showAgeVerification, setShowAgeVerification] = useState(false);
  const [isVerifyingAge, setIsVerifyingAge] = useState(false);
  const [ageCheckComplete, setAgeCheckComplete] = useState(false);

  useEffect(() => {
    // Initialize Telegram Web App
    WebApp.ready();
    WebApp.expand();
    
    // Set modern dark background color for Telegram container
    WebApp.setBackgroundColor('#0a0a0a');
    WebApp.setHeaderColor('#0a0a0a');
    
    // Disable vertical swipes to prevent accidental closes
    WebApp.disableVerticalSwipes();
    
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
        setAgeCheckComplete(true);
        
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
      setAgeCheckComplete(true);
      
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

  async function loadPersonas() {
    try {
      setIsLoading(true);
      setError(null);
      
      const initData = WebApp.initData;
      const data = await fetchPersonas(initData);
      setPersonas(data);
    } catch (err) {
      console.error('Failed to load personas:', err);
      const errorMsg = t('app.errors.loadFailed');
      setError(errorMsg);
      WebApp.showAlert(errorMsg);
    } finally {
      setIsLoading(false);
    }
  }

  async function loadEnergy() {
    try {
      const initData = WebApp.initData;
      const data = await fetchUserEnergy(initData);
      setEnergy(data);
    } catch (err) {
      console.error('Failed to load energy:', err);
      // Don't show error for energy, just use default
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
      selectScenario(
        selectedPersona.id,
        history ? history.id : null,
        initData
      ).catch(err => {
        console.error('Failed to select scenario:', err);
      });
    } catch (err) {
      console.error('Failed to initiate scenario selection:', err);
    }
  }

  function handleBackToGallery() {
    setCurrentPage('gallery');
    setSelectedPersona(null);
    setHistories([]);
  }

  function handleBackToPrevious() {
    if (currentPage === 'language' || currentPage === 'plans') {
      setCurrentPage('settings');
    } else if (currentPage === 'settings') {
      setCurrentPage('gallery');
    } else {
      handleBackToGallery();
    }
  }

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
    }
  }

  // Determine if bottom nav should be shown (on gallery, settings, language, and plans)
  const showBottomNav = currentPage === 'gallery' || currentPage === 'settings' || currentPage === 'language' || currentPage === 'plans';

  // Get page title
  const getPageTitle = () => {
    if (currentPage === 'gallery') return t('app.header.characters');
    if (currentPage === 'settings') return t('app.header.settings');
    if (currentPage === 'language') return t('settings.language.title');
    if (currentPage === 'plans') return t('app.header.settings');
    if (currentPage === 'history' && selectedPersona) return selectedPersona.name;
    return '';
  };

  // Determine if back button should be shown
  const showBackButton = currentPage === 'settings' || currentPage === 'language' || currentPage === 'plans' || currentPage === 'history';

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

      <header className="app-header">
        <div className="header-content">
          {showBackButton && (
            <button className="back-button" onClick={handleBackToPrevious}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M19 12H5M12 19l-7-7 7-7"/>
              </svg>
            </button>
          )}
          <h1 className="page-title">{getPageTitle()}</h1>
          {currentPage !== 'history' && (
            <div className="energy-display">
              <div className="energy-content">
                <span className="energy-icon"></span>
                <div className="energy-info">
                  <span className="energy-value">
                    {energy.is_premium ? '∞' : `${energy.energy}/${energy.max_energy}`}
                  </span>
                </div>
              </div>
              <button className="plus-button" onClick={() => handleNavigate('plans')}>
                +
              </button>
            </div>
          )}
        </div>
      </header>
      
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
          />
        ) : currentPage === 'history' ? (
          <HistorySelection
            persona={selectedPersona}
            histories={histories}
            onHistoryClick={handleHistoryClick}
            onBack={handleBackToGallery}
            isLoading={isLoadingHistories}
          />
        ) : currentPage === 'settings' ? (
          <SettingsPage
            energy={energy}
            onNavigate={handleNavigate}
          />
        ) : currentPage === 'language' ? (
          <LanguagePage />
        ) : currentPage === 'plans' ? (
          <PlansPage />
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

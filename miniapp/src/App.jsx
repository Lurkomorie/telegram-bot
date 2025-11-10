import WebApp from '@twa-dev/sdk';
import { useEffect, useState } from 'react';
import { fetchPersonaHistories, fetchPersonas, fetchUserEnergy, selectScenario } from './api';
import './App.css';
import BottomNav from './components/BottomNav';
import HistorySelection from './components/HistorySelection';
import PersonasGallery from './components/PersonasGallery';
import PremiumPage from './components/PremiumPage';

/**
 * Main App Component
 * Initializes Telegram Web App SDK and manages navigation between pages
 */
function App() {
  const [currentPage, setCurrentPage] = useState('gallery'); // 'gallery' | 'history' | 'premium'
  const [personas, setPersonas] = useState([]);
  const [selectedPersona, setSelectedPersona] = useState(null);
  const [histories, setHistories] = useState([]);
  const [energy, setEnergy] = useState({ energy: 100, max_energy: 100, is_premium: false });
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingHistories, setIsLoadingHistories] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Initialize Telegram Web App
    WebApp.ready();
    WebApp.expand();
    
    // Set modern dark background color for Telegram container
    WebApp.setBackgroundColor('#0a0a0a');
    WebApp.setHeaderColor('#0a0a0a');
    
    // Disable vertical swipes to prevent accidental closes
    WebApp.disableVerticalSwipes();
    
    // Check URL parameters for routing
    const urlParams = new URLSearchParams(window.location.search);
    const page = urlParams.get('page');
    if (page === 'premium') {
      setCurrentPage('premium');
    }
    
    // Load initial data
    loadPersonas();
    loadEnergy();
  }, []);

  // Scroll to top whenever page changes
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [currentPage]);

  async function loadPersonas() {
    try {
      setIsLoading(true);
      setError(null);
      
      const initData = WebApp.initData;
      const data = await fetchPersonas(initData);
      setPersonas(data);
    } catch (err) {
      console.error('Failed to load personas:', err);
      setError('Failed to load characters. Please try again.');
      WebApp.showAlert('Failed to load characters. Please try again.');
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
    if (currentPage === 'premium') {
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
    } else if (page === 'premium') {
      setCurrentPage('premium');
    }
  }

  // Determine if bottom nav should be shown (only on gallery)
  const showBottomNav = currentPage === 'gallery';

  // Get page title
  const getPageTitle = () => {
    if (currentPage === 'gallery') return 'Characters';
    if (currentPage === 'premium') return 'Settings';
    if (currentPage === 'history' && selectedPersona) return selectedPersona.name;
    return '';
  };

  // Determine if back button should be shown
  const showBackButton = currentPage === 'premium' || currentPage === 'history';

  return (
    <div className={`app ${showBottomNav ? 'app-with-nav' : ''}`}>
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
                  {!energy.is_premium && (
                    <span className="energy-regen">+2 ⭐ every 1h</span>
                  )}
                </div>
              </div>
              <button className="plus-button" onClick={() => handleNavigate('premium')}>
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
              Retry
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
        ) : currentPage === 'premium' ? (
          <PremiumPage
            energy={energy}
            onBack={handleBackToPrevious}
          />
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

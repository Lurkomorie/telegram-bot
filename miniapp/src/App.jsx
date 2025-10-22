import WebApp from '@twa-dev/sdk';
import { useEffect, useState } from 'react';
import { fetchPersonaHistories, fetchPersonas, fetchUserEnergy } from './api';
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
  const [energy, setEnergy] = useState({ energy: 100, max_energy: 100 });
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingHistories, setIsLoadingHistories] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Initialize Telegram Web App
    WebApp.ready();
    WebApp.expand();
    
    // Set dark background color for Telegram container
    WebApp.setBackgroundColor('#000000');
    WebApp.setHeaderColor('#000000');
    
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

  function handleHistoryClick(history) {
    // Send data back to bot
    const data = {
      action: 'select_persona',
      persona_id: selectedPersona.id,
      history_id: history ? history.id : null,
    };
    
    WebApp.sendData(JSON.stringify(data));
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

  // Determine if bottom nav should be shown
  const showBottomNav = currentPage === 'gallery' || currentPage === 'premium';

  // Get page title
  const getPageTitle = () => {
    if (currentPage === 'gallery') return 'Characters';
    if (currentPage === 'premium') return 'Settings';
    return '';
  };

  return (
    <div className={`app ${showBottomNav ? 'app-with-nav' : ''}`}>
      {currentPage !== 'history' && (
        <header className="app-header">
          <div className="header-content">
            <h1 className="page-title">{getPageTitle()}</h1>
            <div className="energy-display">
              <span className="energy-icon">⚡</span>
              <span className="energy-value">{energy.energy}/{energy.max_energy}</span>
              <button className="plus-button" onClick={() => handleNavigate('premium')}>
                +
              </button>
            </div>
          </div>
        </header>
      )}
      
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

import { useState } from 'react';
import WebApp from '@twa-dev/sdk';
import './HistorySelection.css';
import { useTranslation } from '../i18n/TranslationContext';
import { deleteCharacter } from '../api';

/**
 * HistorySelection Component
 * Shows available greeting scenarios for a selected persona
 * For custom characters: shows locations grid and custom story option
 * For preset characters: shows existing histories
 */
export default function HistorySelection({ persona, histories, onHistoryClick, onBack, isLoading, onNavigateToCustomStory, onCharacterDeleted }) {
  const { t } = useTranslation();
  const [showMenu, setShowMenu] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const handleDeleteClick = async () => {
    setShowMenu(false);
    
    // Show confirmation dialog
    const confirmed = window.confirm(
      t('characterPage.deleteConfirm.message')
    );
    
    if (!confirmed) return;

    setIsDeleting(true);
    
    try {
      await deleteCharacter(persona.id, WebApp.initData);
      WebApp.showAlert(`${persona.name} deleted successfully`);
      
      // Navigate back to gallery
      if (onCharacterDeleted) {
        onCharacterDeleted();
      }
    } catch (err) {
      console.error('Delete error:', err);
      WebApp.showAlert(err.message || 'Failed to delete character');
    } finally {
      setIsDeleting(false);
    }
  };

  const handleLocationClick = (locationKey) => {
    // Create a pseudo-history object with location info
    onHistoryClick({
      id: null,
      name: t(`characterPage.locations.${locationKey}`),
      location: locationKey
    });
  };

  if (isLoading) {
    return (
      <div className="history-selection">
        <div className="loading">
          <div className="spinner"></div>
          <p>{t('history.loading')}</p>
        </div>
      </div>
    );
  }

  // Custom character layout
  if (persona.is_custom) {
    const locations = ['home', 'office', 'school', 'cafe', 'gym', 'park'];
    
    return (
      <div className="history-selection custom-character-view">
        {/* Character Header */}
        <div className="character-header">
          <div className="character-avatar">
            {persona.avatar_url ? (
              <img src={persona.avatar_url} alt={persona.name} />
            ) : (
              <div className="avatar-placeholder">
                <span>👤</span>
              </div>
            )}
          </div>
          <div className="character-header-info">
            <h2 className="character-name">{persona.name}</h2>
          </div>
          
          {/* Three-dots Menu */}
          <div className="character-menu">
            <button 
              className="menu-button"
              onClick={() => setShowMenu(!showMenu)}
              disabled={isDeleting}
            >
              <span>⋮</span>
            </button>
            {showMenu && (
              <div className="menu-dropdown">
                <button 
                  className="menu-item delete-item"
                  onClick={handleDeleteClick}
                  disabled={isDeleting}
                >
                  {isDeleting ? '⏳' : t('characterPage.deleteMenu')}
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Location Selection */}
        <div className="locations-section">
          <h3 className="section-title">{t('characterPage.selectLocation')}</h3>
          <div className="locations-grid">
            {locations.map((location) => (
              <button
                key={location}
                className="location-card"
                onClick={() => handleLocationClick(location)}
              >
                <span className="location-name">
                  {t(`characterPage.locations.${location}`)}
                </span>
              </button>
            ))}
          </div>
        </div>

        {/* Custom Story Button */}
        <button 
          className="custom-story-button"
          onClick={onNavigateToCustomStory}
        >
          {t('characterPage.createCustomButton')}
        </button>
      </div>
    );
  }

  // Preset character layout (existing behavior)
  return (
    <div className="history-selection">
      <div className="histories-list">
        {histories && histories.length > 0 ? (
          histories.map((history) => (
            <HistoryCard
              key={history.id}
              history={history}
              onClick={() => onHistoryClick(history)}
            />
          ))
        ) : (
          <div className="no-histories">
            <p>{t('history.empty')}</p>
            <button className="start-button" onClick={() => onHistoryClick(null)}>
              {t('history.startButton')}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * HistoryCard Component
 * Individual history/scenario card
 */
function HistoryCard({ history, onClick }) {
  const [imageError, setImageError] = useState(false);

  return (
    <div className="history-card" onClick={onClick}>
      {history.wide_menu_image_url && !imageError ? (
        <div className="history-image wide">
          <img
            src={history.wide_menu_image_url}
            alt="Scenario preview"
            onError={() => setImageError(true)}
          />
        </div>
      ) : history.image_url && !imageError ? (
        <div className="history-image">
          <img
            src={history.image_url}
            alt="Scenario preview"
            onError={() => setImageError(true)}
          />
        </div>
      ) : null}
      <div className="history-content">
        {history.name && (
          <p className="history-name">{history.name}</p>
        )}
        {history.smallDescription && (
          <p className="history-description">{history.smallDescription}</p>
        )}
      </div>
    </div>
  );
}

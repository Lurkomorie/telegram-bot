import WebApp from '@twa-dev/sdk';
import { useEffect, useRef, useState } from 'react';
import { deleteCharacter } from '../api';
import { useTranslation } from '../i18n/TranslationContext';
import CharacterCreation from './CharacterCreation';
import './PersonasGallery.css';

/**
 * PersonasGallery Component
 * Displays a 2-column grid of AI persona cards with images, names, and descriptions
 * Includes "Create Character" card and custom character management
 */
export default function PersonasGallery({ personas, onPersonaClick, isLoading, tokens, onRefresh, onNavigateToTokens }) {
  const { t } = useTranslation();
  const [showCreation, setShowCreation] = useState(false);
  const [deletingId, setDeletingId] = useState(null);
  const onRefreshRef = useRef(onRefresh);
  const personasRef = useRef(personas);

  const handleDelete = async (personaId, personaName, e) => {
    e.stopPropagation(); // Prevent card click
    
    // Show confirmation
    const confirmMsg = t('gallery.deleteConfirm').replace('{name}', personaName);
    const confirmed = window.confirm(confirmMsg);
    if (!confirmed) return;

    setDeletingId(personaId);
    
    try {
      await deleteCharacter(personaId, WebApp.initData);
      
      // Show success message
      const successMsg = t('gallery.deleteSuccess').replace('{name}', personaName);
      WebApp.showAlert(successMsg);
      
      // Refresh personas list
      if (onRefresh) {
        onRefresh();
      }
    } catch (err) {
      console.error('Delete error:', err);
      WebApp.showAlert(err.message || 'Failed to delete character');
    } finally {
      setDeletingId(null);
    }
  };

  const handleCreated = () => {
    setShowCreation(false);
    
    // Store the timestamp when character was created
    const createdAt = Date.now();
    const createdPersonaCheckRef = { stopped: false };
    
    // Function to check if we should continue polling
    const shouldContinuePolling = () => {
      if (createdPersonaCheckRef.stopped) return false;
      
      // Check if any custom character still needs avatar (use ref to get latest personas)
      const currentPersonas = personasRef.current;
      const customCharsWithoutAvatar = currentPersonas?.filter(
        p => p.is_custom && !p.avatar_url
      ) || [];
      
      if (customCharsWithoutAvatar.length === 0) {
        console.log('[GALLERY] ✅ Avatar loaded, stopping scheduled refreshes');
        createdPersonaCheckRef.stopped = true;
        return false;
      }
      
      // Stop after 2 minutes
      if (Date.now() - createdAt > 120000) {
        console.log('[GALLERY] ⏰ 2 minutes elapsed, stopping scheduled refreshes');
        createdPersonaCheckRef.stopped = true;
        return false;
      }
      
      return true;
    };
    
    // Refresh immediately
    if (onRefresh) {
      onRefresh();
    }
    
    // Schedule smart refreshes: 10s, 20s, 30s, 45s, 60s, 90s, 120s (7 calls max)
    const delays = [10000, 20000, 30000, 45000, 60000, 90000, 120000];
    delays.forEach(delay => {
      setTimeout(() => {
        if (shouldContinuePolling() && onRefreshRef.current) {
          console.log(`[GALLERY] 🔄 Scheduled refresh at ${delay/1000}s`);
          onRefreshRef.current();
        }
      }, delay);
    });
  };

  // Keep refs up to date
  useEffect(() => {
    onRefreshRef.current = onRefresh;
    personasRef.current = personas;
  }, [onRefresh, personas]);

  // Auto-open creation if URL has create=true parameter
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('create') === 'true') {
      setShowCreation(true);
      // Clear the parameter from URL to avoid re-triggering
      const newUrl = window.location.pathname + '?page=gallery';
      window.history.replaceState({}, '', newUrl);
    }
  }, []);

  if (isLoading) {
    return (
      <div className="loading">
        <div className="spinner"></div>
        <p>{t('gallery.loading')}</p>
      </div>
    );
  }

  return (
    <>
      <div className="personas-gallery">
        <div className="personas-grid">
          {/* First two personas */}
          {personas && personas.slice(0, 2).map((persona) => (
            <PersonaCard
              key={persona.id}
              persona={persona}
              onClick={() => onPersonaClick(persona)}
              onDelete={persona.is_custom ? handleDelete : null}
              isDeleting={deletingId === persona.id}
            />
          ))}

          {/* Create Character Card - Always 3rd */}
          <div 
            className="persona-card create-card" 
            onClick={() => setShowCreation(true)}
          >
            <div className="create-card-content">
              <h3 className="create-card-title">{t('gallery.createCharacter.title')}</h3>
              <p className="create-card-subtitle">{t('gallery.createCharacter.subtitle')}</p>
            </div>
            {!tokens?.char_created && (
              <div className="create-card-footer">
                <span className="create-card-free-text">{t('gallery.createCharacter.free')}</span>
              </div>
            )}
          </div>

          {/* Remaining Personas */}
          {personas && personas.slice(2).map((persona) => (
            <PersonaCard
              key={persona.id}
              persona={persona}
              onClick={() => onPersonaClick(persona)}
              onDelete={persona.is_custom ? handleDelete : null}
              isDeleting={deletingId === persona.id}
            />
          ))}
        </div>
      </div>

      {/* Character Creation Modal */}
      {showCreation && (
        <CharacterCreation
          onClose={() => setShowCreation(false)}
          onCreated={handleCreated}
          tokens={tokens}
          onNavigateToTokens={onNavigateToTokens}
        />
      )}
    </>
  );
}

/**
 * PersonaCard Component
 * Individual persona card with image, name, and description
 */
function PersonaCard({ persona, onClick, onDelete, isDeleting }) {
  const { t } = useTranslation();
  const [imageError, setImageError] = useState(false);
  const isGeneratingAvatar = persona.is_custom && !persona.avatar_url;

  return (
    <div className="persona-card" onClick={onClick}>
      {persona.avatar_url && !imageError ? (
        <img
          src={persona.avatar_url}
          alt={persona.name}
          className="persona-image"
          onError={() => setImageError(true)}
        />
      ) : (
        <div className={`persona-image-placeholder ${isGeneratingAvatar ? 'generating' : ''}`}>
          {isGeneratingAvatar ? (
            <>
              <span className="spinner-small"></span>
              <span className="generating-text">{t('gallery.arrivingSoon')}</span>
            </>
          ) : (
            <span className="placeholder-icon">👤</span>
          )}
        </div>
      )}
      
      <div className="persona-info">
        <h3 className="persona-name">{persona.name}</h3>
        {persona.smallDescription && !persona.is_custom && (
          <p className="persona-description">{persona.smallDescription}</p>
        )}
      </div>
    </div>
  );
}


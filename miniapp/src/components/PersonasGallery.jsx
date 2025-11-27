import { useState, useEffect, useRef } from 'react';
import WebApp from '@twa-dev/sdk';
import './PersonasGallery.css';
import { useTranslation } from '../i18n/TranslationContext';
import CharacterCreation from './CharacterCreation';
import { deleteCharacter } from '../api';

/**
 * PersonasGallery Component
 * Displays a 2-column grid of AI persona cards with images, names, and descriptions
 * Includes "Create Character" card and custom character management
 */
export default function PersonasGallery({ personas, onPersonaClick, isLoading, tokens, onRefresh }) {
  const { t } = useTranslation();
  const [showCreation, setShowCreation] = useState(false);
  const [deletingId, setDeletingId] = useState(null);
  const pollingIntervalRef = useRef(null);
  const pollCountRef = useRef(0);
  const onRefreshRef = useRef(onRefresh);

  const handleDelete = async (personaId, personaName, e) => {
    e.stopPropagation(); // Prevent card click
    
    // Show confirmation
    const confirmed = window.confirm(`Delete ${personaName}? This cannot be undone.`);
    if (!confirmed) return;

    setDeletingId(personaId);
    
    try {
      await deleteCharacter(personaId, WebApp.initData);
      
      // Show success message
      WebApp.showAlert(`${personaName} deleted successfully`);
      
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
    // Refresh personas list
    if (onRefresh) {
      onRefresh();
    }
  };

  // Keep onRefreshRef up to date
  useEffect(() => {
    onRefreshRef.current = onRefresh;
  }, [onRefresh]);

  // Poll for avatar updates on custom characters without avatars
  useEffect(() => {
    // Check if there are any custom characters without avatars
    const customCharsWithoutAvatar = personas?.filter(
      p => p.is_custom && !p.avatar_url
    ) || [];

    // If no characters need avatars, stop any existing polling
    if (customCharsWithoutAvatar.length === 0) {
      if (pollingIntervalRef.current) {
        console.log('[GALLERY] ✅ All avatars loaded, stopping polling');
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
        pollCountRef.current = 0;
      }
      return;
    }

    // If already polling, don't start a new interval
    if (pollingIntervalRef.current) {
      return;
    }

    // Start polling for avatar updates
    console.log(`[GALLERY] 🔄 Found ${customCharsWithoutAvatar.length} custom characters without avatars, starting polling...`);
    pollCountRef.current = 0;
    const maxPolls = 40; // 40 polls * 3 seconds = 2 minutes maximum
    
    // Do first poll immediately (don't wait 3 seconds)
    if (onRefreshRef.current) {
      console.log('[GALLERY] 🔄 Initial poll for avatar updates...');
      onRefreshRef.current();
    }
    
    pollingIntervalRef.current = setInterval(() => {
      pollCountRef.current++;
      console.log(`[GALLERY] 🔄 Polling for avatar updates... (${pollCountRef.current}/${maxPolls})`);
      
      if (pollCountRef.current >= maxPolls) {
        console.log('[GALLERY] ⏰ Max polling duration reached (2 minutes), stopping...');
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
        pollCountRef.current = 0;
        return;
      }
      
      if (onRefreshRef.current) {
        onRefreshRef.current();
      }
    }, 3000);

    // Cleanup on unmount
    return () => {
      if (pollingIntervalRef.current) {
        console.log('[GALLERY] 🧹 Component unmounting, cleaning up polling');
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
        pollCountRef.current = 0;
      }
    };
  }, [personas]); // Only depend on personas, not onRefresh

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
          {/* Create Character Card */}
          <div 
            className="persona-card create-card" 
            onClick={() => setShowCreation(true)}
          >
            <div className="create-icon-wrapper">
              <span className="create-icon">➕</span>
            </div>
            <div className="persona-info">
              <h3 className="persona-name">Create Your Girlfriend</h3>
              <p className="persona-description">
                {tokens?.is_premium ? '25 ⚡' : '50 ⚡'}
              </p>
            </div>
          </div>

          {/* Existing Personas */}
          {personas && personas.map((persona) => (
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
  const [imageError, setImageError] = useState(false);
  const isGeneratingAvatar = persona.is_custom && !persona.avatar_url;

  return (
    <div className="persona-card" onClick={onClick}>
      {/* Delete Button for Custom Characters */}
      {onDelete && (
        <button
          className="delete-button"
          onClick={(e) => onDelete(persona.id, persona.name, e)}
          disabled={isDeleting}
          title="Delete character"
        >
          {isDeleting ? (
            <span style={{ fontSize: '12px' }}>⏳</span>
          ) : (
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M1 1L13 13M13 1L1 13" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            </svg>
          )}
        </button>
      )}

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
              <span className="generating-text">Generating...</span>
            </>
          ) : (
            <span className="placeholder-icon">👤</span>
          )}
        </div>
      )}
      
      <div className="persona-info">
        <h3 className="persona-name">{persona.name}</h3>
        {persona.smallDescription && (
          <p className="persona-description">{persona.smallDescription}</p>
        )}
      </div>
    </div>
  );
}


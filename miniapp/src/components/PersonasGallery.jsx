import { useState } from 'react';
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
export default function PersonasGallery({ personas, onPersonaClick, isLoading, energy, onRefresh }) {
  const { t } = useTranslation();
  const [showCreation, setShowCreation] = useState(false);
  const [deletingId, setDeletingId] = useState(null);

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
                {energy?.is_premium ? '25 ⚡' : '50 ⚡'}
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
          energy={energy}
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
          {isDeleting ? '⏳' : '🗑️'}
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
        <div className="persona-image-placeholder">
          <span className="placeholder-icon">👤</span>
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


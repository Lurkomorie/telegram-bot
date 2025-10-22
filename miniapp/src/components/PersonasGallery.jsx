import { useState } from 'react';
import './PersonasGallery.css';

/**
 * PersonasGallery Component
 * Displays a 2-column grid of AI persona cards with images, names, and descriptions
 * Matches Lucid Dreams app design
 */
export default function PersonasGallery({ personas, onPersonaClick, isLoading }) {
  if (isLoading) {
    return (
      <div className="loading">
        <div className="spinner"></div>
        <p>Loading characters...</p>
      </div>
    );
  }

  if (!personas || personas.length === 0) {
    return (
      <div className="empty-state">
        <p>No characters available</p>
      </div>
    );
  }

  return (
    <div className="personas-gallery">
      <div className="personas-grid">
        {personas.map((persona) => (
          <PersonaCard
            key={persona.id}
            persona={persona}
            onClick={() => onPersonaClick(persona)}
          />
        ))}
      </div>
    </div>
  );
}

/**
 * PersonaCard Component
 * Individual persona card with image, name, and description
 */
function PersonaCard({ persona, onClick }) {
  const [imageError, setImageError] = useState(false);

  return (
    <div className="persona-card" onClick={onClick}>
      <div className="persona-image-container">
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
        
        {persona.badges && persona.badges.length > 0 && (
          <div className="persona-badges">
            {persona.badges.slice(0, 2).map((badge, index) => (
              <span key={index} className="badge">
                {badge}
              </span>
            ))}
          </div>
        )}
      </div>
      
      <div className="persona-info">
        <h3 className="persona-name">{persona.name}</h3>
        {persona.description && (
          <p className="persona-description">{persona.description}</p>
        )}
      </div>
    </div>
  );
}


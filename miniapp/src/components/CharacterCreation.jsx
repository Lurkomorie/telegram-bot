import { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import WebApp from '@twa-dev/sdk';
import { createCharacter } from '../api';
import {
  HAIR_COLORS,
  HAIR_STYLES,
  EYE_COLORS,
  BODY_TYPES,
  BREAST_SIZES,
  BUTT_SIZES,
} from '../constants';
import './CharacterCreation.css';

/**
 * CharacterCreation Component
 * Visual card-based wizard inspired by candy.ai
 * Step 1: Hair Color (visual color cards)
 * Step 2: Hair Style
 * Step 3: Eye Color (visual eye cards)
 * Step 4: Body Type
 * Step 5: Breast + Butt Size (combined)
 * Step 6: Name + Description
 */
function CharacterCreation({ onClose, onCreated, tokens }) {
  const [currentPage, setCurrentPage] = useState(1);
  const [slideDirection, setSlideDirection] = useState('forward');
  
  const [selections, setSelections] = useState({
    name: '',
    hair_color: 'brown',
    hair_style: 'long_wavy',
    eye_color: 'brown',
    body_type: 'athletic',
    breast_size: 'medium',
    butt_size: 'medium',
    extra_prompt: '',
  });

  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState(null);

  const isPremium = tokens.is_premium;
  const tokenCost = isPremium ? 25 : 50;
  const maxDescriptionLength = isPremium ? 4000 : 500;
  
  const totalPages = 6;

  useEffect(() => {
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = '';
    };
  }, []);

  const handleSelection = (field, value) => {
    setSelections((prev) => ({
      ...prev,
      [field]: value,
    }));
    setError(null);

    // Auto-advance after selection on all pages except final page
    if (currentPage < 6) {
      setTimeout(() => {
        advanceToNextPage();
      }, 300);
    }
  };

  const advanceToNextPage = () => {
    setSlideDirection('forward');
    setCurrentPage((prev) => prev + 1);
  };

  const goToPreviousPage = () => {
    setSlideDirection('backward');
    if (currentPage > 1) {
      setCurrentPage(currentPage - 1);
    } else {
      onClose();
    }
  };

  const handleCreate = async () => {
    if (!selections.name.trim()) {
      setError('Please enter a name');
      return;
    }
    if (!selections.extra_prompt.trim()) {
      setError('Please describe your girlfriend');
      return;
    }
    if (tokens.tokens < tokenCost) {
      setError(`Insufficient tokens. Need ${tokenCost}, have ${tokens.tokens}`);
      return;
    }

    setIsCreating(true);
    setError(null);

    try {
      const result = await createCharacter(selections, WebApp.initData);
      
      if (result.success) {
        WebApp.showAlert(`${selections.name} created successfully! 💕\nGenerating portrait...`);
        onCreated();
      } else {
        setError(result.message || 'Failed to create character');
      }
    } catch (err) {
      console.error('Create character error:', err);
      setError(err.message || 'Failed to create character. Please try again.');
    } finally {
      setIsCreating(false);
    }
  };

  const getPageTitle = () => {
    const titles = {
      1: 'Hair Color',
      2: 'Hair Style',
      3: 'Eye Color',
      4: 'Body Type',
      5: 'Proportions',
      6: 'Final Details'
    };
    return titles[currentPage];
  };

  // Get character image URL for each attribute
  const getCharacterImage = (type, value) => {
    // Placeholder for now - you'll need to add actual images to public folder
    // Format: /characters/{type}-{value}.jpg
    return `/characters/${type}-${value}.jpg`;
  };

  const getHairColorGradient = (colorKey) => {
    const gradients = {
      black: 'linear-gradient(135deg, #2a2a2a 0%, #000000 100%)',
      brown: 'linear-gradient(135deg, #8B4513 0%, #5C3317 100%)',
      blonde: 'linear-gradient(135deg, #FFD700 0%, #DAA520 100%)',
      red: 'linear-gradient(135deg, #DC143C 0%, #B22222 100%)',
      white: 'linear-gradient(135deg, #FFFFFF 0%, #D3D3D3 100%)',
      pink: 'linear-gradient(135deg, #FFB6C1 0%, #FF1493 100%)',
      blue: 'linear-gradient(135deg, #1E90FF 0%, #0047AB 100%)',
      green: 'linear-gradient(135deg, #3CB371 0%, #2E8B57 100%)',
      purple: 'linear-gradient(135deg, #9370DB 0%, #663399 100%)',
      multicolor: 'linear-gradient(135deg, #FF0080 0%, #FF8C00 25%, #FFD700 50%, #00FF00 75%, #0080FF 100%)',
    };
    return gradients[colorKey] || gradients.brown;
  };

  const getEyeColorGradient = (colorKey) => {
    const gradients = {
      brown: 'radial-gradient(circle, #8B4513 0%, #654321 60%, #000000 100%)',
      blue: 'radial-gradient(circle, #87CEEB 0%, #4169E1 60%, #000080 100%)',
      green: 'radial-gradient(circle, #90EE90 0%, #228B22 60%, #006400 100%)',
      hazel: 'radial-gradient(circle, #DAA520 0%, #8B7355 60%, #654321 100%)',
      gray: 'radial-gradient(circle, #C0C0C0 0%, #808080 60%, #404040 100%)',
    };
    return gradients[colorKey] || gradients.brown;
  };

  return createPortal(
    <div className="character-creation-overlay">
      <div className="character-creation-modal">
        {/* Header */}
        <div className="creation-header">
          <button className="back-button" onClick={goToPreviousPage} disabled={isCreating}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M19 12H5M12 19l-7-7 7-7" />
            </svg>
          </button>
          <div className="header-center">
            <div className="step-indicator">
              {Array.from({ length: totalPages }).map((_, i) => (
                <div
                  key={i}
                  className={`step-dot ${i + 1 === currentPage ? 'active' : ''} ${i + 1 < currentPage ? 'completed' : ''}`}
                />
              ))}
            </div>
          </div>
          <div className="token-cost">
            <span className="cost-amount">{tokenCost}</span>
            <span className="cost-icon">⚡</span>
          </div>
        </div>

        {/* Sliding Content */}
        <div className="creation-content-wrapper">
          <div className={`wizard-container slide-${slideDirection}`} key={currentPage}>
            
            {/* Page 1: Hair Color - 5 column compact grid */}
            {currentPage === 1 && (
              <div className="wizard-page">
                <h3 className="page-title">{getPageTitle()}</h3>
                <div className="image-cards-grid-5col">
                  {HAIR_COLORS.map((option) => (
                    <button
                      key={option.value}
                      className={`image-card ${selections.hair_color === option.value ? 'selected' : ''}`}
                      onClick={() => handleSelection('hair_color', option.value)}
                      disabled={isCreating}
                    >
                      <div 
                        className="card-image"
                        style={{ background: getHairColorGradient(option.value) }}
                      />
                      <div className="card-label-overlay">{option.label}</div>
                      {selections.hair_color === option.value && (
                        <div className="check-mark">✓</div>
                      )}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Page 2: Hair Style - 3 column grid */}
            {currentPage === 2 && (
              <div className="wizard-page">
                <h3 className="page-title">{getPageTitle()}</h3>
                <div className="image-cards-grid-3col">
                  {HAIR_STYLES.map((option) => (
                    <button
                      key={option.value}
                      className={`image-card ${selections.hair_style === option.value ? 'selected' : ''}`}
                      onClick={() => handleSelection('hair_style', option.value)}
                      disabled={isCreating}
                    >
                      <div 
                        className="card-image placeholder-gradient"
                        style={{ 
                          background: `linear-gradient(135deg, ${getHairColorGradient(selections.hair_color).split(',')[0]}, #1a1a1a)` 
                        }}
                      >
                        <span className="placeholder-emoji">{option.emoji}</span>
                      </div>
                      <div className="card-label-overlay">{option.label}</div>
                      {selections.hair_style === option.value && (
                        <div className="check-mark">✓</div>
                      )}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Page 3: Eye Color - 5 column grid for consistency */}
            {currentPage === 3 && (
              <div className="wizard-page">
                <h3 className="page-title">{getPageTitle()}</h3>
                <div className="image-cards-grid-5col">
                  {EYE_COLORS.map((option) => (
                    <button
                      key={option.value}
                      className={`image-card eye-card ${selections.eye_color === option.value ? 'selected' : ''}`}
                      onClick={() => handleSelection('eye_color', option.value)}
                      disabled={isCreating}
                    >
                      <div 
                        className="card-image eye-image"
                        style={{ background: getEyeColorGradient(option.value) }}
                      >
                        <div className="eye-shine" />
                      </div>
                      <div className="card-label-overlay">{option.label}</div>
                      {selections.eye_color === option.value && (
                        <div className="check-mark">✓</div>
                      )}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Page 4: Body Type - 2x2 grid for 4 options */}
            {currentPage === 4 && (
              <div className="wizard-page">
                <h3 className="page-title">{getPageTitle()}</h3>
                <div className="image-cards-grid-2col">
                  {BODY_TYPES.map((option) => (
                    <button
                      key={option.value}
                      className={`image-card body-card ${selections.body_type === option.value ? 'selected' : ''}`}
                      onClick={() => handleSelection('body_type', option.value)}
                      disabled={isCreating}
                    >
                      <div className="card-image body-preview">
                        <div className="body-silhouette" data-type={option.value}>
                          <div className="silhouette-shape"></div>
                        </div>
                      </div>
                      <div className="card-label-overlay">
                        <div className="label-main">{option.label}</div>
                        <div className="label-sub">{option.description}</div>
                      </div>
                      {selections.body_type === option.value && (
                        <div className="check-mark">✓</div>
                      )}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Page 5: Breast + Butt Size (Combined) */}
            {currentPage === 5 && (
              <div className="wizard-page">
                <h3 className="page-title">{getPageTitle()}</h3>
                <div className="proportions-section">
                  <div className="size-group-modern">
                    <div className="size-label">Breast Size</div>
                    <div className="size-selector">
                      {BREAST_SIZES.map((option) => (
                        <button
                          key={option.value}
                          className={`size-option ${selections.breast_size === option.value ? 'selected' : ''}`}
                          onClick={() => setSelections({ ...selections, breast_size: option.value })}
                          disabled={isCreating}
                        >
                          <span className="size-label-text">{option.label}</span>
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="size-group-modern">
                    <div className="size-label">Butt Size</div>
                    <div className="size-selector">
                      {BUTT_SIZES.map((option) => (
                        <button
                          key={option.value}
                          className={`size-option ${selections.butt_size === option.value ? 'selected' : ''}`}
                          onClick={() => setSelections({ ...selections, butt_size: option.value })}
                          disabled={isCreating}
                        >
                          <span className="size-label-text">{option.label}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                </div>

                <button
                  className="next-button-large"
                  onClick={advanceToNextPage}
                  disabled={isCreating}
                >
                  NEXT →
                </button>
              </div>
            )}

            {/* Page 6: Name + Description */}
            {currentPage === 6 && (
              <div className="wizard-page final-page">
                <div className="final-inputs">
                  <div className="input-group">
                    <input
                      type="text"
                      className="name-input-final"
                      placeholder="Enter her name..."
                      value={selections.name}
                      onChange={(e) => setSelections({ ...selections, name: e.target.value })}
                      maxLength={100}
                      disabled={isCreating}
                      autoFocus
                    />
                    <div className="input-hint center">
                      {selections.name.length}/100
                    </div>
                  </div>

                  <div className="input-group flex-grow">
                    <label className="input-label-centered">
                      Personality & Relationship
                      {isPremium && <span className="premium-badge-inline">Premium</span>}
                    </label>
                    <div className="textarea-hint">
                      Describe her personality, your relationship, background...
                    </div>
                    <textarea
                      className="description-textarea-final"
                      placeholder="Example: You're my caring girlfriend who loves gaming and coffee. We've been dating for 2 years..."
                      value={selections.extra_prompt}
                      onChange={(e) => setSelections({ ...selections, extra_prompt: e.target.value })}
                      maxLength={maxDescriptionLength}
                      disabled={isCreating}
                    />
                    <div className="input-hint center">
                      <span className={selections.extra_prompt.length > maxDescriptionLength * 0.9 ? 'warning' : ''}>
                        {selections.extra_prompt.length}/{maxDescriptionLength}
                      </span>
                      {!isPremium && (
                        <span className="upgrade-hint">Premium: 4000</span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Error Display */}
          {error && (
            <div className="error-message">
              <span className="error-icon">⚠️</span>
              {error}
            </div>
          )}
        </div>

        {/* Footer - Only on Final Page */}
        {currentPage === 6 && (
          <div className="creation-footer">
            <button
              className="create-button"
              onClick={handleCreate}
              disabled={isCreating}
            >
              {isCreating ? (
                <>
                  <span className="spinner"></span>
                  Creating...
                </>
              ) : (
                <>
                  <span>Create Girlfriend</span>
                  <span className="button-cost">{tokenCost} ⚡</span>
                </>
              )}
            </button>
          </div>
        )}
      </div>
    </div>,
    document.body
  );
}

export default CharacterCreation;

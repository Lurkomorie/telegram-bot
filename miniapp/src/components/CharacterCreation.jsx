import WebApp from '@twa-dev/sdk';
import { useCallback, useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { createCharacter } from '../api';
import {
  BODY_TYPES,
  BREAST_SIZES,
  BUTT_SIZES,
  EYE_COLORS,
  HAIR_COLORS,
  HAIR_STYLES,
} from '../constants';
import { useTranslation } from '../i18n/TranslationContext';
import './CharacterCreation.css';

// Import images directly
import bodyAthleticImg from '../assets/body-athletic.png';
import bodyCurvyImg from '../assets/body-curvy.png';
import bodySlimImg from '../assets/body-slim.png';
import bodyVoluptuousImg from '../assets/body-voluptuous.png';
import braidedImg from '../assets/braided.png';
import curlyImg from '../assets/curly.png';
import lightningImg from '../assets/lightning.png';
import longStraightImg from '../assets/long-straight.png';
import longWavyImg from '../assets/long-wavy.png';
import ponytailImg from '../assets/ponytail.png';
import shortImg from '../assets/short.png';

const HAIR_STYLE_IMAGES = {
  'long_straight': longStraightImg,
  'long_wavy': longWavyImg,
  'short': shortImg,
  'ponytail': ponytailImg,
  'braided': braidedImg,
  'curly': curlyImg,
};

const BODY_TYPE_IMAGES = {
  'slim': bodySlimImg,
  'athletic': bodyAthleticImg,
  'curvy': bodyCurvyImg,
  'voluptuous': bodyVoluptuousImg,
};

/**
 * CharacterCreation Component
 */
function CharacterCreation({ onClose, onCreated, tokens, onNavigateToTokens }) {
  const { t } = useTranslation();
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
  const hasFreeCreation = !tokens?.char_created;
  const maxDescriptionLength = isPremium ? 4000 : 300;
  const maxNameLength = 20;
  
  const totalPages = 6;

  useEffect(() => {
    document.body.style.overflow = 'hidden';
    
    // Show Telegram native back button
    WebApp.BackButton.show();
    WebApp.BackButton.onClick(goToPreviousPage);
    
    return () => {
      document.body.style.overflow = '';
      // Hide back button and remove listener when component unmounts
      WebApp.BackButton.hide();
      WebApp.BackButton.offClick(goToPreviousPage);
    };
  }, [goToPreviousPage]);

  const handleSelection = (field, value) => {
    setSelections((prev) => ({
      ...prev,
      [field]: value,
    }));
    setError(null);
  };

  const advanceToNextPage = () => {
    setSlideDirection('forward');
    setCurrentPage((prev) => prev + 1);
  };

  const goToPreviousPage = useCallback(() => {
    setSlideDirection('backward');
    if (currentPage > 1) {
      setCurrentPage(currentPage - 1);
    } else {
      onClose();
    }
  }, [currentPage, onClose]);

  const handleCreate = async () => {
    if (!selections.name.trim()) {
      setError(t('characterCreation.errors.nameRequired'));
      return;
    }
    if (!selections.extra_prompt.trim()) {
      setError(t('characterCreation.errors.descriptionRequired'));
      return;
    }
    if (!hasFreeCreation && tokens.tokens < tokenCost) {
      // Redirect to energy buy page immediately
      onClose(); // Close character creation modal
      if (onNavigateToTokens) {
        onNavigateToTokens();
      }
      return;
    }

    setIsCreating(true);
    setError(null);

    try {
      const result = await createCharacter(selections, WebApp.initData);
      
      if (result.success) {
        const msg = t('characterCreation.success').replace('{name}', selections.name);
        WebApp.showAlert(msg);
        onCreated();
      } else {
        // Handle specific error cases
        if (result.error === 'insufficient_tokens') {
          // Redirect to energy buy page immediately
          onClose();
          if (onNavigateToTokens) {
            onNavigateToTokens();
          }
        } else {
          setError(result.message || t('characterCreation.errors.creationFailed'));
        }
      }
    } catch (err) {
      console.error('Create character error:', err);
      setError(err.message || t('characterCreation.errors.creationFailed'));
    } finally {
      setIsCreating(false);
    }
  };

  const getPageTitle = () => {
    const titles = {
      1: t('characterCreation.hairColor.title'),
      2: t('characterCreation.hairStyle.title'),
      3: t('characterCreation.eyeColor.title'),
      4: t('characterCreation.bodyType.title'),
      5: t('characterCreation.proportions.title'),
      6: t('characterCreation.final.title')
    };
    return titles[currentPage];
  };

  const getHairColorBright = (colorKey) => {
    const colors = {
      black: '#3a3a3a',
      brown: '#8B5A3C',
      blonde: '#FFE4B5',
      red: '#E74C3C',
      white: '#F5F5F5',
      pink: '#FF69B4',
      blue: '#5DADE2',
      green: '#52D273',
      purple: '#AF7AC5',
      multicolor: 'linear-gradient(135deg, #FF1493 0%, #FFD700 25%, #00FF7F 50%, #1E90FF 75%, #9370DB 100%)',
    };
    return colors[colorKey] || colors.brown;
  };

  const getHairColorBorderActive = (colorKey) => {
    const borders = {
      black: '#1a1a1a',
      brown: '#5C3317',
      blonde: '#DAA520',
      red: '#C0392B',
      white: '#DCDCDC',
      pink: '#FF1493',
      blue: '#3498DB',
      green: '#27AE60',
      purple: '#8E44AD',
      multicolor: '#ffffff',
    };
    return borders[colorKey] || borders.brown;
  };

  const getEyeColorSimple = (colorKey) => {
    const colors = {
      brown: '#8B4513',
      blue: '#4169E1',
      green: '#228B22',
      hazel: '#DAA520',
      gray: '#808080',
    };
    return colors[colorKey] || colors.brown;
  };

  const getEyeColorBorderActive = (colorKey) => {
    const borders = {
      brown: '#654321',
      blue: '#1E3A8A',
      green: '#15803D',
      hazel: '#B8860B',
      gray: '#4B5563',
    };
    return borders[colorKey] || borders.brown;
  };

  return createPortal(
    <div className="character-creation-overlay">
      <div className="character-creation-modal">
        
        {/* Header with back button and title */}
        <div className="character-creation-header">
          <button className="back-button-new" onClick={goToPreviousPage} disabled={isCreating}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <path d="M19 12H5M12 19l-7-7 7-7" />
            </svg>
          </button>
          <h3 className="page-title">{getPageTitle()}</h3>
          <div className="progress-circle">
            <svg width="40" height="40" viewBox="0 0 40 40">
              <defs>
                <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#EF4444" />
                  <stop offset="50%" stopColor="#F97316" />
                  <stop offset="100%" stopColor="#FB923C" />
                </linearGradient>
              </defs>
              <circle
                cx="20"
                cy="20"
                r="16"
                fill="none"
                stroke="rgba(255, 255, 255, 0.1)"
                strokeWidth="2.5"
              />
              <circle
                cx="20"
                cy="20"
                r="16"
                fill="none"
                stroke="url(#gradient)"
                strokeWidth="2.5"
                strokeDasharray={`${(currentPage / totalPages) * 100.5} 100.5`}
                strokeLinecap="round"
                transform="rotate(-90 20 20)"
              />
              <text
                x="20"
                y="20"
                textAnchor="middle"
                dy="0.35em"
                fontSize="11"
                fill="#ffffff"
                fontWeight="700"
              >
                {currentPage}/{totalPages}
              </text>
            </svg>
          </div>
        </div>

        {/* Sliding Content */}
        <div className="creation-content-wrapper">
          <div className={`wizard-container slide-${slideDirection}`} key={currentPage}>
            
            {/* Page 1: Hair Color */}
            {currentPage === 1 && (
              <div className="wizard-page">
                <div className="hair-color-grid">
                  {HAIR_COLORS.map((option) => {
                    const isSelected = selections.hair_color === option.value;
                    const bgColor = getHairColorBright(option.value);
                    const borderColor = getHairColorBorderActive(option.value);
                    const isMulticolor = option.value === 'multicolor';
                    
                    return (
                      <div key={option.value} className="hair-color-item">
                        <button
                          className={`hair-color-box ${isSelected ? 'selected' : ''} ${isMulticolor ? 'multicolor' : ''}`}
                          onClick={() => handleSelection('hair_color', option.value)}
                          disabled={isCreating}
                          style={{
                            background: bgColor,
                            borderColor: isMulticolor ? '#ffffff' : (isSelected ? borderColor : undefined),
                          }}
                        />
                        <span className="hair-color-label">
                          {t(`characterCreation.hairColor.${option.value}`)}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Page 2: Hair Style */}
            {currentPage === 2 && (
              <div className="wizard-page">
                <div className="hair-style-grid">
                  {HAIR_STYLES.map((option) => (
                    <button
                      key={option.value}
                      className={`hair-style-box ${selections.hair_style === option.value ? 'selected' : ''}`}
                      onClick={() => handleSelection('hair_style', option.value)}
                      disabled={isCreating}
                    >
                      <img 
                        src={HAIR_STYLE_IMAGES[option.value]}
                        alt={option.label}
                        className="hair-style-icon"
                      />
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Page 3: Eye Color */}
            {currentPage === 3 && (
              <div className="wizard-page">
                <div className="eye-color-grid">
                  {EYE_COLORS.map((option) => {
                    const isSelected = selections.eye_color === option.value;
                    const bgColor = getEyeColorSimple(option.value);
                    const borderColor = getEyeColorBorderActive(option.value);
                    
                    return (
                      <div 
                        key={option.value}
                        className="eye-color-item"
                      >
                        <button
                          className={`eye-color-circle ${isSelected ? 'selected' : ''}`}
                          onClick={() => handleSelection('eye_color', option.value)}
                          disabled={isCreating}
                          style={{ 
                            background: bgColor,
                            borderColor: isSelected ? borderColor : undefined,
                          }}
                        />
                        <span className="eye-color-label">
                          {t(`characterCreation.eyeColor.${option.value}`)}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Page 4: Body Type */}
            {currentPage === 4 && (
              <div className="wizard-page">
                <div className="body-type-grid">
                  {BODY_TYPES.map((option) => (
                    <button
                      key={option.value}
                      className={`body-type-box ${selections.body_type === option.value ? 'selected' : ''}`}
                      onClick={() => handleSelection('body_type', option.value)}
                      disabled={isCreating}
                    >
                      <img 
                        src={BODY_TYPE_IMAGES[option.value]}
                        alt={option.label}
                        className="body-type-image"
                      />
                      <span className="body-type-label">
                        {t(`characterCreation.bodyType.${option.value}`)}
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Page 5: Breast + Butt Size (Combined) */}
            {currentPage === 5 && (
              <div className="wizard-page">
                <div className="proportions-section">
                  <div className="size-group-new">
                    <div className="size-label-new">{t('characterCreation.proportions.breastSize')}</div>
                    <div className="size-selector-new">
                      {BREAST_SIZES.map((option) => (
                        <button
                          key={option.value}
                          className={`size-option-new ${selections.breast_size === option.value ? 'selected' : ''}`}
                          onClick={() => setSelections({ ...selections, breast_size: option.value })}
                          disabled={isCreating}
                        >
                          <span className="size-label-text">
                            {t(`characterCreation.proportions.${option.value}`)}
                          </span>
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="size-group-new">
                    <div className="size-label-new">{t('characterCreation.proportions.buttSize')}</div>
                    <div className="size-selector-new">
                      {BUTT_SIZES.map((option) => (
                        <button
                          key={option.value}
                          className={`size-option-new ${selections.butt_size === option.value ? 'selected' : ''}`}
                          onClick={() => setSelections({ ...selections, butt_size: option.value })}
                          disabled={isCreating}
                        >
                          <span className="size-label-text">
                            {t(`characterCreation.proportions.${option.value}`)}
                          </span>
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
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
                      placeholder={t('characterCreation.final.namePlaceholder')}
                      value={selections.name}
                      onChange={(e) => setSelections({ ...selections, name: e.target.value.slice(0, maxNameLength) })}
                      maxLength={maxNameLength}
                      disabled={isCreating}
                      autoFocus
                    />
                    <div className="input-hint right">
                      {selections.name.length}/{maxNameLength}
                    </div>
                  </div>

                  <div className="input-group flex-grow">
                    <label className="input-label-centered">
                      {t('characterCreation.final.personalityLabel')}
                      {isPremium && <span className="premium-badge-inline">{t('characterCreation.final.premiumBadge')}</span>}
                    </label>
                    <div className="textarea-hint">
                      {t('characterCreation.final.descriptionHint')}
                    </div>
                    <textarea
                      className="description-textarea-final"
                      placeholder={t('characterCreation.final.descriptionPlaceholder')}
                      value={selections.extra_prompt}
                      onChange={(e) => setSelections({ ...selections, extra_prompt: e.target.value.slice(0, maxDescriptionLength) })}
                      maxLength={maxDescriptionLength}
                      disabled={isCreating}
                    />
                    <div className="input-hint right">
                      <span className={selections.extra_prompt.length > maxDescriptionLength * 0.9 ? 'warning' : ''}>
                        {selections.extra_prompt.length}/{maxDescriptionLength}
                      </span>
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
                  {t('characterCreation.final.creating')}
                </>
              ) : (
                <>
                  <span>{t('characterCreation.final.createButton')}</span>
                  {!hasFreeCreation && (
                    <span className="button-cost">
                      <img src={lightningImg} alt="tokens" className="button-cost-icon" />
                      {tokenCost}
                    </span>
                  )}
                </>
              )}
            </button>
          </div>
        )}

        {/* Next button for all pages except last */}
        {currentPage < 6 && (
          <button
            className="next-button-bottom"
            onClick={advanceToNextPage}
            disabled={isCreating}
          >
            {t('characterCreation.proportions.nextButton')}
            <span>→</span>
          </button>
        )}
      </div>
    </div>,
    document.body
  );
}

export default CharacterCreation;

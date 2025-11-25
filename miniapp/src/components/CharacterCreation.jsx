import { useState, useEffect } from 'react';
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
 * Full-page modal for creating custom girlfriend characters
 * Features intuitive UI, live validation, and great UX
 */
function CharacterCreation({ onClose, onCreated, energy }) {
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
  const [charCount, setCharCount] = useState(0);

  // Determine token cost and max description based on premium status
  const isPremium = energy.is_premium;
  const tokenCost = isPremium ? 25 : 50;
  const maxDescriptionLength = isPremium ? 4000 : 500;

  useEffect(() => {
    setCharCount(selections.extra_prompt.length);
  }, [selections.extra_prompt]);

  // Disable body scrolling when modal is open
  useEffect(() => {
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = '';
    };
  }, []);

  const handleChange = (field, value) => {
    setSelections((prev) => ({
      ...prev,
      [field]: value,
    }));
    setError(null);
  };

  const validateForm = () => {
    if (!selections.name.trim()) {
      return 'Please enter a name for your girlfriend';
    }
    if (selections.name.length > 100) {
      return 'Name must be 100 characters or less';
    }
    if (!selections.extra_prompt.trim()) {
      return 'Please describe your girlfriend';
    }
    if (selections.extra_prompt.length > maxDescriptionLength) {
      return `Description must be ${maxDescriptionLength} characters or less`;
    }
    if (energy.energy < tokenCost) {
      return `Insufficient tokens. Need ${tokenCost}, have ${energy.energy}`;
    }
    return null;
  };

  const handleCreate = async () => {
    const validationError = validateForm();
    if (validationError) {
      setError(validationError);
      return;
    }

    setIsCreating(true);
    setError(null);

    try {
      const result = await createCharacter(selections, WebApp.initData);
      
      if (result.success) {
        // Show success message
        WebApp.showAlert(`${selections.name} created successfully! 💕\nGenerating portrait...`);
        
        // Call parent to refresh and close
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

  const getAttributeLabel = (field) => {
    const labels = {
      hair_color: 'Hair Color',
      hair_style: 'Hair Style',
      eye_color: 'Eye Color',
      body_type: 'Body Type',
      breast_size: 'Breast Size',
      butt_size: 'Butt Size',
    };
    return labels[field];
  };

  const getOptions = (field) => {
    const optionsMap = {
      hair_color: HAIR_COLORS,
      hair_style: HAIR_STYLES,
      eye_color: EYE_COLORS,
      body_type: BODY_TYPES,
      breast_size: BREAST_SIZES,
      butt_size: BUTT_SIZES,
    };
    return optionsMap[field];
  };

  return (
    <div className="character-creation-overlay">
      <div className="character-creation-modal">
        {/* Header */}
        <div className="creation-header">
          <button className="back-button" onClick={onClose} disabled={isCreating}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M19 12H5M12 19l-7-7 7-7" />
            </svg>
          </button>
          <h2>Create Your Girlfriend</h2>
          <div className="token-cost">
            <span className="cost-amount">{tokenCost}</span>
            <span className="cost-icon">⚡</span>
          </div>
        </div>

        {/* Scrollable Content */}
        <div className="creation-content">
          {/* Name Input */}
          <div className="form-section">
            <label className="form-label">
              <span className="label-text">Name</span>
              <span className="label-required">*</span>
            </label>
            <input
              type="text"
              className="name-input"
              placeholder="e.g., Emma, Sophie, Luna..."
              value={selections.name}
              onChange={(e) => handleChange('name', e.target.value)}
              maxLength={100}
              disabled={isCreating}
            />
            <div className="input-hint">
              {selections.name.length}/100 characters
            </div>
          </div>

          {/* Physical Attributes */}
          <div className="form-section">
            <div className="section-title">Physical Attributes</div>
            <div className="attributes-grid">
              {['hair_color', 'hair_style', 'eye_color', 'body_type', 'breast_size', 'butt_size'].map(
                (field) => (
                  <div key={field} className="attribute-select">
                    <label className="select-label">{getAttributeLabel(field)}</label>
                    <select
                      className="custom-select"
                      value={selections[field]}
                      onChange={(e) => handleChange(field, e.target.value)}
                      disabled={isCreating}
                    >
                      {getOptions(field).map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.emoji ? `${option.emoji} ${option.label}` : option.label}
                          {option.description ? ` - ${option.description}` : ''}
                        </option>
                      ))}
                    </select>
                  </div>
                )
              )}
            </div>
          </div>

          {/* Personality & Relationship */}
          <div className="form-section">
            <label className="form-label">
              <span className="label-text">Personality & Relationship</span>
              <span className="label-required">*</span>
              {isPremium && <span className="premium-badge">Premium</span>}
            </label>
            <div className="textarea-hint">
              Describe your girlfriend's personality, your relationship, background, interests, etc.
            </div>
            <textarea
              className="description-textarea"
              placeholder="Example: You're my caring girlfriend who loves gaming and coffee. We've been dating for 2 years. You're playful and supportive, always making me smile. You work as a graphic designer and enjoy cozy evenings together..."
              value={selections.extra_prompt}
              onChange={(e) => handleChange('extra_prompt', e.target.value)}
              maxLength={maxDescriptionLength}
              rows={8}
              disabled={isCreating}
            />
            <div className="input-hint">
              <span className={charCount > maxDescriptionLength * 0.9 ? 'warning' : ''}>
                {charCount}/{maxDescriptionLength} characters
              </span>
              {!isPremium && (
                <span className="upgrade-hint">
                  Premium: {4000} characters
                </span>
              )}
            </div>
          </div>

          {/* Error Display */}
          {error && (
            <div className="error-message">
              <span className="error-icon">⚠️</span>
              {error}
            </div>
          )}
        </div>

        {/* Footer with Create Button */}
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
      </div>
    </div>
  );
}

export default CharacterCreation;


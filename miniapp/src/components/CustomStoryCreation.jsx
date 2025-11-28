import { useState } from 'react';
import WebApp from '@twa-dev/sdk';
import './CustomStoryCreation.css';
import { useTranslation } from '../i18n/TranslationContext';
import { createCustomStory } from '../api';

/**
 * CustomStoryCreation Component
 * Allows users to create a custom story for their character
 */
export default function CustomStoryCreation({ persona, onBack, onStoryCreated }) {
  const { t } = useTranslation();
  const [storyText, setStoryText] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState(null);

  const handleCreate = async () => {
    if (storyText.length < 5) {
      setError('Story must be at least 5 characters');
      return;
    }

    setIsCreating(true);
    setError(null);

    try {
      const result = await createCustomStory({
        persona_id: persona.id,
        story_description: storyText
      }, WebApp.initData);

      if (result.success) {
        // Pass the created story back to start the chat
        onStoryCreated({
          id: result.history_id,
          name: 'Custom Story',
          description: storyText
        });
      } else {
        setError(result.message || 'Failed to create story');
      }
    } catch (err) {
      console.error('Create story error:', err);
      setError(err.message || 'Failed to create story. Please try again.');
    } finally {
      setIsCreating(false);
    }
  };

  const placeholderText = t('customStory.placeholder').replace('{name}', persona.name);
  const titleText = t('customStory.title').replace('{name}', persona.name);

  return (
    <div className="custom-story-creation">
      <div className="custom-story-header">
        <h2 className="custom-story-title">{titleText}</h2>
      </div>

      <div className="custom-story-content">
        <textarea
          className="story-textarea"
          placeholder={placeholderText}
          value={storyText}
          onChange={(e) => setStoryText(e.target.value)}
          disabled={isCreating}
        />
        
        <div className="story-counter">
          {storyText.length} characters
        </div>

        {error && (
          <div className="error-message">
            <span className="error-icon">⚠️</span>
            {error}
          </div>
        )}
      </div>

      <div className="custom-story-footer">
        <button
          className="start-story-button"
          onClick={handleCreate}
          disabled={isCreating || storyText.length < 5}
        >
          {isCreating ? (
            <>
              <span className="spinner-small"></span>
              Creating...
            </>
          ) : (
            t('customStory.startButton')
          )}
        </button>
      </div>
    </div>
  );
}


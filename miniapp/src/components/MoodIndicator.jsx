import { useTranslation } from '../i18n/TranslationContext';
import './MoodIndicator.css';

/**
 * MoodIndicator - Shows the character's mood as hearts
 * @param {Object} props
 * @param {number} props.mood - Mood value 0-100
 * @param {boolean} props.compact - Show compact version (just hearts)
 */
export default function MoodIndicator({ mood = 50, compact = false }) {
  const { t } = useTranslation();
  
  // Calculate filled hearts (0-5 scale)
  const filledHearts = Math.round((mood / 100) * 5);
  
  // Get mood description
  const getMoodLabel = () => {
    if (mood >= 80) return t('mood.veryHappy');
    if (mood >= 60) return t('mood.happy');
    if (mood >= 40) return t('mood.neutral');
    if (mood >= 20) return t('mood.cold');
    return t('mood.veryCold');
  };
  
  // Render hearts
  const renderHearts = () => {
    const hearts = [];
    for (let i = 0; i < 5; i++) {
      hearts.push(
        <span 
          key={i} 
          className={`mood-heart ${i < filledHearts ? 'filled' : 'empty'}`}
        >
          {i < filledHearts ? '❤️' : '🤍'}
        </span>
      );
    }
    return hearts;
  };
  
  if (compact) {
    return (
      <div className="mood-indicator compact" title={getMoodLabel()}>
        {renderHearts()}
      </div>
    );
  }
  
  return (
    <div className="mood-indicator">
      <div className="mood-hearts">
        {renderHearts()}
      </div>
      <span className="mood-label">{getMoodLabel()}</span>
    </div>
  );
}

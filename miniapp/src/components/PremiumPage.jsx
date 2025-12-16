import WebApp from '@twa-dev/sdk';
import { useEffect } from 'react';
import { trackEvent } from '../api';
import starIcon from '../assets/star.webp';
import { useTranslation } from '../i18n/TranslationContext';
import './PremiumPage.css';

/**
 * PremiumPage Component
 * Shows premium tier subscriptions
 */
export default function PremiumPage({ onNavigateToCheckout }) {
  const { t } = useTranslation();
  
  // Track page view
  useEffect(() => {
    const initData = WebApp.initData;
    trackEvent('plans_page_viewed', {}, initData).catch(err => {
      console.error('Failed to track plans page view:', err);
    });
  }, []);

  // Premium tiers with translation keys
  const tiers = [
    {
      id: 'plus_month',
      name: 'Plus',
      icon: '❄️',
      daily: 50,
      bonus: 500,
      stars: 450,
      featureKeys: [
        'premium.plus.feature1',
        'premium.plus.feature2',
        'premium.plus.feature3',
        'premium.plus.feature4',
        'premium.plus.feature5',
        'premium.plus.feature6',
        'premium.plus.feature7'
      ]
    },
    {
      id: 'pro_month',
      name: 'Pro',
      icon: '🔥',
      daily: 75,
      bonus: 750,
      stars: 700,
      featureKeys: [
        'premium.pro.feature1',
        'premium.pro.feature2',
        'premium.pro.feature3'
      ]
    },
    {
      id: 'legendary_month',
      name: 'Legendary',
      icon: '🏆',
      daily: 100,
      bonus: 1000,
      stars: 900,
      featureKeys: [
        'premium.legendary.feature1',
        'premium.legendary.feature2',
        'premium.legendary.feature3',
      ]
    }
  ];

  const handleTierClick = (tier) => {
    onNavigateToCheckout(tier);
  };

  return (
    <div className="premium-page">
      {tiers.map((tier) => (
        <div key={tier.id} className="premium-card">
          <div className="premium-card-header">
            <div className="premium-card-title">
              <span className="tier-icon-large">{tier.icon}</span>
              <span className="tier-name-large">{tier.name}</span>
            </div>
            <div className="premium-card-price">
              <div className="price-amount">
                <img src={starIcon} alt="star" className="star-icon" />
                {tier.stars}
              </div>
              <div className="price-period">{t('premium.perMonth')}</div>
            </div>
          </div>

          <div className="premium-card-body">
            <h3 className="benefits-title">{t('premium.benefits')}</h3>
            <div className="benefits-list">
              {tier.featureKeys.map((featureKey, index) => (
                <div key={index} className="benefit-item">
                  <svg className="check-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points="20 6 9 17 4 12"></polyline>
                  </svg>
                  <span className="benefit-text">{t(featureKey)}</span>
                </div>
              ))}
            </div>
          </div>

          <button 
            className="premium-card-button" 
            onClick={() => handleTierClick(tier)}
          >
            {t('premium.getButton', { name: tier.name })}
          </button>
        </div>
      ))}
    </div>
  );
}

import WebApp from '@twa-dev/sdk';
import { useEffect } from 'react';
import { trackEvent } from '../api';
import christmasBg from '../assets/christmas-bg.webp';
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

  // New Year Sale - 20% off all prices!
  const DISCOUNT_PERCENT = 20;
  const calcDiscount = (price) => Math.round(price * (1 - DISCOUNT_PERCENT / 100));

  // Premium tiers with translation keys (original + discounted)
  const tiers = [
    {
      id: 'plus_month',
      name: 'Plus',
      icon: '❄️',
      daily: 50,
      bonus: 500,
      originalStars: 450,
      stars: calcDiscount(450),
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
      daily: 100,
      bonus: 750,
      originalStars: 700,
      stars: calcDiscount(700),
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
      daily: 150,
      bonus: 1000,
      originalStars: 900,
      stars: calcDiscount(900),
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
      {/* New Year Sale Banner */}
      <div className="sale-banner" style={{ backgroundImage: `url(${christmasBg})` }}>
        <div className="sale-banner-overlay"></div>
        <div className="sale-banner-snow">
          {[...Array(12)].map((_, i) => (
            <span key={i} className="snowflake">❄</span>
          ))}
        </div>
        <div className="sale-banner-content">
          <span className="sale-banner-emoji">🎄</span>
          <div className="sale-banner-text-group">
            <span className="sale-banner-title">NEW YEAR SALE</span>
            <span className="sale-banner-discount">{DISCOUNT_PERCENT}% OFF PREMIUM</span>
          </div>
          <span className="sale-banner-emoji">🎁</span>
        </div>
      </div>

      {tiers.map((tier) => (
        <div key={tier.id} className="premium-card">
          <div className="sale-tag-corner">-{DISCOUNT_PERCENT}%</div>
          <div className="premium-card-header">
            <div className="premium-card-title">
              <span className="tier-icon-large">{tier.icon}</span>
              <span className="tier-name-large">{tier.name}</span>
            </div>
            <div className="premium-card-price">
              <div className="price-original">
                <img src={starIcon} alt="star" className="star-icon-small" />
                <span className="original-stars">{tier.originalStars}</span>
              </div>
              <div className="price-amount discounted">
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

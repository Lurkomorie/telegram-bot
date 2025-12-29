import WebApp from '@twa-dev/sdk';
import { useEffect, useState } from 'react';
import { createInvoice, trackEvent } from '../api';
import christmasBg from '../assets/christmas-bg.webp';
import starIcon from '../assets/star.webp';
import { useTranslation } from '../i18n/TranslationContext';
import './PlansPage.css';

/**
 * PlansPage Component
 * Shows token packages and premium tiers
 */
export default function PlansPage() {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState('tokens');
  const [selectedProduct, setSelectedProduct] = useState('tokens_1000');
  const [isProcessing, setIsProcessing] = useState(false);

  // Track plans page view
  useEffect(() => {
    const initData = WebApp.initData;
    trackEvent('plans_page_viewed', {}, initData).catch(err => {
      console.error('Failed to track plans page view:', err);
    });
  }, []);

  // New Year Sale - 20% off all prices!
  const DISCOUNT_PERCENT = 20;
  const calcDiscount = (price) => Math.round(price * (1 - DISCOUNT_PERCENT / 100));

  // Token packages with bulk discounts (cheaper per token for larger packages)
  const tokenPackages = [
    { id: 'tokens_50', amount: 50, originalStars: 35, stars: calcDiscount(35) },       // 0.70/token
pri    { id: 'tokens_100', amount: 100, originalStars: 68, stars: calcDiscount(68) },     // 0.68/token
    { id: 'tokens_250', amount: 250, originalStars: 165, stars: calcDiscount(165) },   // 0.66/token
    { id: 'tokens_500', amount: 500, originalStars: 320, stars: calcDiscount(320) },   // 0.64/token
    { id: 'tokens_1000', amount: 1000, originalStars: 620, stars: calcDiscount(620), popular: true },  // 0.62/token
    { id: 'tokens_2500', amount: 2500, originalStars: 1500, stars: calcDiscount(1500) }, // 0.60/token
    { id: 'tokens_5000', amount: 5000, originalStars: 2900, stars: calcDiscount(2900) }, // 0.58/token
    { id: 'tokens_10000', amount: 10000, originalStars: 5600, stars: calcDiscount(5600) }, // 0.56/token
    { id: 'tokens_25000', amount: 25000, originalStars: 13500, stars: calcDiscount(13500), bestValue: true },  // 0.54/token
  ];

  // Premium tiers (original + discounted)
  const premiumTiers = [
    { id: 'plus_month', name: 'Plus', daily: 50, originalStars: 450, stars: calcDiscount(450) },
    { id: 'pro_month', name: 'Pro', daily: 75, originalStars: 700, stars: calcDiscount(700), popular: true },
    { id: 'legendary_month', name: 'Legendary', daily: 100, originalStars: 900, stars: calcDiscount(900) },
  ];

  const handlePurchase = async () => {
    if (isProcessing) return;
    
    setIsProcessing(true);
    
    try {
      const initData = WebApp.initData;
      
      // Create invoice via API
      const result = await createInvoice(selectedProduct, initData);
      
      // Check if this is a simulated payment
      if (result.simulated) {
        // Simulated payment - already processed on backend
        WebApp.showAlert('✅ Payment successful! Thank you for your purchase!');
        window.location.reload();
        return;
      }
      
      // Real payment - open Telegram invoice
      const { invoice_link } = result;
      
      // Open invoice using Telegram WebApp API
      WebApp.openInvoice(invoice_link, (status) => {
        if (status === 'paid') {
          WebApp.showAlert('✅ Payment successful! Thank you for your purchase!');
          window.location.reload();
        } else if (status === 'cancelled') {
          WebApp.showAlert('Payment cancelled');
        } else if (status === 'failed') {
          WebApp.showAlert('Payment failed. Please try again.');
        }
        setIsProcessing(false);
      });
    } catch (error) {
      console.error('Failed to create invoice:', error);
      WebApp.showAlert('Failed to create invoice. Please try again.');
      setIsProcessing(false);
    }
  };

  return (
    <div className="plans-page">
      <div className="plans-tabs">
        <button
          className={`tab-button ${activeTab === 'tokens' ? 'active' : ''}`}
          onClick={() => setActiveTab('tokens')}
        >
          🪙 Token Packages
        </button>
        <button
          className={`tab-button ${activeTab === 'tiers' ? 'active' : ''}`}
          onClick={() => setActiveTab('tiers')}
        >
          💎 Premium Tiers
        </button>
      </div>

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
            <span className="sale-banner-discount">{DISCOUNT_PERCENT}% OFF ALL PLANS</span>
          </div>
          <span className="sale-banner-emoji">🎁</span>
        </div>
      </div>

      {activeTab === 'tokens' ? (
        <div className="tokens-section">
          <div className="section-description">
            <p>Purchase tokens for one-time use. Tokens never expire!</p>
          </div>
          <div className="token-packages-grid">
            {tokenPackages.map((pkg) => (
              <div
                key={pkg.id}
                className={`token-package ${selectedProduct === pkg.id ? 'selected' : ''}`}
                onClick={() => setSelectedProduct(pkg.id)}
              >
                <div className="sale-tag">-{DISCOUNT_PERCENT}%</div>
                {pkg.popular && <div className="badge popular">Popular</div>}
                {pkg.bestValue && <div className="badge best-value">Best Value</div>}
                <div className="package-amount">🪙 {pkg.amount.toLocaleString()}</div>
                <div className="package-price-container">
                  <span className="original-price">
                    <img src={starIcon} alt="star" className="star-icon-inline" />
                    {pkg.originalStars.toLocaleString()}
                  </span>
                  <span className="discounted-price">
                    <img src={starIcon} alt="star" className="star-icon-inline" />
                    {pkg.stars.toLocaleString()}
                  </span>
                </div>
                {selectedProduct === pkg.id && (
                  <svg className="checkmark" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                    <polyline points="20 6 9 17 4 12"></polyline>
                  </svg>
                )}
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="tiers-section">
          <div className="section-description">
            <p>Subscribe to get daily tokens automatically. Cancel anytime!</p>
          </div>
          <div className="tiers-grid">
            {premiumTiers.map((tier) => (
              <div
                key={tier.id}
                className={`tier-card ${selectedProduct === tier.id ? 'selected' : ''}`}
                onClick={() => setSelectedProduct(tier.id)}
              >
                <div className="sale-tag">-{DISCOUNT_PERCENT}%</div>
                {tier.popular && <div className="badge popular">Popular</div>}
                <div className="tier-name">{tier.name}</div>
                <div className="tier-daily">+{tier.daily} tokens/day</div>
                <div className="tier-price-container">
                  <span className="original-price">
                    <img src={starIcon} alt="star" className="star-icon-inline" />
                    {tier.originalStars}
                  </span>
                  <span className="discounted-price">
                    <img src={starIcon} alt="star" className="star-icon-inline" />
                    {tier.stars}/mo
                  </span>
                </div>
                <div className="tier-total">{tier.daily * 30} tokens total</div>
                {selectedProduct === tier.id && (
                  <svg className="checkmark" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                    <polyline points="20 6 9 17 4 12"></polyline>
                  </svg>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      <button className="purchase-button-sticky" onClick={handlePurchase} disabled={isProcessing}>
        {isProcessing ? 'Processing...' : `Purchase ${activeTab === 'tokens' ? 'Tokens' : 'Subscription'}`}
      </button>
    </div>
  );
}






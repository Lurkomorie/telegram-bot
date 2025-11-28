import WebApp from '@twa-dev/sdk';
import { useState, useEffect } from 'react';
import { createInvoice, trackEvent } from '../api';
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

  // Token packages with exact pricing
  const tokenPackages = [
    { id: 'tokens_50', amount: 50, stars: 35 },
    { id: 'tokens_100', amount: 100, stars: 70 },
    { id: 'tokens_250', amount: 250, stars: 175 },
    { id: 'tokens_500', amount: 500, stars: 350 },
    { id: 'tokens_1000', amount: 1000, stars: 700, popular: true },
    { id: 'tokens_2500', amount: 2500, stars: 1750 },
    { id: 'tokens_5000', amount: 5000, stars: 3500 },
    { id: 'tokens_10000', amount: 10000, stars: 7000 },
    { id: 'tokens_25000', amount: 25000, stars: 17500, bestValue: true },
  ];

  // Premium tiers
  const premiumTiers = [
    { id: 'plus_month', name: 'Plus', daily: 50, stars: 300 },
    { id: 'pro_month', name: 'Pro', daily: 75, stars: 450, popular: true },
    { id: 'legendary_month', name: 'Legendary', daily: 100, stars: 600 },
  ];

  const handlePurchase = async () => {
    if (isProcessing) return;
    
    setIsProcessing(true);
    
    try {
      const initData = WebApp.initData;
      
      // Create invoice via API
      const { invoice_link } = await createInvoice(selectedProduct, initData);
      
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
                {pkg.popular && <div className="badge popular">Popular</div>}
                {pkg.bestValue && <div className="badge best-value">Best Value</div>}
                <div className="package-amount">🪙 {pkg.amount.toLocaleString()}</div>
                <div className="package-price">⭐ {pkg.stars.toLocaleString()} stars</div>
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
                {tier.popular && <div className="badge popular">Popular</div>}
                <div className="tier-name">{tier.name}</div>
                <div className="tier-daily">+{tier.daily} tokens/day</div>
                <div className="tier-price">⭐ {tier.stars} stars/month</div>
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






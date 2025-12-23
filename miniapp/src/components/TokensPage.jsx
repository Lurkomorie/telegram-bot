import WebApp from '@twa-dev/sdk';
import { useState, useEffect } from 'react';
import { createInvoice, trackEvent } from '../api';
import { useTranslation } from '../i18n/TranslationContext';
import './TokensPage.css';
import lightningIcon from '../assets/lightning.webp';
import starIcon from '../assets/star.webp';
import christmasBg from '../assets/christmas-bg.webp';

/**
 * TokensPage Component
 * Shows token packages for purchase
 */
export default function TokensPage({ tokens }) {
  const { t } = useTranslation();
  const [selectedPackage, setSelectedPackage] = useState('tokens_250');
  const [isProcessing, setIsProcessing] = useState(false);

  // Track page view
  useEffect(() => {
    const initData = WebApp.initData;
    trackEvent('tokens_page_viewed', {}, initData).catch(err => {
      console.error('Failed to track tokens page view:', err);
    });
  }, []);

  // New Year Sale - 20% off all prices!
  const DISCOUNT_PERCENT = 20;
  const calcDiscount = (price) => Math.round(price * (1 - DISCOUNT_PERCENT / 100));

  // Token packages with original + discounted prices
  const packages = [
    { id: 'tokens_50', amount: 50, originalStars: 35, stars: calcDiscount(35) },
    { id: 'tokens_100', amount: 100, originalStars: 70, stars: calcDiscount(70) },
    { id: 'tokens_250', amount: 250, originalStars: 175, stars: calcDiscount(175) },
    { id: 'tokens_500', amount: 500, originalStars: 350, stars: calcDiscount(350) },
    { id: 'tokens_1000', amount: 1000, originalStars: 700, stars: calcDiscount(700) },
    { id: 'tokens_2500', amount: 2500, originalStars: 1750, stars: calcDiscount(1750) },
    { id: 'tokens_5000', amount: 5000, originalStars: 3500, stars: calcDiscount(3500) },
    { id: 'tokens_10000', amount: 10000, originalStars: 7000, stars: calcDiscount(7000) },
    { id: 'tokens_25000', amount: 25000, originalStars: 17500, stars: calcDiscount(17500) }
  ];

  const handlePurchase = async () => {
    if (isProcessing) return;
    
    setIsProcessing(true);
    
    try {
      const initData = WebApp.initData;
      
      // Create invoice via API
      const result = await createInvoice(selectedPackage, initData);
      
      // Check if this is a simulated payment
      if (result.simulated) {
        // Simulated payment - already processed on backend
        WebApp.showAlert(t('tokens.tokensAdded'));
        window.location.reload();
        return;
      }
      
      // Real payment - open Telegram invoice
      const { invoice_link } = result;
      
      // Open invoice using Telegram WebApp API
      WebApp.openInvoice(invoice_link, (status) => {
        if (status === 'paid') {
          WebApp.showAlert(t('tokens.tokensAdded'));
          window.location.reload();
        } else if (status === 'cancelled') {
          WebApp.showAlert(t('tokens.paymentCancelled'));
        } else if (status === 'failed') {
          WebApp.showAlert(t('tokens.paymentFailed'));
        }
        setIsProcessing(false);
      });
    } catch (error) {
      console.error('Failed to create invoice:', error);
      WebApp.showAlert(t('tokens.invoiceFailed'));
      setIsProcessing(false);
    }
  };

  return (
    <div className="tokens-page">
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
            <span className="sale-banner-discount">{DISCOUNT_PERCENT}% OFF ALL TOKENS</span>
          </div>
          <span className="sale-banner-emoji">🎁</span>
        </div>
      </div>

      <div className="packages-list">
        {packages.map((pkg) => (
          <div
            key={pkg.id}
            className={`token-package-item ${selectedPackage === pkg.id ? 'selected' : ''}`}
            onClick={() => setSelectedPackage(pkg.id)}
          >
            <div className="package-left">
              <div className="package-radio">
                {selectedPackage === pkg.id && <div className="radio-dot"></div>}
              </div>
              <div className="package-amount-display">
                <img src={lightningIcon} alt="energy" className="coin-icon" />
                <span className="amount-text">{pkg.amount.toLocaleString()}</span>
              </div>
            </div>
            <div className="package-right">
              <div className="package-price-sale">
                <span className="original-price-inline">
                  <img src={starIcon} alt="star" className="star-icon" />
                  {pkg.originalStars.toLocaleString()}
                </span>
                <span className="discounted-price-inline">
                  <img src={starIcon} alt="star" className="star-icon" />
                  {pkg.stars.toLocaleString()}
                </span>
              </div>
              <div className="sale-tag-small">-{DISCOUNT_PERCENT}%</div>
            </div>
          </div>
        ))}
      </div>

      <button className="purchase-button-tokens" onClick={handlePurchase} disabled={isProcessing}>
        {isProcessing ? t('tokens.processing') : t('tokens.buyButton')}
      </button>
    </div>
  );
}


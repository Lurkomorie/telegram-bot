import WebApp from '@twa-dev/sdk';
import { useState, useEffect } from 'react';
import { createInvoice, trackEvent } from '../api';
import { useTranslation } from '../i18n/TranslationContext';
import './TokensPage.css';
import lightningIcon from '../assets/lightning.webp';
import starIcon from '../assets/star.webp';

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

  // Token packages from screenshot
  const packages = [
    { id: 'tokens_50', amount: 50, stars: 35 },
    { id: 'tokens_100', amount: 100, stars: 70 },
    { id: 'tokens_250', amount: 250, stars: 175 },
    { id: 'tokens_500', amount: 500, stars: 350 },
    { id: 'tokens_1000', amount: 1000, stars: 700 },
    { id: 'tokens_2500', amount: 2500, stars: 1750 },
    { id: 'tokens_5000', amount: 5000, stars: 3500 },
    { id: 'tokens_10000', amount: 10000, stars: 7000 },
    { id: 'tokens_25000', amount: 25000, stars: 17500 }
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
              <div className="package-price-stars">
                <img src={starIcon} alt="star" className="star-icon" />
                {pkg.stars.toLocaleString()}
              </div>
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


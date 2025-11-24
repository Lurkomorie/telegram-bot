import WebApp from '@twa-dev/sdk';
import { useState, useEffect } from 'react';
import { createInvoice, trackEvent } from '../api';
import './TokensPage.css';
import lightningIcon from '../assets/lightning.png';

/**
 * TokensPage Component
 * Shows token packages for purchase
 */
export default function TokensPage({ tokens }) {
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
    { id: 'tokens_50', amount: 50, rubles: 68, stars: 35 },
    { id: 'tokens_100', amount: 100, rubles: 137, stars: 70 },
    { id: 'tokens_250', amount: 250, rubles: 343, stars: 175 },
    { id: 'tokens_500', amount: 500, rubles: 686, stars: 350 },
    { id: 'tokens_1000', amount: 1000, rubles: 1372, stars: 700 },
    { id: 'tokens_2500', amount: 2500, rubles: 3500, stars: 1750 },
    { id: 'tokens_5000', amount: 5000, rubles: 6860, stars: 3500 },
    { id: 'tokens_10000', amount: 10000, rubles: 13720, stars: 7000 },
    { id: 'tokens_25000', amount: 25000, rubles: 34300, stars: 17500 }
  ];

  const handlePurchase = async () => {
    if (isProcessing) return;
    
    setIsProcessing(true);
    
    try {
      const initData = WebApp.initData;
      
      // Create invoice via API
      const { invoice_link } = await createInvoice(selectedPackage, initData);
      
      // Open invoice using Telegram WebApp API
      WebApp.openInvoice(invoice_link, (status) => {
        if (status === 'paid') {
          WebApp.showAlert('✅ Токены успешно добавлены! Спасибо за покупку!');
          window.location.reload();
        } else if (status === 'cancelled') {
          WebApp.showAlert('Оплата отменена');
        } else if (status === 'failed') {
          WebApp.showAlert('Ошибка оплаты. Попробуйте снова.');
        }
        setIsProcessing(false);
      });
    } catch (error) {
      console.error('Failed to create invoice:', error);
      WebApp.showAlert('Не удалось создать счёт. Попробуйте снова.');
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
              <div className="package-price-rubles">{pkg.rubles.toLocaleString()} ₽</div>
              <div className="package-price-stars">/ {pkg.stars.toLocaleString()} звёзд</div>
            </div>
          </div>
        ))}
      </div>

      <button className="purchase-button-tokens" onClick={handlePurchase} disabled={isProcessing}>
        {isProcessing ? 'Обработка...' : 'Купить энергию'}
      </button>
    </div>
  );
}


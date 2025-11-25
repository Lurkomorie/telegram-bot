import WebApp from '@twa-dev/sdk';
import { useState } from 'react';
import { createInvoice } from '../api';
import './CheckoutPage.css';

/**
 * CheckoutPage Component
 * Shows payment options and confirms purchase
 */
export default function CheckoutPage({ tier, onBack }) {
  const [selectedPeriod, setSelectedPeriod] = useState('month'); // 'month' | '3months' | '6months'
  const [isProcessing, setIsProcessing] = useState(false);

  // Price calculation based on period
  const getPriceInfo = () => {
    const basePrice = tier.stars;
    switch (selectedPeriod) {
      case 'month':
        return { price: basePrice, discount: null };
      case '3months':
        return { price: Math.floor(basePrice * 3 * 0.95), discount: '-5%' };
      case '6months':
        return { price: Math.floor(basePrice * 6 * 0.90), discount: '-10%' };
      default:
        return { price: basePrice, discount: null };
    }
  };

  const priceInfo = getPriceInfo();

  const handlePurchase = async () => {
    if (isProcessing) return;
    
    setIsProcessing(true);
    
    try {
      const initData = WebApp.initData;
      
      // Determine the tier ID based on tier and period
      let tierId = tier.id;
      if (selectedPeriod === '3months') {
        tierId = tierId.replace('_month', '_3months');
      } else if (selectedPeriod === '6months') {
        tierId = tierId.replace('_month', '_6months');
      }
      
      // Create invoice via API
      const { invoice_link } = await createInvoice(tierId, initData);
      
      // Open invoice using Telegram WebApp API
      WebApp.openInvoice(invoice_link, (status) => {
        if (status === 'paid') {
          WebApp.showAlert('✅ Подписка успешно оформлена! Спасибо за покупку!');
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
    <div className="checkout-page">
      <div className="checkout-section">
        <h2 className="section-title">СПОСОБ ОПЛАТЫ</h2>
        <div className="payment-option selected">
          <div className="radio-button selected"></div>
          <span className="option-text">Звёздами</span>
        </div>
      </div>

      <div className="checkout-section">
        <h2 className="section-title">ПЕРИОД</h2>
        <div className="period-options">
          <div
            className={`payment-option ${selectedPeriod === 'month' ? 'selected' : ''}`}
            onClick={() => setSelectedPeriod('month')}
          >
            <div className={`radio-button ${selectedPeriod === 'month' ? 'selected' : ''}`}></div>
            <span className="option-text">Месяц</span>
          </div>
          <div
            className={`payment-option ${selectedPeriod === '3months' ? 'selected' : ''}`}
            onClick={() => setSelectedPeriod('3months')}
          >
            <div className={`radio-button ${selectedPeriod === '3months' ? 'selected' : ''}`}></div>
            <span className="option-text">3 месяца</span>
            <span className="discount-badge">-5%</span>
          </div>
          <div
            className={`payment-option ${selectedPeriod === '6months' ? 'selected' : ''}`}
            onClick={() => setSelectedPeriod('6months')}
          >
            <div className={`radio-button ${selectedPeriod === '6months' ? 'selected' : ''}`}></div>
            <span className="option-text">6 месяцев</span>
            <span className="discount-badge">-10%</span>
          </div>
        </div>
      </div>

      <div className="checkout-footer">
        <div className="total-section">
          <span className="total-label">К оплате</span>
          <span className="total-amount">{priceInfo.price.toLocaleString()} звёзд</span>
        </div>
        <button 
          className="pay-button"
          onClick={handlePurchase}
          disabled={isProcessing}
        >
          {isProcessing ? 'Обработка...' : 'Оплатить'}
        </button>
      </div>
    </div>
  );
}


import WebApp from '@twa-dev/sdk';
import { useEffect, useState } from 'react';
import { createInvoice, trackEvent } from '../api';
import starIcon from '../assets/star.webp';
import { useTranslation } from '../i18n/TranslationContext';
import './PremiumPage.css';

/**
 * PremiumPage Component
 * Unified subscription system - 4 periods with same benefits
 */
export default function PremiumPage() {
  const { t } = useTranslation();
  const [selectedProduct, setSelectedProduct] = useState('subscription_monthly');
  const [isProcessing, setIsProcessing] = useState(false);

  // Track page view
  useEffect(() => {
    const initData = WebApp.initData;
    trackEvent('plans_page_viewed', {}, initData).catch(err => {
      console.error('Failed to track plans page view:', err);
    });
  }, []);

  // Unified subscription plans - all give same benefits
  const subscriptionPlans = [
    { 
      id: 'subscription_daily', 
      period: 'day',
      periodKey: 'subscription.period.day',
      stars: 75, 
      originalStars: null,
      discount: null,
      popular: false 
    },
    { 
      id: 'subscription_weekly', 
      period: 'week',
      periodKey: 'subscription.period.week',
      stars: 295, 
      originalStars: 500,
      discount: 41,
      popular: false 
    },
    { 
      id: 'subscription_monthly', 
      period: 'month',
      periodKey: 'subscription.period.month',
      stars: 495, 
      originalStars: 2500,
      discount: 78,
      popular: true
    },
    { 
      id: 'subscription_yearly', 
      period: 'year',
      periodKey: 'subscription.period.year',
      stars: 2495, 
      originalStars: 30000,
      discount: 92,
      popular: false
    }
  ];

  // Benefits list - same for all subscription periods
  const benefits = [
    { icon: '⚡️', key: 'subscription.benefits.unlimitedEnergy' },
    { icon: '🔞', key: 'subscription.benefits.noBlur' },
    { icon: '🎭', key: 'subscription.benefits.enhancedAI' },
    { icon: '🧠', key: 'subscription.benefits.enhancedMemory' },
    { icon: '♻️', key: 'subscription.benefits.fasterGeneration' },
    { icon: '➕', key: 'subscription.benefits.characterBonus' },
    { icon: '💬', key: 'subscription.benefits.extendedDescription' }
  ];

  const handlePurchase = async () => {
    if (isProcessing) return;
    
    setIsProcessing(true);
    
    try {
      const initData = WebApp.initData;
      const result = await createInvoice(selectedProduct, initData);
      
      if (result.simulated) {
        WebApp.showAlert('✅ Payment successful! Thank you for your purchase!');
        window.location.reload();
        return;
      }
      
      const { invoice_link } = result;
      
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
    <div className="premium-page">
      {/* Subscription Plans */}
      <div className="subscription-section">
        <div className="subscription-cards">
          {subscriptionPlans.map((plan) => (
            <div
              key={plan.id}
              className={`subscription-card ${selectedProduct === plan.id ? 'selected' : ''}`}
              onClick={() => setSelectedProduct(plan.id)}
            >
              {plan.popular && <div className="badge popular">Most Popular</div>}
              {plan.discount && <div className="discount-tag">-{plan.discount}%</div>}
              
              <div className="plan-period">{t(plan.periodKey)}</div>
              
              <div className="plan-price-container">
                {plan.originalStars && (
                  <span className="original-price">
                    <img src={starIcon} alt="star" className="star-icon-inline" />
                    {plan.originalStars.toLocaleString()}
                  </span>
                )}
                <span className="current-price">
                  <img src={starIcon} alt="star" className="star-icon-inline" />
                  {plan.stars.toLocaleString()}
                </span>
              </div>
              
              {selectedProduct === plan.id && (
                <svg className="checkmark" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                  <polyline points="20 6 9 17 4 12"></polyline>
                </svg>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Benefits Section */}
      <div className="benefits-section">
        <div className="benefits-header">
          💸 {t('subscription.benefitsTitle')} 👇🏻
        </div>
        <div className="benefits-list">
          {benefits.map((benefit, index) => (
            <div key={index} className="benefit-item">
              <span className="benefit-icon">{benefit.icon}</span>
              <span className="benefit-text">{t(benefit.key)}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Purchase Button */}
      <button className="purchase-button-sticky" onClick={handlePurchase} disabled={isProcessing}>
        {isProcessing ? t('subscription.processing') : t('subscription.purchaseButton')}
      </button>
    </div>
  );
}

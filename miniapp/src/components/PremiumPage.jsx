import WebApp from '@twa-dev/sdk';
import { useEffect, useState } from 'react';
import { createInvoice, getTributeLink, trackEvent } from '../api';
import { useTranslation } from '../i18n/TranslationContext';
import { formatPrice, formatOriginalPrice } from '../utils/pricing';
import PaymentMethodModal from './PaymentMethodModal';
import './PremiumPage.css';

/**
 * PremiumPage Component
 * Unified subscription system - 4 periods with same benefits
 */
export default function PremiumPage() {
  const { t, language } = useTranslation();
  const [selectedProduct, setSelectedProduct] = useState('subscription_monthly');
  const [isProcessing, setIsProcessing] = useState(false);
  const [showPaymentModal, setShowPaymentModal] = useState(false);

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
      stars: 95,
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

  // Discount multiplier for original price display
  const getOriginalMultiplier = (plan) => {
    if (!plan.originalStars) return null;
    return plan.originalStars / plan.stars;
  };

  const handlePurchase = () => {
    if (isProcessing) return;
    setShowPaymentModal(true);
  };

  const handlePaymentMethod = async (method) => {
    setShowPaymentModal(false);
    setIsProcessing(true);

    try {
      const initData = WebApp.initData;

      if (method === 'card' || method === 'crypto') {
        const result = await getTributeLink(selectedProduct, method, initData, language);
        WebApp.openLink(result.url);
        setIsProcessing(false);
        return;
      }

      // Stars payment flow
      const result = await createInvoice(selectedProduct, initData, 'stars');

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
      console.error('Failed to process payment:', error);
      WebApp.showAlert('Failed to process payment. Please try again.');
      setIsProcessing(false);
    }
  };

  const selectedPlan = subscriptionPlans.find(p => p.id === selectedProduct);

  return (
    <div className="premium-page">
      {/* Subscription Plans */}
      <div className="subscription-section">
        <div className="subscription-cards">
          {subscriptionPlans.map((plan) => {
            const multiplier = getOriginalMultiplier(plan);
            return (
              <div
                key={plan.id}
                className={`subscription-card ${selectedProduct === plan.id ? 'selected' : ''}`}
                onClick={() => setSelectedProduct(plan.id)}
              >
                {plan.popular && <div className="badge popular">Most Popular</div>}
                {plan.discount && <div className="discount-tag">-{plan.discount}%</div>}

                <div className="plan-period">{t(plan.periodKey)}</div>

                <div className="plan-price-container">
                  {multiplier && (
                    <span className="original-price">
                      {formatOriginalPrice(plan.id, language, multiplier)}
                    </span>
                  )}
                  <span className="current-price">
                    {formatPrice(plan.id, language)}
                  </span>
                </div>

                {selectedProduct === plan.id && (
                  <svg className="checkmark" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                    <polyline points="20 6 9 17 4 12"></polyline>
                  </svg>
                )}
              </div>
            );
          })}
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

      {/* Payment Method Modal */}
      <PaymentMethodModal
        isOpen={showPaymentModal}
        onClose={() => setShowPaymentModal(false)}
        productId={selectedProduct}
        starsPrice={selectedPlan?.stars || 0}
        onSelectMethod={handlePaymentMethod}
      />
    </div>
  );
}

import WebApp from '@twa-dev/sdk';
import { useState } from 'react';
import { createInvoice } from '../api';
import { useTranslation } from '../i18n/TranslationContext';
import './PlansPage.css';

/**
 * PlansPage Component
 * Shows upgrade plans and pricing options
 */
export default function PlansPage() {
  const { t } = useTranslation();
  const [selectedPlan, setSelectedPlan] = useState('year');
  const [isProcessing, setIsProcessing] = useState(false);

  const plans = [
    {
      id: '2days',
      duration: t('premium.plans.2days.duration'),
      stars: 250,
      period: t('premium.plans.2days.period'),
    },
    {
      id: 'month',
      duration: t('premium.plans.month.duration'),
      stars: 500,
      period: t('premium.plans.month.period'),
    },
    {
      id: '3months',
      duration: t('premium.plans.3months.duration'),
      stars: 1000,
      period: t('premium.plans.3months.period'),
    },
    {
      id: 'year',
      duration: t('premium.plans.year.duration'),
      stars: 3000,
      period: t('premium.plans.year.period'),
    },
  ];

  const features = [
    { icon: '⚡', text: t('premium.features.energy') },
    { icon: '👯', text: t('premium.features.ai') },
    { icon: '📸', text: t('premium.features.photos') },
  ];

  const handleUpgrade = async () => {
    if (isProcessing) return;
    
    setIsProcessing(true);
    
    try {
      const selected = plans.find(p => p.id === selectedPlan);
      const initData = WebApp.initData;
      
      // Create invoice via API
      const { invoice_link } = await createInvoice(selectedPlan, initData);
      
      // Open invoice using Telegram WebApp API
      WebApp.openInvoice(invoice_link, (status) => {
        if (status === 'paid') {
          WebApp.showAlert(t('premium.alerts.paymentSuccess'));
          // Reload the page to refresh premium status
          window.location.reload();
        } else if (status === 'cancelled') {
          WebApp.showAlert(t('premium.alerts.paymentCancelled'));
        } else if (status === 'failed') {
          WebApp.showAlert(t('premium.alerts.paymentFailed'));
        }
        setIsProcessing(false);
      });
    } catch (error) {
      console.error('Failed to create invoice:', error);
      WebApp.showAlert(t('premium.alerts.createFailed'));
      setIsProcessing(false);
    }
  };

  return (
    <div className="plans-page">
      <div className="plans-section">
        <div className="plans-grid">
          {plans.map((plan, index) => (
            <div
              key={plan.id}
              className={`plan-card ${selectedPlan === plan.id ? 'selected' : ''} ${index >= 2 ? 'full-width' : ''}`}
              onClick={() => setSelectedPlan(plan.id)}
            >
              <div className="plan-content">
                <div className="plan-info">
                  <div className="plan-duration">{plan.duration}</div>
                  <div className="plan-price">
                    {plan.stars} <span className="plan-period">⭐ {plan.period}</span>
                  </div>
                </div>
                <div className="plan-selector">
                  {selectedPlan === plan.id && (
                    <svg className="checkmark" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                      <polyline points="20 6 9 17 4 12"></polyline>
                    </svg>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="features-list">
          {features.map((feature, index) => (
            <div key={index} className="feature-item">
              <span className="feature-icon">{feature.icon}</span>
              <span className="feature-text">{feature.text}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="footer-note">
        <p>@sexsplicit_companion_bot</p>
      </div>

      <button className="upgrade-button-sticky" onClick={handleUpgrade} disabled={isProcessing}>
        {isProcessing ? t('premium.processing') : t('premium.upgradeButton')}
      </button>
    </div>
  );
}




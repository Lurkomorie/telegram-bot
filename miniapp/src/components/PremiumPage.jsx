import WebApp from '@twa-dev/sdk';
import { useState } from 'react';
import { createInvoice } from '../api';
import './PremiumPage.css';

/**
 * PremiumPage Component
 * Shows upgrade plans and pricing options
 */
export default function PremiumPage({ energy, onBack }) {
  const [selectedPlan, setSelectedPlan] = useState('year');
  const [isProcessing, setIsProcessing] = useState(false);

  const plans = [
    {
      id: '2days',
      duration: '2 Days',
      stars: 250,
      period: '/ 2 days',
    },
    {
      id: 'month',
      duration: '1 Month',
      stars: 500,
      period: '/ month',
    },
    {
      id: '3months',
      duration: '3 Months',
      stars: 1000,
      period: '/ 3 months',
    },
    {
      id: 'year',
      duration: '1 Year',
      stars: 3000,
      period: '/ year',
    },
  ];

  const features = [
    { icon: '⚡', text: 'Infinite energy' },
    { icon: '👯', text: 'Our most advanced AI engines' },
    { icon: '📸', text: 'Unlimited photo generation' },
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
          WebApp.showAlert('Payment successful! Your premium subscription is now active.');
          // Reload the page to refresh premium status
          window.location.reload();
        } else if (status === 'cancelled') {
          WebApp.showAlert('Payment cancelled.');
        } else if (status === 'failed') {
          WebApp.showAlert('Payment failed. Please try again.');
        }
        setIsProcessing(false);
      });
    } catch (error) {
      console.error('Failed to create invoice:', error);
      WebApp.showAlert('Failed to create payment. Please try again.');
      setIsProcessing(false);
    }
  };

  return (
    <div className="premium-page">
      <div className="plans-section">
        <h3 className="plans-title">Plan</h3>
        
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
        {isProcessing ? 'Processing...' : 'Upgrade 💎'}
      </button>
    </div>
  );
}


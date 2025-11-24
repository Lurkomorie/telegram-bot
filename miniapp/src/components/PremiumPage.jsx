import WebApp from '@twa-dev/sdk';
import { useEffect } from 'react';
import { trackEvent } from '../api';
import './PremiumPage.css';

/**
 * PremiumPage Component
 * Shows premium tier subscriptions
 */
export default function PremiumPage({ onNavigateToCheckout }) {
  // Track page view
  useEffect(() => {
    const initData = WebApp.initData;
    trackEvent('plans_page_viewed', {}, initData).catch(err => {
      console.error('Failed to track plans page view:', err);
    });
  }, []);

  // Premium tiers based on screenshots
  const tiers = [
    {
      id: 'plus_month',
      name: 'Plus',
      icon: '❄️',
      daily: 25,
      stars: 325,
      features: [
        'Бесплатные 25 токенов каждый день',
        'Улучшенная модель ИИ',
        'Дешёвая генерация фотографий',
        'Скачивание фотографий',
        'Свои обои в чате',
        'Генерация голосовых сообщений',
        'Создание фотографий по описанию',
        'Нет никаких ограничений',
        'Дешевле создание персонажа в мастерской',
        'Увеличен лимит до 4,000 символов в описании персонажа',
        'Отправка голосовых сообщений до 30 секунд',
        'Создание групповых чатов'
      ]
    },
    {
      id: 'pro_month',
      name: 'Pro',
      icon: '🔥',
      daily: 75,
      stars: 625,
      features: [
        'Всё что в Plus, а так же',
        'Бесплатные 75 токенов каждый день',
        'Отправка голосовых сообщений до 90 секунд'
      ]
    },
    {
      id: 'legendary_month',
      name: 'Legendary',
      icon: '🏆',
      daily: 100,
      stars: 775,
      features: [
        'Всё что в Premium, а так же',
        'Бесплатные 100 токенов каждый день',
        'Отправка голосовых сообщений до 120 секунд',
        'Генерация анимаций из фотографии',
        'Генерация видео сообщений'
      ]
    }
  ];

  const handleTierClick = (tier) => {
    onNavigateToCheckout(tier);
  };

  return (
    <div className="premium-page">
      {tiers.map((tier) => (
        <div key={tier.id} className="premium-card">
          <div className="premium-card-header">
            <div className="premium-card-title">
              <span className="tier-icon-large">{tier.icon}</span>
              <span className="tier-name-large">{tier.name}</span>
            </div>
            <div className="premium-card-price">
              <div className="price-amount">{tier.stars} ₽</div>
              <div className="price-period">/ месяц</div>
            </div>
          </div>

          <div className="premium-card-body">
            <h3 className="benefits-title">Преимущества</h3>
            <div className="benefits-list">
              {tier.features.map((feature, index) => (
                <div key={index} className="benefit-item">
                  <svg className="check-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points="20 6 9 17 4 12"></polyline>
                  </svg>
                  <span className="benefit-text">{feature}</span>
                </div>
              ))}
            </div>
          </div>

          <button 
            className="premium-card-button" 
            onClick={() => handleTierClick(tier)}
          >
            Получить {tier.name}
          </button>
        </div>
      ))}
    </div>
  );
}

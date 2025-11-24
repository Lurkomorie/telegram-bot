import WebApp from '@twa-dev/sdk';
import { useState, useEffect } from 'react';
import { fetchReferralStats } from '../api';
import './ReferralsPage.css';

/**
 * ReferralsPage Component
 * Shows referral system - invite friends and earn tokens
 */
export default function ReferralsPage({ userId }) {
  const [referralsCount, setReferralsCount] = useState(0);
  const [isSharing, setIsSharing] = useState(false);
  const [botUsername, setBotUsername] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadReferralStats();
  }, []);
  
  async function loadReferralStats() {
    try {
      setIsLoading(true);
      const initData = WebApp.initData;
      const stats = await fetchReferralStats(initData);
      setReferralsCount(stats.referrals_count || 0);
      setBotUsername(stats.bot_username || '');
    } catch (error) {
      console.error('Failed to load referral stats:', error);
    } finally {
      setIsLoading(false);
    }
  }

  const handleInviteFriend = async () => {
    if (isSharing || !botUsername) return;
    
    setIsSharing(true);
    
    // Create referral link
    const referralLink = `https://t.me/${botUsername}?start=ref_${userId}`;
    
    try {
      // Copy link to clipboard
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(referralLink);
        WebApp.showPopup({
          title: 'Ссылка скопирована!',
          message: 'Реферальная ссылка скопирована в буфер обмена',
          buttons: [{ type: 'ok' }]
        });
      } else {
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = referralLink;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        
        WebApp.showPopup({
          title: 'Ссылка скопирована!',
          message: 'Реферальная ссылка скопирована в буфер обмена',
          buttons: [{ type: 'ok' }]
        });
      }
    } catch (err) {
      console.error('Failed to copy link:', err);
      WebApp.showAlert('Не удалось скопировать ссылку');
    } finally {
      setTimeout(() => setIsSharing(false), 500);
    }
  };

  return (
    <div className="referrals-page">
      <div className="referrals-hero">
        <div className="hero-icon">👥</div>
        <h1 className="hero-title">Превращай друзей в токены!</h1>
      </div>

      <div className="earnings-card">
        <div className="earnings-label">Зарабатывай</div>
        <div className="earnings-amount">50 токенов</div>
        <div className="earnings-description">с каждого друга</div>
      </div>

      <div className="referrals-stats">
        <h3 className="stats-title">Рефералы</h3>
        <div className="stats-item">
          <div className="stats-icon">👫</div>
          <span className="stats-label">Друзей приглашено</span>
          <span className="stats-count">{referralsCount}</span>
        </div>
        <div className="stats-note">
          Друг должен перейти по вашей ссылке и зайти в приложение чтобы получить токены
        </div>
      </div>

      <button className="invite-button" onClick={handleInviteFriend} disabled={isSharing}>
        {isSharing ? 'Открытие...' : 'Пригласить друга'}
      </button>
    </div>
  );
}


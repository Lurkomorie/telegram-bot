import WebApp from '@twa-dev/sdk';
import { useState, useEffect } from 'react';
import { fetchReferralStats } from '../api';
import { useTranslation } from '../i18n/TranslationContext';
import './ReferralsPage.css';

/**
 * ReferralsPage Component
 * Shows referral system - invite friends and earn tokens
 */
export default function ReferralsPage({ userId }) {
  const { t } = useTranslation();
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
          title: t('referrals.linkCopiedTitle'),
          message: t('referrals.linkCopiedMessage'),
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
          title: t('referrals.linkCopiedTitle'),
          message: t('referrals.linkCopiedMessage'),
          buttons: [{ type: 'ok' }]
        });
      }
    } catch (err) {
      console.error('Failed to copy link:', err);
      WebApp.showAlert(t('referrals.copyFailed'));
    } finally {
      setTimeout(() => setIsSharing(false), 500);
    }
  };

  return (
    <div className="referrals-page">
      <div className="referrals-hero">
        <div className="hero-icon">👥</div>
        <h1 className="hero-title">{t('referrals.title')}</h1>
      </div>

      <div className="earnings-card">
        <div className="earnings-label">{t('referrals.earn')}</div>
        <div className="earnings-amount">{t('referrals.tokensAmount')}</div>
        <div className="earnings-description">{t('referrals.perFriend')}</div>
      </div>

      <div className="referrals-stats">
        <h3 className="stats-title">{t('referrals.statsTitle')}</h3>
        <div className="stats-item">
          <div className="stats-icon">👫</div>
          <span className="stats-label">{t('referrals.friendsInvited')}</span>
          <span className="stats-count">{referralsCount}</span>
        </div>
        <div className="stats-note">
          {t('referrals.note')}
        </div>
      </div>

      <button className="invite-button" onClick={handleInviteFriend} disabled={isSharing}>
        {isSharing ? t('referrals.opening') : t('referrals.inviteButton')}
      </button>
    </div>
  );
}


import { useTranslation } from "../i18n/TranslationContext";
import "./PaymentMethodModal.css";

function CardIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="1" y="4" width="22" height="16" rx="3" />
      <line x1="1" y1="10" x2="23" y2="10" />
    </svg>
  );
}

function CryptoIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <path d="M9.5 8h4a2 2 0 0 1 0 4h-4v4h4a2 2 0 0 0 0-4" />
      <line x1="12" y1="6" x2="12" y2="8" />
      <line x1="12" y1="16" x2="12" y2="18" />
    </svg>
  );
}

function StarsIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
    </svg>
  );
}

export default function PaymentMethodModal({
  isOpen,
  onClose,
  onSelectMethod,
}) {
  const { t } = useTranslation();

  if (!isOpen) return null;

  return (
    <div className="payment-method-overlay" onClick={onClose}>
      <div className="payment-method-buttons" onClick={(e) => e.stopPropagation()}>
        <button className="payment-method-btn card-btn" onClick={() => onSelectMethod("card")}>
          <span className="btn-icon"><CardIcon /></span>
          {t("paymentModal.card")}
        </button>
        <button className="payment-method-btn crypto-btn" onClick={() => onSelectMethod("crypto")}>
          <span className="btn-icon"><CryptoIcon /></span>
          {t("paymentModal.crypto")}
        </button>
        <button className="payment-method-btn stars-btn" onClick={() => onSelectMethod("stars")}>
          <span className="btn-icon"><StarsIcon /></span>
          {t("paymentModal.stars")}
        </button>
        <button className="payment-close-btn" onClick={onClose}>
          <span className="close-x">✕</span>
          <span>{t("paymentModal.close")}</span>
        </button>
      </div>
    </div>
  );
}

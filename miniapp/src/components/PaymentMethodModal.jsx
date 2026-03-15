import { useTranslation } from "../i18n/TranslationContext";
import { formatPrice, getStarsWithMarkup } from "../utils/pricing";
import "./PaymentMethodModal.css";

/**
 * PaymentMethodModal - Payment method selection modal
 * Shows Card, Crypto, and Stars options with appropriate pricing
 */
export default function PaymentMethodModal({
  isOpen,
  onClose,
  productId,
  starsPrice,
  onSelectMethod,
}) {
  const { t, language } = useTranslation();

  if (!isOpen) return null;

  const cardCryptoPrice = formatPrice(productId, language);
  const markupStars = getStarsWithMarkup(starsPrice);

  return (
    <div className="payment-modal-overlay" onClick={onClose}>
      <div
        className="payment-modal-content"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="payment-modal-buttons">
          <button
            className="payment-method-btn card-btn"
            onClick={() => onSelectMethod("card")}
          >
            <span className="payment-method-icon">💳</span>
            <span className="payment-method-label">
              {t("paymentModal.card")}
            </span>
            <span className="payment-method-price">{cardCryptoPrice}</span>
          </button>

          <button
            className="payment-method-btn crypto-btn"
            onClick={() => onSelectMethod("crypto")}
          >
            <span className="payment-method-icon">🪙</span>
            <span className="payment-method-label">
              {t("paymentModal.crypto")}
            </span>
            <span className="payment-method-price">{cardCryptoPrice}</span>
          </button>

          <button
            className="payment-method-btn stars-btn"
            onClick={() => onSelectMethod("stars")}
          >
            <span className="payment-method-icon">⭐</span>
            <span className="payment-method-label">
              {t("paymentModal.stars")}
            </span>
            <span className="payment-method-price-group">
              <span className="payment-method-price">
                {markupStars.toLocaleString()} ⭐
              </span>
              <span className="payment-method-markup">
                {t("paymentModal.starsNote")}
              </span>
            </span>
          </button>
        </div>

        <button className="payment-modal-close" onClick={onClose}>
          {t("paymentModal.close")}
        </button>
      </div>
    </div>
  );
}

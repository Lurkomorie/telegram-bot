import WebApp from "@twa-dev/sdk";
import { useEffect, useState } from "react";
import { createInvoice, getTributeLink, trackEvent } from "../api";
import lightningIcon from "../assets/lightning.webp";
import { useTranslation } from "../i18n/TranslationContext";
import { formatPrice } from "../utils/pricing";
import PaymentMethodModal from "./PaymentMethodModal";
import "./TokensPage.css";

/**
 * TokensPage Component
 * Shows token packages for purchase
 */
export default function TokensPage({ tokens }) {
  const { t, language } = useTranslation();
  const [selectedPackage, setSelectedPackage] = useState("tokens_250");
  const [isProcessing, setIsProcessing] = useState(false);
  const [showPaymentModal, setShowPaymentModal] = useState(false);

  // Track page view
  useEffect(() => {
    const initData = WebApp.initData;
    trackEvent("tokens_page_viewed", {}, initData).catch((err) => {
      console.error("Failed to track tokens page view:", err);
    });
  }, []);

  // New Year Sale - 20% off all prices!
  const DISCOUNT_PERCENT = 20;

  // Token packages with bulk discounts (cheaper per token for larger packages)
  const packages = [
    { id: "tokens_50", amount: 50, stars: 28 },
    { id: "tokens_100", amount: 100, stars: 52 },
    { id: "tokens_250", amount: 250, stars: 120 },
    { id: "tokens_500", amount: 500, stars: 240 },
    { id: "tokens_1000", amount: 1000, stars: 480 },
    { id: "tokens_2500", amount: 2500, stars: 1120 },
    { id: "tokens_5000", amount: 5000, stars: 2160 },
    { id: "tokens_10000", amount: 10000, stars: 4000 },
    { id: "tokens_25000", amount: 25000, stars: 9600 },
  ];

  const handlePurchase = () => {
    if (isProcessing) return;
    setShowPaymentModal(true);
  };

  const handlePaymentMethod = async (method) => {
    setShowPaymentModal(false);
    setIsProcessing(true);

    try {
      const initData = WebApp.initData;

      if (method === "card" || method === "crypto") {
        const result = await getTributeLink(selectedPackage, method, initData, language);
        WebApp.openTelegramLink(result.url);
        setIsProcessing(false);
        return;
      }

      // Stars payment flow
      const result = await createInvoice(selectedPackage, initData, "stars");

      if (result.simulated) {
        WebApp.showAlert(t("tokens.tokensAdded"));
        window.location.reload();
        return;
      }

      const { invoice_link } = result;

      WebApp.openInvoice(invoice_link, (status) => {
        if (status === "paid") {
          WebApp.showAlert(t("tokens.tokensAdded"));
          window.location.reload();
        } else if (status === "cancelled") {
          WebApp.showAlert(t("tokens.paymentCancelled"));
        } else if (status === "failed") {
          WebApp.showAlert(t("tokens.paymentFailed"));
        }
        setIsProcessing(false);
      });
    } catch (error) {
      console.error("Failed to process payment:", error);
      WebApp.showAlert(t("tokens.invoiceFailed"));
      setIsProcessing(false);
    }
  };

  const selectedPkg = packages.find((p) => p.id === selectedPackage);

  return (
    <div className="tokens-page">
      <div className="packages-list">
        {packages.map((pkg) => (
          <div
            key={pkg.id}
            className={`token-package-item ${selectedPackage === pkg.id ? "selected" : ""}`}
            onClick={() => setSelectedPackage(pkg.id)}
          >
            <div className="package-left">
              <div className="package-radio">
                {selectedPackage === pkg.id && (
                  <div className="radio-dot"></div>
                )}
              </div>
              <div className="package-amount-display">
                <img src={lightningIcon} alt="energy" className="coin-icon" />
                <span className="amount-text">
                  {pkg.amount.toLocaleString()}
                </span>
              </div>
            </div>
            <div className="package-right">
              <div className="package-price-sale">
                <span className="discounted-price-inline">
                  {formatPrice(pkg.id, language)}
                </span>
              </div>
              <div className="sale-tag-small">-{DISCOUNT_PERCENT}%</div>
            </div>
          </div>
        ))}
      </div>

      <button
        className="purchase-button-tokens"
        onClick={handlePurchase}
        disabled={isProcessing}
      >
        {isProcessing ? t("tokens.processing") : t("tokens.buyButton")}
      </button>

      {/* Payment Method Modal */}
      <PaymentMethodModal
        isOpen={showPaymentModal}
        onClose={() => setShowPaymentModal(false)}
        onSelectMethod={handlePaymentMethod}
      />
    </div>
  );
}

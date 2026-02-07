import WebApp from "@twa-dev/sdk";
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "../i18n/TranslationContext";
import MoodIndicator from "./MoodIndicator";
import "./ShopPage.css";

import analBeadsImg from "../assets/anal-beads.avif";
import giftImg from "../assets/gift.webp";
import lightningIcon from "../assets/lightning.webp";
import lipstickImg from "../assets/lipstick.png";
import roseImg from "../assets/rose.png";
import vibratorImg from "../assets/vibrator.png";
import wineImg from "../assets/wine.png";

const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  (import.meta.env.DEV ? "http://localhost:8000" : "");

const SHOP_ITEMS = [
  {
    key: "wine",
    name: "Wine Bottle",
    nameRu: "Бутылка вина",
    price: 60,
    moodBoost: 15,
    image: wineImg,
  },
  {
    key: "lipstick",
    name: "Lipstick",
    nameRu: "Помада",
    price: 40,
    moodBoost: 10,
    image: lipstickImg,
  },
  {
    key: "rose",
    name: "Rose Bouquet",
    nameRu: "Букет роз",
    price: 50,
    moodBoost: 12,
    image: roseImg,
  },
  {
    key: "mystery",
    name: "Mystery Gift",
    nameRu: "Загадочный подарок",
    price: 100,
    moodBoost: 20,
    image: giftImg,
  },
  {
    key: "vibrator",
    name: "Vibrator",
    nameRu: "Вибратор",
    price: 160,
    moodBoost: 25,
    image: vibratorImg,
  },
  {
    key: "anal_beads",
    name: "Anal Beads",
    nameRu: "Анальные шарики",
    price: 200,
    moodBoost: 30,
    image: analBeadsImg,
  },
];

export default function ShopPage({
  chatId,
  tokens,
  onPurchase,
  onNavigateToTokens,
}) {
  const { t, language } = useTranslation();
  const [isPurchasing, setIsPurchasing] = useState(null);
  const [purchaseSuccess, setPurchaseSuccess] = useState(null);
  const [mood, setMood] = useState(50);

  // Fetch mood when chatId is available
  const fetchMood = useCallback(async () => {
    if (!chatId) return;
    try {
      const initData = WebApp.initData;
      const response = await fetch(
        `${API_BASE}/api/miniapp/chat/${chatId}/mood`,
        {
          headers: {
            "X-Telegram-Init-Data": initData || "",
          },
        },
      );
      if (response.ok) {
        const data = await response.json();
        setMood(data.mood || 50);
      }
    } catch (error) {
      console.error("Failed to fetch mood:", error);
    }
  }, [chatId]);

  useEffect(() => {
    fetchMood();
  }, [fetchMood]);

  const handlePurchase = async (item) => {
    if (isPurchasing || !chatId) return;

    // Check if user has enough tokens
    if (tokens < item.price) {
      WebApp.showPopup(
        {
          title: t("shop.insufficientTokens"),
          message: t("shop.needMoreTokens", { need: item.price, have: tokens }),
          buttons: [
            { id: "buy", type: "default", text: t("shop.buyTokens") },
            { id: "cancel", type: "cancel", text: t("shop.cancel") },
          ],
        },
        (buttonId) => {
          if (buttonId === "buy" && onNavigateToTokens) {
            onNavigateToTokens();
          }
        },
      );
      return;
    }

    setIsPurchasing(item.key);

    try {
      const initData = WebApp.initData;
      const response = await fetch(`${API_BASE}/api/miniapp/shop/purchase`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Telegram-Init-Data": initData || "",
        },
        body: JSON.stringify({
          chat_id: chatId,
          item_key: item.key,
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Purchase failed");
      }

      const result = await response.json();

      // Show success animation
      setPurchaseSuccess(item.key);
      setTimeout(() => setPurchaseSuccess(null), 2000);

      // Notify parent of purchase
      if (onPurchase) {
        onPurchase(result);
      }

      WebApp.showAlert(
        t("shop.purchaseSuccess", {
          item: language === "ru" ? item.nameRu : item.name,
        }),
      );
    } catch (error) {
      console.error("Purchase failed:", error);
      WebApp.showAlert(t("shop.purchaseFailed"));
    } finally {
      setIsPurchasing(null);
    }
  };

  const getItemName = (item) => {
    return language === "ru" ? item.nameRu : item.name;
  };

  return (
    <div className="shop-page">
      <div className="shop-header">
        <div className="shop-header-icon">🎁</div>
        <h1 className="shop-title">{t("shop.title")}</h1>
        <p className="shop-subtitle">{t("shop.subtitle")}</p>
        {chatId && (
          <div className="shop-mood-section">
            <span className="mood-label">{t("mood.herMood")}</span>
            <MoodIndicator mood={mood} compact />
          </div>
        )}
      </div>

      <div className="shop-grid">
        {SHOP_ITEMS.map((item) => (
          <div
            key={item.key}
            className={`shop-item ${isPurchasing === item.key ? "purchasing" : ""} ${purchaseSuccess === item.key ? "success" : ""}`}
            onClick={() => handlePurchase(item)}
          >
            <div className="shop-item-image-container">
              <img
                src={item.image}
                alt={item.name}
                className="shop-item-image"
              />
              {purchaseSuccess === item.key && (
                <div className="purchase-success-overlay">
                  <span className="success-checkmark">✓</span>
                </div>
              )}
            </div>
            <div className="shop-item-info">
              <span className="shop-item-name">{getItemName(item)}</span>
              <div className="shop-item-mood">
                <span className="mood-icon">💖</span>
                <span className="mood-value">+{item.moodBoost}</span>
              </div>
            </div>
            <div className="shop-item-price">
              <img src={lightningIcon} alt="tokens" className="price-icon" />
              <span className="price-value">{item.price}</span>
            </div>
            {isPurchasing === item.key && (
              <div className="purchasing-overlay">
                <div className="purchasing-spinner"></div>
              </div>
            )}
          </div>
        ))}
      </div>

      {!chatId && (
        <div className="shop-no-chat-warning">
          <p>{t("shop.selectChatFirst")}</p>
        </div>
      )}
    </div>
  );
}

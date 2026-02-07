import WebApp from "@twa-dev/sdk";
import { useCallback, useEffect, useState } from "react";
import { fetchUserActiveChat } from "../api";
import { useTranslation } from "../i18n/TranslationContext";
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
    key: "wine",
    name: "Wine Bottle",
    nameRu: "Бутылка вина",
    price: 60,
    moodBoost: 15,
    image: wineImg,
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
  chatId: initialChatId,
  tokens,
  onPurchase,
  onNavigateToTokens,
}) {
  const { t, language } = useTranslation();
  const [isPurchasing, setIsPurchasing] = useState(null);
  const [purchaseSuccess, setPurchaseSuccess] = useState(null);
  const [mood, setMood] = useState(50);
  const [chatId, setChatId] = useState(initialChatId);

  // Self-fetch active chat if not provided
  useEffect(() => {
    if (chatId) return;
    const loadChat = async () => {
      try {
        const initData = WebApp.initData;
        const data = await fetchUserActiveChat(initData);
        if (data.chatId) {
          setChatId(data.chatId);
        }
      } catch (err) {
        console.error("Failed to fetch active chat for shop:", err);
      }
    };
    loadChat();
  }, [chatId]);

  // Sync with parent if initialChatId changes
  useEffect(() => {
    if (initialChatId) setChatId(initialChatId);
  }, [initialChatId]);

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
    if (isPurchasing) return;

    if (!chatId) {
      WebApp.showAlert(t("shop.selectChatFirst"));
      return;
    }

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

      // Re-fetch mood after purchase
      fetchMood();

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

  const getMoodEmoji = () => {
    if (mood >= 80) return "😍";
    if (mood >= 60) return "😊";
    if (mood >= 40) return "😐";
    if (mood >= 20) return "😒";
    return "🥶";
  };

  const getMoodLabel = () => {
    if (mood >= 80) return t("mood.veryHappy");
    if (mood >= 60) return t("mood.happy");
    if (mood >= 40) return t("mood.neutral");
    if (mood >= 20) return t("mood.cold");
    return t("mood.veryCold");
  };

  const getMoodHint = () => {
    if (mood >= 80) return t("shop.moodHintHigh");
    if (mood >= 50) return t("shop.moodHintMid");
    return t("shop.moodHintLow");
  };

  return (
    <div className="shop-page">
      {/* Mood bar */}
      {chatId && (
        <div className="shop-mood-card">
          <div className="mood-bar-header">
            <span className="mood-bar-label">
              {getMoodEmoji()} {getMoodLabel()}
            </span>
            <span className="mood-bar-percent">{mood}%</span>
          </div>
          <div className="mood-bar-track">
            <div className="mood-bar-fill" style={{ width: `${mood}%` }} />
          </div>
          <span className="mood-bar-hint">{getMoodHint()}</span>
        </div>
      )}

      <p className="shop-subtitle">{t("shop.subtitle")}</p>

      {/* Items list */}
      <div className="shop-items-list">
        {SHOP_ITEMS.map((item) => (
          <div
            key={item.key}
            className={`shop-item ${isPurchasing === item.key ? "purchasing" : ""} ${purchaseSuccess === item.key ? "success" : ""}`}
            onClick={() => handlePurchase(item)}
          >
            <div className="shop-item-left">
              <div className="shop-item-image-wrap">
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
                  <span className="mood-heart">❤️</span>
                  <span className="mood-boost-value">+{item.moodBoost}</span>
                </div>
              </div>
            </div>
            <button
              className={`shop-buy-button ${isPurchasing === item.key ? "buying" : ""}`}
              disabled={isPurchasing === item.key}
            >
              {isPurchasing === item.key ? (
                <div className="buy-spinner"></div>
              ) : (
                <>
                  <img src={lightningIcon} alt="tokens" className="buy-icon" />
                  <span className="buy-price">{item.price}</span>
                </>
              )}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

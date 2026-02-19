import WebApp from "@twa-dev/sdk";
import * as LucideIcons from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import lightningIcon from "../assets/lightning.webp";
import { fetchShopItems, fetchUserActiveChat } from "../api";
import { useTranslation } from "../i18n/TranslationContext";
import "./ShopPage.css";

const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  (import.meta.env.DEV ? "http://localhost:8000" : "");

const SHOP_IMAGE_FALLBACKS = {
  flower_bouquet: "assets/shop/flower-bouquet.jpg",
  wine_bottle: "assets/shop/wine-bottle.jpg",
  dildo: "assets/shop/dildo-pink.png",
  cute_pajamas: "assets/shop/cute-pajamas.jpg",
  engagement_ring: "assets/shop/engagement-ring.jpg",
  bondage_rope: "assets/shop/bondage-rope.jpg",
  lace_lingerie: "assets/shop/pink-panties.png",
  fox_ears_headband: "assets/shop/fox-ears-headband.jpg",
  control_orb: "assets/shop/control-orb.jpg",
};

const normalizeImagePath = (rawPath) => {
  if (!rawPath) return "";

  if (
    rawPath.startsWith("http://") ||
    rawPath.startsWith("https://") ||
    rawPath.startsWith("data:")
  ) {
    return rawPath;
  }

  const baseUrl = import.meta.env.BASE_URL || "/";
  const normalizedBase = baseUrl.endsWith("/") ? baseUrl : `${baseUrl}/`;
  const normalizedPath = rawPath.startsWith("/") ? rawPath.slice(1) : rawPath;
  return `${normalizedBase}${normalizedPath}`;
};

export default function ShopPage({
  chatId: initialChatId,
  tokens,
  onPurchase,
  onNavigateToTokens,
}) {
  const { t, language } = useTranslation();
  const [isPurchasing, setIsPurchasing] = useState(null);
  const [mood, setMood] = useState(50);
  const [chatId, setChatId] = useState(initialChatId);
  const [personaName, setPersonaName] = useState("");
  const [personaAvatarUrl, setPersonaAvatarUrl] = useState("");
  const [avatarLoading, setAvatarLoading] = useState(true);
  const [shopItems, setShopItems] = useState([]);
  const [isLoadingItems, setIsLoadingItems] = useState(true);
  const [imageAttemptStage, setImageAttemptStage] = useState({});

  // Fetch active chat meta for shop context panel
  useEffect(() => {
    const loadChat = async () => {
      try {
        const initData = WebApp.initData;
        const data = await fetchUserActiveChat(initData);
        if (!chatId && data.chatId) {
          setChatId(data.chatId);
        }
        setPersonaName(data.personaName || "");
        setPersonaAvatarUrl(data.personaAvatarUrl || "");
      } catch (err) {
        console.error("Failed to fetch active chat for shop:", err);
      } finally {
        setAvatarLoading(false);
      }
    };
    loadChat();
  }, [chatId]);

  // Sync with parent if initialChatId changes
  useEffect(() => {
    if (initialChatId) setChatId(initialChatId);
  }, [initialChatId]);

  // Fetch shop items from backend catalog
  useEffect(() => {
    const loadShopItems = async () => {
      setIsLoadingItems(true);
      try {
        const initData = WebApp.initData;
        const items = await fetchShopItems(initData);
        if (Array.isArray(items)) {
          setShopItems(items);
        } else {
          setShopItems([]);
        }
      } catch (error) {
        console.error("Failed to fetch shop items:", error);
        setShopItems([]);
      } finally {
        setIsLoadingItems(false);
      }
    };

    loadShopItems();
  }, []);

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

  useEffect(() => {
    setImageAttemptStage({});
  }, [shopItems]);

  const handlePurchase = async (item) => {
    if (isPurchasing) return;

    if (!chatId) {
      WebApp.showAlert(t("shop.selectChatFirst"));
      return;
    }

    // Check if user has enough tokens
    if ((tokens || 0) < item.price) {
      WebApp.showPopup(
        {
          title: t("shop.insufficientTokens"),
          message: t("shop.needMoreTokens", { need: item.price, have: tokens || 0 }),
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

      if (onPurchase) {
        onPurchase(result);
      }

      // Close miniapp — backend will send the gift reaction + image in chat
      WebApp.close();
    } catch (error) {
      console.error("Purchase failed:", error);
      WebApp.showAlert(t("shop.purchaseFailed"));
    } finally {
      setIsPurchasing(null);
    }
  };

  const getItemName = (item) => {
    if (language === "ru") {
      return item.name_ru || item.name_en || item.name || item.key;
    }
    return item.name_en || item.name || item.name_ru || item.key;
  };

  const getItemSubtitle = (item) => {
    if (language === "ru") {
      return item.subtitle_ru || item.subtitle_en || "";
    }
    return item.subtitle_en || item.subtitle_ru || "";
  };

  const getItemIconComponent = (item) => {
    const name = item.icon_lucide;
    if (!name) return null;
    const Icon = LucideIcons[name];
    return typeof Icon === "function" ? Icon : null;
  };

  const markImageAsFailed = (key) => {
    setImageAttemptStage((prev) => ({ ...prev, [key]: (prev[key] || 0) + 1 }));
  };

  const getItemImagePath = (item) => {
    const backendPath = normalizeImagePath(item.image_path || "");
    const fallbackPath = normalizeImagePath(SHOP_IMAGE_FALLBACKS[item.key] || "");
    const stage = imageAttemptStage[item.key] || 0;

    if (stage === 0) {
      return backendPath || fallbackPath || "";
    }

    if (stage === 1 && backendPath && fallbackPath && backendPath !== fallbackPath) {
      return fallbackPath;
    }

    return "";
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
      {chatId && (
        <div className="shop-mood-card">
          <div className="shop-character-row">
            <div className={`shop-character-avatar ${avatarLoading ? "skeleton-wave" : ""}`}>
              {personaAvatarUrl ? (
                <img
                  src={personaAvatarUrl}
                  alt={personaName || "Character"}
                  className="shop-character-avatar-image"
                  onLoad={() => setAvatarLoading(false)}
                  onError={() => setAvatarLoading(false)}
                />
              ) : (
                <span className="shop-character-avatar-fallback">
                  {personaName ? personaName.charAt(0).toUpperCase() : "❤"}
                </span>
              )}
            </div>
            <div className="shop-character-meta">
              <span className="shop-character-name">{personaName || t("shop.bannerTitle")}</span>
              <span className="shop-character-mood">{getMoodEmoji()} {getMoodLabel()}</span>
            </div>
            <span className="mood-bar-percent">{mood}%</span>
          </div>

          <div className="mood-bar-track">
            <div className="mood-bar-fill" style={{ width: `${mood}%` }} />
          </div>
          <span className="mood-bar-hint">{getMoodHint()}</span>
        </div>
      )}

      <p className="shop-subtitle">{t("shop.subtitle")}</p>

      {isLoadingItems ? (
        <div className="shop-empty-state">{t("shop.loading")}</div>
      ) : shopItems.length === 0 ? (
        <div className="shop-empty-state">{t("shop.empty")}</div>
      ) : (
        <div className="shop-items-grid">
          {shopItems.map((item) => {
            const IconComponent = getItemIconComponent(item);
            const imagePath = getItemImagePath(item);
            const hasImage = !!imagePath;
            const subtitle = getItemSubtitle(item);

            return (
              <div
                key={item.key}
                className={`shop-item-card ${isPurchasing === item.key ? "purchasing" : ""}`}
                onClick={() => handlePurchase(item)}
              >
                <div className="shop-item-content">
                  <div className="shop-item-header">
                    <h3 className="shop-item-name">{getItemName(item)}</h3>
                    {subtitle ? <p className="shop-item-subtitle">{subtitle}</p> : null}
                  </div>

                  <div className="shop-item-visual-zone">
                    {hasImage ? (
                      <img
                        src={imagePath}
                        alt={getItemName(item)}
                        className="shop-item-image"
                        onError={() => markImageAsFailed(item.key)}
                      />
                    ) : IconComponent ? (
                      <IconComponent className="shop-item-icon" strokeWidth={1.8} />
                    ) : (
                      <span className="shop-item-emoji">{item.icon_emoji_fallback || item.emoji || "🎁"}</span>
                    )}
                  </div>
                </div>

                <button
                  className={`shop-price-pill ${isPurchasing === item.key ? "buying" : ""}`}
                  disabled={isPurchasing === item.key}
                >
                  {isPurchasing === item.key ? (
                    <div className="buy-spinner"></div>
                  ) : (
                    <>
                      <span className="shop-price-value">{item.price}</span>
                      <img src={lightningIcon} alt="tokens" className="shop-price-icon" />
                    </>
                  )}
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

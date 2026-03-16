/**
 * Pricing utility for multi-currency display
 * Maps product IDs to EUR/RUB prices and handles Stars markup
 */

export const STARS_MARKUP = 1.3;

export const EUR_PRICES = {
  subscription_daily: 1.99,
  subscription_weekly: 5.99,
  subscription_monthly: 9.99,
  subscription_yearly: 49.99,
  tokens_50: 0.99,
  tokens_100: 1.49,
  tokens_250: 2.99,
  tokens_500: 4.99,
  tokens_1000: 8.99,
  tokens_2500: 19.99,
  tokens_5000: 34.99,
  tokens_10000: 59.99,
  tokens_25000: 129.99,
};

export const RUB_PRICES = {
  subscription_daily: 179,
  subscription_weekly: 549,
  subscription_monthly: 899,
  subscription_yearly: 4499,
  tokens_50: 100,
  tokens_100: 139,
  tokens_250: 279,
  tokens_500: 449,
  tokens_1000: 799,
  tokens_2500: 1799,
  tokens_5000: 3149,
  tokens_10000: 5399,
  tokens_25000: 11699,
};

/**
 * Format price for display based on language
 * @param {string} productId - Product ID
 * @param {string} language - Language code ('en' or 'ru')
 * @returns {string} Formatted price string (e.g. "€6.49" or "599 ₽")
 */
export function formatPrice(productId, language) {
  if (language === "ru") {
    const price = RUB_PRICES[productId];
    if (price == null) return "";
    return `${price.toLocaleString("ru-RU")} ₽`;
  }
  const price = EUR_PRICES[productId];
  if (price == null) return "";
  return `€${price.toFixed(2)}`;
}

/**
 * Format an original (pre-discount) price for display
 * @param {string} productId - Product ID
 * @param {string} language - Language code
 * @param {number} multiplier - Multiplier to compute original price (e.g. for subscriptions)
 * @returns {string} Formatted original price string
 */
export function formatOriginalPrice(productId, language, multiplier) {
  if (language === "ru") {
    const price = RUB_PRICES[productId];
    if (price == null) return "";
    const original = Math.round(price * multiplier);
    return `${original.toLocaleString("ru-RU")} ₽`;
  }
  const price = EUR_PRICES[productId];
  if (price == null) return "";
  const original = Math.round(price * multiplier * 100) / 100;
  return `€${original.toFixed(2)}`;
}

/**
 * Apply 30% markup to Stars price
 * @param {number} stars - Base Stars price
 * @returns {number} Stars price with 30% markup
 */
export function getStarsWithMarkup(stars) {
  return Math.ceil(stars * STARS_MARKUP);
}

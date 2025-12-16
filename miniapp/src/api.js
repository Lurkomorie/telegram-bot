/**
 * API client for Telegram Mini App
 * Handles communication with the FastAPI backend
 */

const API_BASE = import.meta.env.DEV ? 'http://localhost:8000' : '';

/**
 * Fetch personas from the backend
 * @param {string} initData - Telegram WebApp initData for authentication
 * @returns {Promise<Array>} Array of persona objects
 */
export async function fetchPersonas(initData) {
  const response = await fetch(`${API_BASE}/api/miniapp/personas`, {
    headers: {
      'X-Telegram-Init-Data': initData || '',
    },
  });
  
  if (!response.ok) {
    throw new Error('Failed to fetch personas');
  }
  
  return response.json();
}

/**
 * Fetch histories for a specific persona
 * @param {string} personaId - Persona ID
 * @param {string} initData - Telegram WebApp initData for authentication
 * @returns {Promise<Array>} Array of history objects
 */
export async function fetchPersonaHistories(personaId, initData) {
  const response = await fetch(`${API_BASE}/api/miniapp/personas/${personaId}/histories`, {
    headers: {
      'X-Telegram-Init-Data': initData || '',
    },
  });
  
  if (!response.ok) {
    throw new Error('Failed to fetch histories');
  }
  
  return response.json();
}

/**
 * Check if user has an active chat with a persona
 * @param {string} personaId - Persona ID
 * @param {string} initData - Telegram WebApp initData for authentication
 * @returns {Promise<Object>} Object {hasActiveChat: bool, chatId: string|null}
 */
export async function fetchActiveChat(personaId, initData) {
  const response = await fetch(`${API_BASE}/api/miniapp/personas/${personaId}/active-chat`, {
    headers: {
      'X-Telegram-Init-Data': initData || '',
    },
  });
  
  if (!response.ok) {
    return { hasActiveChat: false, chatId: null };
  }
  
  return response.json();
}

/**
 * Fetch user token balance and premium tier
 * @param {string} initData - Telegram WebApp initData for authentication
 * @returns {Promise<Object>} Token object {tokens, premium_tier, is_premium, can_claim_daily_bonus, next_bonus_in_seconds}
 */
export async function fetchUserEnergy(initData) {
  const response = await fetch(`${API_BASE}/api/miniapp/user/energy`, {
    headers: {
      'X-Telegram-Init-Data': initData || '',
    },
  });
  
  if (!response.ok) {
    throw new Error('Failed to fetch energy');
  }
  
  return response.json();
}

/**
 * Fetch user's language preference
 * @param {string} initData - Telegram WebApp initData for authentication
 * @returns {Promise<Object>} Language object {language: string}
 */
export async function fetchUserLanguage(initData) {
  const response = await fetch(`${API_BASE}/api/miniapp/user/language`, {
    headers: {
      'X-Telegram-Init-Data': initData || '',
    },
  });
  
  if (!response.ok) {
    throw new Error('Failed to fetch language');
  }
  
  return response.json();
}

/**
 * Update user's language preference manually
 * @param {string} language - Language code (e.g., 'en', 'ru', 'fr')
 * @param {string} initData - Telegram WebApp initData for authentication
 * @returns {Promise<Object>} Result object {success: bool, language: string}
 */
export async function updateUserLanguage(language, initData) {
  const response = await fetch(`${API_BASE}/api/miniapp/user/update-language`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Telegram-Init-Data': initData || '',
    },
    body: JSON.stringify({ language }),
  });
  
  if (!response.ok) {
    throw new Error('Failed to update language');
  }
  
  return response.json();
}

/**
 * Check user's age verification status
 * @param {string} initData - Telegram WebApp initData for authentication
 * @returns {Promise<Object>} Age status object {age_verified: bool}
 */
export async function checkAgeVerification(initData) {
  const response = await fetch(`${API_BASE}/api/miniapp/user/age-status`, {
    headers: {
      'X-Telegram-Init-Data': initData || '',
    },
  });
  
  if (!response.ok) {
    throw new Error('Failed to check age verification');
  }
  
  return response.json();
}

/**
 * Verify user's age (mark as 18+)
 * @param {string} initData - Telegram WebApp initData for authentication
 * @returns {Promise<Object>} Result object {success: bool, age_verified: bool}
 */
export async function verifyAge(initData) {
  const response = await fetch(`${API_BASE}/api/miniapp/user/verify-age`, {
    method: 'POST',
    headers: {
      'X-Telegram-Init-Data': initData || '',
    },
  });
  
  if (!response.ok) {
    throw new Error('Failed to verify age');
  }
  
  return response.json();
}

/**
 * Select a scenario and create a chat
 * @param {string} personaId - Persona ID
 * @param {string|null} historyId - History ID (optional)
 * @param {string} initData - Telegram WebApp initData for authentication
 * @param {string|null} location - Location key for custom characters (optional)
 * @param {boolean} continueExisting - Continue existing chat instead of starting new (optional)
 * @returns {Promise<Object>} Result object {success, message}
 */
export async function selectScenario(personaId, historyId, initData, location = null, continueExisting = false) {
  const response = await fetch(`${API_BASE}/api/miniapp/select-scenario`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Telegram-Init-Data': initData || '',
    },
    body: JSON.stringify({
      persona_id: personaId,
      history_id: historyId,
      location: location,
      continue_existing: continueExisting,
    }),
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to select scenario' }));
    throw new Error(error.detail || 'Failed to select scenario');
  }
  
  return response.json();
}

/**
 * Create a Telegram Stars invoice for token package or tier subscription
 * @param {string} productId - Product ID (tokens_100, premium_month, etc.)
 * Generate 3 AI story scenarios for a character
 * @param {Object} characterData - Character attributes (name, hair_color, etc.)
 * @param {string} initData - Telegram WebApp initData for authentication
 * @returns {Promise<Object>} Result object {success, stories: Array}
 */
export async function generateStories(characterData, initData) {
  const response = await fetch(`${API_BASE}/api/miniapp/generate-stories`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Telegram-Init-Data': initData || '',
    },
    body: JSON.stringify(characterData),
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Failed to generate stories' }));
    throw new Error(error.message || error.error || 'Failed to generate stories');
  }
  
  return response.json();
}

/**
 * Create a custom character
 * @param {Object} selections - Character attributes
 * @param {string} initData - Telegram WebApp initData for authentication
 * @returns {Promise<Object>} Result object {success, persona_id, message}
 */
export async function createCharacter(selections, initData) {
  const response = await fetch(`${API_BASE}/api/miniapp/create-character`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Telegram-Init-Data': initData || '',
    },
    body: JSON.stringify(selections),
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Failed to create character' }));
    throw new Error(error.message || error.error || 'Failed to create character');
  }
  
  return response.json();
}

/**
 * Delete a custom character
 * @param {string} personaId - Persona ID to delete
 * @param {string} initData - Telegram WebApp initData for authentication
 * @returns {Promise<Object>} Result object {success, message}
 */
export async function deleteCharacter(personaId, initData) {
  const response = await fetch(`${API_BASE}/api/miniapp/characters/${personaId}`, {
    method: 'DELETE',
    headers: {
      'X-Telegram-Init-Data': initData || '',
    },
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Failed to delete character' }));
    throw new Error(error.message || 'Failed to delete character');
  }
  
  return response.json();
}

/**
 * Create a custom story for a character
 * @param {Object} storyData - Story data {persona_id, story_description}
 * @param {string} initData - Telegram WebApp initData for authentication
 * @returns {Promise<Object>} Result object {success, history_id, message}
 */
export async function createCustomStory(storyData, initData) {
  const response = await fetch(`${API_BASE}/api/miniapp/create-custom-story`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Telegram-Init-Data': initData || '',
    },
    body: JSON.stringify(storyData),
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Failed to create story' }));
    throw new Error(error.message || error.error || 'Failed to create story');
  }
  
  return response.json();
}

/**
 * Create a Telegram Stars invoice for premium subscription
 * @param {string} planId - Plan ID (2days, month, 3months, year)
 * @param {string} initData - Telegram WebApp initData for authentication
 * @returns {Promise<Object>} Invoice object {invoice_link} or simulated result {success, simulated, ...}
 */
export async function createInvoice(productId, initData) {
  const response = await fetch(`${API_BASE}/api/miniapp/create-invoice`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Telegram-Init-Data': initData || '',
    },
    body: JSON.stringify({ product_id: productId }),
  });
  
  if (!response.ok) {
    throw new Error('Failed to create invoice');
  }
  
  const data = await response.json();
  
  // Check if this is a simulated payment
  if (data.simulated) {
    console.log('[SIMULATED PAYMENT] Payment processed immediately:', data);
  }
  
  return data;
}

/**
 * Claim daily bonus (10 tokens)
 * @param {string} initData - Telegram WebApp initData for authentication
 * @returns {Promise<Object>} Result object {success: bool, tokens: int, message: str}
 */
export async function claimDailyBonus(initData) {
  const response = await fetch(`${API_BASE}/api/miniapp/claim-daily-bonus`, {
    method: 'POST',
    headers: {
      'X-Telegram-Init-Data': initData || '',
    },
  });
  
  if (!response.ok) {
    throw new Error('Failed to claim daily bonus');
  }
  
  return response.json();
}

/**
 * Check if user can claim daily bonus
 * @param {string} initData - Telegram WebApp initData for authentication
 * @returns {Promise<Object>} Result object {can_claim: bool, next_claim_seconds: int}
 */
export async function canClaimDailyBonus(initData) {
  const response = await fetch(`${API_BASE}/api/miniapp/can-claim-daily-bonus`, {
    headers: {
      'X-Telegram-Init-Data': initData || '',
    },
  });
  
  if (!response.ok) {
    throw new Error('Failed to check bonus eligibility');
  }
  
  return response.json();
}

/**
 * Track analytics event
 * @param {string} eventName - Event name
 * @param {Object} metadata - Event metadata
 * @param {string} initData - Telegram WebApp initData for authentication
 * @returns {Promise<Object>} Result object {success: bool}
 */
export async function trackEvent(eventName, metadata, initData) {
  const response = await fetch(`${API_BASE}/api/miniapp/track-event`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Telegram-Init-Data': initData || '',
    },
    body: JSON.stringify({
      event_name: eventName,
      metadata: metadata || {},
    }),
  });
  
  if (!response.ok) {
    throw new Error('Failed to track event');
  }
  
  return response.json();
}

/**
 * Fetch user's referral statistics
 * @param {string} initData - Telegram WebApp initData for authentication
 * @returns {Promise<Object>} Referral stats object {referrals_count: int, bot_username: string}
 */
export async function fetchReferralStats(initData) {
  const response = await fetch(`${API_BASE}/api/miniapp/user/referrals`, {
    headers: {
      'X-Telegram-Init-Data': initData || '',
    },
  });
  
  if (!response.ok) {
    throw new Error('Failed to fetch referral stats');
  }
  
  return response.json();
}


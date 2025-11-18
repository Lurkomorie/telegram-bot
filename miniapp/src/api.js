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
 * Fetch user energy and premium status
 * @param {string} initData - Telegram WebApp initData for authentication
 * @returns {Promise<Object>} Energy object {energy, max_energy, is_premium}
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
 * @returns {Promise<Object>} Result object {success, message}
 */
export async function selectScenario(personaId, historyId, initData) {
  const response = await fetch(`${API_BASE}/api/miniapp/select-scenario`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Telegram-Init-Data': initData || '',
    },
    body: JSON.stringify({
      persona_id: personaId,
      history_id: historyId,
    }),
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to select scenario' }));
    throw new Error(error.detail || 'Failed to select scenario');
  }
  
  return response.json();
}

/**
 * Create a Telegram Stars invoice for premium subscription
 * @param {string} planId - Plan ID (2days, month, 3months, year)
 * @param {string} initData - Telegram WebApp initData for authentication
 * @returns {Promise<Object>} Invoice object {invoice_link}
 */
export async function createInvoice(planId, initData) {
  const response = await fetch(`${API_BASE}/api/miniapp/create-invoice`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Telegram-Init-Data': initData || '',
    },
    body: JSON.stringify({ plan_id: planId }),
  });
  
  if (!response.ok) {
    throw new Error('Failed to create invoice');
  }
  
  return response.json();
}


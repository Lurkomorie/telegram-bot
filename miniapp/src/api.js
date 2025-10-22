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
 * Fetch user energy
 * @param {string} initData - Telegram WebApp initData for authentication
 * @returns {Promise<Object>} Energy object {energy, max_energy}
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


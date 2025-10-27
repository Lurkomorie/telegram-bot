const API_BASE = '';  // Same origin

export const api = {
  async getStats() {
    const response = await fetch(`${API_BASE}/api/analytics/stats`);
    if (!response.ok) throw new Error('Failed to fetch stats');
    return response.json();
  },

  async getUsers() {
    const response = await fetch(`${API_BASE}/api/analytics/users`);
    if (!response.ok) throw new Error('Failed to fetch users');
    return response.json();
  },

  async getUserEvents(clientId) {
    const response = await fetch(`${API_BASE}/api/analytics/users/${clientId}/events`);
    if (!response.ok) throw new Error('Failed to fetch user events');
    return response.json();
  }
};


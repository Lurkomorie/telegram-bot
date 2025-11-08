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
  },

  async getAcquisitionSources() {
    const response = await fetch(`${API_BASE}/api/analytics/acquisition-sources`);
    if (!response.ok) throw new Error('Failed to fetch acquisition sources');
    return response.json();
  },

  async getMessagesOverTime(interval = '1h') {
    const response = await fetch(`${API_BASE}/api/analytics/messages-over-time?interval=${interval}`);
    if (!response.ok) throw new Error('Failed to fetch messages over time');
    return response.json();
  },

  async getScheduledMessagesOverTime(interval = '1h') {
    const response = await fetch(`${API_BASE}/api/analytics/scheduled-messages-over-time?interval=${interval}`);
    if (!response.ok) throw new Error('Failed to fetch scheduled messages over time');
    return response.json();
  },

  async getActiveUsersOverTime(period = '7d') {
    const response = await fetch(`${API_BASE}/api/analytics/active-users-over-time?period=${period}`);
    if (!response.ok) throw new Error('Failed to fetch active users over time');
    return response.json();
  },

  async getMessagesByPersona() {
    const response = await fetch(`${API_BASE}/api/analytics/messages-by-persona`);
    if (!response.ok) throw new Error('Failed to fetch messages by persona');
    return response.json();
  },

  async getImagesOverTime(period = '7d') {
    const response = await fetch(`${API_BASE}/api/analytics/images-over-time?period=${period}`);
    if (!response.ok) throw new Error('Failed to fetch images over time');
    return response.json();
  },

  async getEngagementHeatmap() {
    const response = await fetch(`${API_BASE}/api/analytics/engagement-heatmap`);
    if (!response.ok) throw new Error('Failed to fetch engagement heatmap');
    return response.json();
  }
};





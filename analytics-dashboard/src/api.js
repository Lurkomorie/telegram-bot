const API_BASE = '';  // Same origin

export const api = {
  async getStats() {
    const response = await fetch(`${API_BASE}/api/analytics/stats`);
    if (!response.ok) throw new Error('Failed to fetch stats');
    return response.json();
  },

  async getUsers(limit = 500, offset = 0) {
    const response = await fetch(`${API_BASE}/api/analytics/users?limit=${limit}&offset=${offset}`);
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

  async getUserMessagesOverTime(interval = '1h') {
    const response = await fetch(`${API_BASE}/api/analytics/user-messages-over-time?interval=${interval}`);
    if (!response.ok) throw new Error('Failed to fetch user messages over time');
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
  },

  async getImageWaitingTime(interval = '1h') {
    const response = await fetch(`${API_BASE}/api/analytics/image-waiting-time?interval=${interval}`);
    if (!response.ok) throw new Error('Failed to fetch image waiting time');
    return response.json();
  },

  async getImages(page = 1, perPage = 100) {
    const response = await fetch(`${API_BASE}/api/analytics/images?page=${page}&per_page=${perPage}`);
    if (!response.ok) throw new Error('Failed to fetch images');
    return response.json();
  },

  async getStartCodes() {
    const response = await fetch(`${API_BASE}/api/analytics/start-codes`);
    if (!response.ok) throw new Error('Failed to fetch start codes');
    return response.json();
  },

  async createStartCode(data) {
    const response = await fetch(`${API_BASE}/api/analytics/start-codes`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(data)
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to create start code');
    }
    return response.json();
  },

  async updateStartCode(code, data) {
    const response = await fetch(`${API_BASE}/api/analytics/start-codes/${code}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(data)
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to update start code');
    }
    return response.json();
  },

  async deleteStartCode(code) {
    const response = await fetch(`${API_BASE}/api/analytics/start-codes/${code}`, {
      method: 'DELETE'
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to delete start code');
    }
    return response.json();
  },

  async getPersonasWithHistories() {
    const response = await fetch(`${API_BASE}/api/analytics/personas-with-histories`);
    if (!response.ok) throw new Error('Failed to fetch personas with histories');
    return response.json();
  },

  async deleteUserChats(clientId) {
    const response = await fetch(`${API_BASE}/api/analytics/users/${clientId}/chats`, {
      method: 'DELETE'
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to delete user chats');
    }
    return response.json();
  }
};





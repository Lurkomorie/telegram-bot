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

  // System Messages
  async createSystemMessage(data) {
    const response = await fetch(`${API_BASE}/api/analytics/system-messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!response.ok) throw new Error('Failed to create system message');
    return response.json();
  },

  async getSystemMessages(params = {}) {
    const queryParams = new URLSearchParams();
    if (params.page) queryParams.append('page', params.page);
    if (params.per_page) queryParams.append('per_page', params.per_page);
    if (params.status) queryParams.append('status', params.status);
    if (params.target_type) queryParams.append('target_type', params.target_type);
    const response = await fetch(`${API_BASE}/api/analytics/system-messages?${queryParams}`);
    if (!response.ok) throw new Error('Failed to fetch system messages');
    return response.json();
  },

  async getSystemMessage(id) {
    const response = await fetch(`${API_BASE}/api/analytics/system-messages/${id}`);
    if (!response.ok) throw new Error('Failed to fetch system message');
    return response.json();
  },

  async updateSystemMessage(id, data) {
    const response = await fetch(`${API_BASE}/api/analytics/system-messages/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!response.ok) throw new Error('Failed to update system message');
    return response.json();
  },

  async deleteSystemMessage(id) {
    const response = await fetch(`${API_BASE}/api/analytics/system-messages/${id}`, {
      method: 'DELETE'
    });
    if (!response.ok) throw new Error('Failed to delete system message');
    return response.json();
  },

  async sendSystemMessage(id) {
    const response = await fetch(`${API_BASE}/api/analytics/system-messages/${id}/send`, {
      method: 'POST'
    });
    if (!response.ok) throw new Error('Failed to send system message');
    return response.json();
  },

  async cancelSystemMessage(id) {
    const response = await fetch(`${API_BASE}/api/analytics/system-messages/${id}/cancel`, {
      method: 'POST'
    });
    if (!response.ok) throw new Error('Failed to cancel system message');
    return response.json();
  },

  async getSystemMessageDeliveries(id, params = {}) {
    const queryParams = new URLSearchParams();
    if (params.page) queryParams.append('page', params.page);
    if (params.per_page) queryParams.append('per_page', params.per_page);
    if (params.status) queryParams.append('status', params.status);
    const response = await fetch(`${API_BASE}/api/analytics/system-messages/${id}/deliveries?${queryParams}`);
    if (!response.ok) throw new Error('Failed to fetch deliveries');
    return response.json();
  },

  async getSystemMessageStats(id) {
    const response = await fetch(`${API_BASE}/api/analytics/system-messages/${id}/stats`);
    if (!response.ok) throw new Error('Failed to fetch stats');
    return response.json();
  },

  async retryFailedDeliveries(id) {
    const response = await fetch(`${API_BASE}/api/analytics/system-messages/${id}/retry-failed`, {
      method: 'POST'
    });
    if (!response.ok) throw new Error('Failed to retry deliveries');
    return response.json();
  },

  // Templates
  async createTemplate(data) {
    const response = await fetch(`${API_BASE}/api/analytics/system-message-templates`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!response.ok) throw new Error('Failed to create template');
    return response.json();
  },

  async getTemplates(params = {}) {
    const queryParams = new URLSearchParams();
    if (params.page) queryParams.append('page', params.page);
    if (params.per_page) queryParams.append('per_page', params.per_page);
    if (params.is_active !== undefined) queryParams.append('is_active', params.is_active);
    const response = await fetch(`${API_BASE}/api/analytics/system-message-templates?${queryParams}`);
    if (!response.ok) throw new Error('Failed to fetch templates');
    return response.json();
  },

  async getTemplate(id) {
    const response = await fetch(`${API_BASE}/api/analytics/system-message-templates/${id}`);
    if (!response.ok) throw new Error('Failed to fetch template');
    return response.json();
  },

  async updateTemplate(id, data) {
    const response = await fetch(`${API_BASE}/api/analytics/system-message-templates/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!response.ok) throw new Error('Failed to update template');
    return response.json();
  },

  async deleteTemplate(id) {
    const response = await fetch(`${API_BASE}/api/analytics/system-message-templates/${id}`, {
      method: 'DELETE'
    });
    if (!response.ok) throw new Error('Failed to delete template');
    return response.json();
  },

  async createMessageFromTemplate(templateId, targetingData) {
    const response = await fetch(`${API_BASE}/api/analytics/system-message-templates/${templateId}/create-message`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(targetingData)
    });
    if (!response.ok) throw new Error('Failed to create message from template');
    return response.json();
  },

  // Helpers
  async getUserGroups() {
    const response = await fetch(`${API_BASE}/api/analytics/user-groups`);
    if (!response.ok) throw new Error('Failed to fetch user groups');
    return response.json();
  },

  async searchUsers(query, limit = 20) {
    const response = await fetch(`${API_BASE}/api/analytics/users/search?query=${encodeURIComponent(query)}&limit=${limit}`);
    if (!response.ok) throw new Error('Failed to search users');
    return response.json();
  }
};

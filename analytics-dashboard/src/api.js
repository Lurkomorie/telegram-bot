const API_BASE = import.meta.env.VITE_API_BASE_URL || '';  // Same origin if unset

export const api = {
  async getDailyUserStats(date) {
    const response = await fetch(`${API_BASE}/api/analytics/daily-user-stats?date=${date}`);
    if (!response.ok) throw new Error('Failed to fetch daily user stats');
    return response.json();
  },

  async getStats(startDate = null, endDate = null, acquisitionSource = null) {
    let url = `${API_BASE}/api/analytics/stats`;
    const params = new URLSearchParams();
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    if (acquisitionSource) params.append('acquisition_source', acquisitionSource);
    if (params.toString()) url += `?${params.toString()}`;
    
    const response = await fetch(url);
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

  async getAcquisitionSources(startDate = null, endDate = null) {
    let url = `${API_BASE}/api/analytics/acquisition-sources`;
    const params = new URLSearchParams();
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    if (params.toString()) url += `?${params.toString()}`;
    
    const response = await fetch(url);
    if (!response.ok) throw new Error('Failed to fetch acquisition sources');
    return response.json();
  },

  async getMessagesOverTime(interval = '1h', startDate = null, endDate = null, acquisitionSource = null) {
    const params = new URLSearchParams({ interval });
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    if (acquisitionSource) params.append('acquisition_source', acquisitionSource);
    
    const response = await fetch(`${API_BASE}/api/analytics/messages-over-time?${params.toString()}`);
    if (!response.ok) throw new Error('Failed to fetch messages over time');
    return response.json();
  },

  async getScheduledMessagesOverTime(interval = '1h', startDate = null, endDate = null, acquisitionSource = null) {
    const params = new URLSearchParams({ interval });
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    if (acquisitionSource) params.append('acquisition_source', acquisitionSource);
    
    const response = await fetch(`${API_BASE}/api/analytics/scheduled-messages-over-time?${params.toString()}`);
    if (!response.ok) throw new Error('Failed to fetch scheduled messages over time');
    return response.json();
  },

  async getUserMessagesOverTime(interval = '1h', startDate = null, endDate = null, acquisitionSource = null) {
    const params = new URLSearchParams({ interval });
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    if (acquisitionSource) params.append('acquisition_source', acquisitionSource);
    
    const response = await fetch(`${API_BASE}/api/analytics/user-messages-over-time?${params.toString()}`);
    if (!response.ok) throw new Error('Failed to fetch user messages over time');
    return response.json();
  },

  async getActiveUsersOverTime(period = '7d', startDate = null, endDate = null, acquisitionSource = null) {
    const params = new URLSearchParams({ period });
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    if (acquisitionSource) params.append('acquisition_source', acquisitionSource);
    
    const response = await fetch(`${API_BASE}/api/analytics/active-users-over-time?${params.toString()}`);
    if (!response.ok) throw new Error('Failed to fetch active users over time');
    return response.json();
  },

  async getMessagesByPersona(startDate = null, endDate = null, acquisitionSource = null) {
    let url = `${API_BASE}/api/analytics/messages-by-persona`;
    const params = new URLSearchParams();
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    if (acquisitionSource) params.append('acquisition_source', acquisitionSource);
    if (params.toString()) url += `?${params.toString()}`;
    
    const response = await fetch(url);
    if (!response.ok) throw new Error('Failed to fetch messages by persona');
    return response.json();
  },

  async getImagesOverTime(period = '7d', startDate = null, endDate = null, acquisitionSource = null) {
    const params = new URLSearchParams({ period });
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    if (acquisitionSource) params.append('acquisition_source', acquisitionSource);
    
    const response = await fetch(`${API_BASE}/api/analytics/images-over-time?${params.toString()}`);
    if (!response.ok) throw new Error('Failed to fetch images over time');
    return response.json();
  },

  async getVoicesOverTime(period = '7d', startDate = null, endDate = null, acquisitionSource = null) {
    const params = new URLSearchParams({ period });
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    if (acquisitionSource) params.append('acquisition_source', acquisitionSource);
    
    const response = await fetch(`${API_BASE}/api/analytics/voices-over-time?${params.toString()}`);
    if (!response.ok) throw new Error('Failed to fetch voices over time');
    return response.json();
  },

  async getEngagementHeatmap(startDate = null, endDate = null, acquisitionSource = null) {
    let url = `${API_BASE}/api/analytics/engagement-heatmap`;
    const params = new URLSearchParams();
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    if (acquisitionSource) params.append('acquisition_source', acquisitionSource);
    if (params.toString()) url += `?${params.toString()}`;
    
    const response = await fetch(url);
    if (!response.ok) throw new Error('Failed to fetch engagement heatmap');
    return response.json();
  },

  async getImageWaitingTime(interval = '1h', startDate = null, endDate = null, acquisitionSource = null) {
    const params = new URLSearchParams({ interval });
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    if (acquisitionSource) params.append('acquisition_source', acquisitionSource);
    
    const response = await fetch(`${API_BASE}/api/analytics/image-waiting-time?${params.toString()}`);
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
  },

  async getPremiumStats(startDate = null, endDate = null, acquisitionSource = null) {
    let url = `${API_BASE}/api/analytics/premium-stats`;
    const params = new URLSearchParams();
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    if (acquisitionSource) params.append('acquisition_source', acquisitionSource);
    if (params.toString()) url += `?${params.toString()}`;
    
    const response = await fetch(url);
    if (!response.ok) throw new Error('Failed to fetch premium stats');
    return response.json();
  },

  async getPremiumPurchases(startDate = null, endDate = null, limit = 100, offset = 0) {
    const params = new URLSearchParams();
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    params.append('limit', limit);
    params.append('offset', offset);
    
    const response = await fetch(`${API_BASE}/api/analytics/premium-purchases?${params.toString()}`);
    if (!response.ok) throw new Error('Failed to fetch premium purchases');
    return response.json();
  },

  async getConversions(startDate = null, endDate = null) {
    const params = new URLSearchParams();
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    
    const response = await fetch(`${API_BASE}/api/analytics/conversions?${params.toString()}`);
    if (!response.ok) throw new Error('Failed to fetch conversions');
    return response.json();
  },

  async getPremiumUsers() {
    const response = await fetch(`${API_BASE}/api/analytics/premium-users`);
    if (!response.ok) throw new Error('Failed to fetch premium users');
    return response.json();
  },

  // ========== PERSONA MANAGEMENT ==========

  async getPersonas() {
    const response = await fetch(`${API_BASE}/api/analytics/personas`);
    if (!response.ok) throw new Error('Failed to fetch personas');
    return response.json();
  },

  async getPersona(personaId) {
    const response = await fetch(`${API_BASE}/api/analytics/personas/${personaId}`);
    if (!response.ok) throw new Error('Failed to fetch persona');
    return response.json();
  },

  async createPersona(data) {
    const response = await fetch(`${API_BASE}/api/analytics/personas`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(data)
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to create persona');
    }
    return response.json();
  },

  async updatePersona(personaId, data) {
    const response = await fetch(`${API_BASE}/api/analytics/personas/${personaId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(data)
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to update persona');
    }
    return response.json();
  },

  async deletePersona(personaId) {
    const response = await fetch(`${API_BASE}/api/analytics/personas/${personaId}`, {
      method: 'DELETE'
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to delete persona');
    }
    return response.json();
  },

  // ========== PERSONA HISTORY MANAGEMENT ==========

  async getPersonaHistories(personaId) {
    const response = await fetch(`${API_BASE}/api/analytics/personas/${personaId}/histories`);
    if (!response.ok) throw new Error('Failed to fetch persona histories');
    return response.json();
  },

  async createPersonaHistory(data) {
    const response = await fetch(`${API_BASE}/api/analytics/persona-histories`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(data)
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to create persona history');
    }
    return response.json();
  },

  async updatePersonaHistory(historyId, data) {
    const response = await fetch(`${API_BASE}/api/analytics/persona-histories/${historyId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(data)
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to update persona history');
    }
    return response.json();
  },

  async deletePersonaHistory(historyId) {
    const response = await fetch(`${API_BASE}/api/analytics/persona-histories/${historyId}`, {
      method: 'DELETE'
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to delete persona history');
    }
    return response.json();
  },

  // ========== SYSTEM MESSAGES ==========

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

  async resumeSystemMessage(id) {
    const response = await fetch(`${API_BASE}/api/analytics/system-messages/${id}/resume`, {
      method: 'POST'
    });
    if (!response.ok) throw new Error('Failed to resume message');
    return response.json();
  },

  // ========== SYSTEM MESSAGE TEMPLATES ==========

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

  // ========== HELPERS ==========

  async getUserGroups() {
    const response = await fetch(`${API_BASE}/api/analytics/user-groups`);
    if (!response.ok) throw new Error('Failed to fetch user groups');
    return response.json();
  },

  async getPersonasWithHistories() {
    const response = await fetch(`${API_BASE}/api/analytics/personas-with-histories`);
    if (!response.ok) throw new Error('Failed to fetch personas with histories');
    return response.json();
  },

  async searchUsers(query, limit = 20) {
    const response = await fetch(`${API_BASE}/api/analytics/users/search?query=${encodeURIComponent(query)}&limit=${limit}`);
    if (!response.ok) throw new Error('Failed to search users');
    return response.json();
  },

  // ========== FILE UPLOAD ==========

  async uploadFile(file, fileType = 'audio') {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch(`${API_BASE}/api/analytics/upload?file_type=${fileType}`, {
      method: 'POST',
      body: formData
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to upload file');
    }
    return response.json();
  },

  // ========== IMAGE CACHE ==========

  async getMostRefreshedImages(limit = 50) {
    const response = await fetch(`${API_BASE}/api/analytics/most-refreshed-images?limit=${limit}`);
    if (!response.ok) throw new Error('Failed to fetch most refreshed images');
    return response.json();
  },

  async getMostCachedImages(limit = 50) {
    const response = await fetch(`${API_BASE}/api/analytics/most-cached-images?limit=${limit}`);
    if (!response.ok) throw new Error('Failed to fetch most cached images');
    return response.json();
  },

  async blacklistImage(jobId) {
    const response = await fetch(`${API_BASE}/api/analytics/blacklist-image/${jobId}`, {
      method: 'POST'
    });
    if (!response.ok) throw new Error('Failed to blacklist image');
    return response.json();
  },

  async unblacklistImage(jobId) {
    const response = await fetch(`${API_BASE}/api/analytics/unblacklist-image/${jobId}`, {
      method: 'POST'
    });
    if (!response.ok) throw new Error('Failed to unblacklist image');
    return response.json();
  }
};

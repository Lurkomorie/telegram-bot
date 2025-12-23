import { useState, useEffect } from 'react';
import { api } from '../api';
import SystemMessageForm from './SystemMessageForm';
import SystemMessageDeliveryStats from './SystemMessageDeliveryStats';

export default function SystemMessages() {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingMessage, setEditingMessage] = useState(null);
  const [selectedMessage, setSelectedMessage] = useState(null);
  const [showStats, setShowStats] = useState(false);
  const [filters, setFilters] = useState({ status: '', target_type: '' });
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  useEffect(() => {
    loadMessages();
  }, [page, filters]);

  const loadMessages = async () => {
    try {
      setLoading(true);
      const data = await api.getSystemMessages({
        page,
        per_page: 20,
        ...filters
      });
      setMessages(data.messages);
      setTotalPages(data.total_pages);
    } catch (error) {
      console.error('Failed to load messages:', error);
      alert('Failed to load messages');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = () => {
    setEditingMessage(null);
    setShowForm(true);
  };

  const handleEdit = (message) => {
    setEditingMessage(message);
    setShowForm(true);
  };

  const handleDelete = async (id) => {
    if (!confirm('Are you sure you want to delete this message?')) return;
    try {
      await api.deleteSystemMessage(id);
      loadMessages();
    } catch (error) {
      alert('Failed to delete message');
    }
  };

  const handleSend = async (id) => {
    if (!confirm('Send this message now?')) return;
    try {
      await api.sendSystemMessage(id);
      alert('Message sending started');
      loadMessages();
    } catch (error) {
      alert('Failed to send message');
    }
  };

  const handleCancel = async (id) => {
    if (!confirm('Cancel this scheduled message?')) return;
    try {
      await api.cancelSystemMessage(id);
      loadMessages();
    } catch (error) {
      alert('Failed to cancel message');
    }
  };

  const handleViewStats = async (message) => {
    setSelectedMessage(message);
    setShowStats(true);
  };

  const handleResume = async (id) => {
    if (!confirm('Resume sending to users who haven\'t received this message yet?')) return;
    try {
      await api.resumeSystemMessage(id);
      alert('Resume started - sending to remaining users');
      loadMessages();
    } catch (error) {
      alert('Failed to resume message: ' + error.message);
    }
  };

  const getStatusBadge = (status) => {
    const configs = {
      draft: {
        bg: 'bg-gradient-to-r from-gray-400 to-gray-500',
        icon: '📝',
        text: 'Draft'
      },
      scheduled: {
        bg: 'bg-gradient-to-r from-blue-400 to-blue-600',
        icon: '⏰',
        text: 'Scheduled'
      },
      sending: {
        bg: 'bg-gradient-to-r from-yellow-400 to-orange-500',
        icon: '📤',
        text: 'Sending',
        animate: true
      },
      completed: {
        bg: 'bg-gradient-to-r from-green-400 to-emerald-600',
        icon: '✓',
        text: 'Completed'
      },
      failed: {
        bg: 'bg-gradient-to-r from-red-400 to-red-600',
        icon: '✗',
        text: 'Failed'
      },
      cancelled: {
        bg: 'bg-gradient-to-r from-gray-300 to-gray-400',
        icon: '⊗',
        text: 'Cancelled'
      }
    };
    
    const config = configs[status] || configs.draft;
    
    return (
      <span className={`${config.bg} text-white px-3 py-1.5 rounded-full text-xs font-semibold inline-flex items-center gap-1.5 shadow-lg ${config.animate ? 'animate-pulse' : ''}`}>
        <span>{config.icon}</span>
        <span>{config.text}</span>
      </span>
    );
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-purple-50 to-pink-50 p-6">
      {/* Header */}
      <div className="max-w-7xl mx-auto mb-8">
        <div className="backdrop-blur-xl bg-white/70 rounded-3xl shadow-2xl p-8 border border-white/20">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-4xl font-bold bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 bg-clip-text text-transparent mb-2">
                System Messages
              </h1>
              <p className="text-gray-600">Broadcast messages to your users</p>
            </div>
            <button
              onClick={handleCreate}
              className="group relative px-8 py-4 bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 text-white rounded-2xl font-semibold shadow-lg hover:shadow-2xl transform hover:scale-105 transition-all duration-300"
            >
              <span className="relative z-10 flex items-center gap-2">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                Create Message
              </span>
              <div className="absolute inset-0 bg-gradient-to-r from-pink-600 via-purple-600 to-indigo-600 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
            </button>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="max-w-7xl mx-auto mb-6">
        <div className="backdrop-blur-xl bg-white/70 rounded-2xl shadow-lg p-6 border border-white/20">
          <div className="flex gap-4">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-2">Status</label>
              <select
                value={filters.status}
                onChange={(e) => setFilters({ ...filters, status: e.target.value })}
                className="w-full px-4 py-3 rounded-xl border-2 border-gray-200 focus:border-indigo-500 focus:ring-4 focus:ring-indigo-200 transition-all duration-200 bg-white/50 backdrop-blur-sm"
              >
                <option value="">All Statuses</option>
                <option value="draft">Draft</option>
                <option value="scheduled">Scheduled</option>
                <option value="sending">Sending</option>
                <option value="completed">Completed</option>
                <option value="failed">Failed</option>
                <option value="cancelled">Cancelled</option>
              </select>
            </div>
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-2">Target Type</label>
              <select
                value={filters.target_type}
                onChange={(e) => setFilters({ ...filters, target_type: e.target.value })}
                className="w-full px-4 py-3 rounded-xl border-2 border-gray-200 focus:border-purple-500 focus:ring-4 focus:ring-purple-200 transition-all duration-200 bg-white/50 backdrop-blur-sm"
              >
                <option value="">All Target Types</option>
                <option value="all">All Users</option>
                <option value="user">Single User</option>
                <option value="users">Multiple Users</option>
                <option value="group">User Group</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Messages List */}
      <div className="max-w-7xl mx-auto">
        {loading ? (
          <div className="backdrop-blur-xl bg-white/70 rounded-2xl shadow-lg p-12 border border-white/20">
            <div className="flex flex-col items-center gap-4">
              <div className="relative w-16 h-16">
                <div className="absolute inset-0 border-4 border-purple-200 rounded-full"></div>
                <div className="absolute inset-0 border-4 border-t-purple-600 rounded-full animate-spin"></div>
              </div>
              <p className="text-gray-600 font-medium">Loading messages...</p>
            </div>
          </div>
        ) : messages.length === 0 ? (
          <div className="backdrop-blur-xl bg-white/70 rounded-2xl shadow-lg p-12 border border-white/20 text-center">
            <div className="text-6xl mb-4">📭</div>
            <p className="text-gray-500 text-lg">No messages found</p>
            <p className="text-gray-400 text-sm mt-2">Create your first system message to get started</p>
          </div>
        ) : (
          <>
            <div className="grid gap-4 mb-6">
              {messages.map((msg, index) => (
                <div
                  key={msg.id}
                  className="backdrop-blur-xl bg-white/70 rounded-2xl shadow-lg p-6 border border-white/20 hover:shadow-2xl transform hover:scale-[1.01] transition-all duration-300"
                  style={{ animationDelay: `${index * 50}ms` }}
                >
                  <div className="flex items-start gap-6">
                    {/* Message Info */}
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-3">
                        <h3 className="text-xl font-bold text-gray-900">
                          {msg.title || '(No title)'}
                        </h3>
                        {getStatusBadge(msg.status)}
                      </div>
                      
                      <p className="text-gray-600 mb-4 line-clamp-2">
                        {msg.text.replace(/<[^>]+>/g, '').substring(0, 150)}...
                      </p>
                      
                      <div className="flex flex-wrap gap-4 text-sm text-gray-500">
                        <div className="flex items-center gap-2">
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                          </svg>
                          <span>
                            {msg.target_type === 'all' && 'All Users'}
                            {msg.target_type === 'user' && `User: ${msg.target_user_ids?.[0] || 'N/A'}`}
                            {msg.target_type === 'users' && `${msg.target_user_ids?.length || 0} users`}
                            {msg.target_type === 'group' && msg.target_group}
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                          </svg>
                          <span>{new Date(msg.created_at).toLocaleDateString()}</span>
                        </div>
                      </div>
                    </div>
                    
                    {/* Actions */}
                    <div className="flex flex-col gap-2">
                      {msg.status === 'draft' && (
                        <>
                          <button onClick={() => handleEdit(msg)} className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors shadow-md hover:shadow-lg">
                            ✏️ Edit
                          </button>
                          <button onClick={() => handleSend(msg.id)} className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors shadow-md hover:shadow-lg">
                            📤 Send
                          </button>
                          <button onClick={() => handleDelete(msg.id)} className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors shadow-md hover:shadow-lg">
                            🗑️ Delete
                          </button>
                        </>
                      )}
                      {msg.status === 'scheduled' && (
                        <>
                          <button onClick={() => handleEdit(msg)} className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors shadow-md hover:shadow-lg">
                            ✏️ Edit
                          </button>
                          <button onClick={() => handleSend(msg.id)} className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors shadow-md hover:shadow-lg">
                            ⚡ Send Now
                          </button>
                          <button onClick={() => handleCancel(msg.id)} className="px-4 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600 transition-colors shadow-md hover:shadow-lg">
                            ⊗ Cancel
                          </button>
                        </>
                      )}
                      {msg.status === 'sending' && (
                        <>
                          <button onClick={() => handleViewStats(msg)} className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors shadow-md hover:shadow-lg">
                            📊 Stats
                          </button>
                          <button onClick={() => handleResume(msg.id)} className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors shadow-md hover:shadow-lg">
                            ▶️ Resume
                          </button>
                          <button onClick={() => handleCancel(msg.id)} className="px-4 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600 transition-colors shadow-md hover:shadow-lg">
                            ⊗ Cancel
                          </button>
                        </>
                      )}
                      {(msg.status === 'completed' || msg.status === 'failed') && (
                        <>
                          <button onClick={() => handleViewStats(msg)} className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors shadow-md hover:shadow-lg">
                            📊 View Stats
                          </button>
                          <button onClick={() => handleResume(msg.id)} className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors shadow-md hover:shadow-lg">
                            ▶️ Resume
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex justify-center gap-3">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="px-6 py-3 bg-white/70 backdrop-blur-xl rounded-xl border border-white/20 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-white/90 transition-all duration-200 shadow-lg font-medium"
                >
                  ← Previous
                </button>
                <div className="px-6 py-3 bg-gradient-to-r from-indigo-500 to-purple-600 text-white rounded-xl font-semibold shadow-lg">
                  Page {page} of {totalPages}
                </div>
                <button
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="px-6 py-3 bg-white/70 backdrop-blur-xl rounded-xl border border-white/20 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-white/90 transition-all duration-200 shadow-lg font-medium"
                >
                  Next →
                </button>
              </div>
            )}
          </>
        )}
      </div>

      {/* Form Modal */}
      {showForm && (
        <SystemMessageForm
          message={editingMessage}
          onClose={() => {
            setShowForm(false);
            setEditingMessage(null);
          }}
          onSave={() => {
            setShowForm(false);
            setEditingMessage(null);
            loadMessages();
          }}
        />
      )}

      {/* Stats Modal */}
      {showStats && selectedMessage && (
        <SystemMessageDeliveryStats
          messageId={selectedMessage.id}
          onClose={() => {
            setShowStats(false);
            setSelectedMessage(null);
          }}
        />
      )}
    </div>
  );
}


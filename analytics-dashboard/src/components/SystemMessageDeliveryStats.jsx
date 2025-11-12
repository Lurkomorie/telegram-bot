import { useState, useEffect } from 'react';
import { api } from '../api';

export default function SystemMessageDeliveryStats({ messageId, onClose }) {
  const [stats, setStats] = useState(null);
  const [deliveries, setDeliveries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [statusFilter, setStatusFilter] = useState('');

  useEffect(() => {
    loadStats();
    loadDeliveries();
  }, [messageId, page, statusFilter]);

  const loadStats = async () => {
    try {
      const data = await api.getSystemMessageStats(messageId);
      setStats(data);
    } catch (error) {
      console.error('Failed to load stats:', error);
    }
  };

  const loadDeliveries = async () => {
    try {
      setLoading(true);
      const data = await api.getSystemMessageDeliveries(messageId, {
        page,
        per_page: 50,
        status: statusFilter || undefined
      });
      setDeliveries(data.deliveries);
      setTotalPages(data.total_pages);
    } catch (error) {
      console.error('Failed to load deliveries:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleRetryFailed = async () => {
    if (!confirm('Retry all failed deliveries?')) return;
    try {
      await api.retryFailedDeliveries(messageId);
      alert('Retry started');
      loadStats();
      loadDeliveries();
    } catch (error) {
      alert('Failed to retry deliveries');
    }
  };

  if (!stats) return <div>Loading...</div>;

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-6">
      <div className="bg-gradient-to-br from-white/95 to-white/90 backdrop-blur-2xl rounded-3xl p-8 max-w-6xl w-full max-h-[90vh] overflow-y-auto shadow-2xl border border-white/20">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h2 className="text-3xl font-bold bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 bg-clip-text text-transparent">
              Delivery Statistics
            </h2>
            <p className="text-gray-600 mt-1">Real-time message delivery tracking</p>
          </div>
          <button 
            onClick={onClose} 
            className="text-gray-400 hover:text-gray-600 hover:bg-gray-100 p-2 rounded-full transition-all duration-200"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-5 gap-4 mb-8">
          <div className="bg-gradient-to-br from-gray-400 to-gray-600 rounded-2xl p-6 text-white shadow-lg transform hover:scale-105 transition-all duration-300">
            <div className="text-sm opacity-90 mb-2">Total</div>
            <div className="text-3xl font-bold">{stats.total}</div>
          </div>
          <div className="bg-gradient-to-br from-green-400 to-emerald-600 rounded-2xl p-6 text-white shadow-lg transform hover:scale-105 transition-all duration-300">
            <div className="text-sm opacity-90 mb-2">Sent ✓</div>
            <div className="text-3xl font-bold">{stats.sent}</div>
          </div>
          <div className="bg-gradient-to-br from-red-400 to-red-600 rounded-2xl p-6 text-white shadow-lg transform hover:scale-105 transition-all duration-300">
            <div className="text-sm opacity-90 mb-2">Failed ✗</div>
            <div className="text-3xl font-bold">{stats.failed}</div>
          </div>
          <div className="bg-gradient-to-br from-yellow-400 to-orange-500 rounded-2xl p-6 text-white shadow-lg transform hover:scale-105 transition-all duration-300">
            <div className="text-sm opacity-90 mb-2">Blocked 🚫</div>
            <div className="text-3xl font-bold">{stats.blocked}</div>
          </div>
          <div className="bg-gradient-to-br from-blue-400 to-blue-600 rounded-2xl p-6 text-white shadow-lg transform hover:scale-105 transition-all duration-300">
            <div className="text-sm opacity-90 mb-2">Success Rate</div>
            <div className="text-3xl font-bold">{stats.success_rate}%</div>
            <div className="w-full bg-white/30 rounded-full h-2 mt-2">
              <div className="bg-white rounded-full h-2 transition-all duration-500" style={{ width: `${stats.success_rate}%` }}></div>
            </div>
          </div>
        </div>

        {/* Retry Button */}
        {stats.failed > 0 && (
          <div className="mb-6">
            <button
              onClick={handleRetryFailed}
              className="group relative px-6 py-3 bg-gradient-to-r from-orange-500 to-red-600 text-white rounded-xl font-semibold shadow-lg hover:shadow-2xl transform hover:scale-105 transition-all duration-300"
            >
              <span className="relative z-10 flex items-center gap-2">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Retry Failed Deliveries ({stats.failed})
              </span>
            </button>
          </div>
        )}

        {/* Filter */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">Filter by Status</label>
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(1);
            }}
            className="w-64 px-4 py-3 rounded-xl border-2 border-gray-200 focus:border-purple-500 focus:ring-4 focus:ring-purple-200 transition-all duration-200 bg-white/80 backdrop-blur-sm"
          >
            <option value="">All Statuses</option>
            <option value="sent">Sent</option>
            <option value="failed">Failed</option>
            <option value="blocked">Blocked</option>
            <option value="pending">Pending</option>
          </select>
        </div>

        {/* Deliveries Table */}
        {loading ? (
          <div className="backdrop-blur-xl bg-white/70 rounded-2xl shadow-lg p-12 border border-white/20">
            <div className="flex flex-col items-center gap-4">
              <div className="relative w-16 h-16">
                <div className="absolute inset-0 border-4 border-purple-200 rounded-full"></div>
                <div className="absolute inset-0 border-4 border-t-purple-600 rounded-full animate-spin"></div>
              </div>
              <p className="text-gray-600 font-medium">Loading deliveries...</p>
            </div>
          </div>
        ) : deliveries.length === 0 ? (
          <div className="backdrop-blur-xl bg-white/70 rounded-2xl shadow-lg p-12 border border-white/20 text-center">
            <div className="text-6xl mb-4">📭</div>
            <p className="text-gray-500 text-lg">No deliveries found</p>
          </div>
        ) : (
          <>
            <div className="backdrop-blur-xl bg-white/80 rounded-2xl shadow-lg overflow-hidden border border-white/20">
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gradient-to-r from-gray-50 to-gray-100">
                    <tr>
                      <th className="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">User ID</th>
                      <th className="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">Status</th>
                      <th className="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">Retry</th>
                      <th className="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider w-1/2">Error</th>
                      <th className="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">Sent At</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white/50 divide-y divide-gray-200">
                    {deliveries.map((delivery) => (
                      <tr key={delivery.id} className="hover:bg-white/80 transition-colors">
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{delivery.user_id}</td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold shadow-sm ${
                            delivery.status === 'sent' ? 'bg-gradient-to-r from-green-400 to-emerald-600 text-white' :
                            delivery.status === 'failed' ? 'bg-gradient-to-r from-red-400 to-red-600 text-white' :
                            delivery.status === 'blocked' ? 'bg-gradient-to-r from-yellow-400 to-orange-500 text-white' :
                            'bg-gradient-to-r from-gray-300 to-gray-400 text-white'
                          }`}>
                            {delivery.status === 'sent' && '✓'}
                            {delivery.status === 'failed' && '✗'}
                            {delivery.status === 'blocked' && '🚫'}
                            {delivery.status}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
                          <span className="font-mono">{delivery.retry_count} / {delivery.max_retries}</span>
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-700">
                          {delivery.error ? (
                            <div className="group relative">
                              <div className="line-clamp-2 hover:line-clamp-none cursor-help bg-red-50 border border-red-200 rounded-lg px-3 py-2 font-mono text-xs">
                                {delivery.error}
                              </div>
                            </div>
                          ) : (
                            <span className="text-gray-400">-</span>
                          )}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {delivery.sent_at ? (
                            <div>
                              <div className="font-medium">{new Date(delivery.sent_at).toLocaleDateString()}</div>
                              <div className="text-xs text-gray-400">{new Date(delivery.sent_at).toLocaleTimeString()}</div>
                            </div>
                          ) : (
                            '-'
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="mt-6 flex justify-center gap-3">
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
    </div>
  );
}


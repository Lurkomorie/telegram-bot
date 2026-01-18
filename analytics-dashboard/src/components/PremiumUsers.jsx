import { useEffect, useState } from 'react';
import { api } from '../api';
import { formatNumber } from '../utils';
import { Link } from 'react-router-dom';

export default function PremiumUsers() {
  const [users, setUsers] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [sortBy, setSortBy] = useState('total_spent'); // total_spent, purchase_count, last_purchase
  const [sortOrder, setSortOrder] = useState('desc');
  const [filterActive, setFilterActive] = useState('all'); // all, active, expired

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const data = await api.getPremiumUsers();
      setUsers(data.users || []);
      setStats(data.stats || null);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-gray-500">Loading...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-red-500">Error: {error}</div>
      </div>
    );
  }

  const formatDate = (dateString) => {
    if (!dateString) return '—';
    return new Date(dateString).toLocaleString('ru-RU', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const isPremiumActive = (user) => {
    if (!user.premium_until) return true; // Lifetime premium
    return new Date(user.premium_until) > new Date();
  };

  // Filter users
  let filteredUsers = [...users];
  if (filterActive === 'active') {
    filteredUsers = filteredUsers.filter(u => isPremiumActive(u));
  } else if (filterActive === 'expired') {
    filteredUsers = filteredUsers.filter(u => !isPremiumActive(u));
  }

  // Sort users
  filteredUsers.sort((a, b) => {
    let aVal, bVal;
    switch (sortBy) {
      case 'total_spent':
        aVal = a.total_spent_stars || 0;
        bVal = b.total_spent_stars || 0;
        break;
      case 'purchase_count':
        aVal = a.purchase_count || 0;
        bVal = b.purchase_count || 0;
        break;
      case 'last_purchase':
        aVal = a.last_purchase_date ? new Date(a.last_purchase_date).getTime() : 0;
        bVal = b.last_purchase_date ? new Date(b.last_purchase_date).getTime() : 0;
        break;
      default:
        return 0;
    }
    return sortOrder === 'desc' ? bVal - aVal : aVal - bVal;
  });

  const handleSort = (field) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc');
    } else {
      setSortBy(field);
      setSortOrder('desc');
    }
  };

  const SortIcon = ({ field }) => {
    if (sortBy !== field) return <span className="text-gray-400">↕</span>;
    return sortOrder === 'desc' ? <span className="text-blue-600">↓</span> : <span className="text-blue-600">↑</span>;
  };

  return (
    <div className="p-8">
      <div className="mb-8">
        <h2 className="text-3xl font-bold text-gray-800">Премиум пользователи</h2>
        <p className="text-gray-500 mt-1">Детальная информация о тратах премиум пользователей</p>
      </div>

      {/* Stats Overview */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-8">
          <div className="bg-gradient-to-br from-purple-500 to-purple-600 rounded-lg shadow-lg p-6 text-white">
            <p className="text-purple-100 text-sm font-medium">Всего премиум</p>
            <p className="text-3xl font-bold mt-2">{formatNumber(stats.total_premium_users)}</p>
            <p className="text-purple-200 text-xs mt-1">Когда-либо купивших</p>
          </div>
          
          <div className="bg-white rounded-lg shadow p-6">
            <p className="text-gray-500 text-sm font-medium">Активных сейчас</p>
            <p className="text-3xl font-bold text-green-600 mt-2">{formatNumber(stats.active_premium_users)}</p>
            <p className="text-xs text-gray-400 mt-1">С активной подпиской</p>
          </div>
          
          <div className="bg-white rounded-lg shadow p-6">
            <p className="text-gray-500 text-sm font-medium">Средний чек</p>
            <p className="text-3xl font-bold text-blue-600 mt-2">
              ${stats.avg_spent_per_user ? stats.avg_spent_per_user.toFixed(2) : '0.00'}
            </p>
            <p className="text-xs text-gray-400 mt-1">⭐ {formatNumber(Math.round(stats.avg_spent_per_user / 0.013))} звезд</p>
          </div>
          
          <div className="bg-white rounded-lg shadow p-6">
            <p className="text-gray-500 text-sm font-medium">Всего потрачено</p>
            <p className="text-3xl font-bold text-green-600 mt-2">${formatNumber(stats.total_revenue_usd)}</p>
            <p className="text-xs text-gray-400 mt-1">⭐ {formatNumber(stats.total_revenue_stars)} звезд</p>
          </div>
          
          <div className="bg-white rounded-lg shadow p-6">
            <p className="text-gray-500 text-sm font-medium">Покупок на юзера</p>
            <p className="text-3xl font-bold text-orange-600 mt-2">
              {stats.avg_purchases_per_user ? stats.avg_purchases_per_user.toFixed(1) : '0.0'}
            </p>
            <p className="text-xs text-gray-400 mt-1">В среднем</p>
          </div>
        </div>
      )}

      {/* Filters and Sorting */}
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-gray-700">Фильтр:</span>
            <button
              onClick={() => setFilterActive('all')}
              className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                filterActive === 'all'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              Все ({users.length})
            </button>
            <button
              onClick={() => setFilterActive('active')}
              className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                filterActive === 'active'
                  ? 'bg-green-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              Активные ({users.filter(u => isPremiumActive(u)).length})
            </button>
            <button
              onClick={() => setFilterActive('expired')}
              className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                filterActive === 'expired'
                  ? 'bg-red-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              Истекшие ({users.filter(u => !isPremiumActive(u)).length})
            </button>
          </div>
          
          <div className="text-sm text-gray-600">
            Показано: {filteredUsers.length} пользователей
          </div>
        </div>
      </div>

      {/* Users Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Пользователь
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Статус
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Источник
                </th>
                <th 
                  className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                  onClick={() => handleSort('purchase_count')}
                >
                  <div className="flex items-center justify-end gap-1">
                    Покупок <SortIcon field="purchase_count" />
                  </div>
                </th>
                <th 
                  className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                  onClick={() => handleSort('total_spent')}
                >
                  <div className="flex items-center justify-end gap-1">
                    Потрачено <SortIcon field="total_spent" />
                  </div>
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                  USD
                </th>
                <th 
                  className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                  onClick={() => handleSort('last_purchase')}
                >
                  <div className="flex items-center gap-1">
                    Последняя покупка <SortIcon field="last_purchase" />
                  </div>
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Премиум до
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {filteredUsers.map((user) => {
                const isActive = isPremiumActive(user);
                return (
                  <tr key={user.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 whitespace-nowrap">
                      <Link 
                        to={`/users/${user.id}`}
                        className="text-sm font-medium text-blue-600 hover:text-blue-800 hover:underline"
                      >
                        {user.first_name || user.username || 'Unknown'}
                      </Link>
                      <div className="text-xs text-gray-500">ID: {user.id}</div>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        isActive 
                          ? 'bg-green-100 text-green-800' 
                          : 'bg-red-100 text-red-800'
                      }`}>
                        {isActive ? '✓ Активен' : '✗ Истек'}
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                      {user.acquisition_source || '—'}
                    </td>
                    <td className="px-4 py-3 text-right text-sm font-medium text-gray-800">
                      {formatNumber(user.purchase_count || 0)}
                    </td>
                    <td className="px-4 py-3 text-right text-sm font-bold text-purple-600">
                      ⭐ {formatNumber(user.total_spent_stars || 0)}
                    </td>
                    <td className="px-4 py-3 text-right text-sm font-bold text-green-600">
                      ${((user.total_spent_stars || 0) * 0.013).toFixed(2)}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                      {formatDate(user.last_purchase_date)}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                      {user.premium_until ? formatDate(user.premium_until) : '∞ Навсегда'}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {filteredUsers.length === 0 && (
          <div className="text-center py-12 text-gray-500">
            Нет пользователей для отображения
          </div>
        )}
      </div>

      {/* Top Spenders */}
      {users.length > 0 && (
        <div className="mt-8 bg-white rounded-lg shadow p-6">
          <h3 className="text-xl font-bold text-gray-800 mb-4">🏆 Топ-10 по тратам</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[...users]
              .sort((a, b) => (b.total_spent_stars || 0) - (a.total_spent_stars || 0))
              .slice(0, 10)
              .map((user, index) => (
                <div key={user.id} className="flex items-center gap-4 bg-gray-50 rounded-lg p-4">
                  <div className={`text-2xl font-bold ${
                    index === 0 ? 'text-yellow-500' :
                    index === 1 ? 'text-gray-400' :
                    index === 2 ? 'text-orange-600' :
                    'text-gray-600'
                  }`}>
                    #{index + 1}
                  </div>
                  <div className="flex-1">
                    <Link 
                      to={`/users/${user.id}`}
                      className="font-medium text-blue-600 hover:text-blue-800 hover:underline"
                    >
                      {user.first_name || user.username || 'Unknown'}
                    </Link>
                    <div className="text-xs text-gray-500">{user.purchase_count} покупок</div>
                  </div>
                  <div className="text-right">
                    <div className="font-bold text-green-600">
                      ${((user.total_spent_stars || 0) * 0.013).toFixed(2)}
                    </div>
                    <div className="text-xs text-gray-500">
                      ⭐ {formatNumber(user.total_spent_stars || 0)}
                    </div>
                  </div>
                </div>
              ))}
          </div>
        </div>
      )}
    </div>
  );
}

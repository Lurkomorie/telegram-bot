import { useEffect, useState } from 'react';
import { api } from '../api';
import { formatNumber } from '../utils';
import DateRangeFilter from './DateRangeFilter';
import TimeSeriesChart from './TimeSeriesChart';

export default function Payments() {
  const getDefaultStartDate = () => {
    const date = new Date();
    date.setDate(date.getDate() - 30);
    return date.toISOString().split('T')[0];
  };
  
  const getDefaultEndDate = () => {
    return new Date().toISOString().split('T')[0];
  };

  const [startDate, setStartDate] = useState(getDefaultStartDate());
  const [endDate, setEndDate] = useState(getDefaultEndDate());
  const [purchases, setPurchases] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const perPage = 50;

  useEffect(() => {
    fetchData();
  }, [startDate, endDate, page]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [purchasesData, statsData] = await Promise.all([
        api.getPremiumPurchases(startDate, endDate, perPage, (page - 1) * perPage),
        api.getPremiumStats(startDate, endDate)
      ]);
      
      setPurchases(purchasesData.purchases || []);
      setTotalPages(Math.ceil((purchasesData.total || 0) / perPage));
      setStats(statsData);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading && !stats) {
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
    return new Date(dateString).toLocaleString('ru-RU', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getStatusBadge = (status) => {
    const statusColors = {
      'completed': 'bg-green-100 text-green-800',
      'pending': 'bg-yellow-100 text-yellow-800',
      'failed': 'bg-red-100 text-red-800',
      'refunded': 'bg-gray-100 text-gray-800'
    };
    return statusColors[status] || 'bg-gray-100 text-gray-800';
  };

  // Prepare chart data
  const chartData = stats?.revenue_over_time?.map(item => ({
    timestamp: item.date,
    value: item.revenue_usd
  })) || [];

  return (
    <div className="p-8">
      <div className="mb-8">
        <h2 className="text-3xl font-bold text-gray-800">Оплаты</h2>
        <p className="text-gray-500 mt-1">Все данные о платежах и доходах</p>
      </div>

      <DateRangeFilter 
        startDate={startDate}
        endDate={endDate}
        onStartDateChange={setStartDate}
        onEndDateChange={setEndDate}
      />

      {/* Overview Cards */}
      {stats && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <div className="bg-gradient-to-br from-green-500 to-green-600 rounded-lg shadow-lg p-6 text-white">
              <p className="text-green-100 text-sm font-medium">Общий доход</p>
              <p className="text-3xl font-bold mt-2">${formatNumber(stats.total_revenue_usd)}</p>
              <p className="text-green-200 text-xs mt-1">⭐ {formatNumber(stats.total_revenue_stars)} звезд</p>
            </div>
            
            <div className="bg-white rounded-lg shadow p-6">
              <p className="text-gray-500 text-sm font-medium">Всего платежей</p>
              <p className="text-3xl font-bold text-gray-800 mt-2">{formatNumber(stats.total_purchases)}</p>
              <p className="text-xs text-gray-400 mt-1">За выбранный период</p>
            </div>
            
            <div className="bg-white rounded-lg shadow p-6">
              <p className="text-gray-500 text-sm font-medium">Платящих пользователей</p>
              <p className="text-3xl font-bold text-blue-600 mt-2">{formatNumber(stats.paying_users)}</p>
              <p className="text-xs text-gray-400 mt-1">Уникальных покупателей</p>
            </div>
            
            <div className="bg-white rounded-lg shadow p-6">
              <p className="text-gray-500 text-sm font-medium">Средний чек</p>
              <p className="text-3xl font-bold text-purple-600 mt-2">
                ${stats.paying_users > 0 ? (stats.total_revenue_usd / stats.paying_users).toFixed(2) : '0.00'}
              </p>
              <p className="text-xs text-gray-400 mt-1">На одного покупателя</p>
            </div>
          </div>

          {/* Revenue Chart */}
          {chartData.length > 0 && (
            <div className="bg-white rounded-lg shadow p-6 mb-8">
              <h3 className="text-xl font-bold text-gray-800 mb-4">График доходов</h3>
              <TimeSeriesChart 
                data={chartData}
                title="Доход по дням"
                color="#10b981"
                valueFormatter={(value) => `$${value.toFixed(2)}`}
              />
            </div>
          )}

          {/* Payment Type Breakdown */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-xl font-bold text-gray-800 mb-4">По типу платежей</h3>
              <div className="space-y-4">
                <div className="bg-purple-50 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-medium text-gray-800">👑 Премиум подписки</span>
                  </div>
                  <p className="text-2xl font-bold text-gray-800">{formatNumber(stats.tier_subscriptions_count)} покупок</p>
                  <p className="text-sm text-green-600 mt-1">${formatNumber(stats.tier_subscriptions_stars * 0.013)}</p>
                  <p className="text-xs text-gray-500">⭐ {formatNumber(stats.tier_subscriptions_stars)} звезд</p>
                </div>
                <div className="bg-blue-50 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-medium text-gray-800">🪙 Пакеты токенов</span>
                  </div>
                  <p className="text-2xl font-bold text-gray-800">{formatNumber(stats.token_packages_count)} покупок</p>
                  <p className="text-sm text-green-600 mt-1">${formatNumber(stats.token_packages_stars * 0.013)}</p>
                  <p className="text-xs text-gray-500">⭐ {formatNumber(stats.token_packages_stars)} звезд</p>
                  <p className="text-xs text-blue-600 mt-1">🎫 {formatNumber(stats.tokens_sold)} токенов продано</p>
                </div>
              </div>
            </div>

            {/* Payment Plans Breakdown */}
            {stats.by_plan && stats.by_plan.length > 0 && (
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-xl font-bold text-gray-800 mb-4">По продуктам</h3>
                <div className="space-y-3">
                  {stats.by_plan.map((plan) => (
                    <div key={plan.plan_name} className="bg-gray-50 rounded-lg p-3">
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-medium text-gray-800 text-sm">{plan.plan_name}</span>
                        <span className="text-xl">{plan.plan_name.toLowerCase().includes('premium') || plan.plan_name.toLowerCase().includes('tier') ? '👑' : '🪙'}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-lg font-bold text-gray-800">{formatNumber(plan.count)} шт</span>
                        <div className="text-right">
                          <p className="text-sm text-green-600 font-medium">${formatNumber(plan.revenue_usd)}</p>
                          <p className="text-xs text-gray-500">⭐ {formatNumber(plan.revenue_stars)}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </>
      )}

      {/* Payments Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="p-6 border-b">
          <h3 className="text-xl font-bold text-gray-800">Список платежей</h3>
          <p className="text-sm text-gray-500 mt-1">Все транзакции за выбранный период</p>
        </div>
        
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Дата</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Пользователь</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Тип</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Продукт</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Детали</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Звезды</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">USD</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">ID транзакции</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {purchases.map((purchase) => (
                <tr key={purchase.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                    {formatDate(purchase.created_at)}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <div className="text-sm font-medium text-gray-800">
                      {purchase.user?.first_name || purchase.user?.username || 'Unknown'}
                    </div>
                    <div className="text-xs text-gray-500">ID: {purchase.user?.id}</div>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      purchase.transaction_type === 'tier_subscription' 
                        ? 'bg-purple-100 text-purple-800' 
                        : 'bg-blue-100 text-blue-800'
                    }`}>
                      {purchase.transaction_type === 'tier_subscription' ? '👑 Премиум' : '🪙 Токены'}
                    </span>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-700">
                    {purchase.product_id || 'Unknown'}
                  </td>
                  <td className="px-4 py-3 text-right text-sm text-gray-600">
                    {purchase.transaction_type === 'tier_subscription' 
                      ? `${purchase.subscription_days || 0} дней`
                      : `${purchase.tokens_received || 0} токенов`
                    }
                  </td>
                  <td className="px-4 py-3 text-right text-sm font-medium text-gray-800">
                    ⭐ {purchase.amount_stars}
                  </td>
                  <td className="px-4 py-3 text-right text-sm font-bold text-green-600">
                    ${(purchase.amount_stars * 0.013).toFixed(2)}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500 font-mono">
                    {purchase.id.substring(0, 20)}...
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="px-6 py-4 border-t flex items-center justify-between">
            <div className="text-sm text-gray-500">
              Страница {page} из {totalPages}
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Назад
              </button>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Вперед
              </button>
            </div>
          </div>
        )}

        {purchases.length === 0 && (
          <div className="text-center py-12 text-gray-500">
            Нет платежей за выбранный период
          </div>
        )}
      </div>
    </div>
  );
}

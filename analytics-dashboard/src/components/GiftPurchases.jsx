import { useEffect, useState } from 'react';
import { api } from '../api';
import { formatNumber } from '../utils';
import DateRangeFilter from './DateRangeFilter';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';

export default function GiftPurchases() {
  const getDefaultStartDate = () => {
    const date = new Date();
    date.setDate(date.getDate() - 30);
    return date.toISOString().split('T')[0];
  };

  const getDefaultEndDate = () => new Date().toISOString().split('T')[0];

  const [startDate, setStartDate] = useState(getDefaultStartDate());
  const [endDate, setEndDate] = useState(getDefaultEndDate());
  const [stats, setStats] = useState(null);
  const [purchases, setPurchases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const perPage = 50;

  useEffect(() => {
    setPage(1);
  }, [startDate, endDate]);

  useEffect(() => {
    fetchData();
  }, [startDate, endDate, page]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [statsData, purchasesData] = await Promise.all([
        api.getGiftPurchaseStats(startDate, endDate),
        api.getGiftPurchases(startDate, endDate, perPage, (page - 1) * perPage),
      ]);

      setStats(statsData || null);
      setPurchases(purchasesData.purchases || []);
      setTotalPages(Math.max(1, Math.ceil((purchasesData.total || 0) / perPage)));
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return '—';
    return new Date(dateString).toLocaleString('ru-RU', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
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

  const chartData = (stats?.purchases_over_time || []).map((item) => ({
    date: item.date,
    purchases: item.purchase_count,
    tokens: item.tokens_spent,
  }));

  return (
    <div className="p-8">
      <div className="mb-8">
        <h2 className="text-3xl font-bold text-gray-800">Покупки подарков</h2>
        <p className="text-gray-500 mt-1">Статистика покупок в gift shop</p>
      </div>

      <DateRangeFilter
        startDate={startDate}
        endDate={endDate}
        onStartDateChange={setStartDate}
        onEndDateChange={setEndDate}
      />

      {stats && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-8">
            <div className="bg-gradient-to-br from-pink-500 to-rose-600 rounded-lg shadow-lg p-6 text-white">
              <p className="text-pink-100 text-sm font-medium">Всего покупок</p>
              <p className="text-3xl font-bold mt-2">{formatNumber(stats.total_purchases || 0)}</p>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <p className="text-gray-500 text-sm font-medium">Потрачено токенов</p>
              <p className="text-3xl font-bold text-gray-800 mt-2">{formatNumber(stats.total_tokens_spent || 0)}</p>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <p className="text-gray-500 text-sm font-medium">Уникальных покупателей</p>
              <p className="text-3xl font-bold text-blue-600 mt-2">{formatNumber(stats.unique_buyers || 0)}</p>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <p className="text-gray-500 text-sm font-medium">Уникальных чатов</p>
              <p className="text-3xl font-bold text-purple-600 mt-2">{formatNumber(stats.unique_chats || 0)}</p>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <p className="text-gray-500 text-sm font-medium">Средняя цена подарка</p>
              <p className="text-3xl font-bold text-green-600 mt-2">{stats.avg_price || 0}</p>
              <p className="text-xs text-gray-400 mt-1">токенов</p>
            </div>
          </div>

          {chartData.length > 0 && (
            <div className="bg-white rounded-lg shadow p-6 mb-8">
              <h3 className="text-xl font-bold text-gray-800 mb-4">Динамика покупок</h3>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis
                    dataKey="date"
                    tickFormatter={(date) => new Date(date).toLocaleDateString('ru-RU', { month: 'short', day: 'numeric' })}
                    tick={{ fontSize: 12 }}
                    stroke="#9ca3af"
                  />
                  <YAxis yAxisId="left" tick={{ fontSize: 12 }} stroke="#9ca3af" allowDecimals={false} />
                  <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 12 }} stroke="#9ca3af" />
                  <Tooltip
                    content={({ active, payload }) => {
                      if (active && payload && payload.length) {
                        const date = new Date(payload[0].payload.date);
                        return (
                          <div className="bg-white px-3 py-2 shadow-lg rounded border border-gray-200">
                            <p className="text-xs text-gray-500 mb-1">
                              {date.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' })}
                            </p>
                            <p className="text-sm font-bold text-pink-600">
                              Покупки: {payload[0].payload.purchases}
                            </p>
                            <p className="text-sm font-bold text-blue-600">
                              Токены: {payload[0].payload.tokens}
                            </p>
                          </div>
                        );
                      }
                      return null;
                    }}
                  />
                  <Legend />
                  <Line yAxisId="left" type="monotone" dataKey="purchases" name="Покупки" stroke="#ec4899" strokeWidth={2} dot={false} />
                  <Line yAxisId="right" type="monotone" dataKey="tokens" name="Токены" stroke="#2563eb" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-xl font-bold text-gray-800 mb-4">Топ подарки</h3>
              <div className="space-y-3">
                {(stats.by_item || []).slice(0, 8).map((item) => (
                  <div key={item.item_key} className="bg-gray-50 rounded-lg p-3">
                    <div className="flex items-center justify-between">
                      <span className="font-medium text-gray-800">{item.emoji || '🎁'} {item.item_name}</span>
                      <span className="text-sm text-gray-500">{item.category}</span>
                    </div>
                    <div className="flex items-center justify-between mt-1 text-sm">
                      <span className="text-gray-700">{formatNumber(item.purchase_count)} шт</span>
                      <span className="text-blue-600 font-medium">{formatNumber(item.tokens_spent)} токенов</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-xl font-bold text-gray-800 mb-4">По категориям</h3>
              <div className="space-y-3">
                {(stats.by_category || []).map((category) => (
                  <div key={category.category} className="bg-gray-50 rounded-lg p-3">
                    <div className="flex items-center justify-between">
                      <span className="font-medium text-gray-800">{category.category}</span>
                      <span className="text-sm text-gray-500">{formatNumber(category.purchase_count)} покупок</span>
                    </div>
                    <p className="text-sm text-blue-600 mt-1">{formatNumber(category.tokens_spent)} токенов</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </>
      )}

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="px-6 py-4 border-b">
          <h3 className="text-lg font-bold text-gray-800">Последние покупки подарков</h3>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Дата</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Пользователь</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Персона</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Подарок</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Цена</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Mood +</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {purchases.map((purchase) => (
                <tr key={purchase.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-sm text-gray-700">{formatDate(purchase.purchased_at)}</td>
                  <td className="px-4 py-3 text-sm text-gray-700">
                    <div className="font-medium">{purchase.user?.first_name || 'Unknown'}</div>
                    <div className="text-xs text-gray-500">
                      ID: {purchase.user?.id} {purchase.user?.acquisition_source ? `• ${purchase.user.acquisition_source}` : ''}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-700">{purchase.persona_name || '—'}</td>
                  <td className="px-4 py-3 text-sm text-gray-700">
                    <div className="font-medium">{purchase.item_name}</div>
                    <div className="text-xs text-gray-500">{purchase.item_key}</div>
                  </td>
                  <td className="px-4 py-3 text-sm text-right font-medium text-blue-600">{purchase.price_paid}</td>
                  <td className="px-4 py-3 text-sm text-right font-medium text-green-600">+{purchase.mood_boost}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="px-6 py-4 border-t bg-gray-50 flex items-center justify-between">
          <button
            onClick={() => setPage((prev) => Math.max(1, prev - 1))}
            disabled={page <= 1}
            className="px-4 py-2 text-sm bg-white border border-gray-300 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
          >
            ← Назад
          </button>
          <span className="text-sm text-gray-600">Страница {page} из {totalPages}</span>
          <button
            onClick={() => setPage((prev) => Math.min(totalPages, prev + 1))}
            disabled={page >= totalPages}
            className="px-4 py-2 text-sm bg-white border border-gray-300 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Вперед →
          </button>
        </div>
      </div>
    </div>
  );
}


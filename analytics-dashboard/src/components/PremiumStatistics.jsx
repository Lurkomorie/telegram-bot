import { useEffect, useState } from 'react';
import { api } from '../api';
import { formatNumber } from '../utils';
import TimeSeriesChart from './TimeSeriesChart';
import DateRangeFilter from './DateRangeFilter';

export default function PremiumStatistics() {
  // Date filter state
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
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchStats();
  }, [startDate, endDate]);

  const fetchStats = async () => {
    try {
      setLoading(true);
      const data = await api.getPremiumStats(startDate, endDate);
      setStats(data);
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

  const statCards = [
    { label: 'Active Premium Users', value: stats.total_premium_users, icon: '👑', color: 'yellow' },
    { label: 'Total Premium Purchases', value: stats.total_ever_premium_users, icon: '💎', color: 'purple' },
    { label: 'Total Free Users', value: stats.total_free_users, icon: '👥', color: 'blue' },
    { label: 'Conversion Rate', value: `${stats.conversion_rate}%`, icon: '📈', color: 'green' },
  ];

  return (
    <div className="p-8">
      <div className="mb-8">
        <h2 className="text-3xl font-bold text-gray-800">Premium Statistics</h2>
        <p className="text-gray-500 mt-1">Premium user metrics and analytics</p>
      </div>

      {/* Date Range Filter */}
      <DateRangeFilter 
        startDate={startDate}
        endDate={endDate}
        onStartDateChange={setStartDate}
        onEndDateChange={setEndDate}
      />

      {/* Overview Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {statCards.map((stat, index) => (
          <div key={index} className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-500 text-sm font-medium">{stat.label}</p>
                <p className="text-3xl font-bold text-gray-800 mt-2">
                  {formatNumber(stat.value)}
                </p>
              </div>
              <div className={`text-4xl bg-${stat.color}-100 p-3 rounded-lg`}>
                {stat.icon}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Premium Users Over Time */}
      <div className="mb-8">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-xl font-bold text-gray-800 mb-4">Premium Purchases Over Time (All Time)</h3>
          {stats.premium_users_over_time && stats.premium_users_over_time.length > 0 ? (
            <TimeSeriesChart 
              data={stats.premium_users_over_time.map(item => ({ timestamp: item.date, count: item.count }))} 
              title="" 
              color="#f59e0b" 
              height={300} 
            />
          ) : (
            <div className="flex items-center justify-center h-64">
              <p className="text-gray-400">No data available</p>
            </div>
          )}
        </div>
      </div>

      {/* Premium vs Free Comparisons */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Image Generation Comparison */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-xl font-bold text-gray-800 mb-4">Image Generation</h3>
          <div className="space-y-4">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-600">Premium Users</span>
                <span className="text-lg font-bold text-yellow-600">
                  {formatNumber(stats.premium_vs_free_images.premium)}
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-3">
                <div 
                  className="bg-yellow-500 h-3 rounded-full" 
                  style={{ 
                    width: `${(stats.premium_vs_free_images.premium / (stats.premium_vs_free_images.premium + stats.premium_vs_free_images.free) * 100)}%` 
                  }}
                ></div>
              </div>
            </div>
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-600">Free Users</span>
                <span className="text-lg font-bold text-blue-600">
                  {formatNumber(stats.premium_vs_free_images.free)}
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-3">
                <div 
                  className="bg-blue-500 h-3 rounded-full" 
                  style={{ 
                    width: `${(stats.premium_vs_free_images.free / (stats.premium_vs_free_images.premium + stats.premium_vs_free_images.free) * 100)}%` 
                  }}
                ></div>
              </div>
            </div>
          </div>
        </div>

        {/* Engagement Comparison */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-xl font-bold text-gray-800 mb-4">User Engagement</h3>
          <div className="space-y-4">
            <div>
              <div className="text-sm font-medium text-gray-600 mb-1">Premium Users</div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-500">Active Users:</span>
                <span className="text-sm font-bold text-yellow-600">
                  {formatNumber(stats.premium_vs_free_engagement.premium.user_count)}
                </span>
              </div>
              <div className="flex items-center justify-between mt-1">
                <span className="text-xs text-gray-500">Avg Messages:</span>
                <span className="text-sm font-bold text-yellow-600">
                  {stats.premium_vs_free_engagement.premium.avg_messages.toFixed(1)}
                </span>
              </div>
            </div>
            <div className="border-t pt-4">
              <div className="text-sm font-medium text-gray-600 mb-1">Free Users</div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-500">Active Users:</span>
                <span className="text-sm font-bold text-blue-600">
                  {formatNumber(stats.premium_vs_free_engagement.free.user_count)}
                </span>
              </div>
              <div className="flex items-center justify-between mt-1">
                <span className="text-xs text-gray-500">Avg Messages:</span>
                <span className="text-sm font-bold text-blue-600">
                  {stats.premium_vs_free_engagement.free.avg_messages.toFixed(1)}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Summary Table */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-xl font-bold text-gray-800 mb-4">Summary Comparison</h3>
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead>
              <tr className="border-b">
                <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Metric</th>
                <th className="text-right py-3 px-4 text-sm font-medium text-gray-500">Premium</th>
                <th className="text-right py-3 px-4 text-sm font-medium text-gray-500">Free</th>
                <th className="text-right py-3 px-4 text-sm font-medium text-gray-500">Ratio</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b hover:bg-gray-50">
                <td className="py-3 px-4 text-sm text-gray-700">Active Premium Users</td>
                <td className="py-3 px-4 text-sm text-right font-medium text-yellow-600">
                  {formatNumber(stats.total_premium_users)}
                </td>
                <td className="py-3 px-4 text-sm text-right font-medium text-blue-600">
                  {formatNumber(stats.total_free_users)}
                </td>
                <td className="py-3 px-4 text-sm text-right text-gray-600">
                  {((stats.total_premium_users / (stats.total_premium_users + stats.total_free_users)) * 100).toFixed(1)}%
                </td>
              </tr>
              <tr className="border-b hover:bg-gray-50">
                <td className="py-3 px-4 text-sm text-gray-700">Total Premium Purchases</td>
                <td className="py-3 px-4 text-sm text-right font-medium text-yellow-600">
                  {formatNumber(stats.total_ever_premium_users)}
                </td>
                <td className="py-3 px-4 text-sm text-right font-medium text-blue-600">
                  -
                </td>
                <td className="py-3 px-4 text-sm text-right text-gray-600">
                  {stats.conversion_rate}%
                </td>
              </tr>
              <tr className="border-b hover:bg-gray-50">
                <td className="py-3 px-4 text-sm text-gray-700">Images Generated</td>
                <td className="py-3 px-4 text-sm text-right font-medium text-yellow-600">
                  {formatNumber(stats.premium_vs_free_images.premium)}
                </td>
                <td className="py-3 px-4 text-sm text-right font-medium text-blue-600">
                  {formatNumber(stats.premium_vs_free_images.free)}
                </td>
                <td className="py-3 px-4 text-sm text-right text-gray-600">
                  {stats.total_premium_users > 0 ? 
                    `${((stats.premium_vs_free_images.premium / stats.total_premium_users) / 
                        (stats.premium_vs_free_images.free / stats.total_free_users)).toFixed(2)}x` 
                    : 'N/A'}
                </td>
              </tr>
              <tr className="hover:bg-gray-50">
                <td className="py-3 px-4 text-sm text-gray-700">Avg Messages per User</td>
                <td className="py-3 px-4 text-sm text-right font-medium text-yellow-600">
                  {stats.premium_vs_free_engagement.premium.avg_messages.toFixed(1)}
                </td>
                <td className="py-3 px-4 text-sm text-right font-medium text-blue-600">
                  {stats.premium_vs_free_engagement.free.avg_messages.toFixed(1)}
                </td>
                <td className="py-3 px-4 text-sm text-right text-gray-600">
                  {stats.premium_vs_free_engagement.free.avg_messages > 0 ?
                    `${(stats.premium_vs_free_engagement.premium.avg_messages / 
                        stats.premium_vs_free_engagement.free.avg_messages).toFixed(2)}x`
                    : 'N/A'}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}



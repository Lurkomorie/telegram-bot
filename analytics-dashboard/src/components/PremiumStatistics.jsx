import { useEffect, useState } from 'react';
import { api } from '../api';
import { formatNumber } from '../utils';
import DateRangeFilter from './DateRangeFilter';

export default function PremiumStatistics() {
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

  const tokenPercentage = stats.total_stars > 0 
    ? ((stats.token_packages_stars / stats.total_stars) * 100).toFixed(1)
    : 0;
  const tierPercentage = stats.total_stars > 0
    ? ((stats.tier_subscriptions_stars / stats.total_stars) * 100).toFixed(1)
    : 0;

  return (
    <div className="p-8">
      <div className="mb-8">
        <h2 className="text-3xl font-bold text-gray-800">Revenue & Premium</h2>
        <p className="text-gray-500 mt-1">Revenue metrics and payment analytics</p>
      </div>

      <DateRangeFilter 
        startDate={startDate}
        endDate={endDate}
        onStartDateChange={setStartDate}
        onEndDateChange={setEndDate}
      />

      {/* Revenue Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="bg-gradient-to-br from-yellow-400 to-yellow-600 rounded-lg shadow-lg p-6 text-white">
          <p className="text-yellow-100 text-sm font-medium">Total Revenue</p>
          <p className="text-4xl font-bold mt-2">{formatNumber(stats.total_stars)}</p>
          <p className="text-yellow-200 text-sm mt-1">stars</p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-gray-500 text-sm font-medium">Total Purchases</p>
          <p className="text-3xl font-bold text-gray-800 mt-2">{formatNumber(stats.total_purchases)}</p>
          <p className="text-gray-400 text-sm mt-1">transactions</p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-gray-500 text-sm font-medium">Unique Paying Users</p>
          <p className="text-3xl font-bold text-gray-800 mt-2">{formatNumber(stats.unique_paying_users)}</p>
          <p className="text-gray-400 text-sm mt-1">users who paid</p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-gray-500 text-sm font-medium">Avg Purchase Value</p>
          <p className="text-3xl font-bold text-gray-800 mt-2">{formatNumber(stats.avg_purchase_value)}</p>
          <p className="text-gray-400 text-sm mt-1">stars per purchase</p>
        </div>
      </div>

      {/* Revenue Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Token Packages */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xl font-bold text-gray-800">Token Packages</h3>
            <span className="text-2xl">🪙</span>
          </div>
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div className="bg-purple-50 rounded-lg p-4">
              <p className="text-purple-600 text-sm font-medium">Purchases</p>
              <p className="text-2xl font-bold text-purple-800">{formatNumber(stats.token_packages_count)}</p>
            </div>
            <div className="bg-purple-50 rounded-lg p-4">
              <p className="text-purple-600 text-sm font-medium">Revenue</p>
              <p className="text-2xl font-bold text-purple-800">{formatNumber(stats.token_packages_stars)}</p>
              <p className="text-purple-600 text-xs">stars</p>
            </div>
          </div>
          <div className="bg-gray-100 rounded-lg p-4">
            <p className="text-gray-600 text-sm font-medium">Tokens Sold</p>
            <p className="text-2xl font-bold text-gray-800">{formatNumber(stats.tokens_sold)}</p>
          </div>
          <div className="mt-4">
            <div className="flex items-center justify-between text-sm mb-1">
              <span className="text-gray-500">Share of Revenue</span>
              <span className="font-medium text-purple-600">{tokenPercentage}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div 
                className="bg-purple-500 h-2 rounded-full transition-all" 
                style={{ width: `${tokenPercentage}%` }}
              ></div>
            </div>
          </div>
        </div>

        {/* Tier Subscriptions */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xl font-bold text-gray-800">Tier Subscriptions</h3>
            <span className="text-2xl">👑</span>
          </div>
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div className="bg-yellow-50 rounded-lg p-4">
              <p className="text-yellow-600 text-sm font-medium">Purchases</p>
              <p className="text-2xl font-bold text-yellow-800">{formatNumber(stats.tier_subscriptions_count)}</p>
            </div>
            <div className="bg-yellow-50 rounded-lg p-4">
              <p className="text-yellow-600 text-sm font-medium">Revenue</p>
              <p className="text-2xl font-bold text-yellow-800">{formatNumber(stats.tier_subscriptions_stars)}</p>
              <p className="text-yellow-600 text-xs">stars</p>
            </div>
          </div>
          <div className="bg-gray-100 rounded-lg p-4">
            <p className="text-gray-600 text-sm font-medium">Active Premium Users</p>
            <p className="text-2xl font-bold text-gray-800">{formatNumber(stats.total_premium_users)}</p>
          </div>
          <div className="mt-4">
            <div className="flex items-center justify-between text-sm mb-1">
              <span className="text-gray-500">Share of Revenue</span>
              <span className="font-medium text-yellow-600">{tierPercentage}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div 
                className="bg-yellow-500 h-2 rounded-full transition-all" 
                style={{ width: `${tierPercentage}%` }}
              ></div>
            </div>
          </div>
        </div>
      </div>

      {/* User Stats */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-gray-500 text-sm font-medium">Active Premium</p>
          <p className="text-3xl font-bold text-yellow-600 mt-2">{formatNumber(stats.total_premium_users)}</p>
          <p className="text-gray-400 text-sm mt-1">currently active</p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-gray-500 text-sm font-medium">Ever Premium</p>
          <p className="text-3xl font-bold text-purple-600 mt-2">{formatNumber(stats.total_ever_premium_users)}</p>
          <p className="text-gray-400 text-sm mt-1">including expired</p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-gray-500 text-sm font-medium">Conversion Rate</p>
          <p className="text-3xl font-bold text-green-600 mt-2">{stats.conversion_rate}%</p>
          <p className="text-gray-400 text-sm mt-1">free to premium</p>
        </div>
      </div>

      {/* Product Breakdown Table */}
      {stats.packages_breakdown && stats.packages_breakdown.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-xl font-bold text-gray-800 mb-4">Product Breakdown</h3>
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Product</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Type</th>
                  <th className="text-right py-3 px-4 text-sm font-medium text-gray-500">Purchases</th>
                  <th className="text-right py-3 px-4 text-sm font-medium text-gray-500">Revenue (stars)</th>
                  <th className="text-right py-3 px-4 text-sm font-medium text-gray-500">Share</th>
                </tr>
              </thead>
              <tbody>
                {stats.packages_breakdown.map((pkg, index) => {
                  const share = stats.total_stars > 0 
                    ? ((pkg.total_stars / stats.total_stars) * 100).toFixed(1)
                    : 0;
                  return (
                    <tr key={index} className="border-b hover:bg-gray-50">
                      <td className="py-3 px-4 text-sm text-gray-800 font-medium">
                        {pkg.product_id}
                      </td>
                      <td className="py-3 px-4 text-sm">
                        <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                          pkg.transaction_type === 'token_package' 
                            ? 'bg-purple-100 text-purple-800' 
                            : 'bg-yellow-100 text-yellow-800'
                        }`}>
                          {pkg.transaction_type === 'token_package' ? 'Tokens' : 'Subscription'}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-sm text-right text-gray-600">
                        {formatNumber(pkg.count)}
                      </td>
                      <td className="py-3 px-4 text-sm text-right font-medium text-gray-800">
                        {formatNumber(pkg.total_stars)}
                      </td>
                      <td className="py-3 px-4 text-sm text-right">
                        <div className="flex items-center justify-end">
                          <div className="w-16 bg-gray-200 rounded-full h-2 mr-2">
                            <div 
                              className={`h-2 rounded-full ${pkg.transaction_type === 'token_package' ? 'bg-purple-500' : 'bg-yellow-500'}`}
                              style={{ width: `${share}%` }}
                            ></div>
                          </div>
                          <span className="text-gray-600">{share}%</span>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

import { useEffect, useState } from 'react';
import { api } from '../api';
import { formatNumber } from '../utils';
import DateRangeFilter from './DateRangeFilter';

export default function Conversions() {
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
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchData();
  }, [startDate, endDate]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const result = await api.getConversions(startDate, endDate);
      setData(result);
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

  if (!data) return null;

  const { sources, totals } = data;

  return (
    <div className="p-8">
      <div className="mb-8">
        <h2 className="text-3xl font-bold text-gray-800">Conversions & ROI</h2>
        <p className="text-gray-500 mt-1">Revenue, costs, and ROI analysis by acquisition source</p>
      </div>

      <DateRangeFilter 
        startDate={startDate}
        endDate={endDate}
        onStartDateChange={setStartDate}
        onEndDateChange={setEndDate}
      />

      {/* Cost Constants */}
      <div className="bg-gradient-to-r from-slate-700 to-slate-800 rounded-lg shadow-lg p-4 mb-6 text-white">
        <div className="flex items-center gap-8 text-sm">
          <span className="font-medium">Cost Constants:</span>
          <span>💬 ${data.cost_per_message}/message</span>
          <span>🖼️ ${data.cost_per_image}/image</span>
          <span>⭐ 1 star ≈ ${data.stars_to_usd} USD</span>
        </div>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-8">
        <div className="bg-white rounded-lg shadow p-5">
          <p className="text-gray-500 text-sm font-medium">Total Users</p>
          <p className="text-2xl font-bold text-gray-800 mt-1">{formatNumber(totals.total_users)}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-5">
          <p className="text-gray-500 text-sm font-medium">Paying Users</p>
          <p className="text-2xl font-bold text-green-600 mt-1">{formatNumber(totals.paying_users)}</p>
          <p className="text-xs text-gray-400">{totals.overall_conversion}% conversion</p>
        </div>
        <div className="bg-gradient-to-br from-yellow-400 to-yellow-500 rounded-lg shadow p-5 text-white">
          <p className="text-yellow-100 text-sm font-medium">Revenue</p>
          <p className="text-2xl font-bold mt-1">${formatNumber(totals.revenue_usd)}</p>
          <p className="text-yellow-200 text-xs">⭐ {formatNumber(totals.revenue_stars)} stars</p>
        </div>
        <div className="bg-white rounded-lg shadow p-5">
          <p className="text-gray-500 text-sm font-medium">Total Costs</p>
          <p className="text-2xl font-bold text-red-500 mt-1">${formatNumber(totals.total_cost)}</p>
          <p className="text-xs text-gray-400">
            Ad: ${formatNumber(totals.ad_spend)} | LLM: ${formatNumber(totals.llm_cost)} | Img: ${formatNumber(totals.image_cost)}
          </p>
        </div>
        <div className={`rounded-lg shadow p-5 ${totals.net_profit >= 0 ? 'bg-gradient-to-br from-emerald-500 to-emerald-600 text-white' : 'bg-gradient-to-br from-red-500 to-red-600 text-white'}`}>
          <p className={`text-sm font-medium ${totals.net_profit >= 0 ? 'text-emerald-100' : 'text-red-100'}`}>Net Profit</p>
          <p className="text-2xl font-bold mt-1">${formatNumber(totals.net_profit)}</p>
          <p className={`text-xs ${totals.net_profit >= 0 ? 'text-emerald-200' : 'text-red-200'}`}>
            {totals.overall_roi >= 0 ? '+' : ''}{totals.overall_roi}% ROI
          </p>
        </div>
      </div>

      {/* Cost Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-bold text-gray-800">Ad Spend</h3>
            <span className="text-2xl">📢</span>
          </div>
          <p className="text-3xl font-bold text-gray-800">${formatNumber(totals.ad_spend)}</p>
          <p className="text-sm text-gray-500 mt-2">
            {sources.filter(s => s.ad_price > 0).length} sources with ad spend
          </p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-bold text-gray-800">LLM Costs</h3>
            <span className="text-2xl">💬</span>
          </div>
          <p className="text-3xl font-bold text-gray-800">${formatNumber(totals.llm_cost)}</p>
          <p className="text-sm text-gray-500 mt-2">
            {formatNumber(totals.messages)} messages × ${data.cost_per_message}
          </p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-bold text-gray-800">Image Costs</h3>
            <span className="text-2xl">🖼️</span>
          </div>
          <p className="text-3xl font-bold text-gray-800">${formatNumber(totals.image_cost)}</p>
          <p className="text-sm text-gray-500 mt-2">
            {formatNumber(totals.images)} images × ${data.cost_per_image}
          </p>
        </div>
      </div>

      {/* Sources Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="p-6 border-b">
          <h3 className="text-xl font-bold text-gray-800">Breakdown by Acquisition Source</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Source</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Ad $</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Users</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Paying</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Conv %</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Msgs</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Imgs</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Revenue</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">LLM Cost</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Img Cost</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Total Cost</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Profit</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">ROI</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {sources.map((source) => (
                <tr key={source.source} className="hover:bg-gray-50">
                  <td className="px-4 py-3 whitespace-nowrap">
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                      {source.source}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right text-sm text-gray-600">
                    {source.ad_price > 0 ? `$${source.ad_price.toFixed(2)}` : '—'}
                  </td>
                  <td className="px-4 py-3 text-right text-sm font-medium text-gray-800">
                    {formatNumber(source.total_users)}
                  </td>
                  <td className="px-4 py-3 text-right text-sm text-gray-600">
                    {formatNumber(source.paying_users)}
                  </td>
                  <td className="px-4 py-3 text-right text-sm">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                      source.conversion_rate >= 5 ? 'bg-green-100 text-green-800' :
                      source.conversion_rate >= 2 ? 'bg-yellow-100 text-yellow-800' :
                      'bg-gray-100 text-gray-600'
                    }`}>
                      {source.conversion_rate}%
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right text-sm text-gray-600">
                    {formatNumber(source.messages)}
                  </td>
                  <td className="px-4 py-3 text-right text-sm text-gray-600">
                    {formatNumber(source.images)}
                  </td>
                  <td className="px-4 py-3 text-right text-sm font-medium text-green-600">
                    ${source.revenue_usd.toFixed(2)}
                  </td>
                  <td className="px-4 py-3 text-right text-sm text-gray-600">
                    ${source.llm_cost.toFixed(2)}
                  </td>
                  <td className="px-4 py-3 text-right text-sm text-gray-600">
                    ${source.image_cost.toFixed(2)}
                  </td>
                  <td className="px-4 py-3 text-right text-sm font-medium text-red-500">
                    ${source.total_cost.toFixed(2)}
                  </td>
                  <td className={`px-4 py-3 text-right text-sm font-bold ${source.net_profit >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                    ${source.net_profit.toFixed(2)}
                  </td>
                  <td className="px-4 py-3 text-right text-sm">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-bold ${
                      source.roi >= 100 ? 'bg-emerald-100 text-emerald-800' :
                      source.roi >= 0 ? 'bg-green-100 text-green-700' :
                      source.roi >= -50 ? 'bg-yellow-100 text-yellow-800' :
                      'bg-red-100 text-red-800'
                    }`}>
                      {source.roi >= 0 ? '+' : ''}{source.roi}%
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot className="bg-gray-100 font-bold">
              <tr>
                <td className="px-4 py-3 text-sm text-gray-800">TOTALS</td>
                <td className="px-4 py-3 text-right text-sm text-gray-800">${totals.ad_spend.toFixed(2)}</td>
                <td className="px-4 py-3 text-right text-sm text-gray-800">{formatNumber(totals.total_users)}</td>
                <td className="px-4 py-3 text-right text-sm text-gray-800">{formatNumber(totals.paying_users)}</td>
                <td className="px-4 py-3 text-right text-sm text-gray-800">{totals.overall_conversion}%</td>
                <td className="px-4 py-3 text-right text-sm text-gray-800">{formatNumber(totals.messages)}</td>
                <td className="px-4 py-3 text-right text-sm text-gray-800">{formatNumber(totals.images)}</td>
                <td className="px-4 py-3 text-right text-sm text-green-700">${totals.revenue_usd.toFixed(2)}</td>
                <td className="px-4 py-3 text-right text-sm text-gray-800">${totals.llm_cost.toFixed(2)}</td>
                <td className="px-4 py-3 text-right text-sm text-gray-800">${totals.image_cost.toFixed(2)}</td>
                <td className="px-4 py-3 text-right text-sm text-red-600">${totals.total_cost.toFixed(2)}</td>
                <td className={`px-4 py-3 text-right text-sm ${totals.net_profit >= 0 ? 'text-emerald-700' : 'text-red-700'}`}>
                  ${totals.net_profit.toFixed(2)}
                </td>
                <td className={`px-4 py-3 text-right text-sm ${totals.overall_roi >= 0 ? 'text-emerald-700' : 'text-red-700'}`}>
                  {totals.overall_roi >= 0 ? '+' : ''}{totals.overall_roi}%
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      {sources.length === 0 && (
        <div className="text-center py-12 text-gray-500">
          No acquisition sources with data in this period
        </div>
      )}

      {/* Purchase Statistics Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden mt-8">
        <div className="p-6 border-b">
          <h3 className="text-xl font-bold text-gray-800">Purchase Statistics</h3>
          <p className="text-sm text-gray-500 mt-1">Total purchases vs unique paying users (repeat purchase analysis)</p>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Source</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Total Users</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Unique Buyers</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Conv %</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Total Purchases</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Avg Purchases/Buyer</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Repeat Rate</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {sources.map((source) => {
                const avgPurchasesPerBuyer = source.paying_users > 0 
                  ? (source.total_purchases / source.paying_users).toFixed(2) 
                  : '0.00';
                const repeatRate = source.paying_users > 0 && source.total_purchases > source.paying_users
                  ? (((source.total_purchases - source.paying_users) / source.paying_users) * 100).toFixed(1)
                  : '0.0';
                return (
                  <tr key={source.source} className="hover:bg-gray-50">
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                        {source.source}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right text-sm font-medium text-gray-800">
                      {formatNumber(source.total_users)}
                    </td>
                    <td className="px-4 py-3 text-right text-sm text-gray-600">
                      {formatNumber(source.paying_users)}
                    </td>
                    <td className="px-4 py-3 text-right text-sm">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                        source.conversion_rate >= 5 ? 'bg-green-100 text-green-800' :
                        source.conversion_rate >= 2 ? 'bg-yellow-100 text-yellow-800' :
                        'bg-gray-100 text-gray-600'
                      }`}>
                        {source.conversion_rate}%
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right text-sm font-medium text-indigo-600">
                      {formatNumber(source.total_purchases || 0)}
                    </td>
                    <td className="px-4 py-3 text-right text-sm text-gray-600">
                      {avgPurchasesPerBuyer}
                    </td>
                    <td className="px-4 py-3 text-right text-sm">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                        parseFloat(repeatRate) >= 50 ? 'bg-emerald-100 text-emerald-800' :
                        parseFloat(repeatRate) >= 20 ? 'bg-green-100 text-green-700' :
                        'bg-gray-100 text-gray-600'
                      }`}>
                        {repeatRate}%
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
            <tfoot className="bg-gray-100 font-bold">
              <tr>
                <td className="px-4 py-3 text-sm text-gray-800">TOTALS</td>
                <td className="px-4 py-3 text-right text-sm text-gray-800">{formatNumber(totals.total_users)}</td>
                <td className="px-4 py-3 text-right text-sm text-gray-800">{formatNumber(totals.paying_users)}</td>
                <td className="px-4 py-3 text-right text-sm text-gray-800">{totals.overall_conversion}%</td>
                <td className="px-4 py-3 text-right text-sm text-indigo-700">{formatNumber(totals.total_purchases || 0)}</td>
                <td className="px-4 py-3 text-right text-sm text-gray-800">
                  {totals.paying_users > 0 ? ((totals.total_purchases || 0) / totals.paying_users).toFixed(2) : '0.00'}
                </td>
                <td className="px-4 py-3 text-right text-sm text-gray-800">
                  {totals.paying_users > 0 && (totals.total_purchases || 0) > totals.paying_users
                    ? ((((totals.total_purchases || 0) - totals.paying_users) / totals.paying_users) * 100).toFixed(1)
                    : '0.0'}%
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      {/* Unit Economics */}
      <div className="mt-8 bg-white rounded-lg shadow p-6">
        <h3 className="text-xl font-bold text-gray-800 mb-4">Unit Economics</h3>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div className="bg-gray-50 rounded-lg p-4">
            <p className="text-gray-500 text-sm">Cost per User (Acquired)</p>
            <p className="text-2xl font-bold text-gray-800">
              ${totals.total_users > 0 ? (totals.total_cost / totals.total_users).toFixed(4) : '0.00'}
            </p>
          </div>
          <div className="bg-gray-50 rounded-lg p-4">
            <p className="text-gray-500 text-sm">Revenue per User</p>
            <p className="text-2xl font-bold text-green-600">
              ${totals.total_users > 0 ? (totals.revenue_usd / totals.total_users).toFixed(4) : '0.00'}
            </p>
          </div>
          <div className="bg-gray-50 rounded-lg p-4">
            <p className="text-gray-500 text-sm">LTV per Paying User</p>
            <p className="text-2xl font-bold text-purple-600">
              ${totals.paying_users > 0 ? (totals.revenue_usd / totals.paying_users).toFixed(2) : '0.00'}
            </p>
          </div>
          <div className="bg-gray-50 rounded-lg p-4">
            <p className="text-gray-500 text-sm">Cost per Conversion</p>
            <p className="text-2xl font-bold text-orange-600">
              ${totals.paying_users > 0 ? (totals.total_cost / totals.paying_users).toFixed(2) : '0.00'}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}


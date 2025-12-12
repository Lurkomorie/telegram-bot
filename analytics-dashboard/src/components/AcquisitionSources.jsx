import { useEffect, useState } from 'react';
import { api } from '../api';
import DateRangeFilter from './DateRangeFilter';
import Sparkline from './Sparkline';

export default function AcquisitionSources() {
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
  const [sources, setSources] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [sortConfig, setSortConfig] = useState({ key: 'user_count', direction: 'desc' });

  useEffect(() => {
    fetchSources();
  }, [startDate, endDate]);

  const fetchSources = async () => {
    try {
      setLoading(true);
      const data = await api.getAcquisitionSources(startDate, endDate);
      setSources(data);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSort = (key) => {
    let direction = 'asc';
    if (sortConfig.key === key && sortConfig.direction === 'asc') {
      direction = 'desc';
    }
    setSortConfig({ key, direction });
  };

  const getSortedSources = () => {
    const sortedSources = [...sources];
    sortedSources.sort((a, b) => {
      let aValue = a[sortConfig.key];
      let bValue = b[sortConfig.key];

      if (aValue === null || aValue === undefined) return 1;
      if (bValue === null || bValue === undefined) return -1;

      if (aValue < bValue) {
        return sortConfig.direction === 'asc' ? -1 : 1;
      }
      if (aValue > bValue) {
        return sortConfig.direction === 'asc' ? 1 : -1;
      }
      return 0;
    });
    return sortedSources;
  };

  const SortIcon = ({ columnKey }) => {
    if (sortConfig.key !== columnKey) {
      return <span className="text-gray-300 ml-1">↕</span>;
    }
    return (
      <span className="ml-1">
        {sortConfig.direction === 'asc' ? '↑' : '↓'}
      </span>
    );
  };

  const formatNumber = (num) => {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return num?.toLocaleString() || '0';
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

  // Calculate totals
  const totalUsers = sources.reduce((sum, source) => sum + source.user_count, 0);
  const totalEvents = sources.reduce((sum, source) => sum + source.total_events, 0);
  const totalPurchases = sources.reduce((sum, source) => sum + (source.total_purchases || 0), 0);
  const totalStars = sources.reduce((sum, source) => sum + (source.total_stars || 0), 0);
  const sortedSources = getSortedSources();

  return (
    <div className="p-8">
      <div className="mb-8">
        <h2 className="text-3xl font-bold text-gray-800">Acquisition Sources</h2>
        <p className="text-gray-500 mt-1">User acquisition breakdown by source</p>
      </div>

      <DateRangeFilter 
        startDate={startDate}
        endDate={endDate}
        onStartDateChange={setStartDate}
        onEndDateChange={setEndDate}
      />

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-6 mb-8">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-sm text-gray-500 mb-1">Total Sources</div>
          <div className="text-3xl font-bold text-gray-800">{sources.length}</div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-sm text-gray-500 mb-1">Total Users</div>
          <div className="text-3xl font-bold text-gray-800">{formatNumber(totalUsers)}</div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-sm text-gray-500 mb-1">Total Events</div>
          <div className="text-3xl font-bold text-gray-800">{formatNumber(totalEvents)}</div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-sm text-gray-500 mb-1">Total Purchases</div>
          <div className="text-3xl font-bold text-green-600">{formatNumber(totalPurchases)}</div>
        </div>
        <div className="bg-gradient-to-br from-yellow-400 to-yellow-600 rounded-lg shadow-lg p-6 text-white">
          <div className="text-yellow-100 text-sm mb-1">Total Stars</div>
          <div className="text-3xl font-bold">{formatNumber(totalStars)}</div>
        </div>
      </div>

      {/* Sources Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th 
                className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('source')}
              >
                <div className="flex items-center">
                  Source
                  <SortIcon columnKey="source" />
                </div>
              </th>
              <th 
                className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('user_count')}
              >
                <div className="flex items-center">
                  Users
                  <SortIcon columnKey="user_count" />
                </div>
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                New Users (14d)
              </th>
              <th 
                className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('total_purchases')}
              >
                <div className="flex items-center">
                  Purchases
                  <SortIcon columnKey="total_purchases" />
                </div>
              </th>
              <th 
                className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('total_stars')}
              >
                <div className="flex items-center">
                  Stars
                  <SortIcon columnKey="total_stars" />
                </div>
              </th>
              <th 
                className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('total_events')}
              >
                <div className="flex items-center">
                  Events
                  <SortIcon columnKey="total_events" />
                </div>
              </th>
              <th 
                className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('avg_events_per_user')}
              >
                <div className="flex items-center">
                  Avg Events
                  <SortIcon columnKey="avg_events_per_user" />
                </div>
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                % Users
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {sortedSources.map((source, index) => {
              const userPercentage = totalUsers > 0 ? ((source.user_count / totalUsers) * 100).toFixed(1) : 0;
              const starsPercentage = totalStars > 0 ? ((source.total_stars / totalStars) * 100).toFixed(1) : 0;
              
              return (
                <tr key={index} className="hover:bg-gray-50">
                  <td className="px-4 py-4 whitespace-nowrap">
                    <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800">
                      {source.source}
                    </span>
                  </td>
                  <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-900 font-medium">
                    {formatNumber(source.user_count)}
                  </td>
                  <td className="px-4 py-4 whitespace-nowrap">
                    <Sparkline data={source.sparkline_data} />
                  </td>
                  <td className="px-4 py-4 whitespace-nowrap text-sm font-medium text-green-600">
                    {formatNumber(source.total_purchases || 0)}
                  </td>
                  <td className="px-4 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <span className="text-sm font-medium text-yellow-600 mr-2">
                        {formatNumber(source.total_stars || 0)}
                      </span>
                      {source.total_stars > 0 && (
                        <span className="text-xs text-gray-400">
                          ({starsPercentage}%)
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-500">
                    {formatNumber(source.total_events)}
                  </td>
                  <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-500">
                    {source.avg_events_per_user}
                  </td>
                  <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-500">
                    <div className="flex items-center">
                      <div className="flex-1 h-2 bg-gray-200 rounded-full mr-2 w-16">
                        <div 
                          className="h-2 bg-blue-500 rounded-full" 
                          style={{ width: `${userPercentage}%` }}
                        ></div>
                      </div>
                      <span className="w-12 text-right">{userPercentage}%</span>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {sources.length === 0 && (
        <div className="text-center py-12 text-gray-500">
          No acquisition source data available
        </div>
      )}
    </div>
  );
}

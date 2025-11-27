import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import TimeSeriesChart from './TimeSeriesChart';

export default function UserMessageStats() {
  // Default to today
  const [date, setDate] = useState(new Date().toISOString().split('T')[0]);
  const [users, setUsers] = useState([]);
  const [chartData, setChartData] = useState([]);
  const [totalScheduled, setTotalScheduled] = useState(0);
  const [loading, setLoading] = useState(false);
  const [sortConfig, setSortConfig] = useState({ key: 'estimated_cost', direction: 'desc' });

  useEffect(() => {
    loadData();
  }, [date]);

  const loadData = async () => {
    setLoading(true);
    try {
      // Fetch table data
      const stats = await api.getDailyUserStats(date);
      setUsers(stats);
      
      // Calculate total scheduled messages for summary
      const totalSched = stats.reduce((acc, u) => acc + (u.scheduled_messages || 0), 0);
      setTotalScheduled(totalSched);

      // Fetch chart data (global user messages for that day, hourly)
      // We use existing endpoint but filter for the specific day
      const chart = await api.getUserMessagesOverTime('1h', date, date);
      
      // Format chart data for TimeSeriesChart
      // The API returns { timestamp, count }
      const formattedChart = chart.map(item => ({
        timestamp: item.timestamp,
        count: item.count
      }));
      setChartData(formattedChart);
    } catch (e) {
      console.error("Error loading stats:", e);
    }
    setLoading(false);
  };

  const handleSort = (key) => {
    let direction = 'asc';
    if (sortConfig.key === key && sortConfig.direction === 'asc') {
      direction = 'desc';
    }
    setSortConfig({ key, direction });
  };

  const getSortedUsers = () => {
    const sorted = [...users];
    sorted.sort((a, b) => {
      let aValue = a[sortConfig.key];
      let bValue = b[sortConfig.key];

      if (aValue === null || aValue === undefined) return 1;
      if (bValue === null || bValue === undefined) return -1;

      if (aValue < bValue) return sortConfig.direction === 'asc' ? -1 : 1;
      if (aValue > bValue) return sortConfig.direction === 'asc' ? 1 : -1;
      return 0;
    });
    return sorted;
  };

  const SortIcon = ({ columnKey }) => {
    if (sortConfig.key !== columnKey) return <span className="text-gray-300 ml-1">↕</span>;
    return <span className="ml-1">{sortConfig.direction === 'asc' ? '↑' : '↓'}</span>;
  };

  const sortedUsers = getSortedUsers();
  const totalCost = users.reduce((acc, u) => acc + (u.estimated_cost || 0), 0);

  return (
    <div className="p-8">
      <div className="mb-8 flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-800">User Message Statistics</h1>
        <div className="flex items-center gap-4">
            <label className="font-medium text-gray-700">Date:</label>
            <input 
                type="date" 
                value={date}
                onChange={(e) => setDate(e.target.value)}
                className="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
        </div>
      </div>

      {/* Top Charts / Summary */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <div className="lg:col-span-2">
            <TimeSeriesChart 
                data={chartData} 
                title={`User Messages Sent (${date})`} 
                height={300}
            />
        </div>
        <div className="space-y-6">
             {/* Summary Card: Cost */}
            <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold text-gray-700 mb-2">Total Estimated Cost</h3>
                <div className="text-4xl font-bold text-green-600">
                    ${totalCost.toFixed(4)}
                </div>
                <p className="text-sm text-gray-500 mt-1">for {date}</p>
            </div>

            {/* Summary Card: Scheduled Messages */}
            <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold text-gray-700 mb-2">Scheduled Messages Sent</h3>
                <div className="text-4xl font-bold text-purple-600">
                    {totalScheduled}
                </div>
                <p className="text-sm text-gray-500 mt-1">Auto-followups for {date}</p>
            </div>
        </div>
      </div>

      {/* Users Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-xl font-semibold text-gray-800">Users Detail</h3>
        </div>
        
        {loading ? (
            <div className="p-8 text-center text-gray-500">Loading data...</div>
        ) : (
            <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                        <tr>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100" onClick={() => handleSort('user_id')}>
                                <div className="flex items-center">User <SortIcon columnKey="user_id"/></div>
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100" onClick={() => handleSort('user_messages')}>
                                <div className="flex items-center">User Messages <SortIcon columnKey="user_messages"/></div>
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100" onClick={() => handleSort('scheduled_messages')}>
                                <div className="flex items-center">Scheduled Msgs <SortIcon columnKey="scheduled_messages"/></div>
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100" onClick={() => handleSort('estimated_cost')}>
                                <div className="flex items-center">Est. Cost <SortIcon columnKey="estimated_cost"/></div>
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100" onClick={() => handleSort('is_premium')}>
                                <div className="flex items-center">Premium <SortIcon columnKey="is_premium"/></div>
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Actions
                            </th>
                        </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                        {sortedUsers.map((user) => (
                            <tr key={user.user_id} className="hover:bg-gray-50">
                                <td className="px-6 py-4 whitespace-nowrap">
                                    <div className="flex items-center">
                                        <div className="flex-shrink-0 h-10 w-10 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 font-bold">
                                            {(user.first_name || user.username || 'U')[0].toUpperCase()}
                                        </div>
                                        <div className="ml-4">
                                            <div className="text-sm font-medium text-gray-900">
                                                {user.first_name || 'Unknown'}
                                            </div>
                                            <div className="text-sm text-gray-500">
                                                @{user.username || 'no_username'} (ID: {user.user_id})
                                            </div>
                                        </div>
                                    </div>
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                    {user.user_messages}
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                    {user.scheduled_messages}
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-green-600">
                                    ${(user.estimated_cost || 0).toFixed(4)}
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                    {user.is_premium ? (
                                        <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-yellow-100 text-yellow-800">
                                            Premium
                                        </span>
                                    ) : (
                                        <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-gray-100 text-gray-800">
                                            Free
                                        </span>
                                    )}
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                                    <Link to={`/users/${user.user_id}`} className="text-blue-600 hover:text-blue-900">
                                        Timeline
                                    </Link>
                                </td>
                            </tr>
                        ))}
                        {sortedUsers.length === 0 && (
                            <tr>
                                <td colSpan="6" className="px-6 py-4 text-center text-gray-500">
                                    No activity found for this date.
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        )}
      </div>
    </div>
  );
}







import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';
import { formatDate } from '../utils';
import Sparkline from './Sparkline';

export default function Users() {
  const [users, setUsers] = useState([]);
  const [totalUsers, setTotalUsers] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState(null);
  const [sortConfig, setSortConfig] = useState({ key: 'first_activity', direction: 'desc' });
  const [searchQuery, setSearchQuery] = useState('');
  const [deletingUserId, setDeletingUserId] = useState(null);
  const [hasMore, setHasMore] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchUsers = async (append = false) => {
    try {
      if (append) {
        setLoadingMore(true);
      } else {
        setLoading(true);
      }
      
      const offset = append ? users.length : 0;
      const limit = 500; // Fetch 500 users at a time
      
      const data = await api.getUsers(limit, offset);
      
      if (append) {
        setUsers(prev => [...prev, ...data.users]);
      } else {
        setUsers(data.users);
      }
      
      setTotalUsers(data.total);
      setHasMore(data.users.length === limit);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  };

  const loadMoreUsers = () => {
    if (!loadingMore && hasMore) {
      fetchUsers(true);
    }
  };

  const handleDeleteChats = async (userId, userName) => {
    if (!confirm(`Are you sure you want to delete all chats and messages for ${userName || userId}? This action cannot be undone.`)) {
      return;
    }

    try {
      setDeletingUserId(userId);
      const result = await api.deleteUserChats(userId);
      alert(result.message);
      // Refresh users list after deletion
      await fetchUsers();
    } catch (err) {
      alert(`Error: ${err.message}`);
    } finally {
      setDeletingUserId(null);
    }
  };

  const handleSort = (key) => {
    let direction = 'asc';
    if (sortConfig.key === key && sortConfig.direction === 'asc') {
      direction = 'desc';
    }
    setSortConfig({ key, direction });
  };

  const getFilteredAndSortedUsers = () => {
    // Filter users based on search query
    let filteredUsers = users.filter(user => {
      if (!searchQuery) return true;
      
      const query = searchQuery.toLowerCase();
      const firstName = (user.first_name || '').toLowerCase();
      const username = (user.username || '').toLowerCase();
      const clientId = user.client_id.toString();
      const acquisitionSource = (user.acquisition_source || '').toLowerCase();
      
      return firstName.includes(query) || 
             username.includes(query) || 
             clientId.includes(query) ||
             acquisitionSource.includes(query);
    });

    // Sort filtered users
    filteredUsers.sort((a, b) => {
      let aValue = a[sortConfig.key];
      let bValue = b[sortConfig.key];

      // Handle null values
      if (aValue === null || aValue === undefined) return 1;
      if (bValue === null || bValue === undefined) return -1;

      // For dates and numbers, convert to comparable values
      if (sortConfig.key === 'first_activity' || sortConfig.key === 'last_activity' || sortConfig.key === 'last_message_send') {
        aValue = new Date(aValue).getTime();
        bValue = new Date(bValue).getTime();
      }

      if (aValue < bValue) {
        return sortConfig.direction === 'asc' ? -1 : 1;
      }
      if (aValue > bValue) {
        return sortConfig.direction === 'asc' ? 1 : -1;
      }
      return 0;
    });
    
    return filteredUsers;
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

  const filteredUsers = getFilteredAndSortedUsers();

  return (
    <div className="p-8">
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-3xl font-bold text-gray-800">Users</h2>
            <p className="text-gray-500 mt-1">
              {searchQuery ? (
                <>
                  {filteredUsers.length} matching users (of {users.length} loaded, {totalUsers} total)
                </>
              ) : (
                <>
                  Showing {users.length} of {totalUsers} total users
                </>
              )}
            </p>
          </div>
          <div className="w-96">
            <input
              type="text"
              placeholder="Search by name, username, ID, or source..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                User
              </th>
              <th 
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('client_id')}
              >
                <div className="flex items-center">
                  User ID
                  <SortIcon columnKey="client_id" />
                </div>
              </th>
              <th 
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('acquisition_source')}
              >
                <div className="flex items-center">
                  Acquisition Source
                  <SortIcon columnKey="acquisition_source" />
                </div>
              </th>
              <th 
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('total_events')}
              >
                <div className="flex items-center">
                  Total Events
                  <SortIcon columnKey="total_events" />
                </div>
              </th>
              <th 
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('message_events_count')}
              >
                <div className="flex items-center">
                  Send Message Events
                  <SortIcon columnKey="message_events_count" />
                </div>
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Activity (14d)
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Activity Send Message
              </th>
              <th 
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('consecutive_days_streak')}
              >
                <div className="flex items-center">
                  Streak
                  <SortIcon columnKey="consecutive_days_streak" />
                </div>
              </th>
              <th 
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('first_activity')}
              >
                <div className="flex items-center">
                  First Activity
                  <SortIcon columnKey="first_activity" />
                </div>
              </th>
              <th 
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('last_activity')}
              >
                <div className="flex items-center">
                  Last Activity
                  <SortIcon columnKey="last_activity" />
                </div>
              </th>
              <th 
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('last_message_send')}
              >
                <div className="flex items-center">
                  Last Message Send
                  <SortIcon columnKey="last_message_send" />
                </div>
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {filteredUsers.map((user) => (
              <tr key={user.client_id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center">
                    <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center mr-3">
                      <span className="text-blue-600 font-bold">
                        {(user.first_name || user.username || 'U')[0].toUpperCase()}
                      </span>
                    </div>
                    <div>
                      <div className="text-sm font-medium text-gray-900">
                        {user.first_name || 'Unknown'}
                      </div>
                      {user.username && (
                        <div className="text-sm text-gray-500">@{user.username}</div>
                      )}
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {user.client_id}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {user.acquisition_source ? (
                    <span 
                      className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800"
                      title={user.acquisition_timestamp ? `Acquired: ${formatDate(user.acquisition_timestamp)}` : 'Acquisition source'}
                    >
                      {user.acquisition_source}
                    </span>
                  ) : (
                    <span className="text-gray-400 italic">direct</span>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {user.total_events}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {user.message_events_count}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <Sparkline data={user.sparkline_data} />
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <Sparkline data={user.message_sparkline_data} />
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {user.consecutive_days_streak > 0 ? (
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-orange-100 text-orange-800">
                      {user.consecutive_days_streak} {user.consecutive_days_streak === 1 ? 'day' : 'days'}
                    </span>
                  ) : (
                    <span className="text-gray-400">-</span>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {user.first_activity ? formatDate(user.first_activity) : 'N/A'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {user.last_activity ? formatDate(user.last_activity) : 'N/A'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {user.last_message_send ? formatDate(user.last_message_send) : 'N/A'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">
                  <div className="flex items-center gap-3">
                    <button
                      onClick={() => navigate(`/users/${user.client_id}`)}
                      className="text-blue-600 hover:text-blue-800 font-medium"
                    >
                      View Timeline
                    </button>
                    <button
                      onClick={() => handleDeleteChats(user.client_id, user.first_name || user.username)}
                      disabled={deletingUserId === user.client_id}
                      className="text-red-600 hover:text-red-800 font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                      title="Delete all chats and messages for this user"
                    >
                      {deletingUserId === user.client_id ? 'Deleting...' : '🗑️ Delete Chats'}
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Load More Button */}
      {hasMore && !searchQuery && (
        <div className="mt-6 flex justify-center">
          <button
            onClick={loadMoreUsers}
            disabled={loadingMore}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loadingMore ? 'Loading...' : `Load More Users (${totalUsers - users.length} remaining)`}
          </button>
        </div>
      )}

      {/* No More Users Message */}
      {!hasMore && users.length > 0 && !searchQuery && (
        <div className="mt-6 text-center text-gray-500">
          All {totalUsers} users loaded
        </div>
      )}
    </div>
  );
}





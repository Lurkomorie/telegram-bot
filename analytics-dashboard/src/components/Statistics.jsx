import { useEffect, useState } from 'react';
import { api } from '../api';
import { formatNumber } from '../utils';

export default function Statistics() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      setLoading(true);
      const data = await api.getStats();
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
    { label: 'Total Users', value: stats.total_users, icon: '👥', color: 'blue' },
    { label: 'Total Messages', value: stats.total_messages, icon: '💬', color: 'green' },
    { label: 'Total Images', value: stats.total_images, icon: '🖼️', color: 'purple' },
    { label: 'Active Users (7d)', value: stats.active_users_7d, icon: '⚡', color: 'yellow' },
    { label: 'Total Events', value: stats.total_events, icon: '📊', color: 'indigo' },
    { label: 'Avg Messages/User', value: stats.avg_messages_per_user.toFixed(1), icon: '📈', color: 'pink' }
  ];

  return (
    <div className="p-8">
      <div className="mb-8">
        <h2 className="text-3xl font-bold text-gray-800">Statistics</h2>
        <p className="text-gray-500 mt-1">Overview of bot analytics</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
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

      {stats.popular_personas && stats.popular_personas.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-xl font-bold text-gray-800 mb-4">Popular Personas</h3>
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-2 px-2 text-sm font-medium text-gray-500">#</th>
                  <th className="text-left py-2 px-3 text-sm font-medium text-gray-500">Persona</th>
                  <th className="text-right py-2 px-3 text-sm font-medium text-gray-500">Users</th>
                  <th className="text-right py-2 px-3 text-sm font-medium text-gray-500">Interactions</th>
                </tr>
              </thead>
              <tbody>
                {stats.popular_personas.map((persona, index) => (
                  <tr key={index} className="border-b last:border-b-0 hover:bg-gray-50">
                    <td className="py-3 px-2">
                      <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                        <span className="text-blue-600 font-bold text-sm">{index + 1}</span>
                      </div>
                    </td>
                    <td className="py-3 px-3">
                      <span className="font-medium text-gray-700">{persona.name}</span>
                    </td>
                    <td className="py-3 px-3 text-right">
                      <span className="text-gray-600 font-medium">{formatNumber(persona.user_count)}</span>
                      <span className="text-xs text-gray-400 ml-1">users</span>
                    </td>
                    <td className="py-3 px-3 text-right">
                      <span className="text-gray-600">{formatNumber(persona.interaction_count)}</span>
                      <span className="text-xs text-gray-400 ml-1">total</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}


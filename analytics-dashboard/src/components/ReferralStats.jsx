import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../api';
import { formatNumber } from '../utils';
import TimeSeriesChart from './TimeSeriesChart';
import MultiLineChart from './MultiLineChart';
import PieChartComponent from './PieChartComponent';
import HeatmapChart from './HeatmapChart';
import TimeRangeSelector from './TimeRangeSelector';
import DateRangeFilter from './DateRangeFilter';

const TIME_INTERVAL_OPTIONS = [
  { value: '1m', label: '1 minute' },
  { value: '5m', label: '5 minutes' },
  { value: '15m', label: '15 minutes' },
  { value: '30m', label: '30 minutes' },
  { value: '1h', label: '1 hour' },
  { value: '6h', label: '6 hours' },
  { value: '12h', label: '12 hours' },
  { value: '1d', label: '1 day' },
];

const PERIOD_OPTIONS = [
  { value: '7d', label: '7 days' },
  { value: '30d', label: '30 days' },
  { value: '90d', label: '90 days' },
];

export default function ReferralStats() {
  const { sourceName } = useParams();

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
  const [premiumStats, setPremiumStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Time-series data states
  const [messagesInterval, setMessagesInterval] = useState('1h');
  const [messagesData, setMessagesData] = useState([]);
  const [messagesLoading, setMessagesLoading] = useState(true);

  const [userMessagesInterval, setUserMessagesInterval] = useState('1h');
  const [userMessagesData, setUserMessagesData] = useState([]);
  const [userMessagesLoading, setUserMessagesLoading] = useState(true);

  const [scheduledInterval, setScheduledInterval] = useState('1h');
  const [scheduledData, setScheduledData] = useState([]);
  const [scheduledLoading, setScheduledLoading] = useState(true);

  const [activeUsersPeriod, setActiveUsersPeriod] = useState('7d');
  const [activeUsersData, setActiveUsersData] = useState([]);
  const [activeUsersLoading, setActiveUsersLoading] = useState(true);

  const [personaData, setPersonaData] = useState([]);
  const [personaLoading, setPersonaLoading] = useState(true);

  const [imagesPeriod, setImagesPeriod] = useState('7d');
  const [imagesData, setImagesData] = useState([]);
  const [imagesLoading, setImagesLoading] = useState(true);

  const [heatmapData, setHeatmapData] = useState([]);
  const [heatmapLoading, setHeatmapLoading] = useState(true);

  const [imageWaitingInterval, setImageWaitingInterval] = useState('1h');
  const [imageWaitingData, setImageWaitingData] = useState([]);
  const [imageWaitingLoading, setImageWaitingLoading] = useState(true);

  useEffect(() => {
    fetchStats();
    fetchPremiumStats();
    fetchPersonaData();
    fetchHeatmapData();
  }, [startDate, endDate, sourceName]);

  useEffect(() => {
    fetchMessagesData();
  }, [messagesInterval, startDate, endDate, sourceName]);

  useEffect(() => {
    fetchUserMessagesData();
  }, [userMessagesInterval, startDate, endDate, sourceName]);

  useEffect(() => {
    fetchScheduledData();
  }, [scheduledInterval, startDate, endDate, sourceName]);

  useEffect(() => {
    fetchActiveUsersData();
  }, [activeUsersPeriod, startDate, endDate, sourceName]);

  useEffect(() => {
    fetchImagesData();
  }, [imagesPeriod, startDate, endDate, sourceName]);

  useEffect(() => {
    fetchImageWaitingData();
  }, [imageWaitingInterval, startDate, endDate, sourceName]);

  const fetchStats = async () => {
    try {
      setLoading(true);
      const data = await api.getStats(startDate, endDate, sourceName);
      setStats(data);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchPremiumStats = async () => {
    try {
      const data = await api.getPremiumStats(startDate, endDate, sourceName);
      setPremiumStats(data);
    } catch (err) {
      console.error('Error fetching premium stats:', err);
    }
  };

  const fetchMessagesData = async () => {
    try {
      setMessagesLoading(true);
      const data = await api.getMessagesOverTime(messagesInterval, startDate, endDate, sourceName);
      setMessagesData(data);
    } catch (err) {
      console.error('Error fetching messages data:', err);
    } finally {
      setMessagesLoading(false);
    }
  };

  const fetchUserMessagesData = async () => {
    try {
      setUserMessagesLoading(true);
      const data = await api.getUserMessagesOverTime(userMessagesInterval, startDate, endDate, sourceName);
      setUserMessagesData(data);
    } catch (err) {
      console.error('Error fetching user messages data:', err);
    } finally {
      setUserMessagesLoading(false);
    }
  };

  const fetchScheduledData = async () => {
    try {
      setScheduledLoading(true);
      const data = await api.getScheduledMessagesOverTime(scheduledInterval, startDate, endDate, sourceName);
      setScheduledData(data);
    } catch (err) {
      console.error('Error fetching scheduled messages data:', err);
    } finally {
      setScheduledLoading(false);
    }
  };

  const fetchActiveUsersData = async () => {
    try {
      setActiveUsersLoading(true);
      const data = await api.getActiveUsersOverTime(activeUsersPeriod, startDate, endDate, sourceName);
      setActiveUsersData(data);
    } catch (err) {
      console.error('Error fetching active users data:', err);
    } finally {
      setActiveUsersLoading(false);
    }
  };

  const fetchPersonaData = async () => {
    try {
      setPersonaLoading(true);
      const data = await api.getMessagesByPersona(startDate, endDate, sourceName);
      setPersonaData(data);
    } catch (err) {
      console.error('Error fetching persona data:', err);
    } finally {
      setPersonaLoading(false);
    }
  };

  const fetchImagesData = async () => {
    try {
      setImagesLoading(true);
      const data = await api.getImagesOverTime(imagesPeriod, startDate, endDate, sourceName);
      setImagesData(data);
    } catch (err) {
      console.error('Error fetching images data:', err);
    } finally {
      setImagesLoading(false);
    }
  };

  const fetchHeatmapData = async () => {
    try {
      setHeatmapLoading(true);
      const data = await api.getEngagementHeatmap(startDate, endDate, sourceName);
      setHeatmapData(data);
    } catch (err) {
      console.error('Error fetching heatmap data:', err);
    } finally {
      setHeatmapLoading(false);
    }
  };

  const fetchImageWaitingData = async () => {
    try {
      setImageWaitingLoading(true);
      const data = await api.getImageWaitingTime(imageWaitingInterval, startDate, endDate, sourceName);
      setImageWaitingData(data);
    } catch (err) {
      console.error('Error fetching image waiting time data:', err);
      setImageWaitingData([]);
    } finally {
      setImageWaitingLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-100">
        <div className="text-gray-500">Loading...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-100">
        <div className="text-red-500">Error: {error}</div>
      </div>
    );
  }

  // Format waiting time for display
  const formatWaitingTime = (seconds) => {
    if (seconds === 0) return '0s';
    if (seconds < 60) return `${seconds.toFixed(1)}s`;
    const minutes = seconds / 60;
    if (minutes < 60) return `${minutes.toFixed(1)}min`;
    const hours = minutes / 60;
    return `${hours.toFixed(1)}h`;
  };

  const statCards = [
    { label: 'Total Users', value: stats.total_users, icon: '👥', color: 'blue' },
    { label: 'Total Messages', value: stats.total_messages, icon: '💬', color: 'green' },
    { label: 'Total Images', value: stats.total_images, icon: '🖼️', color: 'purple' },
    { label: 'Active Users (7d)', value: stats.active_users_7d, icon: '⚡', color: 'yellow' },
    { label: 'Total Events', value: stats.total_events, icon: '📊', color: 'indigo' },
    { label: 'Avg Messages/User', value: stats.avg_messages_per_user.toFixed(1), icon: '📈', color: 'pink' },
    { label: 'Avg Image Wait Time', value: formatWaitingTime(stats.avg_image_waiting_time), icon: '⏱️', color: 'teal' },
    { label: 'Failed Images', value: stats.failed_images_count, icon: '❌', color: 'red' }
  ];

  const premiumCards = premiumStats ? [
    { label: 'Active Premium Users', value: premiumStats.total_premium_users, icon: '👑', color: 'yellow' },
    { label: 'Total Premium Purchases', value: premiumStats.total_ever_premium_users, icon: '💎', color: 'purple' },
    { label: 'Total Free Users', value: premiumStats.total_free_users, icon: '👥', color: 'blue' },
    { label: 'Conversion Rate', value: `${premiumStats.conversion_rate}%`, icon: '📈', color: 'green' },
  ] : [];

  return (
    <div className="min-h-screen bg-gray-100 p-8">
      <div className="mb-8">
        <h2 className="text-3xl font-bold text-gray-800">Referral Analytics: {sourceName}</h2>
        <p className="text-gray-500 mt-1">Complete analytics overview for acquisition source</p>
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

      {/* Premium Stats Cards */}
      {premiumStats && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {premiumCards.map((stat, index) => (
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
      )}

      {/* Messages Over Time */}
      <div className="mb-8">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xl font-bold text-gray-800">Messages Over Time</h3>
            <TimeRangeSelector
              value={messagesInterval}
              onChange={setMessagesInterval}
              options={TIME_INTERVAL_OPTIONS}
              label="Interval"
            />
          </div>
          {messagesLoading ? (
            <div className="flex items-center justify-center h-64">
              <div className="text-gray-400">Loading...</div>
            </div>
          ) : (
            <TimeSeriesChart data={messagesData} title="" color="#10b981" height={300} />
          )}
        </div>
      </div>

      {/* User Sent Messages Over Time */}
      <div className="mb-8">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xl font-bold text-gray-800">User Sent Messages Over Time</h3>
            <TimeRangeSelector
              value={userMessagesInterval}
              onChange={setUserMessagesInterval}
              options={TIME_INTERVAL_OPTIONS}
              label="Interval"
            />
          </div>
          {userMessagesLoading ? (
            <div className="flex items-center justify-center h-64">
              <div className="text-gray-400">Loading...</div>
            </div>
          ) : (
            <TimeSeriesChart data={userMessagesData} title="" color="#3b82f6" height={300} />
          )}
        </div>
      </div>

      {/* Scheduled Messages Over Time */}
      <div className="mb-8">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xl font-bold text-gray-800">Scheduled Messages Over Time</h3>
            <TimeRangeSelector
              value={scheduledInterval}
              onChange={setScheduledInterval}
              options={TIME_INTERVAL_OPTIONS}
              label="Interval"
            />
          </div>
          {scheduledLoading ? (
            <div className="flex items-center justify-center h-64">
              <div className="text-gray-400">Loading...</div>
            </div>
          ) : (
            <TimeSeriesChart data={scheduledData} title="" color="#f59e0b" height={300} />
          )}
        </div>
      </div>

      {/* Active Users and Images - Side by Side */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Active Users Over Time */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xl font-bold text-gray-800">Active Users Over Time</h3>
            <TimeRangeSelector
              value={activeUsersPeriod}
              onChange={setActiveUsersPeriod}
              options={PERIOD_OPTIONS}
              label="Period"
            />
          </div>
          {activeUsersLoading ? (
            <div className="flex items-center justify-center h-64">
              <div className="text-gray-400">Loading...</div>
            </div>
          ) : (
            <TimeSeriesChart data={activeUsersData} title="" color="#3b82f6" height={250} />
          )}
        </div>

        {/* Images Over Time */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xl font-bold text-gray-800">Images Generated Over Time</h3>
            <TimeRangeSelector
              value={imagesPeriod}
              onChange={setImagesPeriod}
              options={PERIOD_OPTIONS}
              label="Period"
            />
          </div>
          {imagesLoading ? (
            <div className="flex items-center justify-center h-64">
              <div className="text-gray-400">Loading...</div>
            </div>
          ) : (
            <TimeSeriesChart data={imagesData} title="" color="#8b5cf6" height={250} />
          )}
        </div>
      </div>

      {/* Messages by Persona - Pie Chart */}
      <div className="mb-8">
        {personaLoading ? (
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-xl font-bold text-gray-800 mb-4">Messages by Persona</h3>
            <div className="flex items-center justify-center h-64">
              <div className="text-gray-400">Loading...</div>
            </div>
          </div>
        ) : (
          <PieChartComponent data={personaData} title="Messages by Persona" height={400} />
        )}
      </div>

      {/* Popular Personas Table */}
      {stats.popular_personas && stats.popular_personas.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6 mb-8">
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

      {/* Engagement Heatmap */}
      <div className="mb-8">
        {heatmapLoading ? (
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-xl font-bold text-gray-800 mb-4">Engagement Heatmap</h3>
            <div className="flex items-center justify-center h-64">
              <div className="text-gray-400">Loading...</div>
            </div>
          </div>
        ) : (
          <HeatmapChart data={heatmapData} title="Engagement Heatmap" />
        )}
      </div>

      {/* Image Generation Waiting Time */}
      <div className="mb-8">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xl font-bold text-gray-800">Image Generation Waiting Time Over Time</h3>
            <TimeRangeSelector
              value={imageWaitingInterval}
              onChange={setImageWaitingInterval}
              options={TIME_INTERVAL_OPTIONS}
              label="Interval"
            />
          </div>
          {imageWaitingLoading ? (
            <div className="flex items-center justify-center h-64">
              <div className="text-gray-400">Loading...</div>
            </div>
          ) : (
            <MultiLineChart 
              data={imageWaitingData} 
              title="" 
              height={300}
              yAxisLabel="Waiting Time"
            />
          )}
        </div>
      </div>

      {/* Premium Stats Sections */}
      {premiumStats && (
        <>
          {/* Premium Users Over Time */}
          <div className="mb-8">
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-xl font-bold text-gray-800 mb-4">Premium Purchases Over Time (All Time)</h3>
              {premiumStats.premium_users_over_time && premiumStats.premium_users_over_time.length > 0 ? (
                <TimeSeriesChart 
                  data={premiumStats.premium_users_over_time.map(item => ({ timestamp: item.date, count: item.count }))} 
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
                      {formatNumber(premiumStats.premium_vs_free_images.premium)}
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-3">
                    <div 
                      className="bg-yellow-500 h-3 rounded-full" 
                      style={{ 
                        width: `${(premiumStats.premium_vs_free_images.premium / (premiumStats.premium_vs_free_images.premium + premiumStats.premium_vs_free_images.free) * 100)}%` 
                      }}
                    ></div>
                  </div>
                </div>
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-gray-600">Free Users</span>
                    <span className="text-lg font-bold text-blue-600">
                      {formatNumber(premiumStats.premium_vs_free_images.free)}
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-3">
                    <div 
                      className="bg-blue-500 h-3 rounded-full" 
                      style={{ 
                        width: `${(premiumStats.premium_vs_free_images.free / (premiumStats.premium_vs_free_images.premium + premiumStats.premium_vs_free_images.free) * 100)}%` 
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
                      {formatNumber(premiumStats.premium_vs_free_engagement.premium.user_count)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between mt-1">
                    <span className="text-xs text-gray-500">Avg Messages:</span>
                    <span className="text-sm font-bold text-yellow-600">
                      {premiumStats.premium_vs_free_engagement.premium.avg_messages.toFixed(1)}
                    </span>
                  </div>
                </div>
                <div className="border-t pt-4">
                  <div className="text-sm font-medium text-gray-600 mb-1">Free Users</div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-gray-500">Active Users:</span>
                    <span className="text-sm font-bold text-blue-600">
                      {formatNumber(premiumStats.premium_vs_free_engagement.free.user_count)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between mt-1">
                    <span className="text-xs text-gray-500">Avg Messages:</span>
                    <span className="text-sm font-bold text-blue-600">
                      {premiumStats.premium_vs_free_engagement.free.avg_messages.toFixed(1)}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}


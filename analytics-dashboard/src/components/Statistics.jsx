import { useEffect, useState } from 'react';
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

export default function Statistics() {
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

  const [voicesPeriod, setVoicesPeriod] = useState('7d');
  const [voicesData, setVoicesData] = useState([]);
  const [voicesLoading, setVoicesLoading] = useState(true);

  const [heatmapData, setHeatmapData] = useState([]);
  const [heatmapLoading, setHeatmapLoading] = useState(true);

  const [imageWaitingInterval, setImageWaitingInterval] = useState('1h');
  const [imageWaitingData, setImageWaitingData] = useState([]);
  const [imageWaitingLoading, setImageWaitingLoading] = useState(true);

  useEffect(() => {
    fetchStats();
    fetchPersonaData();
    fetchHeatmapData();
  }, [startDate, endDate]);

  useEffect(() => {
    fetchMessagesData();
  }, [messagesInterval, startDate, endDate]);

  useEffect(() => {
    fetchUserMessagesData();
  }, [userMessagesInterval, startDate, endDate]);

  useEffect(() => {
    fetchScheduledData();
  }, [scheduledInterval, startDate, endDate]);

  useEffect(() => {
    fetchActiveUsersData();
  }, [activeUsersPeriod, startDate, endDate]);

  useEffect(() => {
    fetchImagesData();
  }, [imagesPeriod, startDate, endDate]);

  useEffect(() => {
    fetchVoicesData();
  }, [voicesPeriod, startDate, endDate]);

  useEffect(() => {
    fetchImageWaitingData();
  }, [imageWaitingInterval, startDate, endDate]);

  const fetchStats = async () => {
    try {
      setLoading(true);
      const data = await api.getStats(startDate, endDate);
      setStats(data);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchMessagesData = async () => {
    try {
      setMessagesLoading(true);
      const data = await api.getMessagesOverTime(messagesInterval, startDate, endDate);
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
      const data = await api.getUserMessagesOverTime(userMessagesInterval, startDate, endDate);
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
      const data = await api.getScheduledMessagesOverTime(scheduledInterval, startDate, endDate);
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
      const data = await api.getActiveUsersOverTime(activeUsersPeriod, startDate, endDate);
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
      const data = await api.getMessagesByPersona(startDate, endDate);
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
      const data = await api.getImagesOverTime(imagesPeriod, startDate, endDate);
      setImagesData(data);
    } catch (err) {
      console.error('Error fetching images data:', err);
    } finally {
      setImagesLoading(false);
    }
  };

  const fetchVoicesData = async () => {
    try {
      setVoicesLoading(true);
      const data = await api.getVoicesOverTime(voicesPeriod, startDate, endDate);
      setVoicesData(data);
    } catch (err) {
      console.error('Error fetching voices data:', err);
    } finally {
      setVoicesLoading(false);
    }
  };

  const fetchHeatmapData = async () => {
    try {
      setHeatmapLoading(true);
      const data = await api.getEngagementHeatmap(startDate, endDate);
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
      const data = await api.getImageWaitingTime(imageWaitingInterval, startDate, endDate);
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

  // Format waiting time for display
  const formatWaitingTime = (seconds) => {
    if (seconds === 0) return '0s';
    if (seconds < 60) return `${seconds.toFixed(1)}s`;
    const minutes = seconds / 60;
    if (minutes < 60) return `${minutes.toFixed(1)}min`;
    const hours = minutes / 60;
    return `${hours.toFixed(1)}h`;
  };

  // Format characters count for display (e.g., 1.2M, 500K)
  const formatCharacters = (chars) => {
    if (chars === 0) return '0';
    if (chars >= 1000000) return `${(chars / 1000000).toFixed(1)}M`;
    if (chars >= 1000) return `${(chars / 1000).toFixed(1)}K`;
    return chars.toString();
  };

  const statCards = [
    { label: 'Total Users', value: stats.total_users, icon: '👥', color: 'blue' },
    { label: 'Total Messages', value: stats.total_messages, icon: '💬', color: 'green' },
    { label: 'Total Images', value: stats.total_images, icon: '🖼️', color: 'purple' },
    { label: 'Total Voices', value: stats.total_voices, icon: '🎤', color: 'orange' },
    { label: 'Voice Characters', value: formatCharacters(stats.total_voice_characters || 0), icon: '📝', color: 'cyan', tooltip: 'ElevenLabs billed characters' },
    { label: 'Active Users (7d)', value: stats.active_users_7d, icon: '⚡', color: 'yellow' },
    { label: 'Total Events', value: stats.total_events, icon: '📊', color: 'indigo' },
    { label: 'Avg Messages/User', value: stats.avg_messages_per_user.toFixed(1), icon: '📈', color: 'pink' },
    { label: 'Avg Image Wait Time', value: formatWaitingTime(stats.avg_image_waiting_time), icon: '⏱️', color: 'teal' },
    { label: 'Failed Images', value: stats.failed_images_count, icon: '❌', color: 'red' }
  ];

  return (
    <div className="p-8">
      <div className="mb-8">
        <h2 className="text-3xl font-bold text-gray-800">Statistics</h2>
        <p className="text-gray-500 mt-1">Overview of bot analytics</p>
      </div>

      {/* Date Range Filter */}
      <DateRangeFilter 
        startDate={startDate}
        endDate={endDate}
        onStartDateChange={setStartDate}
        onEndDateChange={setEndDate}
      />

      {/* Overview Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
        {statCards.map((stat, index) => (
          <div key={index} className="bg-white rounded-lg shadow p-6" title={stat.tooltip || ''}>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-500 text-sm font-medium">{stat.label}</p>
                <p className="text-3xl font-bold text-gray-800 mt-2">
                  {formatNumber(stat.value)}
                </p>
                {stat.tooltip && (
                  <p className="text-xs text-gray-400 mt-1">{stat.tooltip}</p>
                )}
              </div>
              <div className={`text-4xl bg-${stat.color}-100 p-3 rounded-lg`}>
                {stat.icon}
              </div>
            </div>
          </div>
        ))}
      </div>

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

      {/* Active Users, Images and Voices */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
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

        {/* Voices Over Time */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xl font-bold text-gray-800">Voice Messages Over Time</h3>
            <TimeRangeSelector
              value={voicesPeriod}
              onChange={setVoicesPeriod}
              options={PERIOD_OPTIONS}
              label="Period"
            />
          </div>
          {voicesLoading ? (
            <div className="flex items-center justify-center h-64">
              <div className="text-gray-400">Loading...</div>
            </div>
          ) : (
            <TimeSeriesChart data={voicesData} title="" color="#f97316" height={250} />
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
    </div>
  );
}

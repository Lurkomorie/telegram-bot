import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';

export default function MultiLineChart({ data, title, height = 300, yAxisLabel = 'Value' }) {
  if (!data || data.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-xl font-bold text-gray-800 mb-4">{title}</h3>
        <div className="flex items-center justify-center" style={{ height }}>
          <p className="text-gray-400">No data available</p>
        </div>
      </div>
    );
  }

  // Format data for Recharts - convert null values to undefined so they don't show as 0
  const chartData = data.map(item => ({
    time: item.timestamp,
    all: item.avg_waiting_time !== null ? item.avg_waiting_time : undefined,
    premium: item.avg_premium !== null ? item.avg_premium : undefined,
    free: item.avg_free !== null ? item.avg_free : undefined
  }));

  // Format time/date for display
  const formatXAxis = (timeString) => {
    const date = new Date(timeString);
    
    // If data spans multiple days, show date
    const firstDate = new Date(chartData[0].time);
    const lastDate = new Date(chartData[chartData.length - 1].time);
    const daysDiff = (lastDate - firstDate) / (1000 * 60 * 60 * 24);
    
    if (daysDiff > 2) {
      // Show date for multi-day charts
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    } else {
      // Show time for intraday charts
      return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    }
  };

  // Format seconds for display
  const formatSeconds = (seconds) => {
    if (seconds === null || seconds === undefined) return '';
    if (seconds < 60) return `${seconds.toFixed(1)}s`;
    const minutes = seconds / 60;
    if (minutes < 60) return `${minutes.toFixed(1)}min`;
    const hours = minutes / 60;
    return `${hours.toFixed(1)}h`;
  };

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const date = new Date(payload[0].payload.time);
      return (
        <div className="bg-white px-3 py-2 shadow-lg rounded border border-gray-200">
          <p className="text-xs text-gray-500 mb-2">
            {date.toLocaleString('en-US', { 
              month: 'short', 
              day: 'numeric', 
              hour: '2-digit', 
              minute: '2-digit' 
            })}
          </p>
          {payload.map((entry, index) => (
            <p key={index} className="text-sm font-medium" style={{ color: entry.color }}>
              {entry.name}: {formatSeconds(entry.value)}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-xl font-bold text-gray-800 mb-4">{title}</h3>
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis 
            dataKey="time" 
            tickFormatter={formatXAxis}
            tick={{ fontSize: 12 }}
            stroke="#9ca3af"
          />
          <YAxis 
            tick={{ fontSize: 12 }}
            stroke="#9ca3af"
            tickFormatter={formatSeconds}
            label={{ value: yAxisLabel, angle: -90, position: 'insideLeft', style: { fontSize: 12, fill: '#9ca3af' } }}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend 
            wrapperStyle={{ fontSize: '12px' }}
            iconType="line"
          />
          <Line 
            type="monotone" 
            dataKey="all" 
            stroke="#10b981" 
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 6 }}
            name="All Users"
            connectNulls
          />
          <Line 
            type="monotone" 
            dataKey="premium" 
            stroke="#f59e0b" 
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 6 }}
            name="Premium Users"
            connectNulls
          />
          <Line 
            type="monotone" 
            dataKey="free" 
            stroke="#3b82f6" 
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 6 }}
            name="Free Users"
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}


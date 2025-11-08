import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { formatNumber } from '../utils';

export default function TimeSeriesChart({ data, title, color = '#3b82f6', height = 300 }) {
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

  // Format data for Recharts
  const chartData = data.map(item => ({
    time: item.timestamp || item.date,
    value: item.count
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

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const date = new Date(payload[0].payload.time);
      return (
        <div className="bg-white px-3 py-2 shadow-lg rounded border border-gray-200">
          <p className="text-xs text-gray-500 mb-1">
            {date.toLocaleString('en-US', { 
              month: 'short', 
              day: 'numeric', 
              hour: '2-digit', 
              minute: '2-digit' 
            })}
          </p>
          <p className="text-sm font-bold text-gray-800">
            {formatNumber(payload[0].value)} messages
          </p>
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
            tickFormatter={formatNumber}
          />
          <Tooltip content={<CustomTooltip />} />
          <Line 
            type="monotone" 
            dataKey="value" 
            stroke={color} 
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 6 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}



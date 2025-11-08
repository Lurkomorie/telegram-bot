import { formatNumber } from '../utils';

const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const HOURS = Array.from({ length: 24 }, (_, i) => i);

export default function HeatmapChart({ data, title }) {
  if (!data || data.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-xl font-bold text-gray-800 mb-4">{title}</h3>
        <div className="flex items-center justify-center h-64">
          <p className="text-gray-400">No data available</p>
        </div>
      </div>
    );
  }

  // Create a map for quick lookup
  const dataMap = {};
  let maxValue = 0;
  
  data.forEach(item => {
    const key = `${item.day_of_week}-${item.hour}`;
    dataMap[key] = item.count;
    if (item.count > maxValue) maxValue = item.count;
  });

  // Get color intensity based on value
  const getColor = (count) => {
    if (!count) return 'bg-gray-50';
    const intensity = Math.ceil((count / maxValue) * 5);
    
    const colorMap = {
      1: 'bg-blue-100',
      2: 'bg-blue-200',
      3: 'bg-blue-400',
      4: 'bg-blue-600',
      5: 'bg-blue-800'
    };
    
    return colorMap[intensity] || 'bg-blue-50';
  };

  const getTextColor = (count) => {
    if (!count) return 'text-gray-400';
    const intensity = Math.ceil((count / maxValue) * 5);
    return intensity >= 4 ? 'text-white' : 'text-gray-700';
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-xl font-bold text-gray-800 mb-4">{title}</h3>
      <p className="text-sm text-gray-500 mb-4">Message activity by hour and day of week (last 30 days)</p>
      
      <div className="overflow-x-auto">
        <div className="inline-block min-w-full">
          {/* Header with days */}
          <div className="flex items-center mb-2">
            <div className="w-12 flex-shrink-0"></div>
            {DAYS.map((day, idx) => (
              <div key={idx} className="w-16 text-center text-xs font-medium text-gray-600 flex-shrink-0">
                {day}
              </div>
            ))}
          </div>
          
          {/* Rows for each hour */}
          {HOURS.map(hour => (
            <div key={hour} className="flex items-center mb-1">
              <div className="w-12 text-right text-xs text-gray-500 pr-2 flex-shrink-0">
                {hour.toString().padStart(2, '0')}:00
              </div>
              {DAYS.map((_, dayIdx) => {
                const key = `${dayIdx}-${hour}`;
                const count = dataMap[key] || 0;
                const color = getColor(count);
                const textColor = getTextColor(count);
                
                return (
                  <div
                    key={dayIdx}
                    className={`w-16 h-8 flex items-center justify-center text-xs font-medium ${color} ${textColor} rounded mx-0.5 flex-shrink-0 transition-all hover:scale-110 hover:shadow-md cursor-pointer`}
                    title={`${DAYS[dayIdx]} ${hour}:00 - ${formatNumber(count)} messages`}
                  >
                    {count > 0 ? formatNumber(count) : ''}
                  </div>
                );
              })}
            </div>
          ))}
          
          {/* Legend */}
          <div className="flex items-center justify-center mt-6 space-x-2">
            <span className="text-xs text-gray-500">Less</span>
            <div className="w-6 h-6 bg-gray-50 rounded border border-gray-200"></div>
            <div className="w-6 h-6 bg-blue-100 rounded"></div>
            <div className="w-6 h-6 bg-blue-200 rounded"></div>
            <div className="w-6 h-6 bg-blue-400 rounded"></div>
            <div className="w-6 h-6 bg-blue-600 rounded"></div>
            <div className="w-6 h-6 bg-blue-800 rounded"></div>
            <span className="text-xs text-gray-500">More</span>
          </div>
        </div>
      </div>
    </div>
  );
}



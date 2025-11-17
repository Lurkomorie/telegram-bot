export default function DateRangeFilter({ startDate, endDate, onStartDateChange, onEndDateChange }) {
  // Format date for input value (YYYY-MM-DD)
  const formatDateForInput = (date) => {
    return date.toISOString().split('T')[0];
  };

  // Get default dates (last 30 days)
  const getDefaultEndDate = () => {
    return formatDateForInput(new Date());
  };

  const getDefaultStartDate = () => {
    const date = new Date();
    date.setDate(date.getDate() - 30);
    return formatDateForInput(date);
  };

  return (
    <div className="flex items-center space-x-4 bg-white p-4 rounded-lg shadow mb-6">
      <div className="flex items-center space-x-2">
        <label className="text-sm font-medium text-gray-600">From:</label>
        <input
          type="date"
          value={startDate || getDefaultStartDate()}
          onChange={(e) => onStartDateChange(e.target.value)}
          className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
      </div>
      <div className="flex items-center space-x-2">
        <label className="text-sm font-medium text-gray-600">To:</label>
        <input
          type="date"
          value={endDate || getDefaultEndDate()}
          onChange={(e) => onEndDateChange(e.target.value)}
          className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
      </div>
      <div className="flex items-center space-x-2 ml-4">
        <button
          onClick={() => {
            const end = new Date();
            const start = new Date();
            start.setDate(start.getDate() - 7);
            onStartDateChange(formatDateForInput(start));
            onEndDateChange(formatDateForInput(end));
          }}
          className="px-3 py-1.5 text-sm bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors"
        >
          Last 7 days
        </button>
        <button
          onClick={() => {
            const end = new Date();
            const start = new Date();
            start.setDate(start.getDate() - 30);
            onStartDateChange(formatDateForInput(start));
            onEndDateChange(formatDateForInput(end));
          }}
          className="px-3 py-1.5 text-sm bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors"
        >
          Last 30 days
        </button>
        <button
          onClick={() => {
            const end = new Date();
            const start = new Date();
            start.setDate(start.getDate() - 90);
            onStartDateChange(formatDateForInput(start));
            onEndDateChange(formatDateForInput(end));
          }}
          className="px-3 py-1.5 text-sm bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors"
        >
          Last 90 days
        </button>
      </div>
    </div>
  );
}



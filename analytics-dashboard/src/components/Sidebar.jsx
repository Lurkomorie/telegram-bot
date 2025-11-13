import { Link, useLocation } from 'react-router-dom';

export default function Sidebar() {
  const location = useLocation();
  
  const links = [
    { path: '/statistics', label: 'Statistics', icon: '📊' },
    { path: '/users', label: 'Users', icon: '👥' },
    { path: '/acquisition-sources', label: 'Acquisition Sources', icon: '🎯' },
    { path: '/start-codes', label: 'Start Codes', icon: '🎫' },
    { path: '/images', label: 'Images', icon: '🖼️' }
  ];

  return (
    <div className="w-64 bg-white shadow-lg">
      <div className="p-6 border-b">
        <h1 className="text-2xl font-bold text-gray-800">Analytics</h1>
        <p className="text-sm text-gray-500 mt-1">Telegram Bot</p>
      </div>
      
      <nav className="p-4">
        {links.map(link => (
          <Link
            key={link.path}
            to={link.path}
            className={`flex items-center px-4 py-3 mb-2 rounded-lg transition-colors ${
              location.pathname === link.path
                ? 'bg-blue-50 text-blue-600'
                : 'text-gray-700 hover:bg-gray-50'
            }`}
          >
            <span className="text-xl mr-3">{link.icon}</span>
            <span className="font-medium">{link.label}</span>
          </Link>
        ))}
      </nav>
    </div>
  );
}





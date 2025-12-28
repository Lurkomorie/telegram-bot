import { Link, useLocation } from 'react-router-dom';
import { logout } from './AuthGuard';

export default function Sidebar() {
  const location = useLocation();
  
  const links = [
    { path: '/statistics', label: 'Statistics', icon: '📊' },
    { path: '/premium-statistics', label: 'Premium Stats', icon: '👑' },
    { path: '/conversions', label: 'Conversions', icon: '💰' },
    { path: '/user-message-stats', label: 'User Messages', icon: '📈' },
    { path: '/users', label: 'Users', icon: '👥' },
    { path: '/acquisition-sources', label: 'Acquisition Sources', icon: '🎯' },
    { path: '/start-codes', label: 'Start Codes', icon: '🎫' },
    { path: '/characters', label: 'Characters', icon: '🎭' },
    { path: '/images', label: 'Images', icon: '🖼️' },
    { path: '/translations', label: 'Translations', icon: '🌐' },
    { path: '/system-messages', label: 'System Messages', icon: '📨' },
    { path: '/system-messages/templates', label: 'Templates', icon: '📝' }
  ];

  const handleLogout = () => {
    if (window.confirm('Are you sure you want to logout?')) {
      logout();
    }
  };

  return (
    <div className="w-64 bg-white shadow-lg flex flex-col">
      <div className="p-6 border-b">
        <h1 className="text-2xl font-bold text-gray-800">Analytics</h1>
        <p className="text-sm text-gray-500 mt-1">Telegram Bot</p>
      </div>
      
      <nav className="p-4 flex-1">
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

      <div className="p-4 border-t">
        <button
          onClick={handleLogout}
          className="flex items-center px-4 py-3 w-full rounded-lg text-gray-700 hover:bg-red-50 hover:text-red-600 transition-colors"
        >
          <span className="text-xl mr-3">🚪</span>
          <span className="font-medium">Logout</span>
        </button>
      </div>
    </div>
  );
}





import { Heart, Settings } from 'lucide-react';
import './BottomNav.css';

/**
 * BottomNav Component
 * Translucent bottom navigation bar with icon-only tabs (Lucid Dreams style)
 */
export default function BottomNav({ currentPage, onNavigate }) {
  const tabs = [
    { id: 'gallery', icon: Heart },
    { id: 'premium', icon: Settings },
  ];

  return (
    <div className="bottom-nav">
      <div className="bottom-nav-content">
        {tabs.map((tab) => {
          const IconComponent = tab.icon;
          return (
            <button
              key={tab.id}
              className={`nav-tab ${currentPage === tab.id ? 'active' : ''}`}
              onClick={() => onNavigate(tab.id)}
            >
              <IconComponent className="nav-icon" size={20} strokeWidth={2} />
            </button>
          );
        })}
      </div>
    </div>
  );
}


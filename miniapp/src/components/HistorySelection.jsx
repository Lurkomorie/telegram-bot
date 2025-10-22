import { useState } from 'react';
import './HistorySelection.css';

/**
 * HistorySelection Component
 * Shows available greeting scenarios for a selected persona
 */
export default function HistorySelection({ persona, histories, onHistoryClick, onBack, isLoading }) {
  if (isLoading) {
    return (
      <div className="history-selection">
        <div className="loading">
          <div className="spinner"></div>
          <p>Loading scenarios...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="history-selection">

      <div className="histories-list">
        {histories && histories.length > 0 ? (
          histories.map((history) => (
            <HistoryCard
              key={history.id}
              history={history}
              onClick={() => onHistoryClick(history)}
            />
          ))
        ) : (
          <div className="no-histories">
            <p>No scenarios available. Starting with default greeting...</p>
            <button className="start-button" onClick={() => onHistoryClick(null)}>
              Start Chat
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * HistoryCard Component
 * Individual history/scenario card
 */
function HistoryCard({ history, onClick }) {
  const [imageError, setImageError] = useState(false);

  return (
    <div className="history-card">
      {history.wide_menu_image_url && !imageError ? (
        <div className="history-image wide">
          <img
            src={history.wide_menu_image_url}
            alt="Scenario preview"
            onError={() => setImageError(true)}
          />
        </div>
      ) : history.image_url && !imageError ? (
        <div className="history-image">
          <img
            src={history.image_url}
            alt="Scenario preview"
            onError={() => setImageError(true)}
          />
        </div>
      ) : null}
      <div className="history-content">
        {history.description && (
          <p className="history-description">{history.description}</p>
        )}
        <p className="history-text">"{history.text}"</p>
        <button className="select-button" onClick={onClick}>
          Select This Scenario
        </button>
      </div>
    </div>
  );
}


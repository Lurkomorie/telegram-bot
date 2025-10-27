import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { api } from '../api';
import { formatDate } from '../utils';

export default function UserTimeline() {
  const { clientId } = useParams();
  const navigate = useNavigate();
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [copiedText, setCopiedText] = useState(null);

  useEffect(() => {
    fetchEvents();
  }, [clientId]);

  const fetchEvents = async () => {
    try {
      setLoading(true);
      const data = await api.getUserEvents(clientId);
      setEvents(data);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text, label) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopiedText(label);
      setTimeout(() => setCopiedText(null), 2000);
    });
  };

  const renderEvent = (event) => {
    const { event_name, message, persona_name, image_url, meta, created_at } = event;

    // User messages - right side (blue)
    if (event_name === 'user_message') {
      return (
        <div className="flex justify-end mb-4">
          <div className="max-w-2xl">
            <div className="bg-blue-500 text-white rounded-lg px-4 py-3 shadow">
              <p className="text-sm whitespace-pre-wrap">{message}</p>
            </div>
            <div className="text-xs text-gray-500 mt-1 text-right">{formatDate(created_at)}</div>
          </div>
        </div>
      );
    }

    // AI messages - left side (gray)
    if (event_name === 'ai_message') {
      return (
        <div className="flex justify-start mb-4">
          <div className="max-w-2xl">
            {persona_name && (
              <div className="text-xs text-gray-600 font-medium mb-1">{persona_name}</div>
            )}
            <div className="bg-gray-200 text-gray-800 rounded-lg px-4 py-3 shadow">
              <p className="text-sm whitespace-pre-wrap">{message}</p>
            </div>
            <div className="text-xs text-gray-500 mt-1">{formatDate(created_at)}</div>
          </div>
        </div>
      );
    }

    // Images - left side with image
    if (event_name === 'image_generated' && image_url) {
      const hasPrompts = event.prompt || event.negative_prompt;
      
      return (
        <div className="flex justify-start mb-4">
          <div className="max-w-md">
            {persona_name && (
              <div className="text-xs text-gray-600 font-medium mb-1">{persona_name}</div>
            )}
            <div className="relative group">
              <div className="bg-gray-100 rounded-lg overflow-hidden shadow">
                <img src={image_url} alt="Generated" className="w-full" />
              </div>
              
              {/* Hover overlay with prompts */}
              {hasPrompts && (
                <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-75 transition-all duration-200 rounded-lg flex items-center justify-center opacity-0 group-hover:opacity-100">
                  <div className="p-4 max-h-full overflow-y-auto">
                    {event.prompt && (
                      <div className="mb-3">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-white text-xs font-bold">Prompt:</span>
                          <button
                            onClick={() => copyToClipboard(event.prompt, 'prompt')}
                            className="text-white text-xs bg-blue-500 hover:bg-blue-600 px-2 py-1 rounded"
                          >
                            {copiedText === 'prompt' ? '✓ Copied' : 'Copy'}
                          </button>
                        </div>
                        <p className="text-white text-xs break-words">{event.prompt}</p>
                      </div>
                    )}
                    {event.negative_prompt && (
                      <div>
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-white text-xs font-bold">Negative Prompt:</span>
                          <button
                            onClick={() => copyToClipboard(event.negative_prompt, 'negative')}
                            className="text-white text-xs bg-red-500 hover:bg-red-600 px-2 py-1 rounded"
                          >
                            {copiedText === 'negative' ? '✓ Copied' : 'Copy'}
                          </button>
                        </div>
                        <p className="text-white text-xs break-words">{event.negative_prompt}</p>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
            <div className="text-xs text-gray-500 mt-1">{formatDate(created_at)}</div>
            {hasPrompts && (
              <div className="text-xs text-gray-400 mt-1 italic">Hover to see prompts</div>
            )}
          </div>
        </div>
      );
    }

    // Commands and other events - center (badges)
    const eventLabels = {
      start_command: '/start',
      chat_cleared: '/clear',
      persona_selected: `Selected: ${persona_name}`,
      story_selected: `Story: ${meta?.story_name || 'Selected'}`,
      chat_continued: 'Continued chat',
      image_refresh: 'Refreshed image',
      command: meta?.command || 'Command',
      premium_action: `Premium: ${meta?.action || 'Action'}`
    };

    const label = eventLabels[event_name] || event_name;

    return (
      <div className="flex justify-center mb-4">
        <div className="text-center">
          <span className="inline-block bg-gray-300 text-gray-700 text-xs px-3 py-1 rounded-full font-medium">
            {label}
          </span>
          <div className="text-xs text-gray-500 mt-1">{formatDate(created_at)}</div>
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-gray-500">Loading timeline...</div>
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

  return (
    <div className="p-8">
      <div className="mb-8 flex items-center">
        <button
          onClick={() => navigate('/users')}
          className="mr-4 text-blue-600 hover:text-blue-800"
        >
          ← Back
        </button>
        <div>
          <h2 className="text-3xl font-bold text-gray-800">User Timeline</h2>
          <p className="text-gray-500 mt-1">User ID: {clientId} • {events.length} events</p>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow p-6 max-w-4xl mx-auto">
        {events.length === 0 ? (
          <div className="text-center text-gray-500 py-8">No events found</div>
        ) : (
          <div className="space-y-2">
            {events.map((event) => (
              <div key={event.id}>{renderEvent(event)}</div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}


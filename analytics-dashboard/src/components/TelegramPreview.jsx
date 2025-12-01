export default function TelegramPreview({ formData, darkMode = false }) {
  // Sanitize HTML to match what Telegram will actually display
  const sanitizeHtmlForTelegram = (html) => {
    if (!html) return "";
    
    // Simulate the backend sanitization
    let cleaned = html;
    
    // Replace paragraph tags with line breaks
    cleaned = cleaned.replace(/<p[^>]*>/gi, '');
    cleaned = cleaned.replace(/<\/p>/gi, '\n\n');
    
    // Replace <br> with newlines
    cleaned = cleaned.replace(/<br\s*\/?>/gi, '\n');
    
    // Convert headers to bold
    cleaned = cleaned.replace(/<h[1-6][^>]*>/gi, '<b>');
    cleaned = cleaned.replace(/<\/h[1-6]>/gi, '</b>\n\n');
    
    // Remove div tags
    cleaned = cleaned.replace(/<\/?div[^>]*>/gi, '');
    
    // Remove span tags (keep content)
    cleaned = cleaned.replace(/<span(?![^>]*class="tg-spoiler")[^>]*>/gi, '');
    cleaned = cleaned.replace(/<\/span>/gi, '');
    
    // Remove style and class attributes
    cleaned = cleaned.replace(/\s+style="[^"]*"/gi, '');
    cleaned = cleaned.replace(/\s+class="(?!tg-spoiler)[^"]*"/gi, '');
    
    // Convert lists
    cleaned = cleaned.replace(/<ul[^>]*>/gi, '');
    cleaned = cleaned.replace(/<\/ul>/gi, '\n');
    cleaned = cleaned.replace(/<ol[^>]*>/gi, '');
    cleaned = cleaned.replace(/<\/ol>/gi, '\n');
    cleaned = cleaned.replace(/<li[^>]*>/gi, '• ');
    cleaned = cleaned.replace(/<\/li>/gi, '\n');
    
    // Clean up multiple newlines
    cleaned = cleaned.replace(/\n{3,}/g, '\n\n');
    
    return cleaned.trim();
  };

  const renderText = () => {
    if (!formData.text) {
      return <div className="text-gray-400 italic">No message text</div>;
    }
    
    // For HTML parse mode, sanitize and render
    if (formData.parse_mode === 'HTML') {
      const sanitized = sanitizeHtmlForTelegram(formData.text);
      return (
        <div className="whitespace-pre-wrap">
          <div 
            className={darkMode ? 'text-gray-100' : 'text-gray-800'}
            dangerouslySetInnerHTML={{ __html: sanitized }}
          />
          {sanitized !== formData.text && (
            <div className="mt-3 pt-3 border-t border-gray-300/50">
              <div className="text-xs text-blue-600 font-medium mb-1">ℹ️ Preview Note:</div>
              <div className="text-xs text-gray-500">
                HTML cleaned for Telegram (only <b>&lt;b&gt;</b>, <i>&lt;i&gt;</i>, <u>&lt;u&gt;</u>, <s>&lt;s&gt;</s>, <a>&lt;a&gt;</a> supported)
              </div>
            </div>
          )}
        </div>
      );
    }
    
    // For MarkdownV2, just show as plain text for now
    return <div className={`${darkMode ? 'text-gray-100' : 'text-gray-800'} whitespace-pre-wrap`}>{formData.text}</div>;
  };

  const renderMedia = () => {
    if (formData.media_type === 'none' || !formData.media_url) {
      return null;
    }

    const mediaStyle = {
      width: '100%',
      borderRadius: '8px',
      marginBottom: '8px'
    };

    switch (formData.media_type) {
      case 'photo':
        return (
          <img 
            src={formData.media_url} 
            alt="Preview" 
            style={mediaStyle}
            onError={(e) => {
              e.target.style.display = 'none';
              e.target.parentElement.innerHTML = '<div class="text-red-500 text-sm p-2">Failed to load image</div>';
            }}
          />
        );
      case 'video':
        return (
          <div className="bg-gray-200 rounded-lg p-4 text-center">
            <div className="text-4xl mb-2">🎥</div>
            <div className="text-sm text-gray-600">Video</div>
            <div className="text-xs text-gray-500 mt-1">{formData.media_url}</div>
          </div>
        );
      case 'animation':
        return (
          <div className="bg-gray-200 rounded-lg p-4 text-center">
            <div className="text-4xl mb-2">🎬</div>
            <div className="text-sm text-gray-600">Animation/GIF</div>
            <div className="text-xs text-gray-500 mt-1">{formData.media_url}</div>
          </div>
        );
      default:
        return null;
    }
  };

  const renderButtons = () => {
    if (!formData.buttons || formData.buttons.length === 0) {
      return null;
    }

    return (
      <div className="mt-2 space-y-1">
        {formData.buttons.map((btn, idx) => (
          <button
            key={idx}
            className="w-full bg-blue-500 text-white text-sm py-2 px-3 rounded hover:bg-blue-600 transition-colors"
            disabled
          >
            {btn.text}
          </button>
        ))}
      </div>
    );
  };

  return (
    <div className="h-full flex flex-col">
      <div className="mb-4">
        <h3 className="text-lg font-semibold">Telegram Preview</h3>
        <p className="text-xs text-gray-500">How your message will appear</p>
      </div>
      
      {/* Telegram-like Container */}
      <div 
        className="flex-1 rounded-lg p-4 overflow-y-auto"
        style={{
          background: darkMode 
            ? 'linear-gradient(to bottom, #212121 0%, #1a1a1a 100%)'
            : 'linear-gradient(to bottom, #e5f3ff 0%, #d4e8f7 100%)',
          minHeight: '400px'
        }}
      >
        {/* Chat Container */}
        <div className="max-w-sm mx-auto">
          {/* Message Bubble */}
          <div 
            className={`rounded-lg shadow-sm p-3 mb-2 ${darkMode ? 'bg-gray-800 text-gray-100' : 'bg-white text-gray-800'}`}
          >
            {/* Title */}
            {formData.title && (
              <div className={`font-semibold mb-2 border-b pb-1 ${darkMode ? 'text-gray-100 border-gray-600' : 'text-gray-900 border-gray-300'}`}>
                {formData.title}
              </div>
            )}
            
            {/* Media */}
            {renderMedia()}
            
            {/* Text */}
            <div>
              {renderText()}
            </div>
            
            {/* Buttons */}
            {renderButtons()}
            
            {/* Timestamp */}
            <div className={`text-xs mt-2 text-right ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>
              {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}


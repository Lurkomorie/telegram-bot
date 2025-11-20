import { useEffect, useState } from 'react';
import { api } from '../api';

// Image preview component
function ImagePreview({ url, alt = "Preview" }) {
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState(false);

  if (!url) return null;

  return (
    <div className="mt-2">
      {!error ? (
        <img
          src={url}
          alt={alt}
          className={`max-w-xs max-h-48 rounded border border-gray-300 ${loaded ? '' : 'hidden'}`}
          onLoad={() => setLoaded(true)}
          onError={() => setError(true)}
        />
      ) : (
        <div className="text-sm text-red-500">Failed to load image</div>
      )}
      {!loaded && !error && (
        <div className="text-sm text-gray-500">Loading image...</div>
      )}
    </div>
  );
}

export default function Characters() {
  const [personas, setPersonas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedPersona, setExpandedPersona] = useState(null);
  const [histories, setHistories] = useState({});
  
  // Persona modal state
  const [showPersonaModal, setShowPersonaModal] = useState(false);
  const [editingPersona, setEditingPersona] = useState(null);
  const [personaFormData, setPersonaFormData] = useState({
    name: '',
    key: '',
    prompt: '',
    image_prompt: '',
    badges: '',
    visibility: 'public',
    description: '',
    small_description: '',
    emoji: '',
    intro: '',
    avatar_url: ''
  });
  const [personaFormErrors, setPersonaFormErrors] = useState({});

  // History modal state
  const [showHistoryModal, setShowHistoryModal] = useState(false);
  const [editingHistory, setEditingHistory] = useState(null);
  const [historyPersonaId, setHistoryPersonaId] = useState(null);
  const [historyFormData, setHistoryFormData] = useState({
    name: '',
    small_description: '',
    description: '',
    text: '',
    image_url: '',
    wide_menu_image_url: '',
    image_prompt: ''
  });
  const [historyFormErrors, setHistoryFormErrors] = useState({});

  useEffect(() => {
    fetchPersonas();
  }, []);

  const fetchPersonas = async () => {
    try {
      setLoading(true);
      const data = await api.getPersonas();
      setPersonas(data);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchHistories = async (personaId) => {
    try {
      const data = await api.getPersonaHistories(personaId);
      setHistories(prev => ({ ...prev, [personaId]: data }));
    } catch (err) {
      console.error('Error fetching histories:', err);
    }
  };

  const togglePersonaExpansion = (personaId) => {
    if (expandedPersona === personaId) {
      setExpandedPersona(null);
    } else {
      setExpandedPersona(personaId);
      if (!histories[personaId]) {
        fetchHistories(personaId);
      }
    }
  };

  // ========== PERSONA OPERATIONS ==========

  const openCreatePersonaModal = () => {
    setEditingPersona(null);
    setPersonaFormData({
      name: '',
      key: '',
      prompt: '',
      image_prompt: '',
      badges: '',
      visibility: 'public',
      description: '',
      small_description: '',
      emoji: '',
      intro: '',
      avatar_url: ''
    });
    setPersonaFormErrors({});
    setShowPersonaModal(true);
  };

  const openEditPersonaModal = (persona) => {
    setEditingPersona(persona);
    setPersonaFormData({
      name: persona.name || '',
      key: persona.key || '',
      prompt: persona.prompt || '',
      image_prompt: persona.image_prompt || '',
      badges: (persona.badges || []).join(', '),
      visibility: persona.visibility || 'public',
      description: persona.description || '',
      small_description: persona.small_description || '',
      emoji: persona.emoji || '',
      intro: persona.intro || '',
      avatar_url: persona.avatar_url || ''
    });
    setPersonaFormErrors({});
    setShowPersonaModal(true);
  };

  const closePersonaModal = () => {
    setShowPersonaModal(false);
    setEditingPersona(null);
    setPersonaFormData({
      name: '',
      key: '',
      prompt: '',
      image_prompt: '',
      badges: '',
      visibility: 'public',
      description: '',
      small_description: '',
      emoji: '',
      intro: '',
      avatar_url: ''
    });
    setPersonaFormErrors({});
  };

  const validatePersonaForm = () => {
    const errors = {};
    
    if (!personaFormData.name.trim()) {
      errors.name = 'Name is required';
    }
    
    setPersonaFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handlePersonaSubmit = async (e) => {
    e.preventDefault();
    
    if (!validatePersonaForm()) {
      return;
    }
    
    try {
      const payload = {
        name: personaFormData.name,
        key: personaFormData.key || null,
        prompt: personaFormData.prompt || null,
        image_prompt: personaFormData.image_prompt || null,
        badges: personaFormData.badges || null,
        visibility: personaFormData.visibility,
        description: personaFormData.description || null,
        small_description: personaFormData.small_description || null,
        emoji: personaFormData.emoji || null,
        intro: personaFormData.intro || null,
        avatar_url: personaFormData.avatar_url || null
      };
      
      if (editingPersona) {
        await api.updatePersona(editingPersona.id, payload);
      } else {
        await api.createPersona(payload);
      }
      
      await fetchPersonas();
      closePersonaModal();
    } catch (err) {
      setPersonaFormErrors({ submit: err.message });
    }
  };

  const handlePersonaDelete = async (personaId, personaName) => {
    if (!window.confirm(`Are you sure you want to delete "${personaName}"? This will also delete all associated histories.`)) {
      return;
    }
    
    try {
      await api.deletePersona(personaId);
      await fetchPersonas();
      if (expandedPersona === personaId) {
        setExpandedPersona(null);
      }
    } catch (err) {
      alert(`Error deleting persona: ${err.message}`);
    }
  };

  // ========== HISTORY OPERATIONS ==========

  const openCreateHistoryModal = (personaId) => {
    setEditingHistory(null);
    setHistoryPersonaId(personaId);
    setHistoryFormData({
      name: '',
      small_description: '',
      description: '',
      text: '',
      image_url: '',
      wide_menu_image_url: '',
      image_prompt: ''
    });
    setHistoryFormErrors({});
    setShowHistoryModal(true);
  };

  const openEditHistoryModal = (history, personaId) => {
    setEditingHistory(history);
    setHistoryPersonaId(personaId);
    setHistoryFormData({
      name: history.name || '',
      small_description: history.small_description || '',
      description: history.description || '',
      text: history.text || '',
      image_url: history.image_url || '',
      wide_menu_image_url: history.wide_menu_image_url || '',
      image_prompt: history.image_prompt || ''
    });
    setHistoryFormErrors({});
    setShowHistoryModal(true);
  };

  const closeHistoryModal = () => {
    setShowHistoryModal(false);
    setEditingHistory(null);
    setHistoryPersonaId(null);
    setHistoryFormData({
      name: '',
      small_description: '',
      description: '',
      text: '',
      image_url: '',
      wide_menu_image_url: '',
      image_prompt: ''
    });
    setHistoryFormErrors({});
  };

  const validateHistoryForm = () => {
    const errors = {};
    
    if (!historyFormData.text.trim()) {
      errors.text = 'Greeting text is required';
    }
    
    setHistoryFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleHistorySubmit = async (e) => {
    e.preventDefault();
    
    if (!validateHistoryForm()) {
      return;
    }
    
    try {
      const payload = {
        name: historyFormData.name || null,
        small_description: historyFormData.small_description || null,
        description: historyFormData.description || null,
        text: historyFormData.text,
        image_url: historyFormData.image_url || null,
        wide_menu_image_url: historyFormData.wide_menu_image_url || null,
        image_prompt: historyFormData.image_prompt || null
      };
      
      if (editingHistory) {
        await api.updatePersonaHistory(editingHistory.id, payload);
      } else {
        payload.persona_id = historyPersonaId;
        await api.createPersonaHistory(payload);
      }
      
      await fetchHistories(historyPersonaId);
      closeHistoryModal();
    } catch (err) {
      setHistoryFormErrors({ submit: err.message });
    }
  };

  const handleHistoryDelete = async (historyId, historyName, personaId) => {
    if (!window.confirm(`Are you sure you want to delete story "${historyName || 'Untitled'}"?`)) {
      return;
    }
    
    try {
      await api.deletePersonaHistory(historyId);
      await fetchHistories(personaId);
    } catch (err) {
      alert(`Error deleting history: ${err.message}`);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-gray-500">Loading...</div>
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
      <div className="mb-8 flex justify-between items-center">
        <div>
          <h2 className="text-3xl font-bold text-gray-800">Characters</h2>
          <p className="text-gray-500 mt-1">Manage AI personas and their stories</p>
        </div>
        <button
          onClick={openCreatePersonaModal}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
        >
          + Create Character
        </button>
      </div>

      {/* Summary Card */}
      <div className="bg-white rounded-lg shadow p-6 mb-8">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <div className="text-sm text-gray-500 mb-1">Total Characters</div>
            <div className="text-3xl font-bold text-gray-800">{personas.length}</div>
          </div>
          <div>
            <div className="text-sm text-gray-500 mb-1">Public</div>
            <div className="text-3xl font-bold text-green-600">
              {personas.filter(p => p.visibility === 'public').length}
            </div>
          </div>
          <div>
            <div className="text-sm text-gray-500 mb-1">Private/Custom</div>
            <div className="text-3xl font-bold text-gray-600">
              {personas.filter(p => p.visibility !== 'public').length}
            </div>
          </div>
        </div>
      </div>

      {/* Personas List */}
      <div className="space-y-4">
        {personas.map((persona) => (
          <div key={persona.id} className="bg-white rounded-lg shadow overflow-hidden">
            {/* Persona Header */}
            <div className="p-6">
              <div className="flex items-start justify-between">
                <div className="flex items-start space-x-4 flex-1">
                  {/* Avatar Preview */}
                  {persona.avatar_url && (
                    <img
                      src={persona.avatar_url}
                      alt={persona.name}
                      className="w-16 h-16 rounded-lg object-cover border border-gray-200"
                      onError={(e) => { e.target.style.display = 'none'; }}
                    />
                  )}
                  
                  {/* Persona Info */}
                  <div className="flex-1">
                    <div className="flex items-center space-x-3 mb-2">
                      {persona.emoji && <span className="text-2xl">{persona.emoji}</span>}
                      <h3 className="text-xl font-bold text-gray-800">{persona.name}</h3>
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        persona.visibility === 'public' 
                          ? 'bg-green-100 text-green-800' 
                          : 'bg-gray-100 text-gray-800'
                      }`}>
                        {persona.visibility}
                      </span>
                    </div>
                    
                    {persona.key && (
                      <div className="text-sm text-gray-500 mb-1">
                        <span className="font-mono bg-gray-100 px-2 py-1 rounded">key: {persona.key}</span>
                      </div>
                    )}
                    
                    {persona.small_description && (
                      <p className="text-sm text-gray-600 mb-2">{persona.small_description}</p>
                    )}
                    
                    {persona.badges && persona.badges.length > 0 && (
                      <div className="flex flex-wrap gap-2 mb-2">
                        {persona.badges.map((badge, idx) => (
                          <span key={idx} className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-blue-100 text-blue-800">
                            {badge}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="flex space-x-2 ml-4">
                  <button
                    onClick={() => togglePersonaExpansion(persona.id)}
                    className="px-3 py-1 text-sm text-blue-600 hover:text-blue-900 border border-blue-600 rounded hover:bg-blue-50 transition-colors"
                  >
                    {expandedPersona === persona.id ? 'Hide Stories' : 'Show Stories'}
                  </button>
                  <button
                    onClick={() => openEditPersonaModal(persona)}
                    className="px-3 py-1 text-sm text-blue-600 hover:text-blue-900"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => handlePersonaDelete(persona.id, persona.name)}
                    className="px-3 py-1 text-sm text-red-600 hover:text-red-900"
                  >
                    Delete
                  </button>
                </div>
              </div>
            </div>

            {/* Expanded Histories Section */}
            {expandedPersona === persona.id && (
              <div className="border-t border-gray-200 bg-gray-50 p-6">
                <div className="flex justify-between items-center mb-4">
                  <h4 className="text-lg font-semibold text-gray-800">Stories</h4>
                  <button
                    onClick={() => openCreateHistoryModal(persona.id)}
                    className="px-3 py-1 text-sm bg-green-600 text-white rounded hover:bg-green-700 transition-colors"
                  >
                    + Add Story
                  </button>
                </div>

                {histories[persona.id] && histories[persona.id].length > 0 ? (
                  <div className="space-y-3">
                    {histories[persona.id].map((history) => (
                      <div key={history.id} className="bg-white rounded-lg p-4 border border-gray-200">
                        <div className="flex justify-between items-start">
                          <div className="flex-1">
                            <h5 className="font-semibold text-gray-800 mb-1">
                              {history.name || <span className="text-gray-400 italic">Untitled Story</span>}
                            </h5>
                            {history.small_description && (
                              <p className="text-sm text-gray-600 mb-2">{history.small_description}</p>
                            )}
                            <p className="text-sm text-gray-700 mb-2 line-clamp-2">{history.text}</p>
                            <div className="flex flex-wrap gap-4 mt-2">
                              {history.image_url && (
                                <img
                                  src={history.image_url}
                                  alt="Story portrait"
                                  className="w-20 h-20 rounded object-cover border border-gray-300"
                                  onError={(e) => { e.target.style.display = 'none'; }}
                                />
                              )}
                              {history.wide_menu_image_url && (
                                <img
                                  src={history.wide_menu_image_url}
                                  alt="Story wide banner"
                                  className="h-20 rounded object-cover border border-gray-300"
                                  onError={(e) => { e.target.style.display = 'none'; }}
                                />
                              )}
                            </div>
                          </div>
                          <div className="flex space-x-2 ml-4">
                            <button
                              onClick={() => openEditHistoryModal(history, persona.id)}
                              className="text-sm text-blue-600 hover:text-blue-900"
                            >
                              Edit
                            </button>
                            <button
                              onClick={() => handleHistoryDelete(history.id, history.name, persona.id)}
                              className="text-sm text-red-600 hover:text-red-900"
                            >
                              Delete
                            </button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-gray-500">
                    No stories yet. Click "Add Story" to create one.
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {personas.length === 0 && (
        <div className="text-center py-12 text-gray-500">
          No characters yet. Create one to get started!
        </div>
      )}

      {/* Persona Modal */}
      {showPersonaModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 overflow-y-auto">
          <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full mx-4 my-8 max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-gray-200 sticky top-0 bg-white">
              <h3 className="text-xl font-bold text-gray-800">
                {editingPersona ? 'Edit Character' : 'Create Character'}
              </h3>
            </div>
            
            <form onSubmit={handlePersonaSubmit} className="p-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Name */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Name <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={personaFormData.name}
                    onChange={(e) => setPersonaFormData({ ...personaFormData, name: e.target.value })}
                    className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                      personaFormErrors.name ? 'border-red-500' : 'border-gray-300'
                    }`}
                    placeholder="e.g., Sweet Girlfriend"
                  />
                  {personaFormErrors.name && (
                    <p className="mt-1 text-sm text-red-600">{personaFormErrors.name}</p>
                  )}
                </div>

                {/* Key */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Key (Optional)
                  </label>
                  <input
                    type="text"
                    value={personaFormData.key}
                    onChange={(e) => setPersonaFormData({ ...personaFormData, key: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="e.g., sweet_girlfriend"
                  />
                </div>

                {/* Emoji */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Emoji
                  </label>
                  <input
                    type="text"
                    value={personaFormData.emoji}
                    onChange={(e) => setPersonaFormData({ ...personaFormData, emoji: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="e.g., 💕"
                    maxLength={10}
                  />
                </div>

                {/* Visibility */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Visibility
                  </label>
                  <select
                    value={personaFormData.visibility}
                    onChange={(e) => setPersonaFormData({ ...personaFormData, visibility: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    <option value="public">Public</option>
                    <option value="private">Private</option>
                    <option value="custom">Custom</option>
                  </select>
                </div>
              </div>

              {/* Small Description */}
              <div className="mt-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Small Description
                </label>
                <input
                  type="text"
                  value={personaFormData.small_description}
                  onChange={(e) => setPersonaFormData({ ...personaFormData, small_description: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="One-line description for persona selection"
                />
              </div>

              {/* Description */}
              <div className="mt-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Description
                </label>
                <textarea
                  value={personaFormData.description}
                  onChange={(e) => setPersonaFormData({ ...personaFormData, description: e.target.value })}
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="Short description for UI"
                />
              </div>

              {/* Intro */}
              <div className="mt-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Introduction Message
                </label>
                <textarea
                  value={personaFormData.intro}
                  onChange={(e) => setPersonaFormData({ ...personaFormData, intro: e.target.value })}
                  rows={2}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="Introduction message"
                />
              </div>

              {/* Prompt */}
              <div className="mt-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Dialogue Prompt
                </label>
                <textarea
                  value={personaFormData.prompt}
                  onChange={(e) => setPersonaFormData({ ...personaFormData, prompt: e.target.value })}
                  rows={4}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-sm"
                  placeholder="Custom personality prompt for dialogue"
                />
              </div>

              {/* Image Prompt */}
              <div className="mt-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Image Generation Prompt
                </label>
                <textarea
                  value={personaFormData.image_prompt}
                  onChange={(e) => setPersonaFormData({ ...personaFormData, image_prompt: e.target.value })}
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-sm"
                  placeholder="SDXL tags for image generation"
                />
              </div>

              {/* Badges */}
              <div className="mt-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Badges (comma-separated)
                </label>
                <input
                  type="text"
                  value={personaFormData.badges}
                  onChange={(e) => setPersonaFormData({ ...personaFormData, badges: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="e.g., Popular, New, NSFW"
                />
                <p className="mt-1 text-sm text-gray-500">Separate multiple badges with commas</p>
              </div>

              {/* Avatar URL */}
              <div className="mt-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Avatar URL
                </label>
                <input
                  type="text"
                  value={personaFormData.avatar_url}
                  onChange={(e) => setPersonaFormData({ ...personaFormData, avatar_url: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="https://..."
                />
                <ImagePreview url={personaFormData.avatar_url} alt="Avatar preview" />
              </div>

              {personaFormErrors.submit && (
                <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                  <p className="text-sm text-red-600">{personaFormErrors.submit}</p>
                </div>
              )}

              {/* Actions */}
              <div className="flex justify-end space-x-3 mt-6 pt-6 border-t">
                <button
                  type="button"
                  onClick={closePersonaModal}
                  className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
                >
                  {editingPersona ? 'Update' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* History Modal */}
      {showHistoryModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 overflow-y-auto">
          <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full mx-4 my-8 max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-gray-200 sticky top-0 bg-white">
              <h3 className="text-xl font-bold text-gray-800">
                {editingHistory ? 'Edit Story' : 'Create Story'}
              </h3>
            </div>
            
            <form onSubmit={handleHistorySubmit} className="p-6">
              {/* Name */}
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Story Name
                </label>
                <input
                  type="text"
                  value={historyFormData.name}
                  onChange={(e) => setHistoryFormData({ ...historyFormData, name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="e.g., The Dairy Queen"
                />
              </div>

              {/* Small Description */}
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Small Description
                </label>
                <input
                  type="text"
                  value={historyFormData.small_description}
                  onChange={(e) => setHistoryFormData({ ...historyFormData, small_description: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="Short story description for menu"
                />
              </div>

              {/* Description */}
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Scene Description
                </label>
                <textarea
                  value={historyFormData.description}
                  onChange={(e) => setHistoryFormData({ ...historyFormData, description: e.target.value })}
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="Scene-setting description (sent before greeting)"
                />
              </div>

              {/* Greeting Text */}
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Greeting Message <span className="text-red-500">*</span>
                </label>
                <textarea
                  value={historyFormData.text}
                  onChange={(e) => setHistoryFormData({ ...historyFormData, text: e.target.value })}
                  rows={4}
                  className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                    historyFormErrors.text ? 'border-red-500' : 'border-gray-300'
                  }`}
                  placeholder="The greeting message for this story"
                />
                {historyFormErrors.text && (
                  <p className="mt-1 text-sm text-red-600">{historyFormErrors.text}</p>
                )}
              </div>

              {/* Image Prompt */}
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Image Prompt (SDXL)
                </label>
                <textarea
                  value={historyFormData.image_prompt}
                  onChange={(e) => setHistoryFormData({ ...historyFormData, image_prompt: e.target.value })}
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-sm"
                  placeholder="SDXL prompt used for the greeting image (for continuity)"
                />
              </div>

              {/* Portrait Image URL */}
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Portrait Image URL
                </label>
                <input
                  type="text"
                  value={historyFormData.image_url}
                  onChange={(e) => setHistoryFormData({ ...historyFormData, image_url: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="https://..."
                />
                <ImagePreview url={historyFormData.image_url} alt="Portrait preview" />
              </div>

              {/* Wide Menu Image URL */}
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Wide Menu Image URL
                </label>
                <input
                  type="text"
                  value={historyFormData.wide_menu_image_url}
                  onChange={(e) => setHistoryFormData({ ...historyFormData, wide_menu_image_url: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="https://..."
                />
                <ImagePreview url={historyFormData.wide_menu_image_url} alt="Wide banner preview" />
              </div>

              {historyFormErrors.submit && (
                <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                  <p className="text-sm text-red-600">{historyFormErrors.submit}</p>
                </div>
              )}

              {/* Actions */}
              <div className="flex justify-end space-x-3 pt-6 border-t">
                <button
                  type="button"
                  onClick={closeHistoryModal}
                  className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors font-medium"
                >
                  {editingHistory ? 'Update' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}



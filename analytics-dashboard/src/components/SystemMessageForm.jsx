import { useEffect, useRef, useState } from 'react';
import ReactQuill from 'react-quill';
import 'react-quill/dist/quill.snow.css';
import { api } from '../api';
import EmojiPicker from './EmojiPicker';
import TelegramPreview from './TelegramPreview';

export default function SystemMessageForm({ message, onClose, onSave }) {
  const [formData, setFormData] = useState({
    title: '',
    text: '',
    media_type: 'none',
    media_url: '',
    audio_url: '',
    buttons: [],
    target_type: 'all',
    target_user_ids: [],
    target_group: '',
    exclude_acquisition_source: '',
    send_immediately: false,
    scheduled_at: '',
    parse_mode: 'HTML',
    disable_web_page_preview: false,
    show_hide_button: false,
    template_id: null
  });
  const [templates, setTemplates] = useState([]);
  const [userGroups, setUserGroups] = useState([]);
  const [acquisitionSources, setAcquisitionSources] = useState([]);
  const [selectedAcquisitionSource, setSelectedAcquisitionSource] = useState('');
  const [userSearchQuery, setUserSearchQuery] = useState('');
  const [userSearchResults, setUserSearchResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [savingTemplate, setSavingTemplate] = useState(false);
  const [templateName, setTemplateName] = useState('');
  const [showTemplateDialog, setShowTemplateDialog] = useState(false);
  const [buttonForm, setButtonForm] = useState({ text: '', url: '', callback_data: '', web_app_url: '' });
  const [darkMode, setDarkMode] = useState(false);
  const [showEmojiPicker, setShowEmojiPicker] = useState(false);
  const quillRef = useRef(null);
  const emojiButtonAdded = useRef(false);

  useEffect(() => {
    // Add custom emoji button to ReactQuill toolbar after editor mounts
    const addEmojiButton = () => {
      if (quillRef.current && !emojiButtonAdded.current) {
        const editor = quillRef.current.getEditor();
        if (editor) {
          const toolbarElement = editor.container.previousSibling;
          
          // Find the toolbar container
          if (toolbarElement && toolbarElement.classList.contains('ql-toolbar')) {
            // Check if emoji button already exists
            let emojiButton = toolbarElement.querySelector('.ql-emoji');
            if (!emojiButton) {
              // Create emoji button
              emojiButton = document.createElement('button');
              emojiButton.type = 'button';
              emojiButton.className = 'ql-emoji';
              emojiButton.innerHTML = '😀';
              emojiButton.title = 'Insert Emoji';
              emojiButton.style.cssText = 'font-size: 18px; padding: 0 8px; border: none; background: transparent; cursor: pointer;';
              emojiButton.onclick = (e) => {
                e.preventDefault();
                e.stopPropagation();
                setShowEmojiPicker(true);
              };
              
              // Find the link button and insert emoji button after it
              const linkButton = toolbarElement.querySelector('.ql-link');
              if (linkButton && linkButton.parentNode) {
                // Insert after the link button's parent (which is usually a span wrapper)
                const separator = document.createElement('span');
                separator.className = 'ql-formats';
                separator.appendChild(emojiButton);
                linkButton.parentNode.parentNode.insertBefore(separator, linkButton.parentNode.nextSibling);
              } else {
                // Fallback: create a new format group
                const separator = document.createElement('span');
                separator.className = 'ql-formats';
                separator.appendChild(emojiButton);
                toolbarElement.appendChild(separator);
              }
              emojiButtonAdded.current = true;
            }
          }
        }
      }
    };

    // Try immediately, then with a small delay to ensure editor is ready
    addEmojiButton();
    const timeoutId = setTimeout(addEmojiButton, 100);
    
    return () => clearTimeout(timeoutId);
  }, []); // Run once on mount

  useEffect(() => {
    if (message) {
      const text = message.text || '';
      setFormData({
        title: message.title || '',
        text: text,
        media_type: message.media_type || 'none',
        media_url: message.media_url || '',
        audio_url: message.audio_url || '',
        buttons: message.buttons || [],
        target_type: message.target_type || 'all',
        target_user_ids: message.target_user_ids || [],
        target_group: message.target_group || '',
        exclude_acquisition_source: message.ext?.exclude_acquisition_source || '',
        send_immediately: message.send_immediately || false,
        scheduled_at: message.scheduled_at ? new Date(message.scheduled_at).toISOString().slice(0, 16) : '',
        parse_mode: message.ext?.parse_mode || 'HTML',
        disable_web_page_preview: message.ext?.disable_web_page_preview || false,
        show_hide_button: message.ext?.show_hide_button || false,
        template_id: message.template_id
      });
    }
    loadTemplates();
    loadUserGroups();
    loadAcquisitionSources();
    
    // Initialize selectedAcquisitionSource if editing existing message
    if (message?.target_group?.startsWith('acquisition_source:')) {
      setSelectedAcquisitionSource(message.target_group.replace('acquisition_source:', ''));
    }
  }, [message]);

  const loadTemplates = async () => {
    try {
      const data = await api.getTemplates({ is_active: true });
      setTemplates(data.templates);
    } catch (error) {
      console.error('Failed to load templates:', error);
    }
  };

  const loadUserGroups = async () => {
    try {
      const data = await api.getUserGroups();
      // Filter out the acquisition_source:* placeholder
      setUserGroups(data.groups.filter(g => g.name !== 'acquisition_source:*'));
    } catch (error) {
      console.error('Failed to load user groups:', error);
    }
  };

  const loadAcquisitionSources = async () => {
    try {
      const data = await api.getAcquisitionSources();
      // Filter out 'direct' as it's not an acquisition source
      setAcquisitionSources(data.filter(s => s.source !== 'direct'));
    } catch (error) {
      console.error('Failed to load acquisition sources:', error);
    }
  };

  const searchUsers = async (query) => {
    if (query.length < 2) {
      setUserSearchResults([]);
      return;
    }
    try {
      const results = await api.searchUsers(query);
      setUserSearchResults(results);
    } catch (error) {
      console.error('Failed to search users:', error);
    }
  };

  const handleTextChange = (content, delta, source, editor) => {
    // content is already the HTML string from ReactQuill
    setFormData({ ...formData, text: content });
  };

  const handleEmojiSelect = (emoji) => {
    if (quillRef.current) {
      const quill = quillRef.current.getEditor();
      const range = quill.getSelection();
      const index = range ? range.index : quill.getLength();
      quill.insertText(index, emoji, 'user');
      quill.setSelection(index + emoji.length);
      // Update formData with the new HTML content
      const html = quill.root.innerHTML;
      setFormData({ ...formData, text: html });
    }
    setShowEmojiPicker(false);
  };

  const handleSaveTemplate = async () => {
    if (!templateName.trim()) {
      alert('Please enter a template name');
      return;
    }
    setSavingTemplate(true);
    try {
      await api.createTemplate({
        name: templateName,
        title: formData.title,
        text: formData.text,
        media_type: formData.media_type,
        media_url: formData.media_url,
        audio_url: formData.audio_url || undefined,
        buttons: formData.buttons.length > 0 ? formData.buttons : undefined
      });
      setShowTemplateDialog(false);
      setTemplateName('');
      await loadTemplates();
      alert('Template saved successfully!');
    } catch (error) {
      alert('Failed to save template: ' + error.message);
    } finally {
      setSavingTemplate(false);
    }
  };

  const handleAddButton = () => {
    if (!buttonForm.text) return;
    const button = {
      text: buttonForm.text,
      url: buttonForm.url || undefined,
      callback_data: buttonForm.callback_data || undefined,
      web_app: buttonForm.web_app_url ? { url: buttonForm.web_app_url } : undefined
    };
    setFormData({
      ...formData,
      buttons: [...formData.buttons, button]
    });
    setButtonForm({ text: '', url: '', callback_data: '', web_app_url: '' });
  };

  const handleRemoveButton = (index) => {
    setFormData({
      ...formData,
      buttons: formData.buttons.filter((_, i) => i !== index)
    });
  };

  const handleAddUser = (userId) => {
    if (!formData.target_user_ids.includes(userId)) {
      setFormData({
        ...formData,
        target_user_ids: [...formData.target_user_ids, userId]
      });
    }
    setUserSearchQuery('');
    setUserSearchResults([]);
  };

  const handleRemoveUser = (userId) => {
    setFormData({
      ...formData,
      target_user_ids: formData.target_user_ids.filter(id => id !== userId)
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Validate acquisition source selection
    if (formData.target_type === 'group' && formData.target_group === 'acquisition_source:') {
      alert('Please select an acquisition source');
      return;
    }
    
    setLoading(true);
    try {
      const submitData = {
        ...formData,
        scheduled_at: formData.scheduled_at ? new Date(formData.scheduled_at).toISOString() : null,
        buttons: formData.buttons.length > 0 ? formData.buttons : undefined
      };

      if (message) {
        await api.updateSystemMessage(message.id, submitData);
      } else {
        await api.createSystemMessage(submitData);
      }
      onSave();
    } catch (error) {
      alert('Failed to save message: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-7xl w-full max-h-[90vh] flex flex-col">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-bold">{message ? 'Edit Message' : 'Create Message'}</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700">✕</button>
        </div>

        <div className="flex gap-6 flex-1 overflow-hidden">
          {/* Left Side - Form */}
          <div className="flex-1 overflow-y-auto pr-4">
            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Template Selection */}
              <div>
                <label className="block text-sm font-medium mb-1">Template (optional)</label>
                <select
                  value={formData.template_id || ''}
                  onChange={(e) => {
                    const templateId = e.target.value || null;
                    if (templateId && !message) {
                      const template = templates.find(t => t.id === templateId);
                        if (template) {
                        setFormData({
                          ...formData,
                          template_id: templateId,
                          text: formData.text || template.text,
                          title: formData.title || template.title,
                          media_type: formData.media_type === 'none' ? template.media_type : formData.media_type,
                          media_url: formData.media_url || template.media_url,
                          audio_url: formData.audio_url || template.audio_url || '',
                          buttons: formData.buttons.length === 0 ? (template.buttons || []) : formData.buttons
                        });
                      }
                    } else {
                      setFormData({ ...formData, template_id: templateId });
                    }
                  }}
                  className="w-full border rounded px-3 py-2"
                >
                  <option value="">None</option>
                  {templates.map(t => (
                    <option key={t.id} value={t.id}>{t.name}</option>
                  ))}
                </select>
              </div>

              {/* Title */}
              <div>
                <label className="block text-sm font-medium mb-1">Title (optional)</label>
                <input
                  type="text"
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  className="w-full border rounded px-3 py-2"
                />
              </div>

              {/* Text with WYSIWYG Editor */}
              <div>
                <label className="block text-sm font-medium mb-1">Message Text *</label>
                <ReactQuill
                  ref={quillRef}
                  theme="snow"
                  value={formData.text}
                  onChange={handleTextChange}
                  modules={{
                    toolbar: [
                      [{ 'header': [1, 2, 3, false] }],
                      ['bold', 'italic', 'underline', 'strike'],
                      [{ 'list': 'ordered'}, { 'list': 'bullet' }],
                      [{ 'color': [] }, { 'background': [] }],
                      ['link'],
                      ['clean']
                    ]
                  }}
                  style={{ minHeight: '200px', marginBottom: '50px' }}
                />
                <p className="text-xs text-gray-500 mt-1">Supports HTML formatting, emojis, and links</p>
              </div>

              {/* Media Type */}
              <div>
                <label className="block text-sm font-medium mb-1">Media Type</label>
                <select
                  value={formData.media_type}
                  onChange={(e) => setFormData({ ...formData, media_type: e.target.value })}
                  className="w-full border rounded px-3 py-2"
                >
                  <option value="none">None</option>
                  <option value="photo">Photo</option>
                  <option value="video">Video</option>
                  <option value="animation">Animation/GIF</option>
                </select>
              </div>

              {/* Media URL */}
              {formData.media_type !== 'none' && (
                <div>
                  <label className="block text-sm font-medium mb-1">Media URL *</label>
                  <input
                    type="url"
                    value={formData.media_url}
                    onChange={(e) => setFormData({ ...formData, media_url: e.target.value })}
                    required={formData.media_type !== 'none'}
                    className="w-full border rounded px-3 py-2"
                    placeholder="https://example.com/image.jpg"
                  />
                </div>
              )}

              {/* Audio URL (Voice Message) */}
              <div>
                <label className="block text-sm font-medium mb-1">Voice Message (OGG) - optional</label>
                <div className="flex gap-2 mb-2">
                  <input
                    type="url"
                    value={formData.audio_url}
                    onChange={(e) => setFormData({ ...formData, audio_url: e.target.value })}
                    className="flex-1 border rounded px-3 py-2"
                    placeholder="URL or upload file below"
                  />
                  {formData.audio_url && (
                    <button
                      type="button"
                      onClick={() => setFormData({ ...formData, audio_url: '' })}
                      className="px-3 py-2 bg-red-100 text-red-700 rounded hover:bg-red-200"
                      title="Clear"
                    >
                      ✕
                    </button>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <label className="flex-1 flex items-center justify-center px-4 py-3 bg-gray-100 border-2 border-dashed border-gray-300 rounded-lg cursor-pointer hover:bg-gray-200 transition-colors">
                    <input
                      type="file"
                      accept=".ogg,.mp3,.wav,.m4a,audio/*"
                      className="hidden"
                      onChange={async (e) => {
                        const file = e.target.files?.[0];
                        if (file) {
                          try {
                            const result = await api.uploadFile(file, 'audio');
                            setFormData({ ...formData, audio_url: result.url });
                          } catch (error) {
                            alert('Failed to upload audio: ' + error.message);
                          }
                        }
                        e.target.value = '';
                      }}
                    />
                    <span className="text-gray-600">📁 Upload audio file (OGG, MP3, WAV)</span>
                  </label>
                </div>
                <p className="text-xs text-gray-500 mt-1">Audio will be sent as a voice message after the main message</p>
              </div>

              {/* Buttons */}
              <div>
                <label className="block text-sm font-medium mb-1">Buttons</label>
                <div className="space-y-2 mb-2">
                  {formData.buttons.map((btn, idx) => (
                    <div key={idx} className="flex items-center gap-2 bg-gray-50 p-2 rounded">
                      <span className="flex-1">
                        {btn.text}
                        {btn.web_app?.url && <span className="text-xs text-gray-500 ml-2">(Web App)</span>}
                        {btn.url && <span className="text-xs text-gray-500 ml-2">(Link)</span>}
                      </span>
                      <button
                        type="button"
                        onClick={() => handleRemoveButton(idx)}
                        className="text-red-600 hover:text-red-800"
                      >
                        Remove
                      </button>
                    </div>
                  ))}
                </div>
                
                {/* Quick Actions - Fill form with preset values */}
                <div className="mb-3">
                  <label className="block text-xs text-gray-500 mb-1">Quick Actions (click to fill form below)</label>
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={() => setButtonForm({ text: 'Create Character', url: '', callback_data: '', web_app_url: '/miniapp?page=gallery&create=true' })}
                      className="px-3 py-1 text-sm bg-purple-100 text-purple-700 rounded hover:bg-purple-200"
                    >
                      Create Character
                    </button>
                    <button
                      type="button"
                      onClick={() => setButtonForm({ text: 'Browse Characters', url: '', callback_data: '', web_app_url: '/miniapp?page=gallery' })}
                      className="px-3 py-1 text-sm bg-blue-100 text-blue-700 rounded hover:bg-blue-200"
                    >
                      Browse Characters
                    </button>
                    <button
                      type="button"
                      onClick={() => setButtonForm({ text: 'View Premium', url: '', callback_data: '', web_app_url: '/miniapp?page=premium' })}
                      className="px-3 py-1 text-sm bg-yellow-100 text-yellow-700 rounded hover:bg-yellow-200"
                    >
                      View Premium
                    </button>
                    <button
                      type="button"
                      onClick={() => setButtonForm({ text: 'Get Energy', url: '', callback_data: '', web_app_url: '/miniapp?page=tokens' })}
                      className="px-3 py-1 text-sm bg-green-100 text-green-700 rounded hover:bg-green-200"
                    >
                      Get Energy
                    </button>
                  </div>
                </div>

                {/* Button Form */}
                <div className="border-t pt-3">
                  <label className="block text-xs text-gray-500 mb-1">Button details (customize text and add)</label>
                  <div className="grid grid-cols-2 gap-2">
                    <input
                      type="text"
                      placeholder="Button text"
                      value={buttonForm.text}
                      onChange={(e) => setButtonForm({ ...buttonForm, text: e.target.value })}
                      className="border rounded px-3 py-2"
                    />
                    <input
                      type="url"
                      placeholder="URL (optional)"
                      value={buttonForm.url}
                      onChange={(e) => setButtonForm({ ...buttonForm, url: e.target.value })}
                      className="border rounded px-3 py-2"
                    />
                    <input
                      type="text"
                      placeholder="Callback data (optional)"
                      value={buttonForm.callback_data}
                      onChange={(e) => setButtonForm({ ...buttonForm, callback_data: e.target.value })}
                      className="border rounded px-3 py-2"
                    />
                    <input
                      type="text"
                      placeholder="Web App URL (optional, e.g. /miniapp?page=gallery)"
                      value={buttonForm.web_app_url}
                      onChange={(e) => setButtonForm({ ...buttonForm, web_app_url: e.target.value })}
                      className="border rounded px-3 py-2"
                    />
                  </div>
                  <button
                    type="button"
                    onClick={handleAddButton}
                    className="mt-2 bg-gray-200 px-4 py-2 rounded hover:bg-gray-300"
                  >
                    Add Custom Button
                  </button>
                </div>
              </div>

              {/* Target Type */}
              <div>
                <label className="block text-sm font-medium mb-1">Target</label>
                <select
                  value={formData.target_type}
                  onChange={(e) => setFormData({ ...formData, target_type: e.target.value, target_user_ids: [], target_group: '', exclude_acquisition_source: '' })}
                  className="w-full border rounded px-3 py-2"
                >
                  <option value="all">All Users</option>
                  <option value="user">Single User</option>
                  <option value="users">Multiple Users</option>
                  <option value="group">User Group</option>
                </select>
              </div>

              {/* Exclude Acquisition Source (for All Users) */}
              {formData.target_type === 'all' && acquisitionSources.length > 0 && (
                <div>
                  <label className="block text-sm font-medium mb-1">Exclude Acquisition Source (optional)</label>
                  <select
                    value={formData.exclude_acquisition_source || ''}
                    onChange={(e) => setFormData({ ...formData, exclude_acquisition_source: e.target.value })}
                    className="w-full border rounded px-3 py-2"
                  >
                    <option value="">None - Include all sources</option>
                    {acquisitionSources.map(source => (
                      <option key={source.source} value={source.source}>
                        Exclude: {source.source} ({source.user_count} users)
                      </option>
                    ))}
                  </select>
                  <p className="text-xs text-gray-500 mt-1">Optionally exclude users from a specific acquisition source</p>
                </div>
              )}

              {/* User Selection */}
              {(formData.target_type === 'user' || formData.target_type === 'users') && (
                <div>
                  <label className="block text-sm font-medium mb-1">Select Users</label>
                  <input
                    type="text"
                    placeholder="Search by username or ID"
                    value={userSearchQuery}
                    onChange={(e) => {
                      setUserSearchQuery(e.target.value);
                      searchUsers(e.target.value);
                    }}
                    className="w-full border rounded px-3 py-2 mb-2"
                  />
                  {userSearchResults.length > 0 && (
                    <div className="border rounded max-h-40 overflow-y-auto">
                      {userSearchResults.map(user => (
                        <div
                          key={user.id}
                          onClick={() => handleAddUser(user.id)}
                          className="p-2 hover:bg-gray-100 cursor-pointer"
                        >
                          {user.first_name} (@{user.username || 'no username'}) - {user.id}
                        </div>
                      ))}
                    </div>
                  )}
                  {formData.target_user_ids.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-2">
                      {formData.target_user_ids.map(userId => (
                        <span key={userId} className="bg-blue-100 px-2 py-1 rounded flex items-center gap-1">
                          {userId}
                          <button
                            type="button"
                            onClick={() => handleRemoveUser(userId)}
                            className="text-red-600"
                          >
                            ✕
                          </button>
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Group Selection */}
              {formData.target_type === 'group' && (
                <div>
                  <label className="block text-sm font-medium mb-1">User Group</label>
                  <select
                    value={formData.target_group.startsWith('acquisition_source:') ? 'acquisition_source' : formData.target_group}
                    onChange={(e) => {
                      if (e.target.value === 'acquisition_source') {
                        // Set placeholder to trigger showing the source dropdown
                        setFormData({ ...formData, target_group: selectedAcquisitionSource ? `acquisition_source:${selectedAcquisitionSource}` : 'acquisition_source:' });
                      } else {
                        setSelectedAcquisitionSource('');
                        setFormData({ ...formData, target_group: e.target.value });
                      }
                    }}
                    className="w-full border rounded px-3 py-2"
                  >
                    <option value="">Select group</option>
                    {userGroups.map(group => (
                      <option key={group.name} value={group.name}>{group.name} - {group.description}</option>
                    ))}
                    {acquisitionSources.length > 0 && (
                      <option value="acquisition_source">acquisition_source - Users from specific acquisition source</option>
                    )}
                  </select>
                  
                  {/* Acquisition Source Selection */}
                  {(formData.target_group === 'acquisition_source' || formData.target_group.startsWith('acquisition_source:')) && acquisitionSources.length > 0 && (
                    <div className="mt-2">
                      <label className="block text-sm font-medium mb-1">Select Acquisition Source</label>
                      <select
                        value={selectedAcquisitionSource}
                        onChange={(e) => {
                          setSelectedAcquisitionSource(e.target.value);
                          setFormData({ ...formData, target_group: e.target.value ? `acquisition_source:${e.target.value}` : '' });
                        }}
                        className="w-full border rounded px-3 py-2"
                      >
                        <option value="">Select source</option>
                        {acquisitionSources.map(source => (
                          <option key={source.source} value={source.source}>
                            {source.source} ({source.user_count} users)
                          </option>
                        ))}
                      </select>
                    </div>
                  )}
                </div>
              )}

              {/* Schedule Options */}
              <div>
                <label className="block text-sm font-medium mb-1">Schedule</label>
                <div className="space-y-2">
                  <label className="flex items-center">
                    <input
                      type="radio"
                      checked={formData.send_immediately}
                      onChange={() => setFormData({ ...formData, send_immediately: true, scheduled_at: '' })}
                      className="mr-2"
                    />
                    Send Immediately
                  </label>
                  <label className="flex items-center">
                    <input
                      type="radio"
                      checked={!formData.send_immediately}
                      onChange={() => setFormData({ ...formData, send_immediately: false })}
                      className="mr-2"
                    />
                    Schedule for Later
                  </label>
                  {!formData.send_immediately && (
                    <input
                      type="datetime-local"
                      value={formData.scheduled_at}
                      onChange={(e) => setFormData({ ...formData, scheduled_at: e.target.value })}
                      required={!formData.send_immediately}
                      className="w-full border rounded px-3 py-2"
                    />
                  )}
                </div>
              </div>

              {/* Parse Mode */}
              <div>
                <label className="block text-sm font-medium mb-1">Parse Mode</label>
                <select
                  value={formData.parse_mode}
                  onChange={(e) => setFormData({ ...formData, parse_mode: e.target.value })}
                  className="w-full border rounded px-3 py-2"
                >
                  <option value="HTML">HTML</option>
                  <option value="MarkdownV2">MarkdownV2</option>
                </select>
              </div>

              {/* Options */}
              <div className="space-y-2">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={formData.disable_web_page_preview}
                    onChange={(e) => setFormData({ ...formData, disable_web_page_preview: e.target.checked })}
                    className="mr-2"
                  />
                  Disable web page preview
                </label>
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={formData.show_hide_button}
                    onChange={(e) => setFormData({ ...formData, show_hide_button: e.target.checked })}
                    className="mr-2"
                  />
                  Show "Hide" button (allows users to dismiss the message)
                </label>
              </div>

              {/* Actions */}
              <div className="flex justify-between gap-2 pt-4">
                <button
                  type="button"
                  onClick={() => setShowTemplateDialog(true)}
                  className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
                >
                  💾 Save as Template
                </button>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={onClose}
                    className="px-4 py-2 border rounded hover:bg-gray-50"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={loading}
                    className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
                  >
                    {loading ? 'Saving...' : message ? 'Update' : 'Create'}
                  </button>
                </div>
              </div>
            </form>
          </div>

          {/* Right Side - Telegram Preview */}
          <div className="w-80 flex-shrink-0">
            <div className="mb-2 flex justify-end">
              <button
                type="button"
                onClick={() => setDarkMode(!darkMode)}
                className="px-3 py-1 text-sm bg-gray-200 rounded hover:bg-gray-300"
              >
                {darkMode ? '☀️ Light' : '🌙 Dark'}
              </button>
            </div>
            <TelegramPreview formData={formData} darkMode={darkMode} />
          </div>
        </div>

        {/* Emoji Picker */}
        {showEmojiPicker && (
          <EmojiPicker
            onSelect={handleEmojiSelect}
            onClose={() => setShowEmojiPicker(false)}
          />
        )}

        {/* Save Template Dialog */}
        {showTemplateDialog && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 max-w-md w-full">
              <h3 className="text-lg font-bold mb-4">Save as Template</h3>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Template Name *</label>
                  <input
                    type="text"
                    value={templateName}
                    onChange={(e) => setTemplateName(e.target.value)}
                    className="w-full border rounded px-3 py-2"
                    placeholder="Enter template name"
                    autoFocus
                  />
                </div>
                <div className="flex justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => {
                      setShowTemplateDialog(false);
                      setTemplateName('');
                    }}
                    className="px-4 py-2 border rounded hover:bg-gray-50"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={handleSaveTemplate}
                    disabled={savingTemplate || !templateName.trim()}
                    className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
                  >
                    {savingTemplate ? 'Saving...' : 'Save'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

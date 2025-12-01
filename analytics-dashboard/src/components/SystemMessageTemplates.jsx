import { useState, useEffect } from 'react';
import { api } from '../api';
import SystemMessageForm from './SystemMessageForm';

export default function SystemMessageTemplates() {
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState(null);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  useEffect(() => {
    loadTemplates();
  }, [page]);

  const loadTemplates = async () => {
    try {
      setLoading(true);
      const data = await api.getTemplates({ page, per_page: 20 });
      setTemplates(data.templates);
      setTotalPages(data.total_pages);
    } catch (error) {
      console.error('Failed to load templates:', error);
      alert('Failed to load templates');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = () => {
    setEditingTemplate(null);
    setShowForm(true);
  };

  const handleEdit = (template) => {
    setEditingTemplate(template);
    setShowForm(true);
  };

  const handleDelete = async (id) => {
    if (!confirm('Are you sure you want to delete this template?')) return;
    try {
      await api.deleteTemplate(id);
      loadTemplates();
    } catch (error) {
      alert('Failed to delete template');
    }
  };

  const handleUseTemplate = (template) => {
    // Create a message from template
    setEditingTemplate({
      ...template,
      template_id: template.id,
      target_type: 'all',
      send_immediately: false
    });
    setShowForm(true);
  };

  const [showQuickSetup, setShowQuickSetup] = useState(true);

  const quickSetupExamples = [
    {
      title: "Premium Upsell with Mini App",
      buttonText: "🎁 Grab the Special Offer",
      webAppUrl: "/miniapp?page=premium",
      message: "That girl in the GIF? She's waiting for your command...\n\nDon't miss this rare chance to enjoy VIP access to the fullest!\n\nThis is a one-time purchase. No subscription. No auto-renewal.\n\n👉 <b>Activate VIP now – before this exclusive offer disappears!</b>"
    },
    {
      title: "Low Energy Notification",
      buttonText: "⚡ Get Premium",
      webAppUrl: "/miniapp?page=premium",
      message: "⚡ <b>Running Low on Energy?</b>\n\nUpgrade to Premium and unlock:\n• ∞ Infinite energy\n• 📸 Unlimited photos\n• 👯 Advanced AI models\n\nNo subscription. Pay once, enjoy forever!"
    },
    {
      title: "New Characters Announcement",
      buttonText: "✨ Explore New Characters",
      webAppUrl: "/miniapp?page=gallery",
      message: "🆕 <b>New Characters Just Dropped!</b>\n\nWe added 5 new AI companions with unique personalities and looks.\n\nCheck them out now!"
    }
  ];

  const copyExample = (example) => {
    const text = `Message: ${example.message}\n\nButton Text: ${example.buttonText}\nWeb App URL: ${example.webAppUrl}`;
    navigator.clipboard.writeText(text);
    alert('Copied to clipboard! Now paste into your message form.');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-purple-50 to-pink-50 p-6">
      {/* Header */}
      <div className="max-w-7xl mx-auto mb-8">
        <div className="backdrop-blur-xl bg-white/70 rounded-3xl shadow-2xl p-8 border border-white/20">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-4xl font-bold bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 bg-clip-text text-transparent mb-2">
                Message Templates
              </h1>
              <p className="text-gray-600">Pre-built templates with Mini App buttons</p>
            </div>
            <button
              onClick={handleCreate}
              className="group relative px-8 py-4 bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 text-white rounded-2xl font-semibold shadow-lg hover:shadow-2xl transform hover:scale-105 transition-all duration-300"
            >
              <span className="relative z-10 flex items-center gap-2">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                Create Template
              </span>
            </button>
          </div>
        </div>
      </div>

      {/* Quick Setup Examples */}
      {showQuickSetup && (
        <div className="max-w-7xl mx-auto mb-8">
          <div className="backdrop-blur-xl bg-gradient-to-br from-blue-500/10 to-purple-500/10 rounded-2xl shadow-lg p-6 border border-blue-200/50">
            <div className="flex justify-between items-start mb-6">
              <div className="flex items-center gap-3">
                <div className="text-4xl">💡</div>
                <div>
                  <h2 className="text-2xl font-bold text-gray-800">Mini App Buttons - Quick Setup</h2>
                  <p className="text-sm text-gray-600">Click buttons to open your app inside Telegram (like your competitor!)</p>
                </div>
              </div>
              <button 
                onClick={() => setShowQuickSetup(false)}
                className="text-gray-400 hover:text-gray-600 p-2 rounded-lg hover:bg-white/50 transition-all"
              >
                ✕
              </button>
            </div>
            
            <div className="bg-white/80 rounded-xl p-6 mb-6">
              <h3 className="font-bold text-gray-900 mb-4 text-lg">🎯 How Web App Buttons Work:</h3>
              <div className="grid md:grid-cols-2 gap-4 mb-4">
                <div className="bg-green-50 border-2 border-green-200 rounded-xl p-4">
                  <div className="text-2xl mb-2">✅</div>
                  <h4 className="font-semibold text-green-900 mb-2">What happens:</h4>
                  <ul className="text-sm text-green-800 space-y-1">
                    <li>• User clicks button</li>
                    <li>• Mini app opens <b>inside Telegram</b></li>
                    <li>• Opens directly to Premium/Gallery page</li>
                    <li>• Payment flows instantly!</li>
                  </ul>
                </div>
                <div className="bg-blue-50 border-2 border-blue-200 rounded-xl p-4">
                  <div className="text-2xl mb-2">📱</div>
                  <h4 className="font-semibold text-blue-900 mb-2">How to set up:</h4>
                  <ol className="text-sm text-blue-800 space-y-1 list-decimal list-inside">
                    <li>Add button in message form</li>
                    <li>Fill "Web App URL" field</li>
                    <li>Use: <code className="bg-blue-200 px-1 rounded">/miniapp?page=premium</code></li>
                    <li>Done! 🎉</li>
                  </ol>
                </div>
              </div>
              
              <div className="bg-purple-50 border border-purple-200 rounded-xl p-4">
                <h4 className="font-semibold text-purple-900 mb-3">📍 Available Pages:</h4>
                <div className="grid md:grid-cols-2 gap-3">
                  <div className="bg-white rounded-lg p-3">
                    <code className="text-purple-700 font-bold text-sm">/miniapp?page=premium</code>
                    <p className="text-gray-600 text-xs mt-1">➜ Premium purchase & settings</p>
                  </div>
                  <div className="bg-white rounded-lg p-3">
                    <code className="text-blue-700 font-bold text-sm">/miniapp?page=gallery</code>
                    <p className="text-gray-600 text-xs mt-1">➜ Character gallery & selection</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Examples */}
            <div className="space-y-4">
              {quickSetupExamples.map((example, index) => (
                <div key={index} className="bg-white/90 rounded-xl p-6 border border-gray-200/50 hover:shadow-xl transition-all duration-300">
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h3 className="text-lg font-bold text-gray-900">{example.title}</h3>
                    </div>
                    <button
                      onClick={() => copyExample(example)}
                      className="px-4 py-2 bg-gradient-to-r from-blue-500 to-purple-600 text-white text-sm rounded-lg hover:shadow-lg transition-all duration-200 font-medium"
                    >
                      📋 Copy Example
                    </button>
                  </div>
                  
                  <div className="grid md:grid-cols-2 gap-4">
                    <div>
                      <label className="text-xs font-bold text-gray-700 uppercase mb-2 block">Message:</label>
                      <div className="bg-gray-50 rounded-lg p-3 text-sm text-gray-700 font-mono whitespace-pre-wrap border border-gray-200 max-h-32 overflow-y-auto">
                        {example.message}
                      </div>
                    </div>
                    <div className="space-y-3">
                      <div>
                        <label className="text-xs font-bold text-gray-700 uppercase mb-2 block">Button Text:</label>
                        <div className="bg-blue-50 rounded-lg p-3 text-sm font-semibold text-blue-900 border border-blue-200">
                          {example.buttonText}
                        </div>
                      </div>
                      <div>
                        <label className="text-xs font-bold text-gray-700 uppercase mb-2 block">Web App URL:</label>
                        <div className="bg-purple-50 rounded-lg p-3 text-sm font-mono text-purple-900 border border-purple-200">
                          {example.webAppUrl}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Saved Templates */}
      <div className="max-w-7xl mx-auto">
        <div className="backdrop-blur-xl bg-white/70 rounded-2xl shadow-lg p-6 border border-white/20">
          <h2 className="text-2xl font-bold text-gray-800 mb-6">💾 Your Saved Templates</h2>
          {loading ? (
            <div className="flex justify-center py-12">
              <div className="relative w-16 h-16">
                <div className="absolute inset-0 border-4 border-purple-200 rounded-full"></div>
                <div className="absolute inset-0 border-4 border-t-purple-600 rounded-full animate-spin"></div>
              </div>
            </div>
          ) : templates.length === 0 ? (
            <div className="text-center py-12">
              <div className="text-6xl mb-4">📝</div>
              <p className="text-gray-500 text-lg">No saved templates yet</p>
              <p className="text-gray-400 text-sm mt-2">Create templates from the message form</p>
            </div>
          ) : (
            <>
              <div className="grid gap-4 mb-6">
                {templates.map((template) => (
                  <div key={template.id} className="backdrop-blur-xl bg-white/70 rounded-xl p-6 border border-white/20 hover:shadow-xl transition-all duration-300">
                    <div className="flex justify-between items-start mb-4">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <h3 className="text-xl font-bold text-gray-900">{template.name}</h3>
                          <span className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-semibold ${
                            template.is_active 
                              ? 'bg-gradient-to-r from-green-400 to-emerald-600 text-white' 
                              : 'bg-gradient-to-r from-gray-300 to-gray-400 text-white'
                          }`}>
                            {template.is_active ? '✓ Active' : '⊗ Inactive'}
                          </span>
                        </div>
                        {template.title && (
                          <p className="text-sm font-medium text-gray-700 mb-2">{template.title}</p>
                        )}
                        <p className="text-sm text-gray-600 line-clamp-2 mb-3">{template.text?.substring(0, 150)}...</p>
                        {template.buttons && template.buttons.length > 0 && (
                          <div className="flex gap-2 flex-wrap">
                            {template.buttons.map((btn, idx) => (
                              <span key={idx} className="inline-flex items-center gap-1 px-3 py-1.5 bg-gradient-to-r from-blue-100 to-purple-100 text-blue-900 rounded-lg text-xs font-medium border border-blue-200">
                                {btn.text}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                      <div className="flex flex-col gap-2 ml-4">
                        <button 
                          onClick={() => handleUseTemplate(template)} 
                          className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors shadow-md whitespace-nowrap"
                        >
                          ✨ Use
                        </button>
                        <button 
                          onClick={() => handleEdit(template)} 
                          className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors shadow-md whitespace-nowrap"
                        >
                          ✏️ Edit
                        </button>
                        <button 
                          onClick={() => handleDelete(template.id)} 
                          className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors shadow-md whitespace-nowrap"
                        >
                          🗑️ Delete
                        </button>
                      </div>
                    </div>
                    <div className="text-xs text-gray-500 flex items-center gap-2">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                      </svg>
                      {new Date(template.created_at).toLocaleDateString()}
                    </div>
                  </div>
                ))}
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex justify-center gap-3">
                  <button
                    onClick={() => setPage(p => Math.max(1, p - 1))}
                    disabled={page === 1}
                    className="px-6 py-3 bg-white/70 backdrop-blur-xl rounded-xl border border-white/20 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-white/90 transition-all duration-200 shadow-lg font-medium"
                  >
                    ← Previous
                  </button>
                  <div className="px-6 py-3 bg-gradient-to-r from-indigo-500 to-purple-600 text-white rounded-xl font-semibold shadow-lg">
                    Page {page} of {totalPages}
                  </div>
                  <button
                    onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                    disabled={page === totalPages}
                    className="px-6 py-3 bg-white/70 backdrop-blur-xl rounded-xl border border-white/20 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-white/90 transition-all duration-200 shadow-lg font-medium"
                  >
                    Next →
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* Form Modal - reuse SystemMessageForm but adapt for templates */}
      {showForm && (
        <TemplateForm
          template={editingTemplate}
          onClose={() => {
            setShowForm(false);
            setEditingTemplate(null);
          }}
          onSave={() => {
            setShowForm(false);
            setEditingTemplate(null);
            loadTemplates();
          }}
        />
      )}
    </div>
  );
}

// Simplified template form (similar to SystemMessageForm but without targeting/scheduling)
function TemplateForm({ template, onClose, onSave }) {
  const [formData, setFormData] = useState({
    name: '',
    title: '',
    text: '',
    media_type: 'none',
    media_url: '',
    buttons: [],
    is_active: true
  });
  const [loading, setLoading] = useState(false);
  const [buttonForm, setButtonForm] = useState({ text: '', url: '', callback_data: '', web_app_url: '' });

  useEffect(() => {
    if (template) {
      setFormData({
        name: template.name || '',
        title: template.title || '',
        text: template.text || '',
        media_type: template.media_type || 'none',
        media_url: template.media_url || '',
        buttons: template.buttons || [],
        is_active: template.is_active !== undefined ? template.is_active : true
      });
    }
  }, [template]);

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

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const submitData = {
        ...formData,
        buttons: formData.buttons.length > 0 ? formData.buttons : undefined
      };

      if (template) {
        await api.updateTemplate(template.id, submitData);
      } else {
        await api.createTemplate(submitData);
      }
      onSave();
    } catch (error) {
      alert('Failed to save template: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-6">
      <div className="bg-gradient-to-br from-white/95 to-white/90 backdrop-blur-2xl rounded-3xl p-8 max-w-4xl w-full max-h-[90vh] overflow-y-auto shadow-2xl border border-white/20">
        <div className="flex justify-between items-center mb-6">
          <div>
            <h2 className="text-3xl font-bold bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 bg-clip-text text-transparent">
              {template ? 'Edit Template' : 'Create Template'}
            </h2>
            <p className="text-gray-600 text-sm mt-1">Reusable message templates with buttons</p>
          </div>
          <button 
            onClick={onClose} 
            className="text-gray-400 hover:text-gray-600 hover:bg-gray-100 p-2 rounded-full transition-all duration-200"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className="block text-sm font-medium mb-1">Name *</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              required
              className="w-full border rounded px-3 py-2"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Title (optional)</label>
            <input
              type="text"
              value={formData.title}
              onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              className="w-full border rounded px-3 py-2"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Message Text *</label>
            <textarea
              value={formData.text}
              onChange={(e) => setFormData({ ...formData, text: e.target.value })}
              required
              rows={6}
              className="w-full border rounded px-3 py-2"
            />
          </div>

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

          {formData.media_type !== 'none' && (
            <div>
              <label className="block text-sm font-medium mb-1">Media URL</label>
              <input
                type="url"
                value={formData.media_url}
                onChange={(e) => setFormData({ ...formData, media_url: e.target.value })}
                className="w-full border rounded px-3 py-2"
              />
            </div>
          )}

          <div>
            <label className="block text-sm font-medium mb-1">Buttons</label>
            <div className="space-y-2 mb-2">
              {formData.buttons.map((btn, idx) => (
                <div key={idx} className="flex items-center gap-2 bg-gray-50 p-2 rounded">
                  <span className="flex-1">{btn.text}</span>
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
                placeholder="Web App URL (e.g. /miniapp?page=premium)"
                value={buttonForm.web_app_url}
                onChange={(e) => setButtonForm({ ...buttonForm, web_app_url: e.target.value })}
                className="border rounded px-3 py-2"
              />
            </div>
            <div className="mt-2 bg-blue-50 border border-blue-200 rounded-lg p-3">
              <p className="text-xs text-blue-900">
                💡 <b>Web App URL opens your Mini App inside Telegram!</b><br/>
                Use <code className="bg-blue-200 px-1 rounded">/miniapp?page=premium</code> for Premium page or <code className="bg-blue-200 px-1 rounded">/miniapp?page=gallery</code> for Gallery
              </p>
            </div>
            <button
              type="button"
              onClick={handleAddButton}
              className="mt-3 bg-gradient-to-r from-blue-500 to-purple-600 text-white px-4 py-2 rounded-lg hover:shadow-lg transition-all font-medium"
            >
              ➕ Add Button
            </button>
          </div>

          <div>
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={formData.is_active}
                onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                className="mr-2"
              />
              Active
            </label>
          </div>

          <div className="flex justify-end gap-2 pt-4">
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
              {loading ? 'Saving...' : template ? 'Update' : 'Create'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}


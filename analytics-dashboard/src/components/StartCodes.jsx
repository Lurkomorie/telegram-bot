import { useEffect, useState } from 'react';
import { api } from '../api';

export default function StartCodes() {
  const [codes, setCodes] = useState([]);
  const [personas, setPersonas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [editingCode, setEditingCode] = useState(null);
  const [formData, setFormData] = useState({
    code: '',
    description: '',
    persona_id: '',
    history_id: '',
    is_active: true
  });
  const [formErrors, setFormErrors] = useState({});

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [codesData, personasData] = await Promise.all([
        api.getStartCodes(),
        api.getPersonasWithHistories()
      ]);
      setCodes(codesData);
      setPersonas(personasData);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const openCreateModal = () => {
    setEditingCode(null);
    setFormData({
      code: '',
      description: '',
      persona_id: '',
      history_id: '',
      is_active: true
    });
    setFormErrors({});
    setShowModal(true);
  };

  const openEditModal = (code) => {
    setEditingCode(code);
    setFormData({
      code: code.code,
      description: code.description || '',
      persona_id: code.persona_id || '',
      history_id: code.history_id || '',
      is_active: code.is_active
    });
    setFormErrors({});
    setShowModal(true);
  };

  const closeModal = () => {
    setShowModal(false);
    setEditingCode(null);
    setFormData({
      code: '',
      description: '',
      persona_id: '',
      history_id: '',
      is_active: true
    });
    setFormErrors({});
  };

  const validateForm = () => {
    const errors = {};
    
    if (!editingCode) {
      if (!formData.code) {
        errors.code = 'Code is required';
      } else if (formData.code.length !== 5) {
        errors.code = 'Code must be exactly 5 characters';
      } else if (!/^[A-Za-z0-9]+$/.test(formData.code)) {
        errors.code = 'Code must be alphanumeric';
      }
    }
    
    if (formData.history_id && !formData.persona_id) {
      errors.history_id = 'Persona must be selected when history is selected';
    }
    
    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }
    
    try {
      const payload = {
        description: formData.description || null,
        persona_id: formData.persona_id || null,
        history_id: formData.history_id || null,
        is_active: formData.is_active
      };
      
      if (editingCode) {
        await api.updateStartCode(editingCode.code, payload);
      } else {
        payload.code = formData.code.toUpperCase();
        await api.createStartCode(payload);
      }
      
      await fetchData();
      closeModal();
    } catch (err) {
      setFormErrors({ submit: err.message });
    }
  };

  const handleDelete = async (code) => {
    if (!window.confirm(`Are you sure you want to delete start code "${code}"?`)) {
      return;
    }
    
    try {
      await api.deleteStartCode(code);
      await fetchData();
    } catch (err) {
      alert(`Error deleting code: ${err.message}`);
    }
  };

  const getSelectedPersona = () => {
    return personas.find(p => p.id === formData.persona_id);
  };

  const getAvailableHistories = () => {
    const persona = getSelectedPersona();
    return persona ? persona.histories : [];
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
          <h2 className="text-3xl font-bold text-gray-800">Start Codes</h2>
          <p className="text-gray-500 mt-1">Manage bot start codes for acquisition tracking and onboarding</p>
        </div>
        <button
          onClick={openCreateModal}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
        >
          + Create Code
        </button>
      </div>

      {/* Summary Card */}
      <div className="bg-white rounded-lg shadow p-6 mb-8">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <div className="text-sm text-gray-500 mb-1">Total Codes</div>
            <div className="text-3xl font-bold text-gray-800">{codes.length}</div>
          </div>
          <div>
            <div className="text-sm text-gray-500 mb-1">Active Codes</div>
            <div className="text-3xl font-bold text-green-600">
              {codes.filter(c => c.is_active).length}
            </div>
          </div>
          <div>
            <div className="text-sm text-gray-500 mb-1">Total Users</div>
            <div className="text-3xl font-bold text-gray-800">
              {codes.reduce((sum, c) => sum + c.user_count, 0)}
            </div>
          </div>
        </div>
      </div>

      {/* Codes Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Code
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Description
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Persona / History
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Users
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {codes.map((code) => (
              <tr key={code.code} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className="inline-flex items-center px-3 py-1 rounded-md text-sm font-mono font-bold bg-blue-100 text-blue-800">
                    {code.code}
                  </span>
                </td>
                <td className="px-6 py-4">
                  <div className="text-sm text-gray-900 max-w-md truncate">
                    {code.description || <span className="text-gray-400 italic">No description</span>}
                  </div>
                </td>
                <td className="px-6 py-4">
                  {code.persona_name ? (
                    <div className="text-sm">
                      <div className="font-medium text-gray-900">{code.persona_name}</div>
                      {code.history_name && (
                        <div className="text-gray-500">{code.history_name}</div>
                      )}
                    </div>
                  ) : (
                    <span className="text-sm text-gray-400 italic">Default selection</span>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                    code.is_active 
                      ? 'bg-green-100 text-green-800' 
                      : 'bg-gray-100 text-gray-800'
                  }`}>
                    {code.is_active ? 'Active' : 'Inactive'}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 font-medium">
                  {code.user_count}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                  <button
                    onClick={() => openEditModal(code)}
                    className="text-blue-600 hover:text-blue-900 mr-4"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => handleDelete(code.code)}
                    className="text-red-600 hover:text-red-900"
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {codes.length === 0 && (
        <div className="text-center py-12 text-gray-500">
          No start codes yet. Create one to get started!
        </div>
      )}

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-screen overflow-y-auto">
            <div className="p-6 border-b border-gray-200">
              <h3 className="text-xl font-bold text-gray-800">
                {editingCode ? 'Edit Start Code' : 'Create Start Code'}
              </h3>
            </div>
            
            <form onSubmit={handleSubmit} className="p-6">
              {/* Code */}
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Code <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={formData.code}
                  onChange={(e) => setFormData({ ...formData, code: e.target.value.toUpperCase() })}
                  disabled={!!editingCode}
                  maxLength={5}
                  className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono ${
                    editingCode ? 'bg-gray-100 cursor-not-allowed' : ''
                  } ${formErrors.code ? 'border-red-500' : 'border-gray-300'}`}
                  placeholder="e.g., ABC12"
                />
                {formErrors.code && (
                  <p className="mt-1 text-sm text-red-600">{formErrors.code}</p>
                )}
                {!editingCode && (
                  <p className="mt-1 text-sm text-gray-500">5 alphanumeric characters</p>
                )}
              </div>

              {/* Description */}
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Description
                </label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="Info about this start code..."
                />
              </div>

              {/* Persona */}
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Persona (Optional)
                </label>
                <select
                  value={formData.persona_id}
                  onChange={(e) => setFormData({ ...formData, persona_id: e.target.value, history_id: '' })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="">-- None (Default Selection) --</option>
                  {personas.map((persona) => (
                    <option key={persona.id} value={persona.id}>
                      {persona.name}
                    </option>
                  ))}
                </select>
              </div>

              {/* History */}
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  History (Optional)
                </label>
                <select
                  value={formData.history_id}
                  onChange={(e) => setFormData({ ...formData, history_id: e.target.value })}
                  disabled={!formData.persona_id}
                  className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                    !formData.persona_id ? 'bg-gray-100 cursor-not-allowed' : ''
                  } ${formErrors.history_id ? 'border-red-500' : 'border-gray-300'}`}
                >
                  <option value="">-- None --</option>
                  {getAvailableHistories().map((history) => (
                    <option key={history.id} value={history.id}>
                      {history.name}
                    </option>
                  ))}
                </select>
                {formErrors.history_id && (
                  <p className="mt-1 text-sm text-red-600">{formErrors.history_id}</p>
                )}
              </div>

              {/* Active Status */}
              <div className="mb-6">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={formData.is_active}
                    onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                    className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                  />
                  <span className="ml-2 text-sm font-medium text-gray-700">Active</span>
                </label>
              </div>

              {formErrors.submit && (
                <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                  <p className="text-sm text-red-600">{formErrors.submit}</p>
                </div>
              )}

              {/* Actions */}
              <div className="flex justify-end space-x-3">
                <button
                  type="button"
                  onClick={closeModal}
                  className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
                >
                  {editingCode ? 'Update' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}


import { useEffect, useState } from 'react';
import { api } from '../api';
import { formatNumber } from '../utils';

export default function ImageCache() {
  const [mostRefreshed, setMostRefreshed] = useState([]);
  const [mostCached, setMostCached] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('refreshed');
  const [actionLoading, setActionLoading] = useState(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [refreshed, cached] = await Promise.all([
        api.getMostRefreshedImages(50),
        api.getMostCachedImages(50)
      ]);
      setMostRefreshed(refreshed);
      setMostCached(cached);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleBlacklist = async (jobId, isBlacklisted) => {
    try {
      setActionLoading(jobId);
      if (isBlacklisted) {
        await api.unblacklistImage(jobId);
      } else {
        await api.blacklistImage(jobId);
      }
      // Refresh data
      await fetchData();
    } catch (err) {
      alert('Error: ' + err.message);
    } finally {
      setActionLoading(null);
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

  const currentImages = activeTab === 'refreshed' ? mostRefreshed : mostCached;

  return (
    <div className="p-8">
      <div className="mb-8">
        <h2 className="text-3xl font-bold text-gray-800">Image Cache</h2>
        <p className="text-gray-500 mt-1">Manage cached images and view statistics</p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-500 text-sm font-medium">Most Refreshed</p>
              <p className="text-3xl font-bold text-gray-800 mt-2">{mostRefreshed.length}</p>
              <p className="text-xs text-gray-400 mt-1">Images users refreshed often</p>
            </div>
            <div className="text-4xl bg-orange-100 p-3 rounded-lg">🔄</div>
          </div>
        </div>
        
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-500 text-sm font-medium">Most Served from Cache</p>
              <p className="text-3xl font-bold text-gray-800 mt-2">{mostCached.length}</p>
              <p className="text-xs text-gray-400 mt-1">Popular cached images</p>
            </div>
            <div className="text-4xl bg-green-100 p-3 rounded-lg">💾</div>
          </div>
        </div>
        
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-500 text-sm font-medium">Blacklisted</p>
              <p className="text-3xl font-bold text-gray-800 mt-2">
                {[...mostRefreshed, ...mostCached].filter(img => img.is_blacklisted).length}
              </p>
              <p className="text-xs text-gray-400 mt-1">Excluded from cache</p>
            </div>
            <div className="text-4xl bg-red-100 p-3 rounded-lg">🚫</div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white rounded-lg shadow">
        <div className="border-b">
          <div className="flex">
            <button
              onClick={() => setActiveTab('refreshed')}
              className={`px-6 py-4 font-medium transition-colors ${
                activeTab === 'refreshed'
                  ? 'text-blue-600 border-b-2 border-blue-600'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              🔄 Most Refreshed ({mostRefreshed.length})
            </button>
            <button
              onClick={() => setActiveTab('cached')}
              className={`px-6 py-4 font-medium transition-colors ${
                activeTab === 'cached'
                  ? 'text-blue-600 border-b-2 border-blue-600'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              💾 Most Served from Cache ({mostCached.length})
            </button>
          </div>
        </div>

        {/* Image Grid */}
        <div className="p-6">
          {currentImages.length === 0 ? (
            <div className="text-center text-gray-500 py-8">
              No images found
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {currentImages.map((image) => (
                <div
                  key={image.id}
                  className={`border rounded-lg overflow-hidden ${
                    image.is_blacklisted ? 'border-red-300 bg-red-50' : 'border-gray-200'
                  }`}
                >
                  {/* Image */}
                  <div className="aspect-square bg-gray-100 relative">
                    <img
                      src={image.result_url}
                      alt="Generated image"
                      className={`w-full h-full object-cover ${
                        image.is_blacklisted ? 'opacity-50' : ''
                      }`}
                      loading="lazy"
                    />
                    {image.is_blacklisted && (
                      <div className="absolute inset-0 flex items-center justify-center">
                        <span className="text-4xl">🚫</span>
                      </div>
                    )}
                  </div>

                  {/* Info */}
                  <div className="p-3">
                    <div className="flex justify-between text-sm mb-2">
                      <span className="text-gray-500">
                        {activeTab === 'refreshed' ? '🔄 Refreshed:' : '💾 Served:'}
                      </span>
                      <span className="font-bold text-gray-800">
                        {formatNumber(activeTab === 'refreshed' ? image.refresh_count : image.cache_serve_count)}
                      </span>
                    </div>
                    
                    <div className="text-xs text-gray-400 mb-3 line-clamp-2" title={image.prompt}>
                      {image.prompt?.slice(0, 100)}...
                    </div>

                    {/* Actions */}
                    <button
                      onClick={() => handleBlacklist(image.id, image.is_blacklisted)}
                      disabled={actionLoading === image.id}
                      className={`w-full py-2 px-3 rounded text-sm font-medium transition-colors ${
                        image.is_blacklisted
                          ? 'bg-green-100 text-green-700 hover:bg-green-200'
                          : 'bg-red-100 text-red-700 hover:bg-red-200'
                      } ${actionLoading === image.id ? 'opacity-50 cursor-not-allowed' : ''}`}
                    >
                      {actionLoading === image.id
                        ? 'Loading...'
                        : image.is_blacklisted
                        ? '✓ Unblacklist'
                        : '🚫 Blacklist'}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

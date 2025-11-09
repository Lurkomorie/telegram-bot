import { useState, useEffect } from 'react';
import { api } from '../api';

export default function Images() {
  const [imagesData, setImagesData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [expandedImage, setExpandedImage] = useState(null);

  const perPage = 100;

  useEffect(() => {
    loadImages(currentPage);
  }, [currentPage]);

  const loadImages = async (page) => {
    try {
      setLoading(true);
      const data = await api.getImages(page, perPage);
      setImagesData(data);
      setError(null);
    } catch (err) {
      setError(err.message);
      console.error('Error loading images:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (isoString) => {
    const date = new Date(isoString);
    return date.toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getSourceBadgeColor = (source) => {
    switch (source) {
      case 'scheduler':
        return 'bg-purple-100 text-purple-800';
      case 'history_start':
        return 'bg-blue-100 text-blue-800';
      case 'message_response':
        return 'bg-green-100 text-green-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getSourceLabel = (source) => {
    switch (source) {
      case 'scheduler':
        return 'Auto-Message';
      case 'history_start':
        return 'History Start';
      case 'message_response':
        return 'Message Reply';
      default:
        return source;
    }
  };

  const handlePageChange = (newPage) => {
    if (newPage >= 1 && newPage <= imagesData.total_pages) {
      setCurrentPage(newPage);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  if (loading && !imagesData) {
    return (
      <div className="p-8">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/4 mb-6"></div>
          <div className="space-y-4">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-24 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800">Error: {error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-800">Generated Images</h1>
        <p className="text-gray-500 mt-2">
          Showing {imagesData?.images.length || 0} of {imagesData?.total || 0} images
          {imagesData && ` (Page ${imagesData.page} of ${imagesData.total_pages})`}
        </p>
      </div>

      {/* Images List */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Preview
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Date
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  User
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Persona
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Source
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Prompt
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {imagesData?.images.map((image) => (
                <tr key={image.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    {image.image_url ? (
                      <img
                        src={image.image_url}
                        alt="Generated"
                        className="h-16 w-16 object-cover rounded cursor-pointer hover:opacity-80 transition"
                        onClick={() => setExpandedImage(image)}
                      />
                    ) : (
                      <div className="h-16 w-16 bg-gray-200 rounded flex items-center justify-center">
                        <span className="text-gray-400 text-xs">No image</span>
                      </div>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {formatDate(image.created_at)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm">
                      <div className="font-medium text-gray-900">
                        {image.first_name || 'Unknown'}
                      </div>
                      <div className="text-gray-500">
                        {image.username ? `@${image.username}` : `ID: ${image.user_id}`}
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900">
                      {image.persona_name || 'Unknown'}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${getSourceBadgeColor(image.source)}`}>
                      {getSourceLabel(image.source)}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-sm text-gray-900 max-w-md">
                      <div className="line-clamp-2" title={image.prompt}>
                        {image.prompt || 'N/A'}
                      </div>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pagination */}
      {imagesData && imagesData.total_pages > 1 && (
        <div className="mt-6 flex items-center justify-between">
          <div className="text-sm text-gray-700">
            Page {imagesData.page} of {imagesData.total_pages}
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => handlePageChange(1)}
              disabled={currentPage === 1}
              className="px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              First
            </button>
            <button
              onClick={() => handlePageChange(currentPage - 1)}
              disabled={currentPage === 1}
              className="px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Previous
            </button>
            
            {/* Page numbers */}
            {[...Array(Math.min(5, imagesData.total_pages))].map((_, i) => {
              let pageNum;
              if (imagesData.total_pages <= 5) {
                pageNum = i + 1;
              } else if (currentPage <= 3) {
                pageNum = i + 1;
              } else if (currentPage >= imagesData.total_pages - 2) {
                pageNum = imagesData.total_pages - 4 + i;
              } else {
                pageNum = currentPage - 2 + i;
              }

              return (
                <button
                  key={pageNum}
                  onClick={() => handlePageChange(pageNum)}
                  className={`px-3 py-2 border rounded-md text-sm font-medium ${
                    currentPage === pageNum
                      ? 'bg-blue-600 text-white border-blue-600'
                      : 'border-gray-300 text-gray-700 bg-white hover:bg-gray-50'
                  }`}
                >
                  {pageNum}
                </button>
              );
            })}

            <button
              onClick={() => handlePageChange(currentPage + 1)}
              disabled={currentPage === imagesData.total_pages}
              className="px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Next
            </button>
            <button
              onClick={() => handlePageChange(imagesData.total_pages)}
              disabled={currentPage === imagesData.total_pages}
              className="px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Last
            </button>
          </div>
        </div>
      )}

      {/* Image Modal */}
      {expandedImage && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4"
          onClick={() => setExpandedImage(null)}
        >
          <div className="max-w-5xl max-h-full bg-white rounded-lg shadow-xl overflow-auto" onClick={(e) => e.stopPropagation()}>
            <div className="p-6">
              <div className="flex justify-between items-start mb-4">
                <h2 className="text-2xl font-bold text-gray-800">Image Details</h2>
                <button
                  onClick={() => setExpandedImage(null)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              {/* Image */}
              <div className="mb-4">
                <img
                  src={expandedImage.image_url}
                  alt="Generated"
                  className="max-w-full max-h-96 mx-auto rounded"
                />
              </div>

              {/* Details */}
              <div className="space-y-3 text-sm">
                <div>
                  <span className="font-semibold text-gray-700">Date:</span>
                  <span className="ml-2 text-gray-900">{formatDate(expandedImage.created_at)}</span>
                </div>
                <div>
                  <span className="font-semibold text-gray-700">User:</span>
                  <span className="ml-2 text-gray-900">
                    {expandedImage.first_name || 'Unknown'} 
                    {expandedImage.username && ` (@${expandedImage.username})`}
                    {` - ID: ${expandedImage.user_id}`}
                  </span>
                </div>
                <div>
                  <span className="font-semibold text-gray-700">Persona:</span>
                  <span className="ml-2 text-gray-900">{expandedImage.persona_name || 'Unknown'}</span>
                </div>
                <div>
                  <span className="font-semibold text-gray-700">Source:</span>
                  <span className={`ml-2 px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${getSourceBadgeColor(expandedImage.source)}`}>
                    {getSourceLabel(expandedImage.source)}
                  </span>
                </div>
                <div>
                  <span className="font-semibold text-gray-700">Prompt:</span>
                  <p className="mt-1 text-gray-900 whitespace-pre-wrap">{expandedImage.prompt || 'N/A'}</p>
                </div>
                {expandedImage.negative_prompt && (
                  <div>
                    <span className="font-semibold text-gray-700">Negative Prompt:</span>
                    <p className="mt-1 text-gray-900 whitespace-pre-wrap">{expandedImage.negative_prompt}</p>
                  </div>
                )}
                <div>
                  <span className="font-semibold text-gray-700">Image URL:</span>
                  <a 
                    href={expandedImage.image_url} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="ml-2 text-blue-600 hover:underline break-all"
                  >
                    {expandedImage.image_url}
                  </a>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}


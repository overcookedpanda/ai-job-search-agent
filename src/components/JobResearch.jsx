import { useState } from 'react';

export default function JobResearch({ onSubmit, isLoading }) {
  const [activeTab, setActiveTab] = useState('url');
  const [jobUrl, setJobUrl] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (jobUrl.trim()) {
      onSubmit(jobUrl);
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-lg p-6 mb-8 border border-gray-100">
      <div className="flex justify-between items-center mb-5">
        <h2 className="text-xl font-bold text-gray-800">Research Your Role</h2>
        {/* Settings button removed as requested */}
      </div>

      {/* Tab Navigation */}
      <div className="flex mb-6 border rounded-lg overflow-hidden">
        <button
          className={`flex-1 py-3 px-4 text-center transition-colors ${activeTab === 'url' 
            ? 'bg-indigo-600 text-blue-950 font-medium' 
            : 'bg-gray-50 text-gray-700 hover:bg-gray-100'}`}
          onClick={() => setActiveTab('url')}
        >
          Job URL
        </button>
        <button
          className={`flex-1 py-3 px-4 text-center transition-colors ${activeTab === 'manual' 
            ? 'bg-indigo-600 text-blue-950 font-medium' 
            : 'bg-gray-50 text-gray-700 hover:bg-gray-100'}`}
          onClick={() => setActiveTab('manual')}
        >
          Manual Entry
        </button>
      </div>

      {/* URL Input */}
      {activeTab === 'url' && (
        <form onSubmit={handleSubmit}>
          <div className="relative mb-5">
            <div className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none text-indigo-500">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
              </svg>
            </div>
            <input
              type="url"
              value={jobUrl}
              onChange={(e) => setJobUrl(e.target.value)}
              placeholder="Enter job listing URL (Lever or Greenhouse)"
              className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              required
            />
          </div>
          <button
            type="submit"
            disabled={isLoading || !jobUrl.trim()}
            className="w-full py-3 px-4 bg-indigo-600 hover:bg-indigo-700 text-blue-950 font-medium rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-300 disabled:opacity-50 transition duration-200 shadow-sm"
          >
            Analyze Job Listing
          </button>
        </form>
      )}

      {/* Manual Entry (Placeholder for now) */}
      {activeTab === 'manual' && (
        <div className="text-center py-6 text-gray-500">
          <p>Manual job description entry coming soon!</p>
          <p className="mt-2 text-sm">For now, please use the Job URL tab.</p>
        </div>
      )}
    </div>
  );
}
import { useState } from 'react';

export default function JobResearch({ onSubmit, isLoading }) {
  const [activeTab, setActiveTab] = useState('url'); // 'url' or 'manual'
  const [jobUrl, setJobUrl] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (jobUrl.trim()) {
      onSubmit(jobUrl);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6 mb-8">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-bold text-gray-800">Research Your Role</h2>
        <button className="text-gray-500 hover:text-gray-700">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z" clipRule="evenodd" />
          </svg>
        </button>
      </div>

      {/* Tab Navigation */}
      <div className="flex mb-4">
        <button
          className={`flex-1 py-2 px-4 text-center ${activeTab === 'url' 
            ? 'bg-white text-gray-800 border-b-2 border-blue-500 font-medium' 
            : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
          onClick={() => setActiveTab('url')}
        >
          Job URL
        </button>
        <button
          className={`flex-1 py-2 px-4 text-center ${activeTab === 'manual' 
            ? 'bg-white text-gray-800 border-b-2 border-blue-500 font-medium' 
            : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
          onClick={() => setActiveTab('manual')}
        >
          Manual Entry
        </button>
      </div>

      {/* URL Input */}
      {activeTab === 'url' && (
        <form onSubmit={handleSubmit}>
          <div className="relative mb-4">
            <div className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none text-gray-400">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
              </svg>
            </div>
            <input
              type="url"
              value={jobUrl}
              onChange={(e) => setJobUrl(e.target.value)}
              placeholder="Enter job listing URL (Lever or Greenhouse)"
              className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>
          <button
            type="submit"
            disabled={isLoading || !jobUrl.trim()}
            className="w-full py-3 px-4 bg-teal-400 hover:bg-teal-500 text-white font-medium rounded-md focus:outline-none focus:ring-2 focus:ring-teal-300 disabled:opacity-50 transition duration-200"
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
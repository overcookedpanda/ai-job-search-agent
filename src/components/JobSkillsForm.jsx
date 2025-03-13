import { useState } from 'react';

export default function JobSkillsForm({ onSubmit, isLoading }) {
  const [url, setUrl] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (url.trim()) {
      onSubmit(url);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6 mb-6">
      <h2 className="text-xl font-semibold mb-4">Analyze Job Posting</h2>
      <form onSubmit={handleSubmit}>
        <div className="mb-4">
          <label htmlFor="job-url" className="block text-gray-700 font-medium mb-2">
            Job Posting URL
          </label>
          <input
            id="job-url"
            type="url"
            placeholder="https://example.com/job-posting"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            required
            className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <button
          type="submit"
          disabled={isLoading}
          className="bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
        >
          {isLoading ? 'Analyzing...' : 'Analyze Job'}
        </button>
      </form>
    </div>
  );
}
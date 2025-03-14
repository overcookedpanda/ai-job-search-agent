import { useState } from 'react';

export default function JobResearch({ onSubmit, isLoading, disabled }) {
  const [jobUrl, setJobUrl] = useState('');
  const [urlError, setUrlError] = useState('');

  const validateJobUrl = (url) => {
    // Check if URL is valid
    try {
      new URL(url);
    } catch (_) {
      return "Please enter a valid URL";
    }

    // Check if URL is likely a job posting
    const jobSiteDomains = [
      'indeed.com',
      'glassdoor.com',
      'monster.com',
      'ziprecruiter.com',
      'lever.co',
      'greenhouse.io',
      'workday',
      'jobs.',
      'career',
      'careers',
      'apply',
      'job-',
      'job/',
      'position',
      'vacancy',
      'recruit'
    ];

    const isLikelyJobSite = jobSiteDomains.some(domain => url.toLowerCase().includes(domain));

    if (!isLikelyJobSite) {
      return "This doesn't appear to be a job listing URL. Please enter a URL from a job board or company careers page.";
    }

    return "";
  };

  const handleSubmit = (e) => {
    e.preventDefault();

    if (!jobUrl.trim()) {
      setUrlError("Please enter a URL");
      return;
    }

    const error = validateJobUrl(jobUrl);
    if (error) {
      setUrlError(error);
      return;
    }

    setUrlError('');
    onSubmit(jobUrl);
  };

  const handleUrlChange = (e) => {
    setJobUrl(e.target.value);
    if (urlError) setUrlError('');
  };

  return (
    <div className="bg-white rounded-xl shadow-lg p-6 mb-8 border border-gray-100">
      <div className="mb-5">
        <h2 className="text-xl font-bold text-gray-800">Research Role</h2>
        <p className="text-gray-600 mt-2">Enter any job listing URL to analyze the required skills and qualifications.</p>
      </div>

      <form onSubmit={handleSubmit}>
        <div className="relative mb-2">
          <div className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none text-mint-500">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
            </svg>
          </div>
          <input
            type="url"
            value={jobUrl}
            onChange={handleUrlChange}
            placeholder="Enter job listing URL"
            className={`w-full pl-10 pr-4 py-3 border ${urlError ? 'border-red-500' : 'border-gray-300'} rounded-lg focus:outline-none focus:ring-2 ${urlError ? 'focus:ring-red-500 focus:border-red-500' : 'focus:ring-mint-500 focus:border-mint-500'}`}
            required
            disabled={disabled || isLoading}
          />
        </div>

        {urlError && (
          <div className="mb-4 text-red-500 text-sm">
            {urlError}
          </div>
        )}

        <button
          type="submit"
          disabled={isLoading || !jobUrl.trim() || disabled}
          className="w-full py-3 px-4 bg-mint-600 hover:bg-mint-700 text-green-950 font-medium rounded-lg focus:outline-none focus:ring-2 focus:ring-mint-300 disabled:opacity-50 transition duration-200 shadow-sm"
        >
          {isLoading ? 'Analyzing...' : disabled ? 'Waiting for backend...' : 'Analyze Job Listing'}
        </button>
      </form>

      <div className="mt-4 text-sm text-gray-500">
        <p>Supported sites: Indeed, Glassdoor, Lever, Greenhouse, Workday, and most company career pages.</p>
      </div>
    </div>
  );
}
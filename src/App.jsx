import { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';
import JobResearch from './components/JobResearch';
import LoadingSpinner from './components/LoadingSpinner';
import SkillsResults from './components/SkillsResults';

// Use environment variable for API URL with fallback for development vs production
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:10000';
const API_URL = `${API_BASE_URL}/api/analyze-job`;
const HEALTH_CHECK_URL = `${API_BASE_URL}/api/health`;

function App() {
  const [jobSkills, setJobSkills] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [backendStatus, setBackendStatus] = useState('checking');

  // Check backend status when the page loads
  useEffect(() => {
    const checkBackendStatus = async () => {
      try {
        setBackendStatus('loading');
        const response = await axios.get(HEALTH_CHECK_URL);
        if (response.data.status === 'online') {
          setBackendStatus('ready');
        }
      } catch (err) {
        console.error('Backend not ready:', err);
        setBackendStatus('unavailable');

        // Try again after a short delay
        setTimeout(checkBackendStatus, 3000);
      }
    };

    checkBackendStatus();
  }, []);

  const analyzeJobPosting = async (url) => {
    setIsLoading(true);
    setError(null);
    setJobSkills(null);

    try {
      const response = await axios.post(API_URL, { url });
      setJobSkills(response.data);
    } catch (err) {
      console.error('Error analyzing job:', err);
      setError(err.response?.data?.error || err.message || 'Failed to analyze job posting');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-10">
      <div className="max-w-4xl mx-auto px-4">
        <header className="text-center mb-10">
          <h1 className="text-4xl font-bold text-gray-800 mb-4">AI Interview Preparation</h1>
          <p className="text-gray-600 max-w-2xl mx-auto">
            Research roles, practice interviews, and get personalized feedback to ace your next tech interview.
          </p>
        </header>

        <main>
          {backendStatus === 'checking' || backendStatus === 'loading' ? (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 text-center mb-8">
              <div className="flex flex-col items-center">
                <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-blue-500 mb-3"></div>
                <p className="text-blue-700 font-medium">Initializing backend service...</p>
                <p className="text-blue-600 text-sm mt-2">This may take up to 30 seconds if the service was inactive.</p>
              </div>
            </div>
          ) : backendStatus === 'unavailable' ? (
            <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center mb-8">
              <p className="text-red-700 font-medium">
                Backend service is currently unavailable. Please try again in a moment.
              </p>
            </div>
          ) : null}

          <JobResearch
            onSubmit={analyzeJobPosting}
            isLoading={isLoading}
            disabled={backendStatus !== 'ready'}
          />
          
          {isLoading && <LoadingSpinner />}
          
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6">
              <strong className="font-bold">Error: </strong>
              <span>{error}</span>
            </div>
          )}
          
          {jobSkills && !isLoading && <SkillsResults skills={jobSkills} />}
        </main>
        
        <footer className="mt-14 text-center text-gray-500 text-sm">
          <p>© {new Date().getFullYear()} Overcooked Panda</p>
        </footer>
      </div>
    </div>
  );
}

export default App;
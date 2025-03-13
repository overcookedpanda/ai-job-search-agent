import { useState } from 'react';
import axios from 'axios';
import './App.css';
import JobResearch from './components/JobResearch';
import LoadingSpinner from './components/LoadingSpinner';
import SkillsResults from './components/SkillsResults';

// Use environment variable for API URL with fallback
const API_URL = import.meta.env.VITE_API_URL || '/.netlify/functions/job-search';

function App() {
  const [jobSkills, setJobSkills] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

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
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-4xl mx-auto px-4">
        <header className="text-center mb-10">
          <h1 className="text-4xl font-bold text-gray-800 mb-2">AI Interview Preparation</h1>
          <p className="text-gray-600 max-w-2xl mx-auto">
            Research roles, practice interviews, and get personalized feedback to ace your next tech interview.
          </p>
        </header>

        <main>
          <JobResearch onSubmit={analyzeJobPosting} isLoading={isLoading} />

          {isLoading && <LoadingSpinner />}

          {error && (
            <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-6">
              <strong className="font-bold">Error: </strong>
              <span>{error}</span>
            </div>
          )}

          {jobSkills && !isLoading && <SkillsResults skills={jobSkills} />}
        </main>

        <footer className="mt-12 text-center text-gray-500 text-sm">
          <p>© {new Date().getFullYear()} Overcooked Panda</p>
        </footer>
      </div>
    </div>
  );
}

export default App;
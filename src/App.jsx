import { useState } from 'react';
import axios from 'axios';
import JobSkillsForm from './components/JobSkillsForm';
import SkillsResults from './components/SkillsResults';
import LoadingSpinner from './components/LoadingSpinner';
import './App.css';

// Use environment variable for API URL with fallback
const API_URL = import.meta.env.VITE_API_URL || '/.netlify/functions/job-search';

function App() {
  const [jobSkills, setJobSkills] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const analyzeJobPosting = async (url) => {
    setIsLoading(true);
    setError(null);

    try {
      // For development/testing without a backend
      // Uncomment this block to use mock data instead of making API calls
      /*
      setTimeout(() => {
        setJobSkills({
          job_title: "AI Automation Engineer",
          required_skills: {
            technical_skills: [".NET/.NET Core", "Web/REST APIs", "Microsoft Copilot Studio", "PowerAutomate"],
            soft_skills: ["Strong analytical and communication skills", "Innovative problem solving"],
            education: ["Degree in Computer Science or related field"],
            experience: ["2+ years with .NET/.NET Core"]
          },
          preferred_skills: ["Legal industry knowledge", "Agile methodology"]
        });
        setIsLoading(false);
      }, 2000);
      return;
      */

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
        <header className="text-center mb-8">
          <h1 className="text-3xl font-bold text-blue-600 mb-2">Job Skills Analyzer</h1>
          <p className="text-gray-600">Extract required skills from job postings to better prepare for applications</p>
        </header>

        <main>
          <JobSkillsForm onSubmit={analyzeJobPosting} isLoading={isLoading} />

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
          <p>© {new Date().getFullYear()} Job Skills Analyzer</p>
        </footer>
      </div>
    </div>
  );
}

export default App;
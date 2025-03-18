import { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';
import JobResearch from './components/JobResearch';
import LoadingSpinner from './components/LoadingSpinner';
import SkillsResults from './components/SkillsResults';
import InterviewQuestions from './components/InterviewQuestions';

// Use environment variable for API URL with fallback for development vs production
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:10000';
const API_URL = `${API_BASE_URL}/api/analyze-job`;
const QUESTIONS_URL = `${API_BASE_URL}/api/generate-questions`;
const HEALTH_CHECK_URL = `${API_BASE_URL}/api/health`;

function App() {
  const [jobSkills, setJobSkills] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [backendStatus, setBackendStatus] = useState('checking');
  const [interviewQuestions, setInterviewQuestions] = useState(null);
  const [isLoadingQuestions, setIsLoadingQuestions] = useState(false);
  // Add state for structured data
  const [structuredJobData, setStructuredJobData] = useState(null);

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
    setInterviewQuestions(null);
    setStructuredJobData(null);

    try {
      const response = await axios.post(API_URL, { url });
      setJobSkills(response.data);

      // Try to extract structured data if available
      if (response.data && typeof response.data === 'object') {
        if (response.data.job_title && response.data.required_skills) {
          // We have structured data
          setStructuredJobData(response.data);
        }
      }
    } catch (err) {
      console.error('Error analyzing job:', err);
      setError(err.response?.data?.error || err.message || 'Failed to analyze job posting');
    } finally {
      setIsLoading(false);
    }
  };

  const handleStructuredDataReady = (data) => {
    setStructuredJobData(data);
  };

  const generateInterviewQuestions = async () => {
    if (!jobSkills) return;

    setIsLoadingQuestions(true);
    try {
      // Use the structured data if available, otherwise use a modified version of the raw output
      const dataToSend = structuredJobData || {
        job_title: "Position from job posting",
        raw_output: jobSkills.raw_output || "No job description available"
      };

      console.log("Sending data for interview questions:", dataToSend);

      const response = await axios.post(QUESTIONS_URL, {
        job_details: dataToSend
      });

      setInterviewQuestions(response.data);
    } catch (err) {
      console.error('Error generating interview questions:', err);
      setError("Failed to generate interview questions. Please try again.");
    } finally {
      setIsLoadingQuestions(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-10">
      <div className="max-w-4xl mx-auto px-4">
        <header className="text-center mb-10">
          <h1 className="text-4xl font-bold text-gray-800 dark:text-white mb-4">AI Interview Preparation</h1>
          <p className="text-gray-600 dark:text-gray-300 max-w-2xl mx-auto">
            Research roles, practice interviews, and get personalized feedback to ace your next tech interview.
          </p>
        </header>

        <main>
          {backendStatus === 'checking' || backendStatus === 'loading' ? (
            <div className="bg-blue-50 dark:bg-blue-900 border border-blue-200 dark:border-blue-800 rounded-lg p-6 text-center mb-8">
              <div className="flex flex-col items-center">
                <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-blue-500 dark:border-blue-300 mb-3"></div>
                <p className="text-blue-700 dark:text-blue-300 font-medium">Initializing backend service...</p>
                <p className="text-blue-600 dark:text-blue-300 text-sm mt-2">This may take up to 50 seconds if the service was inactive.</p>
              </div>
            </div>
          ) : backendStatus === 'unavailable' ? (
            <div className="bg-red-50 dark:bg-red-900 border border-red-200 dark:border-red-800 rounded-lg p-6 text-center mb-8">
              <p className="text-red-700 dark:text-red-300 font-medium">
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

          {jobSkills && !isLoading && (
            <>
              <SkillsResults
                skills={jobSkills}
                onStructuredDataReady={handleStructuredDataReady}
              />

              {/* Generate Interview Questions Section */}
              <div className="mt-8 text-center">
                {isLoadingQuestions ? (
                  <div className="flex flex-col items-center justify-center">
                    <div className="bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg px-6 py-4 inline-flex items-center">
                      <div className="animate-spin rounded-full h-5 w-5 border-2 border-mint-400 border-t-transparent mr-3"></div>
                      <span className="text-gray-800 dark:text-gray-200">Generating Questions...</span>
                    </div>
                    <p className="text-center text-gray-700 dark:text-gray-400 mt-3">This could take a while... please be patient.</p>
                  </div>
                ) : (
                  // Normal State - Now a div styled as a button
                  <div
                    onClick={generateInterviewQuestions}
                    className="border border-gray-300 dark:bg-gray-800 inline-block py-3 px-8 bg-mint-600 hover:bg-mint-500 dark:text-white font-medium rounded-lg shadow-md transition duration-200 cursor-pointer"
                  >
                    Generate Interview Questions
                  </div>
                )}
              </div>
            </>
          )}

          <InterviewQuestions
              questions={interviewQuestions}
              isLoading={isLoadingQuestions}
          />
        </main>

        <footer className="mt-14 text-center text-gray-500 dark:text-gray-400 text-sm">
          <p>© {new Date().getFullYear()} Overcooked Panda</p>
        </footer>
      </div>
    </div>
  );
}

export default App;
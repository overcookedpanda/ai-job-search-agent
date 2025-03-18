// src/components/InterviewQuestions.jsx
import React, { useState } from "react";
import ReactMarkdown from 'react-markdown';

export default function InterviewQuestions({ questions, isLoading }) {
  const [activeTab, setActiveTab] = useState("technical");
  const [expandedQuestion, setExpandedQuestion] = useState(null);

  // Return null when there are no questions and we're not loading
  if (!questions && !isLoading) {
    return null;
  }

  // Show loading state
  if (isLoading) {
    return (
      <div className="mt-8">
        <p className="text-center text-gray-600 mt-2">This could take a while... please be patient.</p>
      </div>
    );
  }

  // Return null when there are no questions (but we're not loading)
  if (!questions) {
    return null;
  }

  const toggleQuestion = (index) => {
    if (expandedQuestion === index) {
      setExpandedQuestion(null);
    } else {
      setExpandedQuestion(index);
    }
  };

  // Get difficulty color
  const getDifficultyColor = (difficulty) => {
    switch (difficulty?.toLowerCase()) {
      case "easy":
        return "bg-green-100 text-green-800";
      case "medium":
        return "bg-yellow-100 text-yellow-800";
      case "hard":
        return "bg-red-100 text-red-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  // Helper to safely access content
  const safeArray = (arr) => Array.isArray(arr) ? arr : [];

  // Get company research content safely - handle both string and object formats
  const companyResearch = typeof questions.company_research === 'object'
    ? questions.company_research
    : { company_overview: questions.company_research || "" };

  // Get preparation tips safely
  const preparationTips = safeArray(questions.preparation_tips);

  // Get question arrays safely
  const technicalQuestions = safeArray(questions.technical_questions);
  const behavioralQuestions = safeArray(questions.behavioral_questions);

  // Function to process company research sections
  const formatCompanyResearchSection = (title, content) => {
    if (!content) return null;

    return (
      <div className="mb-4">
        <h4 className="text-lg font-medium text-gray-700 mb-2">{title}</h4>
        <div className="prose prose-sm max-w-none text-gray-600">
          {content.split('\n').map((paragraph, i) => (
            paragraph.trim() && (
              <p key={i}>
                <ReactMarkdown>
                  {paragraph}
                </ReactMarkdown>
              </p>
            )
          ))}
        </div>
      </div>
    );
  };

  return (
    <div className="bg-white rounded-xl shadow-lg p-6 border border-gray-100 mt-8">
      <h2 className="text-2xl font-bold text-gray-800 mb-6 text-center">Interview Preparation</h2>

      {/* Company Research Section */}
      {(companyResearch.company_overview || companyResearch.culture_and_values ||
        companyResearch.interview_process || companyResearch.recent_news) && (
        <div className="mb-8">
          <h3 className="text-xl font-semibold text-gray-800 mb-3 flex items-center">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2 text-blue-600" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M4 4a2 2 0 012-2h8a2 2 0 012 2v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4zm3 1h6v4H7V5zm8 8v2h1v1H4v-1h1v-2H4v-1h16v1h-1z" clipRule="evenodd" />
            </svg>
            Company Research
          </h3>
          <div className="bg-gray-50 p-4 rounded-lg">
            {formatCompanyResearchSection("Company Overview", companyResearch.company_overview)}
            {formatCompanyResearchSection("Culture and Values", companyResearch.culture_and_values)}
            {formatCompanyResearchSection("Interview Process", companyResearch.interview_process)}
            {formatCompanyResearchSection("Recent News", companyResearch.recent_news)}
          </div>
        </div>
      )}

      {/* Tabs - Only show if we have any data to display */}
      {(technicalQuestions.length > 0 || behavioralQuestions.length > 0 || preparationTips.length > 0) && (
        <div className="border-b border-gray-200 mb-6">
          <nav className="-mb-px flex flex-col sm:flex-row w-full gap-2 sm:gap-0">
            <button
              onClick={() => setActiveTab("technical")}
              className={`py-2 px-4 text-center border-b-2 font-medium text-sm ${
                activeTab === "technical"
                  ? "border-mint-500 text-mint-600 bg-mint-50"
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
              }`}
            >
              Technical Questions
            </button>
            <button
              onClick={() => setActiveTab("behavioral")}
              className={`py-2 px-4 text-center border-b-2 font-medium text-sm ${
                activeTab === "behavioral"
                  ? "border-mint-500 text-mint-600 bg-mint-50"
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
              }`}
            >
              Behavioral Questions
            </button>
            <button
              onClick={() => setActiveTab("tips")}
              className={`py-2 px-4 text-center border-b-2 font-medium text-sm ${
                activeTab === "tips"
                  ? "border-mint-500 text-mint-600 bg-mint-50"
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
              }`}
            >
              Preparation Tips
            </button>
          </nav>
        </div>
      )}

      {/* Question Lists */}
      {activeTab === "technical" && (
        <div>
          {technicalQuestions.length === 0 ? (
            <p className="text-center text-gray-500 py-8">No technical questions available.</p>
          ) : (
            <ul className="space-y-4">
              {technicalQuestions.map((q, index) => (
                <li key={index} className="border border-gray-200 rounded-lg overflow-hidden">
                  <button
                    onClick={() => toggleQuestion(index)}
                    className="w-full text-left px-4 py-3 flex justify-between items-center hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex-1">
                      <div className="font-medium text-gray-800">
                        <ReactMarkdown>
                          {q.question}
                        </ReactMarkdown>
                      </div>
                      <div className="flex space-x-2 mt-1">
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getDifficultyColor(q.difficulty)}`}>
                          {q.difficulty}
                        </span>
                      </div>
                    </div>
                    <svg
                      className={`h-5 w-5 text-gray-500 transform transition-transform ${expandedQuestion === index ? 'rotate-180' : ''}`}
                      xmlns="http://www.w3.org/2000/svg"
                      viewBox="0 0 20 20"
                      fill="currentColor"
                    >
                      <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
                    </svg>
                  </button>
                  {expandedQuestion === index && (
                    <div className="px-4 py-3 bg-gray-50 border-t border-gray-200">
                      <h4 className="text-sm font-semibold text-gray-500 mb-2">Answer Tips:</h4>
                      <div className="text-sm text-gray-600">
                        {q.answer_tips.split('\n').map((tip, i) => (
                          <p key={i} className="mb-2">
                            <ReactMarkdown>
                              {tip}
                            </ReactMarkdown>
                          </p>
                        ))}
                      </div>
                    </div>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {activeTab === "behavioral" && (
        <div>
          {behavioralQuestions.length === 0 ? (
            <p className="text-center text-gray-500 py-8">No behavioral questions available.</p>
          ) : (
            <ul className="space-y-4">
              {behavioralQuestions.map((q, index) => (
                <li key={index} className="border border-gray-200 rounded-lg overflow-hidden">
                  <button
                    onClick={() => toggleQuestion(index + 100)} // Offset to avoid collision with technical questions
                    className="w-full text-left px-4 py-3 flex justify-between items-center hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex-1">
                      <div className="font-medium text-gray-800">
                        <ReactMarkdown>
                          {q.question}
                        </ReactMarkdown>
                      </div>
                      <div className="flex space-x-2 mt-1">
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getDifficultyColor(q.difficulty)}`}>
                          {q.difficulty}
                        </span>
                      </div>
                    </div>
                    <svg
                      className={`h-5 w-5 text-gray-500 transform transition-transform ${expandedQuestion === index + 100 ? 'rotate-180' : ''}`}
                      xmlns="http://www.w3.org/2000/svg"
                      viewBox="0 0 20 20"
                      fill="currentColor"
                    >
                      <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
                    </svg>
                  </button>
                  {expandedQuestion === index + 100 && (
                    <div className="px-4 py-3 bg-gray-50 border-t border-gray-200">
                      <h4 className="text-sm font-semibold text-gray-500 mb-2">Answer Tips:</h4>
                      <div className="text-sm text-gray-600">
                        {q.answer_tips.split('\n').map((tip, i) => (
                          <p key={i} className="mb-2">
                            <ReactMarkdown>
                              {tip}
                            </ReactMarkdown>
                          </p>
                        ))}
                      </div>
                    </div>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {activeTab === "tips" && (
        <div>
          {preparationTips.length === 0 ? (
            <p className="text-center text-gray-500 py-8">No preparation tips available.</p>
          ) : (
            <ul className="space-y-4">
              {preparationTips.map((tip, index) => (
                <li key={index} className="bg-gray-50 p-4 rounded-lg">
                  <div className="flex items-start">
                    <div>
                      <p className="w-full text-left px-4 py-3 flex justify-between font-semibold text-gray-900">{index + 1}. {tip.title}</p>
                      <p className="w-full text-left px-4 py-3 flex justify-between items-center text-gray-700">{tip.description}</p>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
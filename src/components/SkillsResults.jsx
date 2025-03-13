export default function SkillsResults({ skills }) {
  // Handle plain text responses
  if (typeof skills === 'string') {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-semibold mb-4">Analysis Results</h2>
        <pre className="whitespace-pre-wrap text-gray-700">{skills}</pre>
      </div>
    );
  }

  // Handle raw output format
  if (skills?.raw_output) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-semibold mb-4">Analysis Results</h2>
        <pre className="whitespace-pre-wrap text-gray-700">{skills.raw_output}</pre>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-2xl font-semibold text-blue-600 mb-4 pb-2 border-b">
        {skills?.job_title || 'Job Analysis'}
      </h2>

      {skills?.required_skills && (
        <div className="mb-6">
          <h3 className="text-xl font-semibold text-gray-800 mb-3">Required Skills</h3>

          {Object.entries(skills.required_skills).map(([category, categorySkills]) => (
            <div key={category} className="mb-4">
              <h4 className="text-lg font-medium text-blue-500 mb-2 capitalize">
                {category.replace('_', ' ')}
              </h4>
              <ul className="list-disc pl-5 space-y-1">
                {categorySkills.map((skill, index) => (
                  <li key={index} className="text-gray-700">{skill}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}

      {skills?.preferred_skills && skills.preferred_skills.length > 0 && (
        <div>
          <h3 className="text-xl font-semibold text-gray-800 mb-3">Preferred Skills</h3>
          <ul className="list-disc pl-5 space-y-1">
            {skills.preferred_skills.map((skill, index) => (
              <li key={index} className="text-gray-700">{skill}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
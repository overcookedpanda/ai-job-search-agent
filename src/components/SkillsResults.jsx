export default function SkillsResults({ skills }) {
  // Handle plain text responses
  if (typeof skills === 'string') {
    return (
      <div className="bg-white rounded-xl shadow-lg p-6 border border-gray-100">
        <h2 className="text-xl font-bold text-gray-800 mb-4">Analysis Results</h2>
        <pre className="whitespace-pre-wrap text-gray-700">{skills}</pre>
      </div>
    );
  }

  // Handle raw output format
  if (skills?.raw_output) {
    return (
      <div className="bg-white rounded-xl shadow-lg p-6 border border-gray-100">
        <h2 className="text-xl font-bold text-gray-800 mb-4">Analysis Results</h2>
        <pre className="whitespace-pre-wrap text-gray-700">{skills.raw_output}</pre>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-lg p-6 border border-gray-100">
      <h2 className="text-xl font-bold text-gray-800 mb-5">
        Here are the required skills for the {skills?.job_title || 'position'} at {skills?.company}
      </h2>

      {skills?.required_skills && (
        <>
          {/* Technical Skills */}
          {skills.required_skills.technical_skills && (
            <div className="mb-6">
              <h3 className="text-lg font-bold text-gray-700 mb-3">
                Technical Skills
              </h3>
              <ul className="list-none space-y-2 mt-3">
                {skills.required_skills.technical_skills.map((skill, index) => (
                  <li key={index} className="flex items-start">
                    <span className="inline-block w-2 h-2 bg-gray-500 rounded-full mt-2 mr-3"></span>
                    <span className="text-gray-800">{skill}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Soft Skills */}
          {skills.required_skills.soft_skills && (
            <div className="mb-6">
              <h3 className="text-lg font-bold text-gray-700 mb-3">
                Soft Skills
              </h3>
              <ul className="list-none space-y-2 mt-3">
                {skills.required_skills.soft_skills.map((skill, index) => (
                  <li key={index} className="flex items-start">
                    <span className="inline-block w-2 h-2 bg-gray-500 rounded-full mt-2 mr-3"></span>
                    <span className="text-gray-800">{skill}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Education and Experience */}
          {(skills.required_skills.education || skills.required_skills.experience) && (
            <div className="mb-6">
              <h3 className="text-lg font-bold text-gray-700 mb-3">
                Education and Experience
              </h3>
              <ul className="list-none space-y-2 mt-3">
                {skills.required_skills.education?.map((item, index) => (
                  <li key={`edu-${index}`} className="flex items-start">
                    <span className="inline-block w-2 h-2 bg-gray-500 rounded-full mt-2 mr-3"></span>
                    <span className="text-gray-800">{item}</span>
                  </li>
                ))}
                {skills.required_skills.experience?.map((item, index) => (
                  <li key={`exp-${index}`} className="flex items-start">
                    <span className="inline-block w-2 h-2 bg-gray-500 rounded-full mt-2 mr-3"></span>
                    <span className="text-gray-800">{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}

      {/* Preferred Skills */}
      {skills?.preferred_skills && skills.preferred_skills.length > 0 && (
        <div>
          <h3 className="text-lg font-bold text-gray-700 mb-3">
            Preferred Skills
          </h3>
          <ul className="list-none space-y-2 mt-3">
            {skills.preferred_skills.map((skill, index) => (
              <li key={index} className="flex items-start">
                <span className="inline-block w-2 h-2 bg-gray-500 rounded-full mt-2 mr-3"></span>
                <span className="text-gray-800">{skill}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
import React from "react";
import ReactMarkdown from "react-markdown";

export default function SkillsResults({ skills }) {
  return (
    <div className="bg-white rounded-xl shadow-lg p-6 border border-gray-100">
      <h2 className="text-2xl font-bold text-gray-800 mb-4 text-center">Analysis Results</h2>
      <div className="prose prose-lg text-gray-800 max-w-none text-left">
        <ReactMarkdown
          components={{
            h1: ({ node, ...props }) => <h1 className="text-3xl font-extrabold mt-4 mb-3" {...props} />,
            h2: ({ node, ...props }) => <h2 className="text-2xl font-bold mt-4 mb-2 border-b pb-1" {...props} />,
            h3: ({ node, ...props }) => <h3 className="text-xl font-bold mt-3 mb-1" {...props} />,
            h4: ({ node, ...props }) => <h3 className="text-lg font-semibold mt-3 mb-1" {...props} />,
            p: ({ node, ...props }) => <p className="mt-1 mb-2 text-gray-700" {...props} />,
            ul: ({ node, ...props }) => <ul className="list-disc list-inside mt-2 mb-2 text-gray-700" {...props} />,
            li: ({ node, ...props }) => <li className="ml-4" {...props} />,
          }}
        >
          {skills.raw_output}
        </ReactMarkdown>
      </div>
    </div>
  );
}
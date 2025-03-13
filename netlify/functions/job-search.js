const axios = require('axios');
const cheerio = require('cheerio');
const { OpenAI } = require('openai');

// Initialize OpenAI client
const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY
});

exports.handler = async function(event, context) {
  // Only allow POST requests
  if (event.httpMethod !== 'POST') {
    return {
      statusCode: 405,
      body: JSON.stringify({ error: 'Method not allowed' })
    };
  }

  try {
    const { url } = JSON.parse(event.body);

    if (!url) {
      return {
        statusCode: 400,
        body: JSON.stringify({ error: 'URL is required' })
      };
    }

    // Fetch job posting
    console.log(`Fetching job posting from: ${url}`);
    const jobDescription = await fetchJobDescription(url);

    if (!jobDescription) {
      return {
        statusCode: 400,
        body: JSON.stringify({ error: 'Could not extract job description from the provided URL' })
      };
    }

    // Analyze job description
    console.log('Analyzing job description...');
    const skills = await analyzeJobSkills(jobDescription);

    return {
      statusCode: 200,
      body: JSON.stringify(skills)
    };
  } catch (error) {
    console.error('Error processing job analysis:', error);

    return {
      statusCode: 500,
      body: JSON.stringify({
        error: 'Failed to analyze job posting',
        details: error.message
      })
    };
  }
};

async function fetchJobDescription(url) {
  try {
    const response = await axios.get(url, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
      }
    });

    const html = response.data;
    const $ = cheerio.load(html);

    // Try to extract from JSON-LD
    let jobDescription = '';
    $('script[type="application/ld+json"]').each((_, el) => {
      try {
        const data = JSON.parse($(el).html());
        if (data['@type'] === 'JobPosting' && data.description) {
          jobDescription = data.description;
          return false; // Break the loop
        }
      } catch (e) {
        // Continue if JSON parsing fails
      }
    });

    // If not found in JSON-LD, try meta tags
    if (!jobDescription) {
      const meta = $('meta[property="og:description"]').attr('content');
      if (meta) jobDescription = meta;
    }

    // If still not found, try common job description containers
    if (!jobDescription) {
      const selectors = [
        '.job-description', '#job-description', '.description',
        '[data-automation="jobDescription"]', '.job-details'
      ];

      for (const selector of selectors) {
        if ($(selector).length) {
          jobDescription = $(selector).text();
          break;
        }
      }
    }

    // If still nothing, get the whole body text as fallback
    if (!jobDescription) {
      jobDescription = $('body').text();
    }

    return jobDescription.trim();
  } catch (error) {
    console.error('Error fetching job description:', error);
    throw new Error(`Failed to fetch job description: ${error.message}`);
  }
}

async function analyzeJobSkills(jobDescription) {
  try {
    const prompt = `
      Extract the required skills from the following job description.
      
      For the output:
      1. First identify the job title
      2. Then organize skills into these categories:
         - Technical Skills (programming languages, tools, technologies)
         - Soft Skills (interpersonal, communication, etc.)
         - Education and Experience (degrees, years of experience, etc.)
      3. List any preferred skills separately
      
      Format the output as a JSON object with this structure:
      {
          "job_title": "Title of the position",
          "required_skills": {
              "technical_skills": ["skill1", "skill2"],
              "soft_skills": ["skill1", "skill2"],
              "education": ["requirement1"],
              "experience": ["requirement1", "requirement2"]
          },
          "preferred_skills": ["skill1", "skill2"]
      }
      
      Job Description:
      ${jobDescription}
    `;

    const response = await openai.chat.completions.create({
      model: "gpt-3.5-turbo",
      messages: [
        {
          role: "system",
          content: "You extract structured information from job descriptions and output only valid JSON."
        },
        {
          role: "user",
          content: prompt
        }
      ],
      temperature: 0.1,
    });

    const content = response.choices[0].message.content.trim();

    try {
      // Try to parse JSON directly
      return JSON.parse(content);
    } catch (e) {
      // If direct parsing fails, try to extract JSON from text
      const jsonMatch = content.match(/{[\s\S]*}/);
      if (jsonMatch) {
        try {
          return JSON.parse(jsonMatch[0]);
        } catch (e2) {
          // If all parsing fails, return raw text
          return { raw_output: content };
        }
      } else {
        return { raw_output: content };
      }
    }
  } catch (error) {
    console.error('Error analyzing job skills with OpenAI:', error);
    throw new Error(`Failed to analyze job skills: ${error.message}`);
  }
}
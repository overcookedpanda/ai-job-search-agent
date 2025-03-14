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

    try {
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
    } catch (fetchError) {
      console.error('Detailed fetch error:', {
        message: fetchError.message,
        stack: fetchError.stack,
        response: fetchError.response ? {
          status: fetchError.response.status,
          statusText: fetchError.response.statusText,
          headers: fetchError.response.headers,
          data: fetchError.response.data
        } : 'No response data'
      });

      return {
        statusCode: 500,
        body: JSON.stringify({
          error: 'Failed to fetch job description',
          details: fetchError.message,
          url: url
        })
      };
    }
  } catch (error) {
    console.error('General error processing job analysis:', {
      message: error.message,
      stack: error.stack
    });

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
    console.log('Making request with headers:', {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
      'Accept': 'text/html,application/xhtml+xml,application/xml',
      'Accept-Language': 'en-US,en;q=0.9',
    });

    const response = await axios.get(url, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml',
        'Accept-Language': 'en-US,en;q=0.9',
      },
      timeout: 10000 // 10 seconds timeout
    });

    console.log('Response status:', response.status);
    console.log('Response headers:', response.headers);

    const html = response.data;
    console.log('HTML length:', html.length);

    // Log a sample of the HTML to see what we're working with
    console.log('HTML sample:', html.substring(0, 300) + '...');

    const $ = cheerio.load(html);

    // Try to extract from JSON-LD
    let jobDescription = '';
    const jsonLdScripts = $('script[type="application/ld+json"]');
    console.log(`Found ${jsonLdScripts.length} JSON-LD scripts`);

    jsonLdScripts.each((_, el) => {
      try {
        const scriptContent = $(el).html();
        console.log('JSON-LD content sample:', scriptContent.substring(0, 200) + '...');

        const data = JSON.parse(scriptContent);
        if (data['@type'] === 'JobPosting' && data.description) {
          console.log('Found job description in JSON-LD!');
          jobDescription = data.description;
          return false; // Break the loop
        }
      } catch (e) {
        console.error('Error parsing JSON-LD:', e.message);
      }
    });

    // If not found in JSON-LD, try meta tags
    if (!jobDescription) {
      const meta = $('meta[property="og:description"]').attr('content');
      if (meta) {
        console.log('Found job description in meta tags');
        jobDescription = meta;
      }
    }

    // If still not found, try common job description containers
    if (!jobDescription) {
      const selectors = [
        '.job-description', '#job-description', '.description',
        '[data-automation="jobDescription"]', '.job-details'
      ];

      for (const selector of selectors) {
        const elements = $(selector);
        if (elements.length) {
          console.log(`Found ${elements.length} elements with selector: ${selector}`);
          jobDescription = elements.text();
          break;
        }
      }
    }

    // If still nothing, get the whole body text as fallback
    if (!jobDescription) {
      console.log('No specific job description found, using body text');
      jobDescription = $('body').text();
    }

    console.log('Extracted job description length:', jobDescription.length);
    console.log('Job description sample:', jobDescription.substring(0, 200) + '...');

    return jobDescription.trim();
  } catch (error) {
    console.error('Error fetching job description:', {
      message: error.message,
      stack: error.stack,
      response: error.response ? {
        status: error.response.status,
        statusText: error.response.statusText,
        headers: error.response.headers
      } : 'No response'
    });

    throw error;
  }
}

async function analyzeJobSkills(jobDescription) {
  try {
    console.log('Starting OpenAI analysis');
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
      model: "gpt-4-turbo", // Upgrade from gpt-3.5-turbo
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
    console.log('OpenAI response received, length:', content.length);
    console.log('Response sample:', content.substring(0, 200) + '...');

    try {
      // Try to parse JSON directly
      return JSON.parse(content);
    } catch (e) {
      console.error('Error parsing OpenAI response as JSON:', e.message);

      // If direct parsing fails, try to extract JSON from text
      const jsonMatch = content.match(/{[\s\S]*}/);
      if (jsonMatch) {
        try {
          console.log('Found JSON pattern in response, attempting to parse');
          return JSON.parse(jsonMatch[0]);
        } catch (e2) {
          console.error('Error parsing extracted JSON pattern:', e2.message);
          // If all parsing fails, return raw text
          return { raw_output: content };
        }
      } else {
        console.log('No JSON pattern found in response, returning raw output');
        return { raw_output: content };
      }
    }
  } catch (error) {
    console.error('Error analyzing job skills with OpenAI:', {
      message: error.message,
      stack: error.stack
    });
    throw error;
  }
}
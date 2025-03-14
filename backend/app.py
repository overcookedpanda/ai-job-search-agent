from flask import Flask, request, jsonify
from flask_cors import CORS
import asyncio
import json
import re
import html
import requests
import logging
import os
import openai
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from agents import Agent, Runner, function_tool, RunConfig, set_tracing_export_api_key

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

api_key = os.environ.get('OPENAI_API_KEY')
if not api_key:
    print("WARNING: OPENAI_API_KEY environment variable is not set")
else:
    print(f"Using OpenAI API key starting with: {api_key[:4]}{'*' * 8}")
    # Explicitly set the API key for the OpenAI client
    openai.api_key = api_key
    set_tracing_export_api_key(api_key)

app = Flask(__name__)
CORS(app)


@function_tool
def fetch_job_description(url: str) -> str:
    """Fetches and extracts the job description from a job posting URL."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        # Try to extract from JSON-LD first (most reliable)
        soup = BeautifulSoup(response.text, 'html.parser')
        job_description = ""

        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                if data.get('@type') == 'JobPosting' and 'description' in data:
                    job_description = data['description']
                    # Clean up the text
                    job_description = html.unescape(job_description)
                    # Fix common encoding issues
                    job_description = job_description.replace('\xa0', ' ')
                    job_description = re.sub(r'\s+', ' ', job_description).strip()
                    break
            except:
                continue

        if not job_description:
            # Fallback to meta description
            meta_desc = soup.find('meta', property='og:description')
            if meta_desc and meta_desc.get('content'):
                job_description = html.unescape(meta_desc.get('content'))

        # If still not found, try common job description containers
        if not job_description:
            selectors = [
                '.job-description', '#job-description', '.description',
                '[data-automation="jobDescription"]', '.job-details'
            ]

            for selector in selectors:
                elements = soup.select(selector)
                if elements:
                    job_description = elements[0].get_text()
                    break

        # If still not found, use body text as a last resort
        if not job_description:
            job_description = soup.body.get_text()

        return job_description

    except Exception as e:
        return f"Error fetching job description: {str(e)}"


@function_tool
def extract_skills(job_description: str) -> dict:
    """Extracts key skills from a job description using GPT."""
    import openai
    import json
    client = openai.OpenAI()  # Ensure OPENAI_API_KEY is set in environment

    prompt = """
    Extract the required skills from the following job description.

    For the output:
    1. First identify the job title
    2. Then provide the skills as a structured list separated by type
    3. Separate required from preferred skills

    Format the output as a JSON object with this structure:
    {
        "job_title": "Title of the position",
        "company": "Name of company if mentioned",
        "salary": "Salary range if mentioned",
        "required_skills": {
            "technical_skills": ["skill1", "skill2"],
            "soft_skills": ["skill1", "skill2"],
            "education": ["requirement1"],
            "experience": ["requirement1", "requirement2"]
        },
        "preferred_skills": ["skill1", "skill2"]
    }

    Provide ONLY the JSON output, no additional text.

    Job Description:
    """

    response = client.chat.completions.create(
        model="chatgpt-4o-latest",
        messages=[
            {"role": "system",
             "content": "You extract structured information from job descriptions and output only valid JSON."},
            {"role": "user", "content": prompt + job_description}
        ],
        temperature=0.1,
    )

    skills_text = response.choices[0].message.content.strip()

    # Find JSON within the response if there's any extra text
    json_pattern = re.compile(r'({.*})', re.DOTALL)
    json_match = json_pattern.search(skills_text)

    if json_match:
        skills_text = json_match.group(1)

    try:
        skills_dict = json.loads(skills_text)
        return skills_dict
    except json.JSONDecodeError:
        # Fallback to simple list if JSON parsing fails
        skills = [skill.strip() for skill in skills_text.split(',') if skill.strip()]
        return {"job_title": "Unknown", "required_skills": {"technical_skills": skills}}


# Define the agent
agent = Agent(
    name="JobSkillsExtractor",
    instructions="You are an agent that extracts required skills from job application links.",
    tools=[fetch_job_description, extract_skills],
)


# Helper function to run async code
def run_async(coro):
    try:
        logger.info("Starting async execution with tracing enabled")
        return asyncio.run(coro)
    except RuntimeError as e:
        # Handle case where event loop is already running
        if "already running" in str(e):
            logger.info("Event loop already running, using existing loop")
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(coro)
        raise


@app.route('/api/analyze-job', methods=['POST'])
def analyze_job():
    data = request.json
    if not data or not data.get('url'):
        return jsonify({"error": "URL is required"}), 400

    url = data['url']

    try:
        # Create a runner for the agent with explicit trace settings
        runner = Runner()

        # Log OpenAI key info (safely)
        api_key = os.environ.get('OPENAI_API_KEY', '')
        logger.info(f"Using OpenAI API key starting with: {api_key[:4]}{'*' * 10}")

        # Create an explicit config with tracing enabled
        run_config = RunConfig(
            workflow_name='Job Details Extractor',
            tracing_disabled=False,  # Explicitly enable tracing
        )

        logger.info(f"Running with config: {run_config}")

        # Run the agent with the URL using our async helper
        result = run_async(runner.run(
            starting_agent=agent,
            input=url,
            context={},
            run_config=run_config
        ))

        # Log successful completion of agent run
        logger.info("Agent run completed successfully")

        # Process the result to ensure it's in JSON format
        final_output = result.final_output

        # Check if the output looks like a JSON string
        if '{' in final_output:
            try:
                # Try to extract and parse JSON if present in the output
                json_pattern = re.compile(r'({.*})', re.DOTALL)
                match = json_pattern.search(final_output)

                if match:
                    skills_data = json.loads(match.group(1))
                    return jsonify(skills_data)
                else:
                    # If result is a string representation of a dict
                    import ast
                    skills_data = ast.literal_eval(final_output)
                    return jsonify(skills_data)
            except (json.JSONDecodeError, ValueError, SyntaxError) as e:
                return jsonify({"raw_output": final_output})
        else:
            return jsonify({"raw_output": final_output})

    except Exception as e:
        print(f"Error in analyze_job: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/test', methods=['GET'])
def test():
    """A simple endpoint to test if the API is working"""
    return jsonify({"message": "API is working!"}), 200


if __name__ == '__main__':
    app.run(debug=False, port=10000)
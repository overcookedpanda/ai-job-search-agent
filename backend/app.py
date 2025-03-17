from flask import Flask, request, jsonify
from flask_cors import CORS
import asyncio
import json
import re
import html
import requests
import logging
import os
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import Dict, List, Optional
from agents import Agent, Runner, function_tool, set_tracing_export_api_key

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

api_key = os.environ.get('OPENAI_API_KEY')
if not api_key:
    logger.error("OPENAI_API_KEY environment variable is not set")
else:
    logger.info(f"Using OpenAI API key: {api_key[:3]}...{api_key[-4:]}")
    # Set the API key for the OpenAI Agents SDK
    set_tracing_export_api_key(api_key)

app = Flask(__name__)
CORS(app)


@function_tool
async def fetch_web_content(url: str) -> dict:
    """
    Fetches content from a URL with robust error handling and retry logic.
    Returns both HTML content and text content when successful.
    """
    import requests
    from bs4 import BeautifulSoup
    from urllib.parse import urlparse
    import time

    # Validate URL format
    try:
        result = urlparse(url)
        if not all([result.scheme, result.netloc]):
            return {
                "success": False,
                "error": "Invalid URL format. Please provide a complete URL including http:// or https://",
                "html": None,
                "text": None
            }
    except Exception:
        return {
            "success": False,
            "error": "URL parsing error",
            "html": None,
            "text": None
        }

    # Define headers to mimic a browser
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    # Retry logic
    max_retries = 3
    retry_delay = 2  # seconds

    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, timeout=15)

            # Check if the request was successful
            if response.status_code == 200:
                # Store the full raw HTML
                raw_html = response.text

                # Parse the content with BeautifulSoup for extracting text
                soup = BeautifulSoup(raw_html, 'html.parser')

                # Remove script and style elements for the text version only
                for script_or_style in soup(["script", "style"]):
                    script_or_style.decompose()

                # Get the text content
                text = soup.get_text(separator=' ', strip=True)

                # Clean up the text content
                import re
                # Replace multiple spaces with single space
                text = re.sub(r'\s+', ' ', text)
                # Replace multiple newlines with single newline
                text = re.sub(r'\n+', '\n', text)
                text = text.strip()

                return {
                    "success": True,
                    "error": None,
                    "html": raw_html,  # Return the complete raw HTML
                    "text": text,
                    "title": soup.title.string if soup.title else None,
                    "status_code": response.status_code,
                    "url": response.url  # Include the final URL (after any redirects)
                }
            else:
                # If it's the last attempt, return the error
                if attempt == max_retries - 1:
                    return {
                        "success": False,
                        "error": f"HTTP error: {response.status_code}",
                        "html": None,
                        "text": None,
                        "status_code": response.status_code
                    }

        except requests.exceptions.Timeout:
            if attempt == max_retries - 1:
                return {
                    "success": False,
                    "error": "Request timed out",
                    "html": None,
                    "text": None
                }

        except requests.exceptions.TooManyRedirects:
            return {
                "success": False,
                "error": "Too many redirects",
                "html": None,
                "text": None
            }

        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                return {
                    "success": False,
                    "error": f"Request error: {str(e)}",
                    "html": None,
                    "text": None
                }

        # Wait before retrying
        time.sleep(retry_delay)

    # This should not be reached due to the returns in the loop
    return {
        "success": False,
        "error": "Unknown error occurred",
        "html": None,
        "text": None
    }


@function_tool
async def extract_job_description(html_content: str, url: str) -> dict:
    """
    Extracts job description content from HTML content.
    Uses AI-based text extraction and summarization for more reliable results.

    Args:
        html_content: The HTML content of the job posting page
        url: The URL of the job posting (to help identify the site type)

    Returns:
        A dictionary with the job description and metadata
    """
    from bs4 import BeautifulSoup
    import json
    import re
    from openai import OpenAI

    client = OpenAI()

    result = {
        "success": True,
        "job_description": "",
        "extraction_method": "",
        "title": "",
        "company": "",
    }

    try:
        # Parse the HTML with BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')

        # Get the page title
        result["title"] = soup.title.string if soup.title else ""

        # Remove script, style, and other non-content elements
        for element in soup(['script', 'style', 'nav', 'footer', 'head', 'header', 'iframe', 'noscript']):
            element.decompose()

        # Get text from main content areas
        main_content = ""

        # Try to find the main content area
        main_elements = soup.select(
            'main, [role="main"], article, .job-description, #job-description, .description, .content, .job-details')
        if main_elements:
            # Use the first main element found
            main_content = main_elements[0].get_text(separator=' ', strip=True)
        else:
            # Fall back to body content
            body = soup.body
            if body:
                main_content = body.get_text(separator=' ', strip=True)
            else:
                main_content = soup.get_text(separator=' ', strip=True)

        # Clean up the text
        main_content = re.sub(r'\s+', ' ', main_content).strip()

        # If the content is too long, we'll need to truncate it for the API call
        if len(main_content) > 12000:
            # Keep the beginning and end, where job details are often found
            main_content = main_content[:6000] + " ... " + main_content[-6000:]

        # Use AI to extract the job description
        response = client.chat.completions.create(
            model="gpt-3.5-turbo-16k",  # Use a model with larger context
            messages=[
                {"role": "system", "content": """You are an expert at extracting job information from web pages.
                Extract the most relevant job posting details from the provided text. Focus on:
                1. Job title
                2. Company name
                3. Job description
                4. Responsibilities
                5. Requirements
                6. Qualifications

                Format your response as coherent paragraphs containing only the job posting information.
                Filter out navigation elements, footers, headers, and other website elements.
                Include all relevant details about the position."""},
                {"role": "user",
                 "content": f"Extract the job posting information from this web page content from URL: {url}\n\n{main_content}"}
            ],
            temperature=0.2,  # Keep it focused on extraction
            max_tokens=4000,  # Allow for a detailed extraction
        )

        job_description = response.choices[0].message.content.strip()

        result["job_description"] = job_description
        result["extraction_method"] = "ai_extraction"

        # Try to extract title and company if not in the output
        if "title" not in result or not result["title"]:
            title_match = re.search(r"Job Title:?\s*([^\n]+)", job_description)
            if title_match:
                result["title"] = title_match.group(1).strip()

        company_match = re.search(r"Company:?\s*([^\n]+)", job_description)
        if company_match:
            result["company"] = company_match.group(1).strip()

        return result

    except Exception as e:
        return {
            "success": False,
            "job_description": "Error extracting job description",
            "extraction_method": "error",
            "error": str(e)
        }


# Define the structured output model
class JobSkillsOutput(BaseModel):
    job_title: str
    company: Optional[str] = None
    salary: Optional[str] = None
    required_skills: Dict[str, List[str]]
    preferred_skills: Optional[List[str]] = None
    benefits: Optional[List[str]] = None
    location: Optional[str] = None


# 1. Content Retrieval Agent
web_content_agent = Agent(
    name="WebContentRetriever",
    instructions="""You are a specialist in retrieving web content. 
    Your only task is to retrieve the content from the provided URL using the fetch_web_content tool.
    Make no modifications to the content and simply pass along the result.""",
    model="gpt-3.5-turbo",  # Using a faster model since this is a simple task
    tools=[fetch_web_content]
)

# 2. Job Description Extraction Agent
job_description_agent = Agent(
    name="JobDescriptionExtractor",
    instructions="""You are a specialist in extracting job descriptions from web content.
    Your task is to identify and extract the most relevant job description content from the web page.
    Use the extract_job_description tool to process the HTML and text content.""",
    model="gpt-4o-mini",
    tools=[extract_job_description]
)

# 3. Skills Analysis Agent
skills_analysis_agent = Agent(
    name="SkillsAnalyzer",
    instructions="""You are an expert at analyzing job descriptions and extracting key information.
    Carefully read the job description and identify:

    1. The job title
    2. The company name
    3. Salary information (if available)
    4. Technical skills required
    5. Soft skills required
    6. Education requirements
    7. Experience requirements
    8. Preferred (but not required) skills
    9. Benefits offered
    10. Location/remote work information

    Categorize the information clearly and be comprehensive in your analysis.
    """,
    model="gpt-4o-mini",
    output_type=JobSkillsOutput
)

# Now set up our main orchestration agent
job_analysis_orchestrator = Agent(
    name="JobAnalysisOrchestrator",
    instructions="""You are an assistant that coordinates job posting analysis.
    Your workflow is:
    1. First retrieve the web content from the URL
    2. Then extract the job description from the web content
    3. Finally, analyze the job description to identify skills and requirements

    Don't skip any steps and make sure to follow this workflow precisely.""",
    model="gpt-4o-mini",
    tools=[fetch_web_content],  # Give it the ability to fetch content directly
    handoffs=[web_content_agent, job_description_agent, skills_analysis_agent]
)


# Helper function to run async code
def run_async(coro):
    try:
        logger.info("Starting async execution")
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
        # Use the orchestrator agent to manage the workflow
        result = run_async(Runner.run(
            starting_agent=job_analysis_orchestrator,
            input=url,
            context={}
        ))

        # With output_type specified, the model should return a structured object
        if hasattr(result.final_output, "model_dump"):
            # This is a Pydantic model
            return jsonify(result.final_output.model_dump())
        elif isinstance(result.final_output, dict):
            # This is already a dict
            return jsonify(result.final_output)
        else:
            # This is probably a string, try to extract JSON
            try:
                import re
                json_pattern = re.compile(r'({.*})', re.DOTALL)
                match = json_pattern.search(result.final_output)
                if match:
                    skills_data = json.loads(match.group(1))
                    return jsonify(skills_data)
                else:
                    return jsonify({"raw_output": result.final_output})
            except Exception:
                return jsonify({"raw_output": result.final_output})

    except Exception as e:
        logger.error(f"Error in analyze_job: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """Simple health check endpoint to wake up the backend"""
    return jsonify({
        "status": "online",
        "message": "Backend is ready"
    }), 200


if __name__ == '__main__':
    app.run(debug=False, port=10000)
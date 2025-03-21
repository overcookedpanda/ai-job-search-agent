from flask import Flask, request, jsonify
from flask_cors import CORS
import asyncio
import json
import logging
import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import List, Optional
from agents import Agent, Runner, function_tool, set_tracing_export_api_key, WebSearchTool
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from metrics import track_openai_usage, init_metrics, MetricsMiddleware

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


init_metrics()
app.wsgi_app = MetricsMiddleware(app.wsgi_app)


def track_openai_call(client_method, *args, **kwargs):
    """
    Wrapper for OpenAI API calls to track usage metrics

    Args:
        client_method: The OpenAI client method to call
        *args, **kwargs: Arguments to pass to the method

    Returns:
        The result of the OpenAI API call
    """
    model = kwargs.get('model', 'unknown')
    logger.info(f"Making OpenAI API call to model: {model}")

    response = client_method(*args, **kwargs)

    # Debug the response structure
    logger.debug(f"Response type: {type(response)}")
    if hasattr(response, 'usage'):
        logger.debug(f"Usage attributes: {dir(response.usage)}")
    else:
        logger.debug("Response has no usage attribute")

    # Extract usage information if available
    if hasattr(response, 'usage'):
        try:
            # OpenAI Chat API structure
            if hasattr(response.usage, 'prompt_tokens'):
                input_tokens = response.usage.prompt_tokens
                output_tokens = response.usage.completion_tokens
                logger.info(f"Tracking OpenAI usage for {model}: {input_tokens} input, {output_tokens} output tokens")
                track_openai_usage(model, input_tokens, output_tokens)
            # Agents SDK structure
            elif hasattr(response.usage, 'input_tokens'):
                input_tokens = response.usage.input_tokens
                output_tokens = response.usage.output_tokens
                logger.info(f"Tracking OpenAI usage for {model}: {input_tokens} input, {output_tokens} output tokens")
                track_openai_usage(model, input_tokens, output_tokens)
            else:
                logger.warning(f"Unknown usage structure: {vars(response.usage)}")
        except Exception as e:
            logger.warning(f"Error tracking OpenAI usage: {str(e)}")

    return response


def track_agent_run(result):
    """
    Track token usage from an Agent run result

    Args:
        result: The RunResult from an Agent run
    """
    # Try to get the model name from the agent for better context
    agent_model = 'unknown'
    try:
        if hasattr(result, 'last_agent') and hasattr(result.last_agent, 'model'):
            agent_model = result.last_agent.model
            logger.info(f"Found agent model from last_agent: {agent_model}")
        elif result.new_items:
            for item in result.new_items:
                if hasattr(item, 'agent') and hasattr(item.agent, 'model'):
                    agent_model = item.agent.model
                    logger.info(f"Found agent model from new_items: {agent_model}")
                    break
    except Exception as e:
        logger.warning(f"Error extracting agent model: {str(e)}")

    # Log raw_responses information
    logger.info(f"Number of raw_responses: {len(result.raw_responses) if hasattr(result, 'raw_responses') else 0}")

    # Only process actual response data with usage information
    tracked_any = False
    for i, response in enumerate(result.raw_responses):
        logger.debug(f"Processing raw_response {i}, type: {type(response)}")

        if hasattr(response, 'usage'):
            # Use the model from the response if available, otherwise use the agent model
            model = getattr(response, 'model', agent_model)
            logger.info(f"Found model for response {i}: {model}")

            # Log usage attributes
            if hasattr(response.usage, '__dict__'):
                logger.debug(f"Usage attributes: {response.usage.__dict__}")
            else:
                logger.debug(f"Usage attributes: {dir(response.usage)}")

            try:
                # Only track if we have both input and output tokens
                if hasattr(response.usage, 'input_tokens') and hasattr(response.usage, 'output_tokens'):
                    input_tokens = response.usage.input_tokens
                    output_tokens = response.usage.output_tokens

                    logger.info(f"Found token counts - input: {input_tokens}, output: {output_tokens}")

                    # Only record if we have actual token counts
                    if input_tokens > 0 or output_tokens > 0:
                        track_openai_usage(model, input_tokens, output_tokens)
                        tracked_any = True
                        logger.info(f"Tracked usage for model {model}")
                else:
                    # Check for OpenAI direct API format
                    if hasattr(response.usage, 'prompt_tokens') and hasattr(response.usage, 'completion_tokens'):
                        input_tokens = response.usage.prompt_tokens
                        output_tokens = response.usage.completion_tokens

                        logger.info(
                            f"Found OpenAI format token counts - prompt: {input_tokens}, completion: {output_tokens}")

                        if input_tokens > 0 or output_tokens > 0:
                            track_openai_usage(model, input_tokens, output_tokens)
                            tracked_any = True
                            logger.info(f"Tracked usage for model {model} (OpenAI format)")
                    else:
                        logger.warning(f"Response {i} has usage but missing expected token attributes")
            except Exception as e:
                logger.warning(f"Error extracting token usage from response {i}: {str(e)}")
        else:
            logger.debug(f"Response {i} has no usage attribute")

    # Log if we couldn't track any actual usage
    if tracked_any:
        logger.info(f"Successfully tracked usage for model {agent_model}")
    else:
        logger.warning(f"No actual token usage data found for model {agent_model}")


@function_tool
def parse_url(url: str) -> dict:
    """
    Performs basic parsing of a URL to validate its structure.

    Args:
        url: The URL to parse

    Returns:
        A dictionary with parsed URL components and validation status
    """
    from urllib.parse import urlparse

    try:
        parsed_url = urlparse(url)
        if not all([parsed_url.scheme, parsed_url.netloc]):
            return {
                "is_valid": False,
                "reason": "Invalid URL structure. URL must include http:// or https://"
            }

        return {
            "is_valid": True,
            "scheme": parsed_url.scheme,
            "domain": parsed_url.netloc,
            "path": parsed_url.path,
            "query": parsed_url.query
        }
    except Exception as e:
        return {
            "is_valid": False,
            "reason": f"URL parsing error: {str(e)}"
        }


@function_tool
async def fetch_web_content(url: str) -> dict:
    """
    Fetches content from a URL using Firecrawl with robust error handling.

    Args:
        url: The URL to scrape

    Returns:
        A dictionary containing scraping results or error information
    """
    import os
    from firecrawl import FirecrawlApp

    # Retrieve Firecrawl API key from environment
    firecrawl_api_key = os.environ.get('FIRECRAWL_API_KEY')
    if not firecrawl_api_key:
        return {
            "success": False,
            "error": "Firecrawl API key not found in environment variables",
            "text": None
        }

    try:
        # Initialize Firecrawl app
        app = FirecrawlApp(api_key=firecrawl_api_key)

        # Scrape the URL with both markdown and HTML formats
        scrape_result = app.scrape_url(url, params={'formats': ['markdown']})

        # Check if scraping was successful
        if not scrape_result:
            return {
                "success": False,
                "error": "No content retrieved from the URL",
                "text": None
            }

        return {
            "success": True,
            "error": None,
            "text": scrape_result.get('markdown', ''),
            "title": scrape_result.get('metadata', {}).get('title', ''),
            "url": url
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Firecrawl scraping error: {str(e)}",
            "text": None
        }


@function_tool
async def validate_job_url(url: str) -> dict:
    """
    Analyzes a URL to determine if it's likely a job posting.

    Args:
        url: The URL to analyze

    Returns:
        A dictionary with validation results
    """
    from openai import OpenAI
    import json

    client = OpenAI()

    prompt = f"""Analyze this URL: {url}

    Is this likely to be a job posting URL? Consider:
    1. Domain - Is it a known job board (indeed, linkedin, glassdoor, etc.) or company careers page?
    2. URL path - Does it contain job-related terms like "job", "career", "position", "apply"?
    3. URL parameters - Are there job ID parameters or similar?
    4. Overall structure - Does it match common patterns for job listings?

    Return a JSON object with these fields:
    - is_valid: true if this appears to be a valid URL structure
    - likely_job_posting: true if this is likely a job posting page
    - confidence: a number between 0 and 1 indicating your confidence
    - reason: a brief explanation of your decision
    """

    response = track_openai_call(
        client.chat.completions.create,
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are an expert at analyzing URLs to determine if they are job postings."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.1
    )

    try:
        content = response.choices[0].message.content
        # Try to extract JSON from the response
        import re
        json_pattern = re.compile(r'{.*}', re.DOTALL)
        match = json_pattern.search(content)
        if match:
            result = json.loads(match.group(0))
            return result
        else:
            # Fallback if we couldn't extract JSON
            return {
                "is_valid": True,
                "likely_job_posting": True,
                "confidence": 0.5,
                "reason": "Could not parse validation result"
            }
    except Exception as e:
        return {
            "is_valid": True,
            "likely_job_posting": True,
            "confidence": 0.5,
            "reason": f"Error during validation: {str(e)}"
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
        response = track_openai_call(
                client.chat.completions.create,
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

class URLValidationResult(BaseModel):
    is_valid: bool = Field(..., description="Whether the URL has a valid structure")
    likely_job_posting: bool = Field(..., description="Whether this is likely a job posting URL")
    confidence: float = Field(..., description="Confidence level between 0 and 1")
    reason: str = Field(..., description="Explanation for the validation result")

# Define the structured output model
class RequiredSkills(BaseModel):
    technical_skills: List[str] = Field(default_factory=list, description="Technical skills required for the job")
    soft_skills: List[str] = Field(default_factory=list, description="Soft skills required for the job")
    education: List[str] = Field(default_factory=list, description="Education requirements")
    experience: List[str] = Field(default_factory=list, description="Experience requirements")


class JobSkillsOutput(BaseModel):
    job_title: str = Field(..., description="The title of the job position")
    company: Optional[str] = Field(None, description="The company offering the position")
    salary: Optional[str] = Field(None, description="Salary range if mentioned")
    required_skills: RequiredSkills = Field(..., description="Required skills categorized by type")
    preferred_skills: Optional[List[str]] = Field(None, description="Skills that are preferred but not required")
    benefits: Optional[List[str]] = Field(None, description="Benefits mentioned in the job posting")
    location: Optional[str] = Field(None, description="Job location (remote, hybrid, onsite, city, etc.)")


class JobDetails(BaseModel):
    benefits: Optional[List[str]] = None
    company: str
    job_title: str
    location: str
    preferred_skills: Optional[List[str]] = None
    required_skills: RequiredSkills
    salary: Optional[str] = None


class JobRequest(BaseModel):
    job_details: JobDetails


class CompanyResearchOutput(BaseModel):
    company_overview: str
    culture_and_values: Optional[str] = None
    interview_process: Optional[str] = None
    recent_news: Optional[str] = None


class PreparationTip(BaseModel):
    title: str
    description: str


class PrepTipsOutput(BaseModel):
    preparation_tips: List[PreparationTip]


class InterviewQuestion(BaseModel):
    question: str
    difficulty: str  # Easy, Medium, Hard
    answer_tips: str


class TechnicalQuestionsOutput(BaseModel):
    technical_questions: List[InterviewQuestion]  # Direct list without the "response" wrapper


class BehavioralQuestionsOutput(BaseModel):
    behavioral_questions: List[InterviewQuestion]  # Direct list of behavioral questions


class InterviewPrepOutput(BaseModel):
    company_research: CompanyResearchOutput
    technical_questions: List[InterviewQuestion]
    behavioral_questions: List[InterviewQuestion]
    preparation_tips: List[PreparationTip]


url_validation_agent = Agent(
    name="URLValidator",
    instructions="""You are an expert at analyzing URLs to determine if they are job postings.

    Analyze the given URL and determine if it's likely to be a job posting page. Consider:
    1. Domain - Is it a known job board (indeed, linkedin, glassdoor, etc.) or company careers page?
    2. URL path - Does it contain job-related terms like "job", "career", "position", "apply"?
    3. URL parameters - Are there job ID parameters or similar?
    4. Overall structure - Does it match common patterns for job listings?

    Known job sites include: indeed.com, linkedin.com/jobs, glassdoor.com, monster.com, ziprecruiter.com, 
    lever.co, greenhouse.io, workday.com, careers pages, and company websites with /jobs or /careers paths.

    Return your analysis in the required format, being very careful about whether this is likely a job posting.
    Only confirm likely_job_posting as true if you are reasonably confident it is an actual job posting URL.
    """,
    model="gpt-4o-mini",  # Using a model that supports structured outputs
    output_type=URLValidationResult
)


web_content_agent = Agent(
    name="WebContentRetriever",
    instructions="""You are a specialist in retrieving web content. 
    Your only task is to retrieve the content from the provided URL using the fetch_web_content tool.
    Make no modifications to the content and simply pass along the result.""",
    model="gpt-3.5-turbo",  # Using a faster model since this is a simple task
    tools=[fetch_web_content]
)

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

job_description_agent = Agent(
    name="JobDescriptionExtractor",
    instructions="""You are a specialist in extracting job descriptions from web content.
    Your task is to identify and extract the most relevant job description content from the web page.
    Use the extract_job_description tool to process the HTML and text content.

    Once you have successfully extracted the job description, you MUST hand off to the SkillsAnalyzer agent
    to analyze the skills and qualifications required for the position.""",
    model="gpt-4o-mini",
    tools=[extract_job_description],
    handoffs=[skills_analysis_agent]
)

job_analysis_orchestrator = Agent(
    name="JobAnalysisOrchestrator",
    instructions="""You are an assistant that coordinates job posting analysis.
    Your workflow is:

    1. First parse the URL to verify it has a valid structure using the parse_url tool
    2. If the structure is valid, use the URLValidator to determine if it's likely a job posting
    3. If it's likely a job posting, retrieve the web content from the URL
    4. Then extract the job description from the web content
    5. Finally, analyze the job description to identify skills and requirements

    If the URL doesn't have a valid structure or doesn't look like a job posting, inform the user and do not proceed with retrieval.
    Don't skip any steps and make sure to follow this workflow precisely.
    """,
    model="gpt-4o-mini",
    tools=[
        parse_url,
        fetch_web_content,
        url_validation_agent.as_tool(
            tool_name="validate_job_url",
            tool_description="Analyzes a URL to determine if it's likely a job posting"
        )
    ],
    handoffs=[web_content_agent, job_description_agent, skills_analysis_agent]
)

preparation_tips_agent = Agent(
    name="InterviewCoach",
    instructions="""You are an interview coach who helps candidates prepare for job interviews.

    Based on the job requirements and company information provided, create 5 specific preparation tips that will
    help the candidate succeed in this particular interview. These should be tailored to the specific role and company.

    Each tip should include:
    1. A clear, concise title
    2. A detailed description with actionable advice

    Use web searches to find accurate and up-to-date information about interview best practices for this type of role.
    """,
    model="gpt-4o-mini",
    tools=[WebSearchTool()],
    output_type=PrepTipsOutput
)

behavioral_questions_agent = Agent(
    name="BehavioralInterviewer",
    instructions="""You are an expert interviewer who assesses cultural fit and soft skills.

    Based on the job requirements and company information already provided, create 5 behavioral interview questions that:
    1. Evaluate the candidate's soft skills and alignment with company values
    2. Range in difficulty (include easy, medium and hard questions)
    3. Include detailed answer tips for the candidate

    Use web searches to find accurate and up-to-date information about relevant behavioral skills for this role.

    Each question should help assess how well the candidate would fit within the company culture and succeed in the role.
    """,
    model="gpt-4o-mini",
    tools=[WebSearchTool()],
    output_type=BehavioralQuestionsOutput
)

technical_questions_agent = Agent(
    name="TechnicalInterviewer",
    instructions="""You are an expert technical interviewer who creates challenging questions for job candidates.

    Based on the job requirements and company information provided, create 5 technical interview questions that:
    1. Target specific technical skills required for the position
    2. Range in difficulty (include easy, medium and hard questions)
    3. Include detailed answer tips for the candidate

    Use web searches to find accurate and up-to-date information.

    Each question should test both theoretical knowledge and practical application.
    """,
    model="gpt-4o-mini",
    tools=[WebSearchTool()],
    output_type=TechnicalQuestionsOutput
)

company_research_agent = Agent(
    name="CompanyResearcher",
    instructions="""You are a professional company researcher who gathers information for job interview candidates.

    Research the given company thoroughly to provide:
    1. Company overview, products and services
    2. Company culture and values
    3. Interview process if available (try looking at Glassdoor or other sites)
    4. Recent developments or news

    Use web searches to find accurate and up-to-date information. Provide a comprehensive but concise summary that would
    help someone preparing for an interview at this company.
    """,
    model="gpt-4o-mini",
    tools=[WebSearchTool()],
    output_type=CompanyResearchOutput
)

interview_prep_orchestrator = Agent(
    name="InterviewPrepOrchestrator",
    instructions="""You are a master interview preparation coach who orchestrates a comprehensive interview prep plan.

    Your process involves the following agents working in sequence:
    1. CompanyResearcher - Researches the company
    2. TechnicalInterviewer - Creates technical interview questions relevant to the position at the company
    3. BehavioralInterviewer - Creates behavioral interview questions relevant to the position at the company
    4. InterviewCoach - Provides preparation tips relevant to the position at the company

    Your role is to initiate this process and compile the final results into a comprehensive interview preparation guide relevant to the position at the company.
    """,
    model="gpt-4o-mini",
    tools=[
        company_research_agent.as_tool(
            tool_name="CompanyResearcher",
            tool_description="Researches the company"
        ),
        technical_questions_agent.as_tool(
            tool_name="TechnicalInterviewer",
            tool_description="Creates technical interview questions relevant to the position at the company"
        ),
        behavioral_questions_agent.as_tool(
            tool_name="BehavioralInterviewer",
            tool_description="Creates behavioral interview questions relevant to the position at the company"
        ),
        preparation_tips_agent.as_tool(
            tool_name="InterviewCoach",
            tool_description="Provides preparation tips relevant to the position at the company"
        ),
        ],
    output_type=InterviewPrepOutput
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

        track_agent_run(result)

        # Check if we received an error message about URL validation
        if isinstance(result.final_output, str) and any(phrase in result.final_output.lower() for phrase in
                                                      ["not a job posting", "invalid url", "not valid", "doesn't appear to be"]):
            logger.info(f"URL validation failed for {url}: {result.final_output}")
            return jsonify({
                "error": "URL validation failed",
                "message": result.final_output
            }), 400

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


@app.route('/api/generate-questions', methods=['POST'])
def generate_interview_questions():
    """Endpoint to generate interview questions for a job."""
    try:
        data = request.get_json()
        job_request = JobRequest(**data)  # Parse and validate with Pydantic
    except Exception as e:
        logger.error(f"Invalid JSON payload: {str(e)}")
        return jsonify({"error": "Invalid job details format"}), 400

    logger.info(f'Received job details: {job_request}')

    try:
        # Run the orchestrator agent with structured input
        result = run_async(Runner.run(
            starting_agent=interview_prep_orchestrator,
            input=json.dumps(data),
            context={}
        ))

        track_agent_run(result)

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
        logger.error(f"Error generating interview questions: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """Simple health check endpoint to wake up the backend"""
    return jsonify({
        "status": "online",
        "message": "Backend is ready"
    }), 200


@app.route('/metrics', methods=['GET'])
def metrics():
    """Expose Prometheus metrics"""
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}


if __name__ == '__main__':
    app.run(debug=False, port=10000)
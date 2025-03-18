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
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX

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
    1. First retrieve the web content from the URL
    2. Then extract the job description from the web content
    3. Finally, analyze the job description to identify skills and requirements

    Don't skip any steps and make sure to follow this workflow precisely.""",
    model="gpt-4o-mini",
    tools=[fetch_web_content],  # Give it the ability to fetch content directly
    handoffs=[web_content_agent, job_description_agent, skills_analysis_agent]
)

preparation_tips_agent = Agent(
    name="InterviewCoach",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    You are an interview coach who helps candidates prepare for job interviews.

    Based on the job requirements and company information provided, create 5 specific preparation tips that will
    help the candidate succeed in this particular interview. These should be tailored to the specific role and company.

    Each tip should include:
    1. A clear, concise title
    2. A detailed description with actionable advice

    Use web searches to find accurate and up-to-date information about interview best practices for this type of role.
    """,
    model="gpt-4o",
    tools=[WebSearchTool()],
    output_type=PrepTipsOutput,
    handoffs=[]
)

behavioral_questions_agent = Agent(
    name="BehavioralInterviewer",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    You are an expert interviewer who assesses cultural fit and soft skills.

    Based on the job requirements and company information already provided, create 5 behavioral interview questions that:
    1. Evaluate the candidate's soft skills and alignment with company values
    2. Range in difficulty (include easy, medium and hard questions)
    3. Include detailed answer tips for the candidate

    Use web searches to find accurate and up-to-date information about relevant behavioral skills for this role.

    Each question should help assess how well the candidate would fit within the company culture and succeed in the role.

    CRITICAL INSTRUCTION: After completing your questions, you MUST hand off to the InterviewCoach agent.
    This is the final required step in the interview preparation process. Do not finish your response without performing this handoff.
    """,
    model="gpt-4o",
    tools=[WebSearchTool()],
    output_type=BehavioralQuestionsOutput,
    handoffs=[preparation_tips_agent]
)

technical_questions_agent = Agent(
    name="TechnicalInterviewer",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    You are an expert technical interviewer who creates challenging questions for job candidates.

    Based on the job requirements and company information provided, create 5 technical interview questions that:
    1. Target specific technical skills required for the position
    2. Range in difficulty (include easy, medium and hard questions)
    3. Include detailed answer tips for the candidate

    Use web searches to find accurate and up-to-date information.

    Each question should test both theoretical knowledge and practical application.

    CRITICAL INSTRUCTION: After completing your questions, you MUST hand off to the BehavioralInterviewer agent.
    This is a required step in the interview preparation process. Do not finish your response without performing this handoff.
    """,
    model="gpt-4o",
    tools=[WebSearchTool()],
    output_type=TechnicalQuestionsOutput,
    handoffs=[behavioral_questions_agent]
)

company_research_agent = Agent(
    name="CompanyResearcher",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    You are a professional company researcher who gathers information for job interview candidates.

    Research the given company thoroughly to provide:
    1. Company overview, products and services
    2. Company culture and values
    3. Interview process if available (try looking at Glassdoor or other sites)
    4. Recent developments or news

    Use web searches to find accurate and up-to-date information. Provide a comprehensive but concise summary that would
    help someone preparing for an interview at this company.

    After you have completed your research, hand off to the TechnicalInterviewer to generate technical questions based on your findings.
    """,
    model="gpt-4o",
    tools=[WebSearchTool()],
    output_type=CompanyResearchOutput,
    handoffs=[technical_questions_agent]
)

interview_prep_orchestrator = Agent(
    name="InterviewPrepOrchestrator",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    You are a master interview preparation coach who orchestrates a comprehensive interview prep plan.

    Your process involves the following agents working in sequence:
    1. CompanyResearcher - Researches the company
    2. TechnicalInterviewer - Creates technical interview questions
    3. BehavioralInterviewer - Creates behavioral interview questions
    4. InterviewCoach - Provides preparation tips

    Your role is to initiate this process and compile the final results into a comprehensive interview preparation guide.
    """,
    model="gpt-4o",
    handoffs=[company_research_agent],
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

        # Combine outputs from all agents into a single InterviewPrepOutput object
        combined_output = build_interview_prep_output(result)

        # Return the combined output as JSON
        return jsonify(combined_output.model_dump())

    except Exception as e:
        logger.error(f"Error generating interview questions: {str(e)}")
        return jsonify({"error": str(e)}), 500


def build_interview_prep_output(run_result):
    """
    Extract outputs from each agent and combine into a final InterviewPrepOutput model.
    """
    # Initialize variables to store outputs
    company_research = None
    technical_questions = []
    behavioral_questions = []
    preparation_tips = []

    # Loop through all the message output items
    for item in run_result.new_items:
        if getattr(item, 'type', None) == 'message_output_item':
            raw_item = getattr(item, 'raw_item', None)
            if raw_item and hasattr(raw_item, 'content') and raw_item.content:
                try:
                    # Extract the text content
                    text = raw_item.content[0].text
                    # Parse the JSON
                    data = json.loads(text)

                    # Determine which agent's output this is based on the content structure
                    if 'company_overview' in data:
                        company_research = CompanyResearchOutput(
                            company_overview=data.get('company_overview', ''),
                            culture_and_values=data.get('culture_and_values', ''),
                            interview_process=data.get('interview_process', ''),
                            recent_news=data.get('recent_news', '')
                        )
                    elif 'technical_questions' in data:
                        technical_questions = [InterviewQuestion(**q) for q in data['technical_questions']]
                    elif 'behavioral_questions' in data:
                        behavioral_questions = [InterviewQuestion(**q) for q in data['behavioral_questions']]
                    elif 'preparation_tips' in data:
                        preparation_tips = [PreparationTip(**tip) for tip in data['preparation_tips']]
                except (json.JSONDecodeError, KeyError, TypeError, AttributeError) as e:
                    logger.error(f"Error processing output item: {e}")

    # Fallback: If we couldn't extract from messages, try to get from final_output
    if hasattr(run_result, 'final_output'):
        if not preparation_tips and hasattr(run_result.final_output, 'preparation_tips'):
            preparation_tips = run_result.final_output.preparation_tips

        # Add other fallback extractions if needed

    # Create and return the combined output, ensuring we have valid defaults
    return InterviewPrepOutput(
        company_research=company_research or CompanyResearchOutput(
            company_overview="", culture_and_values="", interview_process="", recent_news=""
        ),
        technical_questions=technical_questions,
        behavioral_questions=behavioral_questions,
        preparation_tips=preparation_tips
    )


@app.route('/api/health', methods=['GET'])
def health_check():
    """Simple health check endpoint to wake up the backend"""
    return jsonify({
        "status": "online",
        "message": "Backend is ready"
    }), 200


if __name__ == '__main__':
    app.run(debug=False, port=10000)
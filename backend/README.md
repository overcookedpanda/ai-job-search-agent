# AI Interview Preparation Assistant - Backend

This is the backend service for the AI Interview Preparation Assistant. It provides the API endpoints that analyze job postings and extract key skills and qualifications using AI.

## Architecture

The backend is built with Flask and uses OpenAI's API to analyze job descriptions. It consists of:

- A RESTful API service
- Web scraping capabilities to extract job descriptions from URLs
- AI-powered analysis of job requirements

## API Endpoints

### POST /api/analyze-job
Analyzes a job posting URL and returns structured information about required skills.

**Request Body:**
```json
{
  "url": "https://example.com/job-posting"
}
```
### Response:

```json
{
  "job_title": "Software Engineer",
  "company": "Example Corp",
  "salary": "$100,000 - $130,000",
  "required_skills": {
    "technical_skills": ["JavaScript", "React", "Node.js"],
    "soft_skills": ["Communication", "Teamwork"],
    "education": ["Bachelor's degree in Computer Science or related field"],
    "experience": ["3+ years of software development experience"]
  },
  "preferred_skills": ["TypeScript", "AWS"]
}
```
### GET /api/health
Simple health check endpoint.

```json
{
  "status": "online",
  "message": "Backend is ready"
}
```

## Setup and Installation

### Prerequisites

- Python 3.9+
- OpenAI API key

### Installation

1. Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create a `.env` file with your OpenAI API key:

```bash
OPENAI_API_KEY=your_api_key_here
```

4. Start the server:

```bash
python app.py
```
The server will run on port 10000 by default.

### Deployment
The backend is configured for deployment on Render as a Web Service. The deployment is automated using GitHub Actions when changes are pushed to the main branch.

### Production Considerations

- Ensure your OpenAI API key is configured as an environment variable in your production environment
- For high traffic, consider implementing rate limiting and caching
- Monitor API usage to control costs with the OpenAI API
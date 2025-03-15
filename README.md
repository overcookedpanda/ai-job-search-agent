# AI Interview Preparation Assistant

An intelligent tool to help you prepare for tech interviews by analyzing job listings to extract required skills, qualifications, and key information.

Deployed at: https://ai-interview-prep.overcookedpanda.com/

## Features

- **Job Listing Analysis**: Paste any job posting URL to get an AI-powered breakdown of required skills and qualifications
- **Skills Categorization**: View technical skills, soft skills, education requirements, and experience requirements clearly separated
- **Required vs. Preferred**: Understand which skills are required versus preferred for the position

## Technology Stack

### Frontend
- React 19
- TailwindCSS
- Axios for API requests
- React Router for navigation

### Backend
- Flask (Python)
- OpenAI API integration
- Beautiful Soup for web scraping
- OpenAI Agents for intelligent extraction

## Getting Started

### Prerequisites
- Node.js (v18+)
- Python 3.9+
- OpenAI API key

### Installation

#### Frontend Setup
```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

#### Backend Setup
```bash
# Navigate to backend directory
cd backend

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
echo "OPENAI_API_KEY=your_api_key_here" > .env

# Start backend server
python app.py
```

### Running the Application

For development, start both frontend and backend:
```bash
npm run start:all
```
### Deployment
This project is configured for deployment on Render with GitHub Actions automation:

1. Frontend: Static site hosting
2. Backend: Web service

The GitHub workflow in `.github/workflows/deploy.yml` handles automatic deployments when changes are pushed to the main branch.

### Development
#### Environment Variables

- `VITE_API_BASE_URL`: Backend API URL (default: http://localhost:10000)
- `OPENAI_API_KEY`: Your OpenAI API key (required for backend)

### License
This project is licensed under the MIT License - see the LICENSE file for details.
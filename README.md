# AI Recruiting Assistant

An autonomous AI recruiting assistant built with LangGraph that analyzes resumes, performs web research (including GitHub profiles), and evaluates candidates against job descriptions.

## 🧩 Overview

This application helps streamline the recruiting process by:

1. Parsing and analyzing candidate resumes
2. Gathering additional data from the web, including GitHub repositories
3. Comparing candidates' qualifications to job requirements
4. Providing a structured assessment with recommendations

## 🏗️ Architecture

The application follows a LangGraph architecture with conditional routing:

```
                  ┌───────────────┐
                  │   FastAPI     │
                  │   Endpoint    │
                  └───────┬───────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                  LangGraph Workflow                     │
├─────────────────────────────────────────────────────────┤
│                         │                               │
│                         ▼                               │
│                  ┌─────────────┐                        │
│                  │   Resume    │                        │
│                  │   Parser    │                        │
│                  └──────┬──────┘                        │
│                         │                               │
│                         ▼                               │
│                  ┌─────────────┐                        │
│                  │     Job     │                        │
│                  │ Description │                        │
│                  └──────┬──────┘                        │
│                         │                               │
│                         ▼                               │
│                  ┌─────────────┐                        │
│     ┌────No GitHub───┤   Check    │                     │
│     │        Info    │  GitHub    │                     │
│     │                │   Info     │                     │
│     │                └──────┬─────┘                     │
│     │                       │                           │
│     │                       │ GitHub Info Found         │
│     │                       ▼                           │
│     │                ┌─────────────┐                    │
│     │                │   GitHub    │                    │
│     │                │  Research   │                    │
│     │                └──────┬──────┘                    │
│     │                       │                           │
│     ▼                       ▼                           │
│ ┌─────────────┐      ┌─────────────┐                    │
│ │     Web     │◀─────│     Web     │                    │
│ │  Research   │      │  Research   │                    │
│ └──────┬──────┘      └─────────────┘                    │
│        │                                                │
│        ▼                                                │
│ ┌──────────────┐                                        │
│ │   Profile    │                                        │
│ │   Creation   │                                        │
│ └──────┬───────┘                                        │
│        │                                                │
│        ▼                                                │
│ ┌──────────────┐                                        │
│ │   Compare    │                                        │
│ │  Candidate   │                                        │
│ └──────┬───────┘                                        │
│        │                                                │
│        ▼                                                │
│ ┌──────────────┐                                        │
│ │    Final     │                                        │
│ │   Decision   │                                        │
│ └──────────────┘                                        │
└─────────────────────────────────────────────────────────┘
```

### Key Components:

1. **State Management** (`state.py`): Defines the TypedDict structures for workflow state
2. **Nodes** (`nodes.py`): Implements business logic for each workflow step
3. **Graph** (`graph.py`): Orchestrates the workflow with LangGraph and conditional routing
4. **Prompts** (`prompts/`): Contains prompt templates for various analysis tasks
5. **Utils** (`utils/`): Provides utilities for document parsing and GitHub scraping
6. **API** (`app.py`): Exposes a FastAPI endpoint for integration

## 🛠️ Setup Instructions

### Prerequisites

- Python 3.9+
- Required API keys:
  - OpenAI API key (for GPT models)
  - Tavily API key (for web search)

### Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/ai-recruiting-assistant.git
cd ai-recruiting-assistant
```

2. Set up a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install the dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file with your API keys:
```bash
touch .env
```

5. Add your API keys to the `.env` file:
```
OPENAI_API_KEY=your_openai_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
```

## 📂 Project Structure

```
recruiting_assistant/
├── app.py                 # FastAPI application
├── workflow/
│   ├── __init__.py
│   ├── state.py           # State definitions
│   ├── nodes.py           # Node implementations
│   └── graph.py           # LangGraph workflow
├── prompts/
│   ├── __init__.py
│   ├── prompt_loader.py   # Utility for loading prompts
│   ├── resume_analysis.txt
│   ├── job_analysis.txt
│   ├── web_research.txt
│   ├── github_analysis.txt
│   ├── comparison.txt
│   └── final_decision.txt
├── utils/
│   ├── __init__.py
│   ├── document_parser.py  # PDF/DOCX parsing utilities
│   ├── github_extractor.py # GitHub profile extraction
│   └── github_scraper.py   # GitHub repository scraping
├── requirements.txt
└── README.md
```

## 🚀 Usage

### Running the API

```bash
python app.py
```

The API will be available at `http://localhost:8000`.

### API Endpoints

#### POST /api/evaluate_resume

Evaluates a candidate's resume against a job description.

**Parameters:**
- `candidate_name`: Name of the candidate (form field)
- `resume_file`: PDF or DOCX resume file (file upload)
- `job_description`: Job description text (optional form field)
- `job_description_file`: PDF or DOCX job description file (optional file upload)

**Returns:**
A JSON object containing:
- Fit score (Strong Fit, Moderate Fit, or Not a Fit)
- Reasoning behind the assessment
- Recommendations for next steps
- Detailed analysis of the candidate's qualifications

### Example cURL Request

```bash
curl -X POST "http://localhost:8000/api/evaluate_resume" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "candidate_name=John Doe" \
  -F "resume_file=@/path/to/resume.pdf" \
  -F "job_description=Job description text here..."
```

## ✨ Features

- **Robust Document Parsing**: Extracts text from PDF and DOCX files with fallback mechanisms
- **GitHub Profile Discovery**: Searches and analyzes GitHub profiles even if not mentioned in resume
- **Repository Analysis**: Evaluates coding skills based on actual projects
- **Web Research**: Gathers additional information from blogs, conferences, and social profiles
- **Comprehensive Evaluation**: Provides detailed skill matching and recommendations
- **Asynchronous Processing**: Handles long-running evaluations with status tracking
- **Conditional Workflow**: Intelligently routes through GitHub research only when relevant

## 🔄 Workflow Execution

The LangGraph workflow follows this execution path:

1. **Parse Resume**: Extract structured information from the candidate's resume
2. **Parse Job Description**: Analyze the job description to identify requirements
3. **Check GitHub Info**: Determine if GitHub profile info was found in the resume
   - If GitHub info exists → Execute GitHub Research
   - If no GitHub info → Skip to Web Research
4. **GitHub Research** (conditional): Analyze GitHub repositories and coding skills
5. **Web Research**: Gather additional information from the web
6. **Create Candidate Profile**: Combine all gathered information
7. **Compare Candidate to Job**: Evaluate the match between candidate and job
8. **Generate Final Decision**: Produce the final assessment and recommendations

This conditional routing ensures the workflow is efficient, only analyzing GitHub repositories when a profile is available.

## 🧪 Testing

To test the application with an example resume and job description:

```bash
python -m recruiting_assistant.example_usage
```

### Example Output Files

The repository includes two example JSON files that demonstrate the output format:

1. **`evaluation_result.json`** - Contains a complete evaluation output showing the structured assessment of a candidate including:
   - Parsed resume data
   - Job requirements analysis
   - GitHub research findings
   - Web research results
   - Comparison matrix
   - Final decision with recommendations

2. **`evaluation_result_without_github.json`** - Contains a complete evaluation output showing the structured assessment of a candidate include(if github not provided in resume).
   - Parsed resume data
   - Job requirements analysis
   - GitHub research findings
   - Web research results
   - Comparison matrix
   - Final decision with recommendations

These files are useful for:
- Understanding the expected output format
- Testing downstream integrations
- Debugging the evaluation pipeline

You can examine these files to understand the data structure that your application will work with:

```bash
cat examples/evaluation_result.json | jq
```

## 📝 Notes

- The GitHub scraper does not require a GitHub API key but has rate limitations
- For production usage, consider implementing caching to reduce API calls
- All prompts can be customized in the `/prompts` directory
- The conditional workflow can be extended for other specialized research nodes
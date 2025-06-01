# Paper Reader Tools

A comprehensive application for extracting, summarizing, and analyzing academic papers using Google's Gemini API. Features both FastAPI backend and Streamlit frontend interfaces for document processing, management, and search.

## Features

- **AI-Powered Paper Analysis**: Uses Google Gemini 2.0 Flash to generate comprehensive summaries of research papers
- **PDF Text Extraction**: Intelligent extraction of text and structure from academic PDFs
- **Organization System**: Tag-based organization and custom reading lists
- **Search Capabilities**: Keyword search across titles, authors, and content
- **Vector Search**: Optional semantic search using embedding models (with vector extras)
- **Flexible Input**: Process papers from local files or URLs
- **Export Options**: Generate and download formatted PDF reports of summaries

## Project Architecture

The project follows a modular architecture with clear separation of concerns:

```
Paper-reader-tools/            # Project root directory
├── README.md                  # Project documentation
├── pyproject.toml             # Poetry configuration: dependencies and metadata
├── .env                       # Environment variables (API keys, etc.)
├── .env.example               # Example environment configuration
├── Dockerfile                 # Docker container definition
├── docker-compose.yml         # Docker Compose services configuration
├── .dockerignore              # Files to exclude from Docker builds
├── .gitignore                 # Files to exclude from Git
├── data/                      # Database storage directory
├── uploads/                   # Temporary storage for uploaded PDF files
├── output/                    # Generated summaries and PDF reports
├── tests/                     # Test suite for the application
├── paper_reader_tools/        # Main Python package
│   ├── __init__.py            # Package initialization
│   ├── __main__.py            # Entry point for direct execution
│   ├── api/                   # API layer
│   │   ├── __init__.py
│   │   ├── models.py          # API data models (Pydantic)
│   │   └── server.py          # FastAPI server implementation
│   ├── cli.py                 # Command line interface
│   ├── cli_enhanced.py        # Extended CLI with Docker controls
│   ├── repository/            # Data access layer
│   │   ├── __init__.py
│   │   ├── paper_repository.py      # Paper data management
│   │   └── collection_repository.py # Collection data management
│   ├── services/              # Business logic
│   │   ├── __init__.py
│   │   ├── ai_client.py       # Google Gemini AI integration
│   │   ├── extractor.py       # PDF text extraction logic
│   │   ├── pdf_generator.py   # Summary PDF report creation
│   │   └── utils.py           # Helper utilities and functions
│   ├── streamlit_app.py       # Streamlit web interface entry point
│   └── ui/                    # User interface components
│       ├── __init__.py
│       ├── api_client.py      # HTTP client for API interaction
│       └── pages/             # Streamlit page components
│           ├── __init__.py
│           ├── about_page.py  # About information page
│           ├── home_page.py   # Home/landing page
│           ├── library_page.py # Paper library and management
│           ├── process_page.py # Paper processing interface
│           └── settings_page.py # Application settings
```

## Installation

```bash
# Clone the repository
git clone <repo-url>
cd paper-reader-tools

# Basic installation with Poetry
poetry install

# Installation with vector search capabilities
poetry install -E vector
```

## Configuration

Create a `.env` file in the root of the project with your Gemini API credentials:

```
GEMINI_API_URL=https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent
GEMINI_API_KEY=your_api_key_here
```

## Usage

### Development with Auto-Reload

For development with auto-reload (changes to code will be automatically detected):

```bash
# Start the Docker containers in development mode
python cli_enhanced.py docker start --dev

# Make changes to your code, and they will be automatically applied
# No need to rebuild or restart containers for code changes
```

### Web Interface with FastAPI and Streamlit

```bash
# Start the FastAPI server
python cli_enhanced.py api

# Start the Streamlit interface (in another terminal)
python cli_enhanced.py web
```

Then open your browser at http://localhost:8501

### Command Line

```bash
# Process a local PDF file
python cli_enhanced.py process -f path/to/paper.pdf

# Process a PDF from URL
python cli_enhanced.py process -u https://example.com/paper.pdf

# Use Docker to run the complete system
python cli_enhanced.py docker build
python cli_enhanced.py docker start
```

## Technologies

- Backend: FastAPI + Python Async
- Frontend: Streamlit
- AI: Google Gemini 2.0 Flash
- Vector Search: Sentence Transformers

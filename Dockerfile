# Use a more specific Python image tag (instead of just 3.10-slim)
FROM python:3.10.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    gcc \
    pandoc \
    texlive-xetex \
    texlive-fonts-recommended \
    texlive-plain-generic \
    texlive-latex-recommended \  
    texlive-latex-base \         
    lmodern \                    
    curl \
    poppler-utils \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY pyproject.toml poetry.lock* /app/

# Install Poetry
RUN pip install poetry

# Configure poetry to not use a virtual environment
RUN poetry config virtualenvs.create false

# Install dependencies with --no-root flag to avoid README.md requirement
RUN poetry install --no-interaction --no-ansi --no-root

# Explicitly install required packages that might be missing
RUN pip install uvicorn aiohttp requests python-multipart httpx

# Copy the rest of the application
COPY . /app/

# Make directories that might be needed
RUN mkdir -p /app/data /app/uploads /app/output && chmod 777 /app/data /app/uploads /app/output

# Add a health check directly to the image
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=5 \
    CMD curl -f http://localhost:8080/health || exit 1

# Expose port for the application
EXPOSE 8080

# Set the entrypoint to be flexible for development overrides
ENTRYPOINT []

# Default command (can be overridden in docker-compose)
CMD ["python", "-m", "uvicorn", "paper_reader_tools.api.server:app", "--host", "0.0.0.0", "--port", "8080"]

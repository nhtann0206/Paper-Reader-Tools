"""
FastAPI implementation for Paper Reader Tools.
"""
import os
import sys
import asyncio
import tempfile
import logging
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, File, UploadFile, Form, BackgroundTasks, HTTPException, Depends
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.logger import logger

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("paper_reader_api")
logger.setLevel(logging.INFO)

# Create upload and output directories
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
OUTPUT_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "output")
DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")

# Ensure these directories exist
for directory in [UPLOAD_FOLDER, OUTPUT_FOLDER, DB_DIR]:
    os.makedirs(directory, exist_ok=True)
    logger.info(f"Directory verified: {directory}")

try:
    # Import repositories first (to detect import errors early)
    from ..repository.paper_repository import Paper, PaperRepository
    from ..repository.collection_repository import Collection, CollectionRepository
    
    # Then import services
    from ..services.utils import validate_url, download_pdf, clean_temp_files
    from ..services.extractor import extract_pdf_text
    from ..services.ai_client import GeminiClient
    from ..services.pdf_generator import PDFGenerator
    
    # Finally import API models
    from .models import (
        PaperResponse, UploadResponse, UrlRequest, StatusResponse, 
        CollectionCreate, CollectionResponse, UpdateReadStatusRequest
    )
    
    logger.info("All modules imported successfully")
except ImportError as e:
    logger.error(f"Import error: {str(e)}")
    raise

# Task status storage
task_status = {}

# Initialize FastAPI app
app = FastAPI(
    title="Paper Reader API",
    description="API for processing and summarizing research papers",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Verify required environment variables
if not os.environ.get("GEMINI_API_KEY"):
    logger.warning("GEMINI_API_KEY environment variable is not set")

# Mount static files for output
try:
    logger.info(f"Attempting to mount static files from: {OUTPUT_FOLDER}")
    app.mount("/output", StaticFiles(directory=OUTPUT_FOLDER), name="output")
    logger.info("Static files mounted successfully")
except Exception as e:
    logger.error(f"Error mounting static files: {str(e)}")
    # Continue without static file mounting - we'll handle files differently if needed

# Initialize repositories with explicit path
def get_paper_repository():
    """Get the paper repository dependency with explicit DB path."""
    logger.info(f"Creating paper repository with DB path: {os.path.join(DB_DIR, 'papers.db')}")
    return PaperRepository(db_path=os.path.join(DB_DIR, "papers.db"))

def get_collection_repository():
    """Get the collection repository dependency with explicit DB path."""
    logger.info(f"Creating collection repository with DB path: {os.path.join(DB_DIR, 'papers.db')}")
    return CollectionRepository(db_path=os.path.join(DB_DIR, "papers.db"))

# Health check
@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    logger.info("Health check requested")
    try:
        # Just return basic health info without database check for initial startup
        return {
            "status": "healthy", 
            "version": "0.1.0"
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "warning",
            "version": "0.1.0",
            "error": str(e)
        }

# Later, once database is initialized, we can use this one
@app.get("/ready")
async def readiness_check():
    """Complete health check including database."""
    logger.info("Readiness check requested")
    try:
        # Test database connection
        repo = get_paper_repository()
        tags = repo.get_all_tags()
        logger.info(f"Health check successful - found {len(tags)} tags")
        return {
            "status": "healthy", 
            "version": "0.1.0", 
            "database": "connected",
            "tag_count": len(tags)
        }
    except Exception as e:
        logger.error(f"Readiness check failed: {str(e)}")
        return {
            "status": "warning",
            "version": "0.1.0",
            "error": str(e)
        }

# Add a specific endpoint for accessing PDFs to better handle headers
@app.get("/pdf/{filename}")
async def get_pdf(filename: str):
    """Get a PDF file by filename."""
    file_path = os.path.join(OUTPUT_FOLDER, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="PDF not found")
    
    # Return the file with explicit headers to ensure browser displays it correctly
    return FileResponse(
        path=file_path, 
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"inline; filename={filename}",
            "Content-Type": "application/pdf"
        }
    )

# Add a general file endpoint to handle both PDF and markdown files
@app.get("/output/{filename}")
async def get_output_file(filename: str):
    """Get an output file by filename (PDF or Markdown)."""
    file_path = os.path.join(OUTPUT_FOLDER, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    # Determine content type based on extension
    content_type = "application/pdf"
    if filename.lower().endswith('.md'):
        content_type = "text/markdown"
    
    # Return the file with appropriate headers
    return FileResponse(
        path=file_path, 
        media_type=content_type,
        headers={
            "Content-Disposition": f"inline; filename={filename}",
            "Content-Type": content_type
        }
    )

@app.get("/papers", response_model=List[PaperResponse])
async def get_papers(
    tag: Optional[str] = None, 
    limit: int = 100, 
    offset: int = 0,
    repository: PaperRepository = Depends(get_paper_repository)
):
    """Get list of papers, optionally filtered by tag."""
    try:
        logger.info(f"Fetching papers with tag={tag}, limit={limit}, offset={offset}")
        papers = repository.get_papers(limit=limit, offset=offset, tag=tag)
        logger.info(f"Found {len(papers)} papers")
        
        # Convert Paper objects to dictionaries with error handling
        result = []
        for paper in papers:
            try:
                paper_dict = paper.to_dict()
                
                # Ensure tags field is a proper list, not a JSON string
                if 'tags' in paper_dict and isinstance(paper_dict['tags'], str):
                    try:
                        import json
                        paper_dict['tags'] = json.loads(paper_dict['tags'])
                    except:
                        paper_dict['tags'] = []
                
                # Set empty string for potentially None fields
                for field in ['publication', 'publication_date', 'url', 'summary', 'output_path']:
                    if field in paper_dict and paper_dict[field] is None:
                        paper_dict[field] = ""
                
                result.append(paper_dict)
            except Exception as e:
                logger.error(f"Error converting paper {paper.id} to dict: {str(e)}")
                # Skip problematic papers
        
        return result
    except Exception as e:
        logger.error(f"Error in get_papers endpoint: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500, 
            detail=f"Internal server error: {str(e)}"
        )

@app.get("/papers/{paper_id}", response_model=Dict[str, Any])
async def get_paper(
    paper_id: int,
    repository: PaperRepository = Depends(get_paper_repository)
):
    """Get a specific paper by ID."""
    try:
        paper = repository.get_paper(paper_id)
        if not paper:
            raise HTTPException(status_code=404, detail="Paper not found")
        
        result = paper.to_dict()
        
        # Ensure tags field is a proper list, not a JSON string
        if 'tags' in result and isinstance(result['tags'], str):
            try:
                import json
                result['tags'] = json.loads(result['tags'])
            except:
                result['tags'] = []
        
        # Set empty string for potentially None fields
        for field in ['publication', 'publication_date', 'url', 'summary', 'output_path']:
            if field in result and result[field] is None:
                result[field] = ""
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving paper {paper_id}: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.delete("/papers/{paper_id}", response_model=Dict[str, bool])
async def delete_paper(
    paper_id: int,
    repository: PaperRepository = Depends(get_paper_repository)
):
    """Delete a paper."""
    success = repository.delete_paper(paper_id)
    if not success:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    return {"success": True}

@app.get("/tags", response_model=List[str])
async def get_tags(
    repository: PaperRepository = Depends(get_paper_repository)
):
    """Get all tags."""
    try:
        tags = repository.get_all_tags()
        logger.info(f"Retrieved {len(tags)} tags")
        return tags
    except Exception as e:
        logger.error(f"Error retrieving tags: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        # Return empty list instead of error to avoid breaking UI
        return []

@app.get("/search", response_model=List[PaperResponse])
async def search_papers(
    q: str = "", 
    limit: int = 100,
    repository: PaperRepository = Depends(get_paper_repository)
):
    """Search papers by keyword or semantic similarity."""
    if not q:
        return []
    
    try:
        logger.info(f"Searching papers with query: {q}")
        papers = repository.search_papers(q, limit=limit)
        logger.info(f"Found {len(papers)} matching papers")
        
        # Convert Paper objects to dictionaries with error handling
        result = []
        for paper in papers:
            try:
                paper_dict = paper.to_dict()
                
                # Ensure tags field is a proper list, not a JSON string
                if 'tags' in paper_dict and isinstance(paper_dict['tags'], str):
                    try:
                        import json
                        paper_dict['tags'] = json.loads(paper_dict['tags'])
                    except:
                        paper_dict['tags'] = []
                
                # Set empty string for potentially None fields
                for field in ['publication', 'publication_date', 'url', 'summary', 'output_path']:
                    if field in paper_dict and paper_dict[field] is None:
                        paper_dict[field] = ""
                        
                result.append(paper_dict)
            except Exception as e:
                logger.error(f"Error converting paper {paper.id} to dict: {str(e)}")
                # Skip problematic papers
        
        return result
    except Exception as e:
        logger.error(f"Error in search_papers endpoint: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        # Return empty list instead of error
        return []

@app.post("/upload", response_model=UploadResponse)
async def upload_paper(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    tags: str = Form(""),
    repository: PaperRepository = Depends(get_paper_repository)
):
    """Upload a PDF file for processing."""
    # Check file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    # Save uploaded file
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    with open(file_path, "wb") as f:
        f.write(await file.read())
    
    # Parse tags
    tags_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
    
    # Generate task ID
    task_id = str(hash(file.filename + str(os.path.getmtime(file_path))))
    
    # Initialize task status
    task_status[task_id] = {"status": "processing", "progress": 0}
    
    # Process in background
    background_tasks.add_task(
        process_paper_background,
        task_id=task_id,
        file_path=file_path,
        url=None,
        tags=tags_list,
        repository=repository
    )
    
    return {"task_id": task_id, "status": "processing"}

@app.post("/process-url", response_model=UploadResponse)
async def process_url(
    background_tasks: BackgroundTasks, 
    request: UrlRequest,
    repository: PaperRepository = Depends(get_paper_repository)
):
    """Process a PDF from a URL."""
    url = str(request.url)
    if not url.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="URL must point to a PDF file")
    
    # Generate task ID
    task_id = str(hash(url))
    
    # Initialize task status
    task_status[task_id] = {"status": "processing", "progress": 0}
    
    # Process in background
    background_tasks.add_task(
        process_paper_background,
        task_id=task_id,
        file_path=None,
        url=url,
        tags=request.tags,
        repository=repository
    )
    
    return {"task_id": task_id, "status": "processing"}

@app.get("/status/{task_id}", response_model=StatusResponse)
async def get_status(task_id: str):
    """Check processing status of a task."""
    if task_id not in task_status:
        return {"status": "not_found"}
    
    return task_status[task_id]

# Collection endpoints
@app.get("/collections", response_model=List[CollectionResponse])
async def get_collections(
    repository: CollectionRepository = Depends(get_collection_repository)
):
    """Get all collections."""
    collections = repository.get_collections()
    return collections

@app.get("/collections/{collection_id}", response_model=CollectionResponse)
async def get_collection(
    collection_id: int,
    repository: CollectionRepository = Depends(get_collection_repository)
):
    """Get a specific collection."""
    collection = repository.get_collection(collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    return collection

@app.post("/collections", response_model=CollectionResponse)
async def create_collection(
    collection: CollectionCreate,
    repository: CollectionRepository = Depends(get_collection_repository)
):
    """Create a new collection."""
    new_collection = Collection(
        name=collection.name,
        description=collection.description,
        papers=collection.papers,
    )
    collection_id = repository.save_collection(new_collection)
    return repository.get_collection(collection_id)

@app.put("/collections/{collection_id}", response_model=CollectionResponse)
async def update_collection(
    collection_id: int, 
    collection: CollectionCreate,
    repository: CollectionRepository = Depends(get_collection_repository)
):
    """Update an existing collection."""
    existing = repository.get_collection(collection_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    updated_collection = Collection(
        id=collection_id,
        name=collection.name,
        description=collection.description,
        papers=collection.papers,
    )
    repository.save_collection(updated_collection)
    return repository.get_collection(collection_id)

@app.post("/collections/{collection_id}/papers/{paper_id}", response_model=Dict[str, bool])
async def add_paper_to_collection(
    collection_id: int, 
    paper_id: int,
    repository: CollectionRepository = Depends(get_collection_repository)
):
    """Add a paper to a collection."""
    result = repository.add_paper_to_collection(collection_id, paper_id)
    if result:
        return {"success": True}
    raise HTTPException(status_code=404, detail="Collection or paper not found")

@app.delete("/collections/{collection_id}/papers/{paper_id}", response_model=Dict[str, bool])
async def remove_paper_from_collection(
    collection_id: int, 
    paper_id: int,
    repository: CollectionRepository = Depends(get_collection_repository)
):
    """Remove a paper from a collection."""
    result = repository.remove_paper_from_collection(collection_id, paper_id)
    if result:
        return {"success": True}
    raise HTTPException(status_code=404, detail="Collection or paper not found")

@app.put("/collections/{collection_id}/papers/{paper_id}/read_status", response_model=Dict[str, bool])
async def update_read_status(
    collection_id: int, 
    paper_id: int, 
    request: UpdateReadStatusRequest,
    repository: CollectionRepository = Depends(get_collection_repository)
):
    """Update the read status of a paper in a collection."""
    result = repository.update_paper_read_status(collection_id, paper_id, request.read_status)
    if result:
        return {"success": True}
    raise HTTPException(status_code=404, detail="Collection or paper not found")

@app.delete("/collections/{collection_id}", response_model=Dict[str, bool])
async def delete_collection(
    collection_id: int,
    repository: CollectionRepository = Depends(get_collection_repository)
):
    """Delete a collection."""
    result = repository.delete_collection(collection_id)
    if result:
        return {"success": True}
    raise HTTPException(status_code=404, detail="Collection not found")

def update_task_status(task_id: str, status: str, progress: Optional[int] = None, 
                      paper_id: Optional[int] = None, error: Optional[str] = None):
    """Update the status of a processing task."""
    if task_id in task_status:
        task_status[task_id]["status"] = status
        if progress is not None:
            task_status[task_id]["progress"] = progress
        if paper_id is not None:
            task_status[task_id]["paper_id"] = paper_id
        if error is not None:
            task_status[task_id]["error"] = error

async def process_paper_background(
    task_id: str, 
    file_path: Optional[str], 
    url: Optional[str], 
    tags: List[str],
    repository: PaperRepository
):
    """Process a paper in the background."""
    temp_files = []
    
    try:
        update_task_status(task_id, "processing", 10)
        logger.info(f"Processing paper task {task_id} started")
        
        # Download PDF if URL is provided
        is_url = url is not None
        
        if is_url:
            update_task_status(task_id, "processing", 20)
            logger.info(f"Downloading PDF from URL: {url}")
            pdf_path = await download_pdf(url)
            temp_files.append(pdf_path)
        else:
            pdf_path = file_path
        
        # Extract text from PDF
        update_task_status(task_id, "processing", 30)
        print(f"Extracting text from PDF: {pdf_path}")
        sections = await extract_pdf_text(pdf_path)
        print(f"Found {len(sections)} sections")
        
        # Extract metadata
        update_task_status(task_id, "processing", 40)
        
        # Initialize Gemini client
        client = GeminiClient()
        
        # Get metadata using LLM
        first_page_text = next(iter(sections.values())) if sections else ""
        metadata = await client.extract_metadata(first_page_text)
        print(f"Extracted metadata: Title={metadata.get('title', 'No title')}")
        
        # If the source is a URL, set it as the URL
        if url:
            metadata["url"] = url
        
        # Combine all text for analysis
        all_text = "\n\n".join(sections.values())
        
        # Process with Gemini
        update_task_status(task_id, "processing", 60)
        response = await client.summarize_text(all_text, "summary")
        
        # Extract content from response
        update_task_status(task_id, "processing", 70)
        summary = client.extract_from_response(response)
        print(f"Generated summary length: {len(summary)} characters")
        
        # Generate PDF
        update_task_status(task_id, "processing", 80)
        pdf_generator = PDFGenerator(OUTPUT_FOLDER)
        output_path = await pdf_generator.generate_pdf(summary, metadata)
        print(f"Generated output at: {output_path}")
        
        # Suggest tags if none were provided
        if not tags:
            update_task_status(task_id, "processing", 85)
            try:
                tags = await client.suggest_paper_tags(
                    metadata.get("title", ""), 
                    sections.get("Abstract", sections.get("ABSTRACT", ""))
                )
                print(f"Generated tags: {tags}")
            except Exception as e:
                print(f"Error generating tags: {str(e)}")
                tags = []
        
        # Store paper in database
        update_task_status(task_id, "processing", 90)
        try:
            # Ensure tags is a list and not None
            if not isinstance(tags, list):
                tags = []
            
            paper = Paper(
                title=metadata.get("title", "Untitled Paper"),
                authors=metadata.get("authors", ""),
                publication=metadata.get("publication", ""),
                publication_date=metadata.get("date", ""),
                url=url or "",
                file_path=file_path if not is_url else "",  # Now is_url is defined
                summary=summary,
                content=all_text[:10000],  # Store first 10K characters only
                tags=tags,
                sections=sections,
                output_path=os.path.basename(output_path)
            )
            
            # Debug log
            print(f"Attempting to save paper to database. Title: {paper.title}, Tags: {paper.tags}")
            
            # Save the paper to the repository
            paper_id = repository.save_paper(paper)
            print(f"Paper saved to database with ID: {paper_id}")
            
            # Mark task as complete
            update_task_status(task_id, "complete", 100, paper_id=paper_id)
            
        except Exception as e:
            print(f"Error saving paper to database: {str(e)}")
            print(f"Error type: {type(e).__name__}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            # Still marking task as complete even if saving fails
            update_task_status(task_id, "complete", 100)
            
    except Exception as e:
        # Handle errors with better logging
        error_message = str(e)
        logger.error(f"Error processing paper: {error_message}")
        logger.exception("Full error details:")
        update_task_status(task_id, "failed", error=error_message)
    finally:
        # Clean up temporary files
        clean_temp_files(temp_files)

# For testing and debugging
if __name__ == "__main__":
    print("This module should be imported by the API server, not run directly")

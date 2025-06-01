"""
API models for Paper Reader Tools.
"""
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field, HttpUrl

class PaperResponse(BaseModel):
    """Response model for paper details."""
    id: int
    title: str
    authors: str
    publication: str = ""
    publication_date: str = ""
    url: str = ""
    summary: str = ""
    tags: List[str] = Field(default_factory=list)  # Updated to ensure default is empty list
    output_path: str = ""
    processed_date: str

class UploadResponse(BaseModel):
    """Response model for paper upload."""
    task_id: str
    status: str = "processing"

class UrlRequest(BaseModel):
    """Request model for processing a paper URL."""
    url: HttpUrl
    tags: List[str] = []

class StatusResponse(BaseModel):
    """Response model for task status."""
    status: str
    progress: Optional[int] = None
    paper_id: Optional[int] = None
    error: Optional[str] = None

class CollectionCreate(BaseModel):
    """Request model for creating a collection."""
    name: str
    description: str = ""
    papers: List[int] = []

class CollectionResponse(BaseModel):
    """Response model for collection details."""
    id: int
    name: str
    description: str = ""
    papers: List[int] = []
    paper_details: Dict[str, Dict[str, Any]] = {}
    created_at: str

class UpdateReadStatusRequest(BaseModel):
    """Request model for updating read status."""
    read_status: bool

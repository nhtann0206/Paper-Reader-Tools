"""
API client for Streamlit UI to interact with the backend API.
"""
import os
import requests
from typing import Dict, List, Optional, Any
import streamlit as st
import time

# API settings - add retries and debug info
API_URL = os.environ.get("API_URL", "http://localhost:8080")

class APIClient:
    """Client for interacting with the Paper Reader Tools API."""
    
    def __init__(self, api_url: str = API_URL):
        """Initialize the API client with the API URL."""
        self.api_url = api_url
        print(f"Initializing API client with URL: {api_url}")
    
    def get_papers(self, tag: Optional[str] = None, limit: int = 100, offset: int = 0) -> List[Dict]:
        """Get papers from the API."""
        params = {"limit": limit, "offset": offset}
        if tag:
            params["tag"] = tag
        
        # Add retry logic
        max_retries = 3
        retry_delay = 2
        for attempt in range(max_retries):
            try:
                print(f"[API] GET {self.api_url}/papers - Attempt {attempt+1}/{max_retries}")
                response = requests.get(f"{self.api_url}/papers", params=params, timeout=10)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                error_msg = f"Error loading papers (attempt {attempt+1}/{max_retries}): {str(e)}"
                print(error_msg)
                if attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    st.error(error_msg)
                    return []
    
    def get_paper(self, paper_id: int) -> Dict:
        """Get a specific paper from the API."""
        try:
            response = requests.get(f"{self.api_url}/papers/{paper_id}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Error loading paper: {str(e)}")
            return {}
    
    def get_all_tags(self) -> List[str]:
        """Get all tags from the API."""
        try:
            response = requests.get(f"{self.api_url}/tags")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Error loading tags: {str(e)}")
            return []
    
    def search_papers(self, query: str, limit: int = 100) -> List[Dict]:
        """Search papers through the API."""
        try:
            response = requests.get(f"{self.api_url}/search", params={"q": query, "limit": limit})
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Error searching papers: {str(e)}")
            return []
    
    def upload_paper(self, file, tags: str = "") -> Dict:
        """Upload a paper file to the API."""
        try:
            files = {"file": file}
            data = {"tags": tags}
            response = requests.post(f"{self.api_url}/upload", files=files, data=data)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Error uploading paper: {str(e)}")
            return {}
    
    def process_url(self, url: str, tags: List[str] = None) -> Dict:
        """Process a paper URL through the API."""
        try:
            payload = {"url": url, "tags": tags or []}
            response = requests.post(f"{self.api_url}/process-url", json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Error processing URL: {str(e)}")
            return {}
    
    def check_task_status(self, task_id: str) -> Dict:
        """Check the status of a processing task."""
        try:
            response = requests.get(f"{self.api_url}/status/{task_id}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Error checking task status: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    def delete_paper(self, paper_id: int) -> bool:
        """Delete a paper through the API."""
        try:
            response = requests.delete(f"{self.api_url}/papers/{paper_id}")
            response.raise_for_status()
            return response.json().get("success", False)
        except Exception as e:
            st.error(f"Error deleting paper: {str(e)}")
            return False

    def get_collections(self) -> List[Dict]:
        """Get all collections from the API."""
        try:
            response = requests.get(f"{self.api_url}/collections")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Error loading collections: {str(e)}")
            return []

    def get_collection(self, collection_id: int) -> Dict:
        """Get a specific collection from the API."""
        try:
            response = requests.get(f"{self.api_url}/collections/{collection_id}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Error loading collection: {str(e)}")
            return {}

    def create_collection(self, name: str, description: str = "", papers: List[int] = None) -> Dict:
        """Create a new collection."""
        try:
            data = {
                "name": name,
                "description": description,
                "papers": papers or []
            }
            response = requests.post(f"{self.api_url}/collections", json=data)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Error creating collection: {str(e)}")
            return {}

    def add_paper_to_collection(self, collection_id: int, paper_id: int) -> bool:
        """Add a paper to a collection."""
        try:
            response = requests.post(f"{self.api_url}/collections/{collection_id}/papers/{paper_id}")
            response.raise_for_status()
            return response.json().get("success", False)
        except Exception as e:
            st.error(f"Error adding paper to collection: {str(e)}")
            return False

    def remove_paper_from_collection(self, collection_id: int, paper_id: int) -> bool:
        """Remove a paper from a collection."""
        try:
            response = requests.delete(f"{self.api_url}/collections/{collection_id}/papers/{paper_id}")
            response.raise_for_status()
            return response.json().get("success", False)
        except Exception as e:
            st.error(f"Error removing paper from collection: {str(e)}")
            return False

    def update_read_status(self, collection_id: int, paper_id: int, read_status: bool) -> bool:
        """Update read status of a paper in a collection."""
        try:
            response = requests.put(
                f"{self.api_url}/collections/{collection_id}/papers/{paper_id}/read_status",
                json={"read_status": read_status}
            )
            response.raise_for_status()
            return response.json().get("success", False)
        except Exception as e:
            st.error(f"Error updating read status: {str(e)}")
            return False
            
    def delete_collection(self, collection_id: int) -> bool:
        """Delete a collection."""
        try:
            response = requests.delete(f"{self.api_url}/collections/{collection_id}")
            response.raise_for_status()
            return response.json().get("success", False)
        except Exception as e:
            st.error(f"Error deleting collection: {str(e)}")
            return False

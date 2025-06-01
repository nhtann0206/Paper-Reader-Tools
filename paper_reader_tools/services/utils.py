"""
Utility functions for Paper Reader Tools.
"""
import os
import re
import tempfile
import aiohttp
from typing import List, Optional, Any
import asyncio

def validate_url(url: str) -> bool:
    """
    Validate a URL string.
    
    Args:
        url: URL to validate
        
    Returns:
        True if valid
    """
    # Simple URL validation
    pattern = re.compile(
        r'^(?:http|ftp)s?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # or IP
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE
    )
    return bool(pattern.match(url)) and url.lower().endswith('.pdf')

async def download_pdf(url: str) -> str:
    """
    Download a PDF from a URL.
    
    Args:
        url: URL to download from
        
    Returns:
        Path to downloaded file
    """
    if not validate_url(url):
        raise ValueError("Invalid URL. Must be a valid URL ending with .pdf")
    
    # Create a temporary file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    temp_file.close()
    
    # Download PDF
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status != 200:
                    raise Exception(f"Failed to download PDF: HTTP {response.status}")
                
                # Save to temporary file
                with open(temp_file.name, 'wb') as f:
                    f.write(await response.read())
                
                return temp_file.name
        except Exception as e:
            # Clean up file if download failed
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
            raise Exception(f"Error downloading PDF: {str(e)}")

def clean_temp_files(file_paths: List[str]) -> None:
    """
    Clean up temporary files.
    
    Args:
        file_paths: List of file paths to delete
    """
    for path in file_paths:
        try:
            if os.path.exists(path):
                os.unlink(path)
        except Exception as e:
            print(f"Failed to remove temp file {path}: {str(e)}")

async def ensure_directory_exists(directory: str) -> None:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        directory: Directory path
    """
    os.makedirs(directory, exist_ok=True)

async def save_text_file(path: str, content: str) -> None:
    """
    Save text content to a file.
    
    Args:
        path: File path
        content: Text content
    """
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

"""
PDF text and figure extraction.
"""
import os
import re
import fitz  # PyMuPDF
from typing import Dict, List, Any, Tuple, Optional

async def extract_pdf_text(pdf_path: str, max_pages: Optional[int] = None) -> Dict[str, str]:
    """
    Extract text from a PDF file, organized by sections.
    
    Args:
        pdf_path: Path to PDF file
        max_pages: Maximum number of pages to process, or None for all
    
    Returns:
        Dictionary mapping section names to section text
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    sections = {}
    current_section = "Header"
    buffer = []
    
    # Open the PDF
    try:
        pdf_doc = fitz.open(pdf_path)
        page_count = min(pdf_doc.page_count, max_pages or pdf_doc.page_count)
        
        # Extract text from each page
        for page_num in range(page_count):
            page = pdf_doc[page_num]
            text = page.get_text("text")
            
            # Process text line by line
            for line in text.split("\n"):
                # Check if this line might be a section header
                if _is_likely_section_header(line):
                    # Save the current section
                    if buffer:
                        sections[current_section] = "\n".join(buffer).strip()
                        buffer = []
                    
                    current_section = line.strip()
                    continue
                
                buffer.append(line)
            
            # Add a page break to the buffer
            buffer.append("\n")
        
        # Save the last section
        if buffer:
            sections[current_section] = "\n".join(buffer).strip()
        
        # Special case for abstract if not already found
        if "Abstract" not in sections and "ABSTRACT" not in sections:
            abstract = _try_extract_abstract(pdf_doc, page_count)
            if abstract:
                sections["Abstract"] = abstract
                
        pdf_doc.close()
        return sections
        
    except Exception as e:
        raise Exception(f"Error extracting text from PDF: {str(e)}")

def _is_likely_section_header(line: str) -> bool:
    """
    Check if a line is likely to be a section header.
    
    Args:
        line: Text line
    
    Returns:
        True if the line is likely a section header
    """
    # Common section headers
    common_sections = [
        "abstract", "introduction", "background", "related work",
        "method", "methodology", "experiment", "results", "evaluation", 
        "discussion", "conclusion", "references", "appendix"
    ]
    
    # Clean the line
    clean_line = line.strip().lower()
    
    # If line is very short, skip (might be a page number)
    if len(clean_line) < 3:
        return False
    
    # If line is very long, it's unlikely to be a header
    if len(clean_line) > 100:
        return False
    
    # Check for numbered section headers (e.g., "1. Introduction")
    if re.match(r'^\d+\.?\s+\w+', line):
        return True
    
    # Check for common section headers
    for section in common_sections:
        if clean_line == section or clean_line.startswith(f"{section}."):
            return True
        
        # Section headers are often in ALL CAPS
        if line.isupper() and len(line.strip()) > 3 and len(line.strip()) < 50:
            return True
    
    return False

def _try_extract_abstract(pdf_doc, max_pages: int) -> str:
    """
    Try to extract the abstract from a PDF document.
    
    Args:
        pdf_doc: PyMuPDF document
        max_pages: Maximum number of pages to check
    
    Returns:
        Abstract text or empty string
    """
    # Look for abstract in first few pages
    check_pages = min(3, max_pages)
    text = ""
    
    for page_num in range(check_pages):
        page_text = pdf_doc[page_num].get_text("text")
        text += page_text
    
    # Try to find abstract with common patterns
    abstract_pattern = r'(?i)abstract[.\s]+(.*?)(?:\n\n|\r\n\r\n|$)'
    match = re.search(abstract_pattern, text, re.DOTALL)
    
    if match:
        abstract = match.group(1).strip()
        # Check if abstract is reasonably sized
        if 50 < len(abstract) < 2000:
            return abstract
    
    return ""

async def extract_key_figures(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Extract key figures from a PDF file.
    
    Args:
        pdf_path: Path to PDF file
    
    Returns:
        List of dictionaries with figure data
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    figures = []
    
    try:
        pdf_doc = fitz.open(pdf_path)
        
        # Extract images from each page
        for page_num in range(pdf_doc.page_count):
            page = pdf_doc[page_num]
            
            # Extract text for caption detection
            text = page.get_text("text")
            
            # Look for figure references in text
            fig_refs = re.finditer(r'(?i)fig(?:ure|\.)\s*(\d+)[:\.]?\s*([^\n]*)', text)
            
            # Get images on this page
            img_list = page.get_images(full=True)
            
            for img_idx, img in enumerate(img_list):
                try:
                    xref = img[0]
                    base_image = pdf_doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    
                    # Find the nearest figure caption
                    caption = ""
                    fig_num = img_idx + 1
                    
                    for ref in fig_refs:
                        if int(ref.group(1)) == fig_num:
                            caption = ref.group(2).strip()
                            break
                    
                    figures.append({
                        "page": page_num + 1,
                        "caption": caption,
                        "image_data": image_bytes
                    })
                    
                except Exception as e:
                    print(f"Error extracting image: {str(e)}")
                    continue
        
        pdf_doc.close()
        return figures
        
    except Exception as e:
        print(f"Error extracting figures: {str(e)}")
        return []

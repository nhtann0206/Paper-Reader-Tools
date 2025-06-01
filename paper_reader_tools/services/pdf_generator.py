"""
PDF generation for paper summaries.
"""
import os
import re
import datetime
import tempfile
import subprocess
from typing import Dict, List, Any, Optional

class PDFGenerator:
    """Generate PDF summaries from processed paper data."""
    
    def __init__(self, output_dir: str):
        """
        Initialize the PDF generator.
        
        Args:
            output_dir: Directory to save generated PDFs
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    async def generate_pdf(self, content: str, metadata: Dict[str, Any], figures: Optional[List[Dict[str, Any]]] = None, output_filename: Optional[str] = None) -> str:
        """
        Generate a PDF from content and metadata.
        
        Args:
            content: The formatted content
            metadata: Paper metadata (title, authors, etc.)
            figures: List of extracted figures
            output_filename: Name for the output file (without extension)
        
        Returns:
            Path to the generated PDF
        """
        # Use sync implementation
        return self._generate_pdf_sync(content, metadata, figures, output_filename)
    
    def _generate_pdf_sync(self, content: str, metadata: Dict[str, Any], figures: Optional[List[Dict[str, Any]]] = None, output_filename: Optional[str] = None) -> str:
        """
        Synchronous implementation of PDF generation.
        
        Args:
            content: The formatted content
            metadata: Paper metadata (title, authors, etc.)
            figures: List of extracted figures
            output_filename: Name for the output file (without extension)
        
        Returns:
            Path to the generated PDF or Markdown file
        """
        if not output_filename:
            # Create a sanitized filename from the paper title or current timestamp
            if metadata.get("title"):
                # Remove special characters and limit length
                output_filename = re.sub(r'[^\w\s-]', '', metadata.get("title", ""))
                output_filename = re.sub(r'[-\s]+', '-', output_filename).strip('-_')[:100]
            else:
                output_filename = f"paper-summary-{datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}"
        
        # Ensure the filename has no extension
        output_filename = os.path.splitext(output_filename)[0]
        
        # Create markdown content
        md_content = self._format_markdown_content(content, metadata, figures)
        
        # Always save file markdown (as a backup)
        md_output_path = os.path.join(self.output_dir, f"{output_filename}.md")
        with open(md_output_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
            
        # Try to create PDF with pandoc
        pdf_output_path = os.path.join(self.output_dir, f"{output_filename}.pdf")
        
        # Create temporary markdown file for pandoc
        with tempfile.NamedTemporaryFile('w', suffix='.md', delete=False, encoding='utf-8') as tmp:
            tmp.write(md_content)
            tmp_path = tmp.name
        
        try:
            # Use pandoc to convert markdown to PDF with improved settings
            cmd = [
                'pandoc', 
                tmp_path,
                '-o', pdf_output_path,
                '--pdf-engine=xelatex',
                '-V', 'colorlinks=true',
                '-V', 'linkcolor=blue',
                '-V', 'urlcolor=blue',
                '-V', 'toccolor=blue',
                '--toc',
                '-V', 'geometry:margin=1in',
            ]
            
            # Run process with 60-second timeout
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True,
                timeout=60  # Add a timeout to prevent hanging
            )
            
            if result.returncode == 0 and os.path.exists(pdf_output_path) and os.path.getsize(pdf_output_path) > 0:
                print(f"Successfully generated PDF at {pdf_output_path}")
                return pdf_output_path
            else:
                # Print detailed error for debugging
                print(f"PDF generation failed: {result.stderr}")
                
                # Try with minimal options if first attempt failed
                minimal_cmd = [
                    'pandoc', 
                    tmp_path,
                    '-o', pdf_output_path,
                    '--pdf-engine=xelatex'
                ]
                
                result = subprocess.run(minimal_cmd, capture_output=True, text=True)
                
                if result.returncode == 0 and os.path.exists(pdf_output_path) and os.path.getsize(pdf_output_path) > 0:
                    print(f"Successfully generated PDF with minimal options at {pdf_output_path}")
                    return pdf_output_path
                    
                # Fall back to returning markdown path
                print(f"Both PDF generation attempts failed, returning markdown path instead")
                return md_output_path
        
        except subprocess.TimeoutExpired:
            print("PDF generation timed out")
            return md_output_path
        except Exception as e:
            print(f"Error generating PDF: {str(e)}")
            return md_output_path
        finally:
            # Clean up temporary file
            try:
                os.unlink(tmp_path)
            except:
                pass
    
    def _format_markdown_content(self, content: str, metadata: Dict[str, Any], figures: Optional[List[Dict[str, Any]]] = None) -> str:
        """
        Format the content as markdown for PDF generation.
        
        Args:
            content: Raw content
            metadata: Paper metadata
            figures: List of figures
        
        Returns:
            Formatted markdown content
        """
        # Create a header with metadata
        header = f"# {metadata.get('title', 'Untitled Paper')}\n\n"
        
        if metadata.get("authors"):
            header += f"**Authors:** {metadata.get('authors')}\n\n"
        
        if metadata.get("publication") or metadata.get("date"):
            pub_info = []
            if metadata.get("publication"):
                pub_info.append(metadata["publication"])
            if metadata.get("date"):
                pub_info.append(metadata["date"])
            header += f"**Publication:** {', '.join(pub_info)}\n\n"
        
        if metadata.get("url"):
            header += f"**Source:** [{metadata['url']}]({metadata['url']})\n\n"
        
        # Add a divider
        header += "---\n\n"
        
        # Add content
        formatted_content = header + content
        
        # Add figures if available
        if figures and len(figures) > 0:
            figures_section = "\n\n## Figures\n\n"
            
            for i, figure in enumerate(figures):
                caption = figure.get("caption", f"Figure {i+1}")
                figures_section += f"### {caption}\n\n"
                figures_section += f"[Figure {i+1}]\n\n"  # Placeholder for figure
            
            formatted_content += figures_section
        
        return formatted_content

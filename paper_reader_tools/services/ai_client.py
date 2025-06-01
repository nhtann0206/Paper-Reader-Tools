"""
Client for AI services.
"""
import os
import json
import aiohttp
import asyncio
from typing import Dict, List, Optional, Any

# Load environment variables
GEMINI_API_URL = os.environ.get(
    "GEMINI_API_URL", 
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

class GeminiClient:
    """Client for interacting with the Gemini API."""
    
    def __init__(self):
        """Initialize the Gemini client."""
        self.api_url = GEMINI_API_URL
        self.api_key = GEMINI_API_KEY
        
        if not self.api_key:
            print("Warning: GEMINI_API_KEY not set. API requests will fail.")
    
    async def summarize_text(self, text: str, prompt_type: str = "summary") -> Dict[str, Any]:
        """
        Generate a summary of the provided text.
        
        Args:
            text: Text to summarize
            prompt_type: Type of summary to generate (summary, insights, etc.)
            
        Returns:
            Response from Gemini API
        """
        prompt = self._get_prompt(text, prompt_type)
        
        headers = {
            "Content-Type": "application/json"
        }
        
        # Add API key as query param or header depending on API requirements
        api_url = f"{self.api_url}?key={self.api_key}"
        
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "topP": 0.95,
                "topK": 40,
                "maxOutputTokens": 8192,
            }
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, json=payload, headers=headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"API request failed with status {response.status}: {error_text}")
                
                result = await response.json()
                return result
    
    def extract_from_response(self, response: Dict[str, Any]) -> str:
        """
        Extract the generated text from the API response.
        
        Args:
            response: Response from Gemini API
            
        Returns:
            Generated text
        """
        try:
            return response['candidates'][0]['content']['parts'][0]['text']
        except (KeyError, IndexError):
            return "Error: Could not extract text from response"
    
    def _get_prompt(self, text: str, prompt_type: str) -> str:
        """
        Get the appropriate prompt for the given text and prompt type.
        
        Args:
            text: Input text
            prompt_type: Type of prompt to use
            
        Returns:
            Complete prompt
        """
        if prompt_type == "summary":
            return f"""You are a scientific paper analysis assistant. Your task is to provide a comprehensive but concise summary of the following research paper. The summary should include:

1. Title, Authors, and Publication details
2. Research Questions/Objectives
3. Methodology used
4. Key Findings and Results
5. Main Conclusions and Implications
6. Limitations mentioned in the paper

Format the summary with appropriate Markdown headings for each section. 
Be concise but thorough, and avoid unnecessary text.

Here is the paper content:

{text}
"""
        elif prompt_type == "insights":
            return f"""You are a research analyst specializing in identifying key insights from academic papers. 
Review the following paper content and extract the most important theoretical and practical insights.
Focus especially on novel contributions, surprising findings, and implications for future research and practice.

For your analysis, please include:
1. The main novel contributions of this paper
2. Key insights that contradict or extend previous research
3. Practical applications of the research findings
4. Future research directions suggested by the results
5. Methodological innovations, if any

Paper content:

{text}
"""
        elif prompt_type == "tags":
            return text  # For tag generation, the full prompt is provided directly
        else:
            return f"Please summarize the following text:\n\n{text}"
    
    async def extract_metadata(self, text: str) -> Dict[str, str]:
        """
        Extract metadata from the first page of a paper.
        
        Args:
            text: Text from the first page
            
        Returns:
            Dictionary with metadata fields
        """
        prompt = f"""You are a metadata extraction tool for research papers.
Analyze the following text (likely from the first page of a scientific paper) and extract these metadata elements:
- title: The full title of the paper
- authors: The full author list, correctly formatted
- publication: Journal/conference name or other publication venue
- date: Publication date/year
- abstract: The paper's abstract if present

Return ONLY a JSON object with these fields. Do not include any explanatory text or other formatting.

Here's the text to analyze:

{text[:2000]}
"""
        
        response = await self.summarize_text(prompt, "metadata")
        extracted_text = self.extract_from_response(response)
        
        # Try to parse JSON from the response
        try:
            # Find JSON-like content within response
            import re
            json_match = re.search(r'\{.*\}', extracted_text, re.DOTALL)
            if json_match:
                metadata = json.loads(json_match.group())
                return metadata
        except Exception as e:
            print(f"Error parsing metadata JSON: {str(e)}")
        
        # Fallback: Extract using simpler text parsing
        metadata = {}
        metadata["title"] = self._extract_field(extracted_text, "title")
        metadata["authors"] = self._extract_field(extracted_text, "authors")
        metadata["publication"] = self._extract_field(extracted_text, "publication")
        metadata["date"] = self._extract_field(extracted_text, "date") 
        metadata["abstract"] = self._extract_field(extracted_text, "abstract")
        
        return metadata
    
    async def suggest_paper_tags(self, title: str, abstract: str) -> List[str]:
        """
        Suggest tags for a paper based on title and abstract.
        
        Args:
            title: Paper title
            abstract: Paper abstract
            
        Returns:
            List of suggested tags
        """
        prompt = f"""Generate 3-5 concise, relevant tags for this research paper. 
Return the tags as a simple comma-separated list without any additional text.

Paper Title: {title}

Paper Abstract: {abstract[:1000]}
"""
        
        try:
            response = await self.summarize_text(prompt, "tags")
            tags_text = self.extract_from_response(response)
            
            # Clean up and parse tags
            tags = [tag.strip() for tag in tags_text.replace("\n", ",").split(",") if tag.strip()]
            
            # Remove any explanatory text that might have been included
            tags = [tag for tag in tags if len(tag) < 50 and ":" not in tag and not tag.startswith("Tag")]
            
            return tags[:5]  # Return at most 5 tags
        except Exception as e:
            print(f"Error generating tags: {str(e)}")
            return []
    
    def _extract_field(self, text: str, field_name: str) -> str:
        """
        Simple helper to extract a field from text using basic parsing.
        """
        import re
        pattern = rf'"{field_name}"\s*:\s*"([^"]*)"'
        match = re.search(pattern, text)
        if match:
            return match.group(1)
            
        pattern = rf'"{field_name}"\s*:\s*(\S[^,\n]*)'
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip('"')
        
        return ""

"""
Advanced analysis tools for comparing papers and extracting relationships.
"""
import numpy as np
from typing import List, Dict, Tuple
import re
from .models import Paper, PaperStore
from .api import GeminiClient

async def compare_papers(paper_ids: List[int]) -> Dict:
    """
    Compare multiple papers and identify similarities, differences, and relationships.
    
    Args:
        paper_ids: List of paper IDs to compare
        
    Returns:
        Dictionary with comparison results
    """
    if len(paper_ids) < 2:
        return {"error": "Need at least two papers to compare"}
    
    # Get papers
    store = PaperStore()
    papers = [store.get_paper(pid) for pid in paper_ids]
    papers = [p for p in papers if p]  # Filter out None values
    
    if len(papers) < 2:
        return {"error": "At least one paper ID was invalid"}
    
    # Extract basic metadata for comparison
    metadata_comparison = []
    for paper in papers:
        metadata_comparison.append({
            "id": paper.id,
            "title": paper.title,
            "authors": paper.authors,
            "publication": paper.publication,
            "publication_date": paper.publication_date,
            "tags": paper.tags
        })
    
    # Find common authors
    all_authors = {}
    for paper in papers:
        author_names = [a.strip() for a in paper.authors.split(',') if a.strip()]
        for author in author_names:
            if author in all_authors:
                all_authors[author].append(paper.id)
            else:
                all_authors[author] = [paper.id]
    
    common_authors = {author: papers for author, papers in all_authors.items() if len(papers) > 1}
    
    # Check for common tags
    all_tags = {}
    for paper in papers:
        for tag in paper.tags:
            if tag in all_tags:
                all_tags[tag].append(paper.id)
            else:
                all_tags[tag] = [paper.id]
    
    common_tags = {tag: papers for tag, papers in all_tags.items() if len(papers) > 1}
    
    # Calculate publication date differences
    date_differences = []
    for i, paper1 in enumerate(papers):
        for paper2 in papers[i+1:]:
            try:
                year1 = int(re.search(r'(19|20)\d{2}', paper1.publication_date or "").group(0) or 0)
                year2 = int(re.search(r'(19|20)\d{2}', paper2.publication_date or "").group(0) or 0)
                if year1 and year2:
                    date_differences.append({
                        "paper1": {"id": paper1.id, "title": paper1.title, "year": year1},
                        "paper2": {"id": paper2.id, "title": paper2.title, "year": year2},
                        "difference": abs(year1 - year2)
                    })
            except (AttributeError, ValueError):
                pass
    
    # Use AI to compare papers
    ai_comparison = await compare_papers_with_ai(papers)
    
    return {
        "papers": metadata_comparison,
        "common_authors": common_authors,
        "common_tags": common_tags,
        "date_differences": date_differences,
        "ai_comparison": ai_comparison
    }

async def compare_papers_with_ai(papers: List[Paper]) -> Dict:
    """
    Use AI to compare papers and extract relationships.
    
    Args:
        papers: List of Paper objects to compare
        
    Returns:
        Dictionary with AI-generated comparison
    """
    client = GeminiClient()
    
    # Create a summary of each paper for comparison
    paper_summaries = []
    for i, paper in enumerate(papers):
        paper_summaries.append(f"Paper {i+1}: {paper.title}\n\nAuthors: {paper.authors}\n\nSummary: {paper.summary[:1000]}...")
    
    prompt = f"""
    I'll provide you with summaries of {len(papers)} research papers. Please analyze them and provide:
    
    1. A comparison of the main research questions or objectives
    2. Key methodological similarities and differences
    3. How findings relate to each other (supporting, contradicting, or extending)
    4. Potential synthesis of these papers (what new insights emerge when considering them together)
    
    Format your response as a JSON object with these four keys.
    
    Here are the paper summaries:
    
    {"\n\n".join(paper_summaries)}
    """
    
    response = await client.summarize_text(prompt, "insights")
    comparison_text = client.extract_from_response(response)
    
    # Try to parse as JSON, but if that fails, return as text
    try:
        import json
        # Extract JSON part from the response
        json_match = re.search(r'\{[\s\S]*\}', comparison_text)
        if json_match:
            json_str = json_match.group(0)
            return json.loads(json_str)
        else:
            # Return as structured text if JSON parsing fails
            return {
                "comparison": comparison_text,
                "format": "text"
            }
    except Exception:
        return {
            "comparison": comparison_text,
            "format": "text"
        }

async def extract_research_questions(paper_id: int) -> List[str]:
    """
    Extract research questions from a paper.
    
    Args:
        paper_id: ID of the paper
        
    Returns:
        List of extracted research questions
    """
    store = PaperStore()
    paper = store.get_paper(paper_id)
    
    if not paper:
        return []
    
    client = GeminiClient()
    
    # Focus on abstract and introduction
    abstract = paper.sections.get("Abstract", paper.sections.get("ABSTRACT", ""))
    intro = paper.sections.get("Introduction", paper.sections.get("INTRODUCTION", ""))
    
    content = f"{abstract}\n\n{intro}"
    
    prompt = f"""
    Please analyze this text from a research paper and extract all explicitly stated research questions,
    hypotheses, or research objectives. Format each as a separate item in a JSON array.
    
    Text from paper:
    {content[:3000]}
    """
    
    response = await client.summarize_text(prompt, "insights")
    result = client.extract_from_response(response)
    
    # Parse the result
    try:
        import json
        # Extract JSON array from the result
        json_match = re.search(r'\[[\s\S]*\]', result)
        if json_match:
            json_str = json_match.group(0)
            return json.loads(json_str)
        else:
            # If no JSON array is found, try to extract questions manually
            questions = []
            for line in result.split('\n'):
                line = line.strip()
                if line and (line.endswith('?') or line.startswith('-') or 
                            line.startswith('*') or 
                            re.match(r'^\d+\.', line)):
                    questions.append(line.lstrip('- *').strip())
            return questions
    except Exception:
        # Return an empty list if parsing fails
        return []

async def identify_citation_relationships(paper_ids: List[int]) -> Dict:
    """
    Identify potential citation relationships between papers.
    
    Args:
        paper_ids: List of paper IDs to analyze
        
    Returns:
        Dictionary with potential citation relationships
    """
    store = PaperStore()
    papers = [store.get_paper(pid) for pid in paper_ids]
    papers = [p for p in papers if p]
    
    if len(papers) < 2:
        return {"error": "Need at least two papers"}
    
    # Sort papers by publication date
    sorted_papers = sorted(
        papers, 
        key=lambda p: int(re.search(r'(19|20)\d{2}', p.publication_date or "").group(0) or 9999) 
            if p.publication_date and re.search(r'(19|20)\d{2}', p.publication_date) else 9999
    )
    
    # Find potential citations
    potential_citations = []
    for i, paper1 in enumerate(sorted_papers[:-1]):
        for paper2 in sorted_papers[i+1:]:
            # Check if paper2 might cite paper1 (paper1 is older)
            if paper1.authors:
                author_last_names = [a.strip().split()[-1] for a in paper1.authors.split(',') if a.strip()]
                potential_citation = False
                
                # Check if any author names from paper1 appear in paper2's content
                for author in author_last_names:
                    if len(author) > 3 and author in paper2.content:
                        potential_citation = True
                        break
                
                if potential_citation:
                    potential_citations.append({
                        "citing_paper": {"id": paper2.id, "title": paper2.title},
                        "cited_paper": {"id": paper1.id, "title": paper1.title},
                        "confidence": "low"  # This is just a guess based on text matching
                    })
    
    return {
        "potential_citations": potential_citations
    }

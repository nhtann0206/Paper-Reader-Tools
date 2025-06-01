"""
Vector search functionality for semantic paper searching.
"""
import os
import json
import sqlite3
import numpy as np
from typing import List, Dict, Any, Optional, Tuple

# Default path to the vector database
VECTOR_DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
VECTOR_DB_PATH = os.path.join(VECTOR_DB_DIR, "vectors.db")

try:
    # Try to import sentence transformers, but make it optional
    from sentence_transformers import SentenceTransformer
    VECTORS_ENABLED = True
except ImportError:
    VECTORS_ENABLED = False


class VectorStore:
    """Store and search paper embeddings."""
    
    def __init__(self, db_path=VECTOR_DB_PATH):
        """Initialize vector storage."""
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._create_tables()
        
        # Initialize the model if vectors are enabled
        self.model = None
        if VECTORS_ENABLED:
            try:
                # Use a small but effective model for embeddings
                self.model = SentenceTransformer('all-MiniLM-L6-v2')
            except Exception as e:
                print(f"Warning: Failed to load vector model: {str(e)}")
    
    def _create_tables(self):
        """Create necessary tables if they don't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Table to store vector embeddings for papers
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS embeddings (
            paper_id INTEGER PRIMARY KEY,
            title_vector TEXT,
            content_vector TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_embedding(self, paper_id: int, title: str, content: str) -> bool:
        """
        Create and store embeddings for a paper.
        
        Args:
            paper_id: ID of the paper
            title: Paper title
            content: Paper content (summary or full text)
            
        Returns:
            Success status
        """
        if not VECTORS_ENABLED or self.model is None:
            return False
        
        try:
            # Generate embeddings
            title_vector = self.model.encode(title).tolist() if title else []
            
            # For content, use a sample if it's too long
            if len(content) > 5000:
                # Sample the beginning, middle and end
                content_sample = content[:1500] + " " + content[len(content)//2-750:len(content)//2+750] + " " + content[-1500:]
            else:
                content_sample = content
                
            content_vector = self.model.encode(content_sample).tolist() if content_sample else []
            
            # Store embeddings
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            INSERT OR REPLACE INTO embeddings (paper_id, title_vector, content_vector)
            VALUES (?, ?, ?)
            ''', (
                paper_id,
                json.dumps(title_vector),
                json.dumps(content_vector)
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error adding embeddings: {str(e)}")
            return False
    
    def search(self, query: str, limit: int = 10) -> List[int]:
        """
        Find papers semantically similar to the query.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of paper IDs sorted by relevance
        """
        if not VECTORS_ENABLED or self.model is None:
            return []
        
        try:
            # Generate query embedding
            query_vector = self.model.encode(query)
            
            # Get all embeddings from the database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT paper_id, title_vector, content_vector FROM embeddings")
            embeddings = cursor.fetchall()
            conn.close()
            
            if not embeddings:
                return []
            
            # Calculate similarity scores
            results = []
            for paper_id, title_vector_json, content_vector_json in embeddings:
                title_vector = np.array(json.loads(title_vector_json)) if title_vector_json else np.array([])
                content_vector = np.array(json.loads(content_vector_json)) if content_vector_json else np.array([])
                
                # Calculate cosine similarity
                title_score = 0
                if title_vector.size > 0:
                    title_score = self._cosine_similarity(query_vector, title_vector) * 1.5  # Title gets higher weight
                
                content_score = 0
                if content_vector.size > 0:
                    content_score = self._cosine_similarity(query_vector, content_vector)
                
                # Combined score
                score = max(title_score, content_score)
                results.append((paper_id, score))
            
            # Sort by score (highest first) and return IDs
            results.sort(key=lambda x: x[1], reverse=True)
            return [paper_id for paper_id, _ in results[:limit]]
        
        except Exception as e:
            print(f"Error in vector search: {str(e)}")
            return []
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

"""
Repository for paper storage and retrieval.
"""
import os
import json
import sqlite3
from typing import List, Dict, Optional, Any
import datetime
from dataclasses import dataclass, field, asdict

# Ensure data directories exist
DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.environ.get("DB_PATH", os.path.join(DB_DIR, "papers.db"))

@dataclass
class Paper:
    """Class representing a research paper."""
    id: Optional[int] = None
    title: str = ""
    authors: str = ""
    publication: str = ""
    publication_date: str = ""
    url: str = ""
    file_path: str = ""
    summary: str = ""
    content: str = ""  # Full extracted content
    tags: List[str] = field(default_factory=list)
    sections: dict = field(default_factory=dict)
    processed_date: str = field(default_factory=lambda: datetime.datetime.now().isoformat())
    output_path: str = ""  # Path to generated summary PDF

    def to_dict(self):
        """Convert to dictionary for storage."""
        data = asdict(self)
        # We no longer convert tags to JSON here, as it's causing issues with API responses
        # Just ensure sections are properly serialized
        if isinstance(self.sections, dict):
            data['sections'] = json.dumps(self.sections)
        return data

    @classmethod
    def from_dict(cls, data):
        """Create instance from dictionary."""
        paper_data = dict(data)
        # Handle tags: ensure it's a list whether it came from DB as string or was already a list
        if 'tags' in paper_data:
            if isinstance(paper_data['tags'], str):
                try:
                    paper_data['tags'] = json.loads(paper_data['tags'])
                except json.JSONDecodeError:
                    paper_data['tags'] = []
            elif paper_data['tags'] is None:
                paper_data['tags'] = []
            
        # Handle sections: deserialize from JSON if it's a string
        if isinstance(paper_data.get('sections'), str):
            try:
                paper_data['sections'] = json.loads(paper_data['sections'])
            except json.JSONDecodeError:
                paper_data['sections'] = {}
                
        return cls(**paper_data)


class PaperRepository:
    """Repository for paper storage and retrieval."""
    
    def __init__(self, db_path=DB_PATH):
        """Initialize database connection."""
        self.db_path = db_path
        print(f"Initializing PaperRepository with DB path: {self.db_path}")
        try:
            self._create_tables()
            # Test connection immediately to verify
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            print(f"Connected to database with tables: {tables}")
            conn.close()
        except Exception as e:
            print(f"ERROR initializing repository: {str(e)}")
            # Re-raise to ensure startup fails if DB is inaccessible
            raise
        
    def _create_tables(self):
        """Create necessary tables if they don't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Papers table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS papers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            authors TEXT,
            publication TEXT,
            publication_date TEXT,
            url TEXT,
            file_path TEXT,
            summary TEXT,
            content TEXT,
            tags TEXT,
            sections TEXT,
            processed_date TEXT,
            output_path TEXT
        )
        ''')
        
        # Tags table for faster searching
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
        ''')
        
        # Paper-Tag relationship table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS paper_tags (
            paper_id INTEGER,
            tag_id INTEGER,
            PRIMARY KEY (paper_id, tag_id),
            FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_paper(self, paper: Paper) -> int:
        """
        Save a paper to the database.
        
        Args:
            paper: Paper object to save
            
        Returns:
            ID of the saved paper
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        paper_id = None
        
        try:
            # Convert Paper object to dict for storage
            paper_dict = paper.to_dict()
            paper_id = paper_dict.pop('id', None)
            
            # Process all values to ensure SQLite compatibility
            for key, value in list(paper_dict.items()):
                # Special handling for tags - convert list to JSON string for database storage
                if key == 'tags' and isinstance(value, list):
                    paper_dict[key] = json.dumps(value)
                # Ensure all values are of types SQLite can handle
                elif isinstance(value, (dict, list, tuple, set)) and key not in ['tags', 'sections']:
                    # Convert any other complex objects to JSON string
                    paper_dict[key] = json.dumps(value) if value else None
                elif value is None:
                    # Explicitly handle None values
                    paper_dict[key] = None
                elif not isinstance(value, (str, int, float, bool)):
                    # Convert any other types to string
                    paper_dict[key] = str(value)
            
            if paper_id:
                # Update existing paper
                placeholders = ", ".join([f"{k} = ?" for k in paper_dict.keys()])
                values = list(paper_dict.values())
                sql = f"UPDATE papers SET {placeholders} WHERE id = ?"
                cursor.execute(sql, values + [paper_id])
            else:
                # Insert new paper
                columns = ", ".join(paper_dict.keys())
                placeholders = ", ".join(["?"] * len(paper_dict))
                values = list(paper_dict.values())
                sql = f"INSERT INTO papers ({columns}) VALUES ({placeholders})"
                cursor.execute(sql, values)
                paper_id = cursor.lastrowid
            
            # Save tags as separate entries if needed
            if paper.tags and isinstance(paper.tags, list):
                self._save_paper_tags(cursor, paper_id, paper.tags)
            
            conn.commit()
            return paper_id
            
        except Exception as e:
            conn.rollback()
            print(f"Database error: {str(e)}")
            raise
        finally:
            conn.close()
    
    def _save_paper_tags(self, cursor, paper_id: int, tags: List[str]):
        """Save paper tags to the database."""
        # Clear existing tags for this paper
        cursor.execute("DELETE FROM paper_tags WHERE paper_id = ?", (paper_id,))
        
        # Process each tag
        for tag in tags:
            # Get or create tag
            cursor.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag,))
            cursor.execute("SELECT id FROM tags WHERE name = ?", (tag,))
            tag_id = cursor.fetchone()[0]
            
            # Link tag to paper
            cursor.execute("INSERT INTO paper_tags (paper_id, tag_id) VALUES (?, ?)", 
                         (paper_id, tag_id))
    
    def get_paper(self, paper_id: int) -> Optional[Paper]:
        """
        Retrieve a paper by ID.
        
        Args:
            paper_id: ID of the paper to retrieve
            
        Returns:
            Paper object or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM papers WHERE id = ?", (paper_id,))
        paper_data = cursor.fetchone()
        
        if not paper_data:
            conn.close()
            return None
        
        # Get tags for this paper
        cursor.execute("""
            SELECT t.name FROM tags t
            JOIN paper_tags pt ON t.id = pt.tag_id
            WHERE pt.paper_id = ?
        """, (paper_id,))
        
        tags = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        # Create Paper object
        paper_dict = dict(paper_data)
        paper_dict['tags'] = tags
        
        return Paper.from_dict(paper_dict)
    
    def get_papers(self, limit=100, offset=0, tag=None) -> List[Paper]:
        """
        Retrieve multiple papers, optionally filtered by tag.
        
        Args:
            limit: Maximum number of papers to return
            offset: Number of papers to skip
            tag: Optional tag to filter by
            
        Returns:
            List of Paper objects
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if tag:
                # Fix: Use clearer query logic and better error handling for tag filtering
                try:
                    # First check if the tag exists
                    cursor.execute("SELECT id FROM tags WHERE name = ?", (tag,))
                    tag_row = cursor.fetchone()
                    
                    if not tag_row:
                        print(f"Tag '{tag}' not found in database")
                        return []
                    
                    tag_id = tag_row['id']
                    
                    # Now get papers with this tag using clearer JOIN syntax
                    cursor.execute("""
                        SELECT p.* FROM papers p
                        JOIN paper_tags pt ON p.id = pt.paper_id
                        WHERE pt.tag_id = ?
                        ORDER BY p.processed_date DESC
                        LIMIT ? OFFSET ?
                    """, (tag_id, limit, offset))
                except Exception as e:
                    print(f"Error querying papers by tag: {str(e)}")
                    # Fallback to get all papers if tag query fails
                    cursor.execute("""
                        SELECT * FROM papers
                        ORDER BY processed_date DESC
                        LIMIT ? OFFSET ?
                    """, (limit, offset))
            else:
                cursor.execute("""
                    SELECT * FROM papers
                    ORDER BY processed_date DESC
                    LIMIT ? OFFSET ?
                """, (limit, offset))
                
            paper_rows = cursor.fetchall()
            papers = []
            
            for row in paper_rows:
                try:
                    paper_id = row['id']
                    
                    # Get tags for this paper
                    cursor.execute("""
                        SELECT t.name FROM tags t
                        JOIN paper_tags pt ON t.id = pt.tag_id
                        WHERE pt.paper_id = ?
                    """, (paper_id,))
                    
                    tags = [tag_row[0] for tag_row in cursor.fetchall()]
                    
                    # Create Paper object
                    paper_dict = dict(row)
                    paper_dict['tags'] = tags
                    
                    # Enhanced error handling for paper creation
                    try:
                        paper = Paper.from_dict(paper_dict)
                        papers.append(paper)
                    except Exception as paper_error:
                        print(f"Error creating Paper object from row {paper_id}: {str(paper_error)}")
                        # Continue loop to process other papers
                except Exception as row_error:
                    print(f"Error processing paper row: {str(row_error)}")
                    # Continue loop to process other papers
            
            conn.close()
            return papers
        except Exception as e:
            print(f"ERROR in get_papers: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            # Return empty list instead of crashing
            return []
    
    def search_papers(self, query: str, limit=100) -> List[Paper]:
        """
        Search papers by keyword.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching Paper objects
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Construct search query with wildcards
            search_term = f"%{query}%"
            
            # Fix: Use clearer query with better JOIN syntax and error handling
            cursor.execute("""
                SELECT DISTINCT p.*
                FROM papers p
                LEFT JOIN paper_tags pt ON p.id = pt.paper_id
                LEFT JOIN tags t ON pt.tag_id = t.id
                WHERE 
                    p.title LIKE ? OR
                    p.authors LIKE ? OR
                    p.summary LIKE ? OR
                    p.content LIKE ? OR
                    t.name LIKE ?
                ORDER BY p.processed_date DESC
                LIMIT ?
            """, (search_term, search_term, search_term, search_term, search_term, limit))
            
            paper_rows = cursor.fetchall()
            papers = []
            
            for row in paper_rows:
                try:
                    paper_id = row['id']
                    
                    # Get tags for this paper
                    cursor.execute("""
                        SELECT t.name FROM tags t
                        JOIN paper_tags pt ON t.id = pt.tag_id
                        WHERE pt.paper_id = ?
                    """, (paper_id,))
                    
                    tags = [tag_row[0] for tag_row in cursor.fetchall()]
                    
                    # Create Paper object
                    paper_dict = dict(row)
                    paper_dict['tags'] = tags
                    papers.append(Paper.from_dict(paper_dict))
                except Exception as row_error:
                    print(f"Error processing search result row: {str(row_error)}")
                    # Continue loop to process other papers
            
            conn.close()
            return papers
        except Exception as e:
            print(f"ERROR in search_papers: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return []
    
    def get_all_tags(self) -> List[str]:
        """
        Get all existing tags in the database.
        
        Returns:
            List of tag names
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM tags ORDER BY name")
        tags = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        return tags
    
    def delete_paper(self, paper_id: int) -> bool:
        """
        Delete a paper from the database.
        
        Args:
            paper_id: ID of the paper to delete
            
        Returns:
            True if successful
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM papers WHERE id = ?", (paper_id,))
        success = cursor.rowcount > 0
        
        conn.commit()
        conn.close()
        return success

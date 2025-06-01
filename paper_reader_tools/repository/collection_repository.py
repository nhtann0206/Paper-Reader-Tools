"""
Repository for reading list/collection management.
"""
import os
import sqlite3
from typing import List, Dict, Optional, Any
import datetime
from dataclasses import dataclass, field, asdict

# Ensure data directories exist
DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.environ.get("DB_PATH", os.path.join(DB_DIR, "papers.db"))


@dataclass
class Collection:
    """Class representing a collection of papers."""
    id: Optional[int] = None
    name: str = ""
    description: str = ""
    papers: List[int] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.datetime.now().isoformat())

    def to_dict(self):
        """Convert to dictionary for storage."""
        return asdict(self)


class CollectionRepository:
    """Repository for collection storage and retrieval."""
    
    def __init__(self, db_path=DB_PATH):
        """Initialize database connection."""
        self.db_path = db_path
        print(f"Initializing CollectionRepository with DB path: {self.db_path}")
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
            print(f"ERROR initializing collection repository: {str(e)}")
            # Re-raise to ensure startup fails if DB is inaccessible
            raise
    
    def _create_tables(self):
        """Create necessary tables if they don't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Collections table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS collections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            created_at TEXT
        )
        ''')
        
        # Check if collection_papers table exists, and if it's missing the read_status column
        cursor.execute("PRAGMA table_info(collection_papers)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        if not columns:
            # Table doesn't exist, create it with the read_status column
            cursor.execute('''
            CREATE TABLE collection_papers (
                collection_id INTEGER,
                paper_id INTEGER,
                read_status INTEGER DEFAULT 0,
                PRIMARY KEY (collection_id, paper_id),
                FOREIGN KEY (collection_id) REFERENCES collections(id) ON DELETE CASCADE,
                FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE
            )
            ''')
            print("Created collection_papers table with read_status column")
        elif 'read_status' not in column_names:
            # Table exists but missing read_status column, add it
            print("Adding read_status column to collection_papers table")
            cursor.execute('ALTER TABLE collection_papers ADD COLUMN read_status INTEGER DEFAULT 0')
            
        conn.commit()
        conn.close()
    
    def get_collections(self) -> List[Dict]:
        """Get all collections."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM collections ORDER BY name")
            collections = []
            
            for row in cursor.fetchall():
                collection = dict(row)
                
                # Get papers for this collection with read status
                try:
                    # First check if read_status column exists
                    cursor.execute("PRAGMA table_info(collection_papers)")
                    columns = [col[1] for col in cursor.fetchall()]
                    has_read_status = 'read_status' in columns
                    
                    if has_read_status:
                        cursor.execute('''
                        SELECT paper_id, read_status FROM collection_papers 
                        WHERE collection_id = ?
                        ''', (collection['id'],))
                    else:
                        # Use a simplified query without read_status
                        cursor.execute('''
                        SELECT paper_id FROM collection_papers 
                        WHERE collection_id = ?
                        ''', (collection['id'],))
                    
                    paper_details = {}
                    paper_ids = []
                    for r in cursor.fetchall():
                        paper_id = r[0]
                        # Use defaults if read_status is not available
                        read_status = bool(r[1]) if has_read_status and len(r) > 1 else False
                        paper_details[str(paper_id)] = {"read_status": read_status}
                        paper_ids.append(paper_id)
                    
                    collection['papers'] = paper_ids
                    collection['paper_details'] = paper_details
                except Exception as e:
                    print(f"Error getting paper details: {str(e)}")
                    collection['papers'] = []
                    collection['paper_details'] = {}
                
                collections.append(collection)
            
            conn.close()
            return collections
        except Exception as e:
            print(f"ERROR in get_collections: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            # Return empty list instead of crashing
            return []
    
    def get_collection(self, collection_id: int) -> Optional[Dict]:
        """Get a specific collection."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM collections WHERE id = ?", (collection_id,))
            row = cursor.fetchone()
            
            if not row:
                conn.close()
                return None
            
            collection = dict(row)
            
            # Get papers for this collection with read status
            try:
                # First check if read_status column exists
                cursor.execute("PRAGMA table_info(collection_papers)")
                columns = [col[1] for col in cursor.fetchall()]
                has_read_status = 'read_status' in columns
                
                if has_read_status:
                    cursor.execute('''
                    SELECT paper_id, read_status FROM collection_papers 
                    WHERE collection_id = ?
                    ''', (collection_id,))
                else:
                    # Use a simplified query without read_status
                    cursor.execute('''
                    SELECT paper_id FROM collection_papers 
                    WHERE collection_id = ?
                    ''', (collection_id,))
                
                paper_details = {}
                paper_ids = []
                for r in cursor.fetchall():
                    paper_id = r[0]
                    # Use defaults if read_status is not available
                    read_status = bool(r[1]) if has_read_status and len(r) > 1 else False
                    paper_details[str(paper_id)] = {"read_status": read_status}
                    paper_ids.append(paper_id)
                
                # Add the paper IDs list for backward compatibility
                collection['papers'] = paper_ids
                # Add the detailed paper info
                collection['paper_details'] = paper_details
            except Exception as e:
                print(f"Error getting paper details: {str(e)}")
                collection['papers'] = []
                collection['paper_details'] = {}
            
            conn.close()
            return collection
        except Exception as e:
            print(f"ERROR in get_collection: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return None
    
    def save_collection(self, collection: Collection) -> int:
        """
        Save a collection to the database.
        
        Args:
            collection: Collection object to save
            
        Returns:
            ID of the saved collection
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            if collection.id:
                # Update existing collection
                cursor.execute('''
                UPDATE collections
                SET name = ?, description = ?
                WHERE id = ?
                ''', (collection.name, collection.description, collection.id))
                collection_id = collection.id
            else:
                # Insert new collection
                cursor.execute('''
                INSERT INTO collections (name, description, created_at)
                VALUES (?, ?, ?)
                ''', (collection.name, collection.description, collection.created_at))
                collection_id = cursor.lastrowid
            
            # Update paper associations
            if collection_id:
                # Remove all existing associations
                cursor.execute('''
                DELETE FROM collection_papers 
                WHERE collection_id = ?
                ''', (collection_id,))
                
                # Add new associations
                for paper_id in collection.papers:
                    cursor.execute('''
                    INSERT INTO collection_papers (collection_id, paper_id, read_status)
                    VALUES (?, ?, 0)
                    ''', (collection_id, paper_id))
            
            conn.commit()
            return collection_id
            
        except Exception as e:
            conn.rollback()
            print(f"Error saving collection: {str(e)}")
            return 0
        finally:
            conn.close()
    
    def add_paper_to_collection(self, collection_id: int, paper_id: int) -> bool:
        """Add a paper to a collection."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Check if collection and paper exist
            cursor.execute("SELECT id FROM collections WHERE id = ?", (collection_id,))
            if not cursor.fetchone():
                print(f"Collection {collection_id} not found")
                conn.close()
                return False
            
            cursor.execute("SELECT id FROM papers WHERE id = ?", (paper_id,))
            if not cursor.fetchone():
                print(f"Paper {paper_id} not found")
                conn.close()
                return False
            
            # Add paper to collection
            cursor.execute('''
            INSERT OR IGNORE INTO collection_papers (collection_id, paper_id, read_status)
            VALUES (?, ?, 0)
            ''', (collection_id, paper_id))
            
            conn.commit()
            # Consider it success even if the paper was already in the collection
            return True
            
        except Exception as e:
            print(f"Database error in add_paper_to_collection: {str(e)}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def remove_paper_from_collection(self, collection_id: int, paper_id: int) -> bool:
        """Remove a paper from a collection."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
            DELETE FROM collection_papers 
            WHERE collection_id = ? AND paper_id = ?
            ''', (collection_id, paper_id))
            
            conn.commit()
            return cursor.rowcount > 0
            
        except Exception as e:
            conn.rollback()
            print(f"Error removing paper from collection: {str(e)}")
            return False
        finally:
            conn.close()
    
    def update_paper_read_status(self, collection_id: int, paper_id: int, read_status: bool) -> bool:
        """Update read status for a paper in a collection."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
            UPDATE collection_papers 
            SET read_status = ? 
            WHERE collection_id = ? AND paper_id = ?
            ''', (int(read_status), collection_id, paper_id))
            
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"Error updating read status: {str(e)}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def delete_collection(self, collection_id: int) -> bool:
        """Delete a collection."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # First delete entries from the collection_papers table
            cursor.execute("DELETE FROM collection_papers WHERE collection_id = ?", (collection_id,))
            # Then delete the collection itself
            cursor.execute("DELETE FROM collections WHERE id = ?", (collection_id,))
            
            success = cursor.rowcount > 0
            conn.commit()
            return success
        except Exception as e:
            print(f"Error deleting collection: {str(e)}")
            conn.rollback()
            return False
        finally:
            conn.close()

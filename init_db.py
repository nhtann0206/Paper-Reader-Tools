"""
Initialize the database structure manually.
"""
import os
import sqlite3
import traceback

# Ensure data directories exist
DB_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, "papers.db")

def init_db():
    """Initialize the database with required tables."""
    print(f"Initializing database at: {DB_PATH}")
    
    try:
        # Ensure the directory permissions are correct first
        if not os.path.isdir(DB_DIR):
            os.makedirs(DB_DIR, exist_ok=True)
            print(f"Created directory: {DB_DIR}")
        
        # Check directory permissions
        os.chmod(DB_DIR, 0o777)  # rwx for all users
        print(f"Updated permissions for {DB_DIR}")
        
        # Create a new connection - will create the file if it doesn't exist
        conn = sqlite3.connect(DB_PATH)
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
        
        # Tags table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
        ''')
        
        # Paper-Tag relationship
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS paper_tags (
            paper_id INTEGER,
            tag_id INTEGER,
            PRIMARY KEY (paper_id, tag_id),
            FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
        )
        ''')
        
        # Collections table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS collections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            created_at TEXT
        )
        ''')
        
        # Collection-Paper relationship table with read status
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS collection_papers (
            collection_id INTEGER,
            paper_id INTEGER,
            read_status INTEGER DEFAULT 0,
            PRIMARY KEY (collection_id, paper_id),
            FOREIGN KEY (collection_id) REFERENCES collections(id) ON DELETE CASCADE,
            FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE
        )
        ''')
        
        # Check if collection_papers table is missing read_status column and add it if needed
        cursor.execute("PRAGMA table_info(collection_papers)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        if columns and 'read_status' not in column_names:
            print("Adding missing read_status column to collection_papers table")
            try:
                cursor.execute('ALTER TABLE collection_papers ADD COLUMN read_status INTEGER DEFAULT 0')
                print("Successfully added read_status column")
            except Exception as e:
                print(f"Error adding read_status column: {str(e)}")
        
        conn.commit()
        conn.close()
        
        # Set permissions on the database file
        os.chmod(DB_PATH, 0o666)  # rw for all users
        print(f"Set permissions on database file: {DB_PATH}")
        
        # Test if we can read the database
        test_conn = sqlite3.connect(DB_PATH)
        test_cursor = test_conn.cursor()
        test_cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = test_cursor.fetchall()
        test_conn.close()
        print(f"Database initialized successfully with tables: {tables}")
        
    except Exception as e:
        print(f"Error initializing database: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        raise

if __name__ == "__main__":
    init_db()

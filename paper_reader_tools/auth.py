"""
Authentication and user management for Paper Reader Tools.
"""
import os
import json
import hashlib
import secrets
import datetime
from typing import Dict, List, Optional, Any
import sqlite3
from dataclasses import dataclass, field, asdict

# Path to database
DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
os.makedirs(DB_DIR, exist_ok=True)
AUTH_DB_PATH = os.path.join(DB_DIR, "auth.db")

@dataclass
class User:
    """User model."""
    id: Optional[int] = None
    username: str = ""
    email: str = ""
    password_hash: str = ""  # Store hashed passwords only
    full_name: str = ""
    created_at: str = field(default_factory=lambda: datetime.datetime.now().isoformat())
    is_active: bool = True
    
    def to_dict(self):
        """Convert to dictionary, omitting password."""
        data = asdict(self)
        data.pop("password_hash")
        return data

class AuthManager:
    """Handle user authentication and management."""
    
    def __init__(self, db_path=AUTH_DB_PATH):
        self.db_path = db_path
        self._create_tables()
    
    def _create_tables(self):
        """Create necessary tables if they don't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT,
            created_at TEXT NOT NULL,
            is_active INTEGER NOT NULL
        )
        ''')
        
        # Sessions table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def register_user(self, username: str, email: str, password: str, full_name: str = "") -> Optional[User]:
        """
        Register a new user.
        
        Args:
            username: Unique username
            email: Email address
            password: Plain text password
            full_name: User's full name
            
        Returns:
            User object if successful, None if username/email already exists
        """
        # Check if username or email already exists
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM users WHERE username = ? OR email = ?", (username, email))
        if cursor.fetchone():
            conn.close()
            return None  # User already exists
        
        # Hash password
        password_hash = self._hash_password(password)
        
        # Create new user
        user = User(
            username=username,
            email=email,
            password_hash=password_hash,
            full_name=full_name,
            created_at=datetime.datetime.now().isoformat(),
            is_active=True
        )
        
        try:
            cursor.execute('''
            INSERT INTO users (username, email, password_hash, full_name, created_at, is_active)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                user.username, user.email, user.password_hash,
                user.full_name, user.created_at, int(user.is_active)
            ))
            conn.commit()
            user.id = cursor.lastrowid
            return user
        except Exception as e:
            conn.rollback()
            print(f"Error registering user: {str(e)}")
            return None
        finally:
            conn.close()
    
    def login(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Authenticate a user and create a session.
        
        Args:
            username: Username
            password: Password
            
        Returns:
            Dictionary with user info and token if successful, None otherwise
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Find user by username
        cursor.execute("SELECT * FROM users WHERE username = ? AND is_active = 1", (username,))
        user_data = cursor.fetchone()
        
        if not user_data:
            conn.close()
            return None  # User not found
        
        # Check password
        if not self._verify_password(password, user_data["password_hash"]):
            conn.close()
            return None  # Incorrect password
        
        # Create session token
        token = secrets.token_hex(32)
        expires_at = (datetime.datetime.now() + datetime.timedelta(days=7)).isoformat()
        
        try:
            cursor.execute('''
            INSERT INTO sessions (token, user_id, created_at, expires_at)
            VALUES (?, ?, ?, ?)
            ''', (
                token, user_data["id"], datetime.datetime.now().isoformat(), expires_at
            ))
            conn.commit()
            
            # Create user object
            user = User(
                id=user_data["id"],
                username=user_data["username"],
                email=user_data["email"],
                password_hash="",  # Don't include in response
                full_name=user_data["full_name"],
                created_at=user_data["created_at"],
                is_active=bool(user_data["is_active"])
            )
            
            return {
                "user": user.to_dict(),
                "token": token,
                "expires_at": expires_at
            }
        except Exception as e:
            conn.rollback()
            print(f"Error creating session: {str(e)}")
            return None
        finally:
            conn.close()
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify a session token.
        
        Args:
            token: Session token
            
        Returns:
            User info if valid, None otherwise
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Find session
        cursor.execute('''
        SELECT s.*, u.*
        FROM sessions s
        JOIN users u ON s.user_id = u.id
        WHERE s.token = ? AND s.expires_at > ? AND u.is_active = 1
        ''', (token, datetime.datetime.now().isoformat()))
        
        session_data = cursor.fetchone()
        conn.close()
        
        if not session_data:
            return None  # Invalid or expired token
        
        # Create user object
        user = User(
            id=session_data["id"],
            username=session_data["username"],
            email=session_data["email"],
            password_hash="",  # Don't include in response
            full_name=session_data["full_name"],
            created_at=session_data["created_at"],
            is_active=bool(session_data["is_active"])
        )
        
        return user.to_dict()
    
    def logout(self, token: str) -> bool:
        """
        Invalidate a session token.
        
        Args:
            token: Session token
            
        Returns:
            True if successful, False otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM sessions WHERE token = ?", (token,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception:
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get user by ID.
        
        Args:
            user_id: User ID
            
        Returns:
            User info if found, None otherwise
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user_data = cursor.fetchone()
        conn.close()
        
        if not user_data:
            return None
        
        user = User(
            id=user_data["id"],
            username=user_data["username"],
            email=user_data["email"],
            password_hash="",  # Don't include in response
            full_name=user_data["full_name"],
            created_at=user_data["created_at"],
            is_active=bool(user_data["is_active"])
        )
        
        return user.to_dict()
    
    def _hash_password(self, password: str) -> str:
        """
        Hash a password with salt.
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password
        """
        salt = secrets.token_hex(8)
        hash_obj = hashlib.sha256((password + salt).encode())
        return f"{salt}${hash_obj.hexdigest()}"
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """
        Verify a password against a hash.
        
        Args:
            password: Plain text password
            password_hash: Hashed password with salt
            
        Returns:
            True if password matches, False otherwise
        """
        try:
            salt, hash_value = password_hash.split('$')
            hash_obj = hashlib.sha256((password + salt).encode())
            return hash_obj.hexdigest() == hash_value
        except Exception:
            return False

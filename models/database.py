# database.py
import os
import json
import sqlite3
from pymongo import MongoClient
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
import threading
import time
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(__file__), '..', 'logs', 'database.log')),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages database connections and operations"""
    
    def __init__(self, db_path: str = None):
        """Initialize database connection"""
        self.db_path = db_path or os.path.join(
            os.path.dirname(__file__), 
            '..', 
            'data', 
            'ai_assistant.db'
        )
        self.connection = None
        self.lock = threading.Lock()
        
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
        
    def connect(self):
        """Establish database connection"""
        with self.lock:
            if self.connection is None:
                self.connection = sqlite3.connect(self.db_path)
                self.connection.row_factory = sqlite3.Row
                
    def close(self):
        """Close database connection"""
        with self.lock:
            if self.connection:
                self.connection.close()
                self.connection = None

    def get_preference(self, category: str, key: str, default: Any = None) -> Any:
        """Get a preference value from the database"""
        with self.lock:
            try:
                self.connect()  # Ensure connection exists
                cursor = self.connection.cursor()
                cursor.execute(
                    "SELECT value FROM preferences WHERE category = ? AND key = ?",
                    (category, key)
                )
                result = cursor.fetchone()
                return json.loads(result['value']) if result else default
            except Exception as e:
                logger.error(f"Error getting preference: {str(e)}")
                return default

    def save_preference(self, category: str, key: str, value: Any) -> bool:
        """Save a preference value to the database"""
        with self.lock:
            try:
                self.connect()  # Ensure connection exists
                cursor = self.connection.cursor()
                cursor.execute(
                    """INSERT OR REPLACE INTO preferences 
                    (category, key, value) VALUES (?, ?, ?)""",
                    (category, key, json.dumps(value))
                )
                self.connection.commit()
                return True
            except Exception as e:
                logger.error(f"Error saving preference: {str(e)}")
                return False

    def log_system_event(self, event_type: str, metadata: Dict = None) -> bool:
        """Log system events to database"""
        with self.lock:
            try:
                self.connect()  # Ensure connection exists
                cursor = self.connection.cursor()
                cursor.execute(
                    """INSERT INTO system_events 
                    (timestamp, event_type, metadata) VALUES (?, ?, ?)""",
                    (datetime.now().isoformat(), event_type, json.dumps(metadata or {}))
                )
                self.connection.commit()
                return True
            except Exception as e:
                logger.error(f"Error logging system event: {str(e)}")
                return False

# MongoDB Functions
_mongo_client = None
_mongo_db = None

def get_mongo_collection(collection_name: str):
    """Get a MongoDB collection instance"""
    global _mongo_client, _mongo_db
    
    if _mongo_client is None:
        _mongo_client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"))
        _mongo_db = _mongo_client.get_database(os.getenv("MONGO_DB", "ai_assistant"))
    
    return _mongo_db.get_collection(collection_name)

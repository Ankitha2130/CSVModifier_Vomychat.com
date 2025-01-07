import sqlite3
from contextlib import contextmanager
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Get the database path
DB_PATH = Path(__file__).resolve().parent.parent / "operations.db"

@contextmanager
def get_db_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    try:
        with get_db_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS operations_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation_type TEXT NOT NULL,
                    filename TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    details TEXT
                )
            ''')
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON operations_log(timestamp)
            ''')
            conn.commit()
            logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise

def log_operation(filename: str, operation_type: str, details: str = None):
    try:
        with get_db_connection() as conn:
            conn.execute('''
                INSERT INTO operations_log (operation_type, filename, details)
                VALUES (?, ?, ?)
            ''', (operation_type, filename, details))
            conn.commit()
            logger.info(f"Operation logged: {operation_type} - {filename}")
    except Exception as e:
        logger.error(f"Error logging operation: {str(e)}")
        raise 
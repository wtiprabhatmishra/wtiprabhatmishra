import sqlite3
import os
from werkzeug.security import generate_password_hash
import datetime

# Default database path (can be overridden for testing)
DATABASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(DATABASE_DIR, 'users.db')

def get_db_path():
    """Returns the currently configured database path."""
    return DATABASE_PATH

def set_db_path(path):
    """Sets the database path. Used for testing."""
    global DATABASE_PATH
    DATABASE_PATH = path

def init_db(db_path=None):
    """Initializes the database and creates the users table if it doesn't exist."""
    path_to_use = db_path if db_path else get_db_path()
    conn = None
    try:
        # Ensure the directory for the database exists if it's not in-memory
        if path_to_use != ':memory:':
            os.makedirs(os.path.dirname(path_to_use), exist_ok=True)
            
        conn = sqlite3.connect(path_to_use)
        cursor = conn.cursor()
        # Drop table if it exists, to ensure a clean state for init_db during tests
        # cursor.execute("DROP TABLE IF EXISTS users") 
        # Decided against DROP TABLE here to keep init_db idempotent for production
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                trial_start_date TIMESTAMP
            )
        ''')
        conn.commit()
        # print(f"Database initialized at {path_to_use}") # Quieter for tests
    except sqlite3.Error as e:
        print(f"Database initialization error at {path_to_use}: {e}")
    finally:
        if conn:
            conn.close()

def add_user(email, password, db_path=None):
    """Adds a new user to the database. Hashes the password before storing."""
    path_to_use = db_path if db_path else get_db_path()
    conn = None
    try:
        conn = sqlite3.connect(path_to_use)
        cursor = conn.cursor()
        
        # Check if email already exists
        cursor.execute("SELECT email FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            return False, "Email already registered."

        hashed_password = generate_password_hash(password)
        current_time = datetime.datetime.utcnow() # Using UTC for consistency
        
        cursor.execute('''
            INSERT INTO users (email, password_hash, registration_date, trial_start_date)
            VALUES (?, ?, ?, ?)
        ''', (email, hashed_password, current_time, current_time))
        
        conn.commit()
        return True, "Registration successful! Your 7-day trial has started."
    except sqlite3.Error as e:
        # print(f"Error adding user to {path_to_use}: {e}") # Quieter for tests
        return False, f"Database error: {e}"
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    # This allows initializing the DB by running `python BharatPath/database.py`
    # This will use the default DATABASE_PATH
    print("Initializing database directly with default path...")
    init_db()

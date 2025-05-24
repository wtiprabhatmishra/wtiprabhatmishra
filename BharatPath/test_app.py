import os
import unittest
import tempfile
import sqlite3
from werkzeug.security import check_password_hash

# Temporarily add BharatPath to sys.path to allow direct import of app and database
# This assumes the test is run from the root of the project or BharatPath is in PYTHONPATH
import sys
# Assuming the tests are run from the directory containing BharatPath, or BharatPath is discoverable
# For SWE-bench, the /app directory is the root.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


from BharatPath import app as flask_app  # Renamed to avoid conflict with 'app' variable
from BharatPath import database

class TestBharatPathApp(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Set up for all tests in the class."""
        # Create a temporary file for the test database
        cls.db_fd, cls.test_db_path = tempfile.mkstemp(suffix='.db', prefix='bharatpath_test_')
        # print(f"Using test database: {cls.test_db_path}")

        # Configure database module to use the test database
        database.set_db_path(cls.test_db_path)
        
        # Configure Flask app for testing
        flask_app.app.config['TESTING'] = True
        flask_app.app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for simpler form tests
        flask_app.app.config['SECRET_KEY'] = 'test_secret_key' # Needed for session/flash
        
        # Initialize the test database structure
        # This call to init_db() happens *before* the app is run or database.init_db() in app.py is called
        # So the app's own database.init_db() will use the test_db_path
        # No, app.py's database.init_db() runs at import time of app.py.
        # We need to ensure that set_db_path is called BEFORE app.py's database.init_db() is run.
        # This is tricky. The current app.py initializes DB at module level.
        # For testing, it's better if app.py's init_db is conditional or called within app_context.
        # For now, we'll re-initialize it here AFTER app is imported and its init_db has run on the default path.
        # This means the default users.db might get created, but tests will use test_db_path.
        database.init_db(cls.test_db_path)


        cls.client = flask_app.app.test_client()
        cls.app = flask_app.app # for app_context

    @classmethod
    def tearDownClass(cls):
        """Tear down after all tests in the class."""
        os.close(cls.db_fd)
        os.unlink(cls.test_db_path)
        # print(f"Test database {cls.test_db_path} removed.")
        # Restore original DB path if necessary for other potential test suites (not strictly needed here)
        original_db_dir = os.path.dirname(os.path.abspath(database.__file__))
        original_db_path = os.path.join(original_db_dir, 'users.db')
        database.set_db_path(original_db_path)


    def setUp(self):
        """Set up before each test method."""
        # Ensure a clean database for each test by re-initializing
        # This will clear any data from previous tests
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS users")
        conn.commit()
        conn.close()
        database.init_db(self.test_db_path) # Recreate the table structure

    def tearDown(self):
        """Tear down after each test method (if needed)."""
        # Most cleanup is per-test in setUp or per-class in tearDownClass
        pass

    def test_page_accessibility(self):
        """Test accessibility of main pages (GET requests)."""
        pages = [
            '/', '/about', '/register', '/api_key', '/api/docs', '/payment-methods'
        ]
        for page_url in pages:
            with self.subTest(page=page_url):
                response = self.client.get(page_url)
                self.assertEqual(response.status_code, 200, f"Page {page_url} failed to load.")

    def test_successful_registration(self):
        """Test successful user registration and password hashing."""
        with self.app.app_context(): # Ensure app context for database operations if any are tied to it
            response = self.client.post('/register', data={
                'email': 'testuser@example.com',
                'password': 'password123'
            }, follow_redirects=True) # follow_redirects to check final page content & flashed messages

            self.assertEqual(response.status_code, 200) # Should render register page again
            self.assertIn(b"Registration successful!", response.data)
            self.assertIn(b"view your placeholder API key", response.data) # Check for API key link

            # Verify user in database
            conn = sqlite3.connect(self.test_db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT email, password_hash FROM users WHERE email = ?", ('testuser@example.com',))
            user_record = cursor.fetchone()
            conn.close()

            self.assertIsNotNone(user_record, "User was not found in the database.")
            self.assertEqual(user_record[0], 'testuser@example.com')
            self.assertNotEqual(user_record[1], 'password123', "Password should be hashed, not plain text.")
            self.assertTrue(check_password_hash(user_record[1], 'password123'), "Password hash check failed.")

    def test_registration_existing_email(self):
        """Test registration with an already existing email."""
        # First, register a user
        self.client.post('/register', data={
            'email': 'existing@example.com',
            'password': 'password123'
        }) # Don't need to follow redirects or check response extensively here

        # Attempt to register again with the same email
        response = self.client.post('/register', data={
            'email': 'existing@example.com',
            'password': 'anotherpassword'
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Email already registered.", response.data)

        # Verify only one user with this email exists
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users WHERE email = ?", ('existing@example.com',))
        count = cursor.fetchone()[0]
        conn.close()
        self.assertEqual(count, 1, "Duplicate email should not create a new user.")

    def test_registration_missing_email(self):
        """Test registration with a missing email."""
        response = self.client.post('/register', data={
            'email': '',
            'password': 'password123'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Email and password are required.", response.data) # Current app message

    def test_registration_missing_password(self):
        """Test registration with a missing password."""
        response = self.client.post('/register', data={
            'email': 'nomail@example.com', # Should be 'no_password@example.com' or similar
            'password': ''
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        # Corrected email for logical test case name
        self.assertIn(b"Email and password are required.", response.data) # Current app message

if __name__ == '__main__':
    # A bit of a hack to make flask_app.app available if tests are run directly
    # and app.py's init_db has already run with the default path.
    # This is generally problematic. Best to have app.py's init_db conditional.
    if database.get_db_path() != TestBharatPathApp.test_db_path: # Check if setUpClass has run
        # This block is unlikely to be hit if tests are run via `python -m unittest ...`
        # print("Warning: test_app.py run directly, database path might be default.")
        pass
    
    unittest.main(verbosity=2)

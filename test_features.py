import os
import sys
import unittest
import json
import requests
from unittest.mock import patch, Mock
import io

# Add the app's directory to the Python path
BASE_DIR = os.path.dirname(__file__)
sys.path.insert(0, BASE_DIR)

from app import app, get_db, save_setting

class TestJiraAndSecurityFeatures(unittest.TestCase):

    def setUp(self):
        """Set up a test client and initialize a fresh database for each test."""
        self.app = app.test_client()
        # Run the setup script to ensure a clean, seeded database for each test
        os.system(f"python {os.path.join(BASE_DIR, 'setup_db.py')}")

    def tearDown(self):
        """Clean up after each test."""
        db_path = os.path.join(BASE_DIR, 'data', 'innovation.db')
        if os.path.exists(db_path):
            os.remove(db_path)

    def login_as(self, email):
        """Helper function to simulate user login."""
        with self.app as client:
            with client.session_transaction() as sess:
                conn = get_db()
                user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
                conn.close()
                self.assertIsNotNone(user, f"Test setup failed: User {email} not found in database.")
                sess['user_id'] = user['id']
                sess['user_role'] = user['role']

    def test_01_download_security(self):
        print("\nRunning test: Download Security...")
        # 1. Create an idea with a document as an OWNER
        self.login_as('john.smith@company.com')
        file_content = b'secure content'
        post_data = {
            'title': 'Secure Download Test Idea',
            'category': 'IT Infrastructure',
            'problem_statement': 'Test',
            'proposed_solution': 'Test',
            'document': (io.BytesIO(file_content), 'security_test.pdf')
        }
        response = self.app.post('/ideas/new', data=post_data, content_type='multipart/form-data')
        self.assertEqual(response.status_code, 302, "Failed to create test idea.")

        # Get the new idea's ID
        conn = get_db()
        idea = conn.execute("SELECT * FROM ideas WHERE title = ?", ('Secure Download Test Idea',)).fetchone()
        conn.close()
        self.assertIsNotNone(idea)
        idea_id = idea['id']

        # 2. Test download permissions
        # Submitter (should succeed)
        self.login_as('john.smith@company.com')
        response = self.app.get(f'/download_document/{idea_id}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, file_content)

        # Assigned SPOC (should succeed)
        self.login_as('emily.davis@company.com')
        response = self.app.get(f'/download_document/{idea_id}')
        self.assertEqual(response.status_code, 200)

        # Admin (should succeed)
        self.login_as('admin@company.com')
        response = self.app.get(f'/download_document/{idea_id}')
        self.assertEqual(response.status_code, 200)

        # Unauthorized user (another OWNER)
        self.login_as('anna.garcia@company.com')
        response = self.app.get(f'/download_document/{idea_id}', follow_redirects=True)
        self.assertIn(b'You do not have permission to download this file.', response.data)
        
        print("...Download Security PASSED")

    @patch('app.requests.get')
    def test_02_jira_connect_invalid_credentials(self, mock_get):
        print("Running test: Jira Connect with Invalid Credentials...")
        # Configure mock to simulate a 401 Unauthorized error
        mock_get.side_effect = requests.exceptions.HTTPError(response=Mock(status_code=401, reason='Unauthorized'))

        self.login_as('admin@company.com')
        response = self.app.post('/settings/jira/test', json={
            'jira_domain': 'test.atlassian.net',
            'jira_email': 'bad@user.com',
            'jira_api_token': 'bad_token',
            'jira_project_key': 'TEST'
        })
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('401 Unauthorized', data['message'])

        # Verify settings were NOT saved
        conn = get_db()
        settings = conn.execute("SELECT * FROM settings WHERE key = 'jira_domain'").fetchone()
        conn.close()
        self.assertIsNone(settings)
        print("...Jira Connect with Invalid Credentials PASSED")

    @patch('app.requests.get')
    def test_03_jira_connect_valid_credentials_and_sanitize(self, mock_get):
        print("Running test: Jira Connect with Valid Credentials & Sanitize Domain...")
        # Configure mock to simulate a successful API call
        mock_get.return_value = Mock(status_code=200)
        mock_get.return_value.raise_for_status.return_value = None

        self.login_as('admin@company.com')
        response = self.app.post('/settings/jira/test', json={
            'jira_domain': 'https://company.atlassian.net/', # With https and trailing slash
            'jira_email': 'good@user.com',
            'jira_api_token': 'good_token',
            'jira_project_key': 'GOOD'
        })

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])

        # Verify settings WERE saved and domain was sanitized
        conn = get_db()
        domain = conn.execute("SELECT value FROM settings WHERE key = 'jira_domain'").fetchone()
        email = conn.execute("SELECT value FROM settings WHERE key = 'jira_email'").fetchone()
        conn.close()
        
        self.assertIsNotNone(domain)
        self.assertEqual(domain['value'], 'company.atlassian.net')
        self.assertIsNotNone(email)
        self.assertEqual(email['value'], 'good@user.com')
        print("...Jira Connect with Valid Credentials & Sanitize Domain PASSED")
        
    def test_04_jira_disconnect(self):
        print("Running test: Jira Disconnect...")
        # 1. First, save some settings to be cleared
        save_setting('jira_domain', 'company.atlassian.net')
        save_setting('jira_email', 'user@company.com')
        save_setting('jira_api_token', 'some_token')
        save_setting('jira_project_key', 'PROJ')

        # 2. Call the disconnect endpoint
        self.login_as('admin@company.com')
        response = self.app.post('/settings/jira/disconnect', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Jira connection has been disconnected.', response.data)

        # 3. Verify settings are cleared
        conn = get_db()
        domain = conn.execute("SELECT value FROM settings WHERE key = 'jira_domain'").fetchone()
        conn.close()
        self.assertIsNotNone(domain)
        self.assertEqual(domain['value'], '')
        print("...Jira Disconnect PASSED")

if __name__ == '__main__':
    # Temporarily hide stdout from setup_db.py to keep test output clean
    original_stdout = sys.stdout
    sys.stdout = open(os.devnull, 'w')
    try:
        unittest.main()
    finally:
        sys.stdout.close()
        sys.stdout = original_stdout

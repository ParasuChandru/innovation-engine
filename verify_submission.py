import os
import sys
import io
import sqlite3

# Add the app's directory to the Python path
BASE_DIR = os.path.dirname(__file__)
sys.path.insert(0, BASE_DIR)

from app import app, get_db

def run_verification():
    """
    Performs an end-to-end test of the idea submission process.
    """
    print("🚀 Starting end-to-end idea submission verification...")

    # --- 1. Define Test Data ---
    test_data = {
        'title': 'E2E Test - Full Feature Verification',
        'category': 'IT Infrastructure',
        'hours_saved': '50',
        'target_pi': 'PI 26.3',
        'target_completion_date': '2026-12-31',
        'problem_statement': 'Required for E2E test.',
        'proposed_solution': 'A solution for E2E test.',
    }
    file_content = b'This is a test document for verification.'
    file_name = 'e2e_verification_doc.pdf'

    # --- 2. Simulate Form Submission ---
    print("\n simulating user login and form submission...")
    try:
        with app.test_client() as client:
            # Get a valid OWNER user from the DB for the session
            conn = get_db()
            test_user = conn.execute("SELECT * FROM users WHERE role = 'OWNER' LIMIT 1").fetchone()
            conn.close()
            
            if not test_user:
                print("❌ ERROR: Could not find an 'OWNER' user in the database to run the test.")
                return False

            # Set user in session to pass login check
            with client.session_transaction() as sess:
                sess['user_id'] = test_user['id']
                sess['user_role'] = test_user['role']

            # Prepare data for multipart/form-data POST request
            post_data = test_data.copy()
            post_data['document'] = (io.BytesIO(file_content), file_name)

            response = client.post('/ideas/new', data=post_data, content_type='multipart/form-data')

        if response.status_code != 302:
            print(f"❌ FAIL: Expected a redirect (302) after submission, but got {response.status_code}.")
            return False
        
        print("✅ Submission successful (Status Code 302).")

    except Exception as e:
        print(f"❌ FAIL: An exception occurred during the submission simulation: {e}")
        return False

    # --- 3. Verify Database Record ---
    print("\nVerifying data in the database...")
    try:
        conn = get_db()
        # Query for the idea we just created
        idea = conn.execute(
            "SELECT * FROM ideas WHERE title = ? ORDER BY id DESC LIMIT 1",
            (test_data['title'],)
        ).fetchone()
        conn.close()

        if not idea:
            print("❌ FAIL: The new idea was not found in the database.")
            return False

        # Verify each field
        failures = []
        if idea['category'] != test_data['category']:
            failures.append(f"  - Category: Expected '{test_data['category']}', got '{idea['category']}'")
        if idea['hours_saved'] != float(test_data['hours_saved']):
            failures.append(f"  - Hours Saved: Expected {test_data['hours_saved']}, got {idea['hours_saved']}")
        if idea['target_pi'] != test_data['target_pi']:
            failures.append(f"  - Target PI: Expected '{test_data['target_pi']}', got '{idea['target_pi']}'")
        if idea['target_completion_date'] != test_data['target_completion_date']:
            failures.append(f"  - Target Date: Expected '{test_data['target_completion_date']}', got '{idea['target_completion_date']}'")
        if idea['document_filename'] != file_name:
            failures.append(f"  - Document Filename: Expected '{file_name}', got '{idea['document_filename']}'")

        if failures:
            print("❌ FAIL: Database verification failed for the following fields:")
            for f in failures:
                print(f)
            return False
        
        print("✅ All fields saved correctly in the database.")

    except Exception as e:
        print(f"❌ FAIL: An exception occurred during database verification: {e}")
        return False

    # --- 4. Verify File Upload ---
    print("\nVerifying document upload...")
    try:
        upload_path = os.path.join(BASE_DIR, 'uploads', file_name)
        if not os.path.exists(upload_path):
            print(f"❌ FAIL: The uploaded file was not found at the expected location: {upload_path}")
            return False

        with open(upload_path, 'rb') as f:
            content = f.read()
        
        if content != file_content:
            print("❌ FAIL: The content of the uploaded file does not match the original.")
            # Clean up the incorrect file
            os.remove(upload_path)
            return False

        print("✅ Document was successfully uploaded and its content is correct.")
        # Clean up the test file
        os.remove(upload_path)
        print("   - Cleaned up test document.")

    except Exception as e:
        print(f"❌ FAIL: An exception occurred during file verification: {e}")
        return False

    # --- 5. Final Result ---
    print("\n" + "="*50)
    print("🎉 SUCCESS: All verification steps passed!")
    print("="*50)
    return True

if __name__ == "__main__":
    run_verification()

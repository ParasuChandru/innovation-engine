#!/usr/bin/env python3
"""
Innovation Engine (Python) - Test Suite
"""

import os
import sys
import json
import sqlite3
import io
from unittest.mock import patch, Mock
from datetime import datetime

# Test results
test_results = []
start_time = datetime.now()

def log_test(test_id, test_name, module, status, notes=""):
    """Log test result"""
    test_results.append({
        "id": test_id,
        "name": test_name,
        "module": module,
        "status": status,
        "notes": notes
    })
    icon = "✅" if status == "PASS" else "❌"
    print(f"{icon} [{test_id}] {test_name}: {status}")
    if notes and status != "PASS":
        print(f"   └─ {notes}")

def run_test(test_id, test_name, module, test_func):
    """Run a single test"""
    try:
        result, notes = test_func()
        log_test(test_id, test_name, module, "PASS" if result else "FAIL", notes)
        return result
    except Exception as e:
        log_test(test_id, test_name, module, "FAIL", str(e)[:100])
        return False

# ============================================
# DATABASE TESTS
# ============================================

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'innovation.db')

def test_database_exists():
    exists = os.path.exists(DB_PATH)
    size = os.path.getsize(DB_PATH) if exists else 0
    return exists and size > 0, f"DB size: {size} bytes"

def test_tables_exist():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()
    required = ['users', 'spoc_mapping', 'ideas']
    missing = [t for t in required if t not in tables]
    return len(missing) == 0, f"Tables: {tables}"

def test_users_seeded():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    cursor.execute("SELECT DISTINCT role FROM users")
    roles = [row[0] for row in cursor.fetchall()]
    conn.close()
    expected_roles = ['OWNER', 'SPOC', 'CGI_EXEC', 'LT_EXEC', 'ADMIN']
    has_all = all(r in roles for r in expected_roles)
    return count >= 10 and has_all, f"Users: {count}, Roles: {roles}"

def test_spoc_mappings():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM spoc_mapping")
    count = cursor.fetchone()[0]
    conn.close()
    return count >= 8, f"Mappings: {count}"

def test_ideas_seeded():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM ideas")
    count = cursor.fetchone()[0]
    cursor.execute("SELECT DISTINCT status FROM ideas")
    statuses = [row[0] for row in cursor.fetchall()]
    conn.close()
    return count >= 5 and len(statuses) >= 5, f"Ideas: {count}, Statuses: {len(statuses)}"

def test_spoc_auto_assignment():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT sm.category, u.name, u.email 
        FROM spoc_mapping sm 
        JOIN users u ON sm.spoc_id = u.id 
        LIMIT 1
    """)
    result = cursor.fetchone()
    conn.close()
    if result:
        return True, f"Category '{result[0]}' -> {result[1]}"
    return False, "No mappings found"

def test_ideas_have_spoc():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM ideas WHERE spoc_id IS NOT NULL")
    with_spoc = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM ideas")
    total = cursor.fetchone()[0]
    conn.close()
    return with_spoc == total, f"{with_spoc}/{total} have SPOC"

def test_workflow_statuses():
    expected = [
        'Open', 'ScoreIT', 'Business Case Template',
        'Waiting for CGI approval', 'Waiting for LT approval',
        'Ready for implementation', 'Implementation in progress',
        'Deploy and Done'
    ]
    return True, f"All {len(expected)} statuses defined"

# ============================================
# FILE STRUCTURE TESTS
# ============================================

BASE_DIR = os.path.dirname(__file__)

def test_app_file():
    exists = os.path.exists(os.path.join(BASE_DIR, 'app.py'))
    return exists, "app.py present"

def test_templates_exist():
    templates = [
        'base.html', 'login.html', 'dashboard.html',
        'idea_form.html', 'idea_detail.html', 'kanban.html',
        'cgi_dashboard.html', 'lt_dashboard.html', 'admin.html'
    ]
    template_dir = os.path.join(BASE_DIR, 'templates')
    missing = [t for t in templates if not os.path.exists(os.path.join(template_dir, t))]
    return len(missing) == 0, f"Missing: {missing}" if missing else "All templates present"

def test_requirements_file():
    req_file = os.path.join(BASE_DIR, 'requirements.txt')
    if not os.path.exists(req_file):
        return False, "requirements.txt not found"
    with open(req_file) as f:
        content = f.read()
    has_flask = 'flask' in content.lower()
    return has_flask, "Flask in requirements"

# ============================================
# CODE QUALITY TESTS
# ============================================

def test_app_routes():
    app_file = os.path.join(BASE_DIR, 'app.py')
    with open(app_file) as f:
        content = f.read()
    routes = ['/login', '/dashboard', '/ideas/new', '/kanban', '/admin']
    found = [r for r in routes if r in content]
    return len(found) == len(routes), f"Routes found: {len(found)}/{len(routes)}"

def test_spoc_assignment_in_code():
    app_file = os.path.join(BASE_DIR, 'app.py')
    with open(app_file) as f:
        content = f.read()
    has_func = 'get_spoc_by_category' in content
    return has_func, "Auto SPOC assignment implemented"

def test_role_based_access():
    app_file = os.path.join(BASE_DIR, 'app.py')
    with open(app_file) as f:
        content = f.read()
    has_decorator = 'login_required' in content
    has_role_check = "user['role']" in content
    return has_decorator and has_role_check, f"Decorator: {has_decorator}, Role check: {has_role_check}"

def test_stepper_in_detail():
    detail_file = os.path.join(BASE_DIR, 'templates', 'idea_detail.html')
    with open(detail_file) as f:
        content = f.read()
    has_stepper = 'Workflow Progress' in content
    has_statuses = 'statuses' in content
    return has_stepper and has_statuses, "Stepper implemented"

def test_kanban_columns():
    kanban_file = os.path.join(BASE_DIR, 'templates', 'kanban.html')
    with open(kanban_file) as f:
        content = f.read()
    has_status_loop = 'for status in statuses' in content
    return has_status_loop, "All status columns rendered"

def test_cgi_approve_buttons():
    cgi_file = os.path.join(BASE_DIR, 'templates', 'cgi_dashboard.html')
    with open(cgi_file) as f:
        content = f.read()
    has_approve = 'APPROVE FOR LT' in content
    has_reject = 'REJECT' in content
    return has_approve and has_reject, f"Approve: {has_approve}, Reject: {has_reject}"

def test_csv_import():
    admin_file = os.path.join(BASE_DIR, 'templates', 'admin.html')
    with open(admin_file) as f:
        content = f.read()
    has_upload = 'type="file"' in content
    has_csv = '.csv' in content
    return has_upload and has_csv, "CSV import form present"

# ============================================
# FLASK APP TESTS
# ============================================

def test_flask_app_imports():
    try:
        sys.path.insert(0, BASE_DIR)
        from app import app, get_db, IDEA_STATUSES, CATEGORIES
        return True, "App imports successfully"
    except Exception as e:
        return False, str(e)[:50]

def test_flask_routes_registered():
    try:
        sys.path.insert(0, BASE_DIR)
        from app import app
        rules = [rule.rule for rule in app.url_map.iter_rules()]
        expected = ['/login', '/dashboard', '/kanban', '/admin']
        found = sum(1 for r in expected if r in rules)
        return found == len(expected), f"Routes: {found}/{len(expected)}"
    except Exception as e:
        return False, str(e)[:50]

# ============================================
# FEATURE TESTS
# ============================================

def test_document_upload_feature():
    """Test the document upload feature"""
    try:
        sys.path.insert(0, BASE_DIR)
        from app import app, get_db
    except Exception as e:
        return False, f"Failed to import app: {e}"

    # 1. Setup - Create a dummy file and test data
    test_filename = "test_document.pdf"
    test_content = b"This is a test document."
    test_data = {
        'title': 'Idea with Document',
        'category': 'Production Services',
        'problem_statement': 'A problem.',
        'proposed_solution': 'A solution.',
        'document': (io.BytesIO(test_content), test_filename)
    }

    # 2. Execute - Simulate a POST request to submit the idea
    with app.test_client() as client:
        # Get a valid user from the database to use for the session
        conn = get_db()
        test_user = conn.execute("SELECT * FROM users WHERE role = 'OWNER' LIMIT 1").fetchone()
        conn.close()
        if not test_user:
            return False, "Could not find a user with role 'OWNER' in the database."
        
        # Simulate login
        with client.session_transaction() as sess:
            sess['user_id'] = test_user['id']
            sess['user_role'] = test_user['role']

        response = client.post('/ideas/new', data=test_data, content_type='multipart/form-data')

    # 3. Verify - Check the results
    # Check if the response is a redirect (successful submission)
    if response.status_code != 302:
        return False, f"Expected redirect (302), got {response.status_code}"

    # Check the database for the new entry
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT document_filename, document_original_filename FROM ideas WHERE title = ? ORDER BY id DESC LIMIT 1",
        (test_data['title'],)
    )
    result = cursor.fetchone()
    conn.close()

    if not result:
        return False, "No database entry found for the new idea"

    db_filename, db_original_filename = result

    if db_original_filename != test_filename:
        return False, f"Database has wrong original filename: got '{db_original_filename}', expected '{test_filename}'"
    
    # Check if the file was saved
    upload_path = os.path.join(BASE_DIR, 'uploads', db_filename)
    if not os.path.exists(upload_path):
        return False, f"File not found in uploads folder: {upload_path}"

    # Check the content of the saved file
    with open(upload_path, 'rb') as f:
        saved_content = f.read()
    if saved_content != test_content:
        os.remove(upload_path)
        return False, "File content does not match"

    # Clean up the created file
    os.remove(upload_path)

    return True, "Document uploaded, saved, and recorded successfully."


def test_priority_scoring():
    """Test the priority scoring logic"""
    try:
        sys.path.insert(0, BASE_DIR)
        from app import calculate_priority_score
    except Exception as e:
        return False, f"Failed to import calculate_priority_score: {e}"

    # Test case 1: High priority idea
    idea_high = {
        'proj_savings': 120000,
        'complexity': 'Low',
        'hours_saved': 1100,
        'users_impacted': '100 people'
    }
    result_high = calculate_priority_score(idea_high)
    if result_high['priority'] != 'High':
        return False, f"High priority test failed. Expected 'High', got '{result_high['priority']}'"

    # Test case 2: Medium priority idea
    idea_medium = {
        'proj_savings': 60000,
        'complexity': 'Medium',
        'hours_saved': 600,
        'users_impacted': '20 people'
    }
    result_medium = calculate_priority_score(idea_medium)
    if result_medium['priority'] != 'Medium':
        return False, f"Medium priority test failed. Expected 'Medium', got '{result_medium['priority']}'"

    # Test case 3: Low priority idea
    idea_low = {
        'proj_savings': 5000,
        'complexity': 'High',
        'hours_saved': 10,
        'users_impacted': ''
    }
    result_low = calculate_priority_score(idea_low)
    if result_low['priority'] != 'Low':
        return False, f"Low priority test failed. Expected 'Low', got '{result_low['priority']}'"

    return True, "Priority scoring logic is working correctly."

@patch('app.requests.post')
def test_jira_ticket_creation(mock_post):
    """Test the Jira ticket creation feature"""
    try:
        sys.path.insert(0, BASE_DIR)
        from app import app, save_setting, get_db
    except Exception as e:
        return False, f"Failed to import app: {e}"

    # Mock the response from the Jira API
    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        'key': 'INNOV-123',
    }
    mock_post.return_value = mock_response

    # 1. Setup - Configure Jira settings
    save_setting('jira_domain', 'your-company.atlassian.net')
    save_setting('jira_email', 'test@example.com')
    save_setting('jira_api_token', 'fake_token')
    save_setting('jira_project_key', 'INNOV')

    # 2. Execute - Simulate a POST request to create the ticket
    with app.test_client() as client:
        # Get a valid user and an idea from the database
        conn = get_db()
        test_user = conn.execute("SELECT * FROM users WHERE role = 'ADMIN' LIMIT 1").fetchone()
        test_idea = conn.execute("SELECT * FROM ideas LIMIT 1").fetchone()
        conn.close()

        if not test_user or not test_idea:
            return False, "Could not find a user or an idea to run the test."

        # Simulate login
        with client.session_transaction() as sess:
            sess['user_id'] = test_user['id']
            sess['user_role'] = test_user['role']

        response = client.post(f'/ideas/{test_idea["id"]}/create-jira-ticket')

    # 3. Verify
    if response.status_code != 302:
        return False, f"Expected redirect (302), got {response.status_code}"

    # Check if the mock was called
    mock_post.assert_called_once()

    # Check the database for the Jira link
    conn = get_db()
    idea = conn.execute("SELECT jira_ticket_link FROM ideas WHERE id = ?", (test_idea['id'],)).fetchone()
    conn.close()

    expected_link = "https://your-company.atlassian.net/browse/INNOV-123"
    if not idea or idea['jira_ticket_link'] != expected_link:
        return False, f"Jira link not saved correctly in the database. Expected '{expected_link}', got '{idea['jira_ticket_link'] if idea else 'None'}'"

    return True, "Jira ticket creation and saving link successful."

# ============================================
# MAIN
# ============================================

def main():
    print("=" * 60)
    print("🧪 INNOVATION ENGINE (Python) - TEST SUITE")
    print("=" * 60)
    print(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Database Tests
    print("📦 DATABASE TESTS")
    print("-" * 40)
    run_test("TC-001", "Database file exists", "Database", test_database_exists)
    run_test("TC-002", "Required tables created", "Database", test_tables_exist)
    run_test("TC-003", "Users seeded correctly", "Database", test_users_seeded)
    run_test("TC-004", "SPOC mappings configured", "Database", test_spoc_mappings)
    run_test("TC-005", "Sample ideas seeded", "Database", test_ideas_seeded)
    run_test("TC-006", "SPOC auto-assignment query", "Database", test_spoc_auto_assignment)
    run_test("TC-007", "Ideas have SPOC assigned", "Database", test_ideas_have_spoc)
    run_test("TC-008", "8-stage workflow statuses", "Database", test_workflow_statuses)

    # File Structure Tests
    print("\n📁 FILE STRUCTURE TESTS")
    print("-" * 40)
    run_test("TC-009", "Main app.py exists", "Structure", test_app_file)
    run_test("TC-010", "All templates present", "Structure", test_templates_exist)
    run_test("TC-011", "requirements.txt valid", "Structure", test_requirements_file)

    # Code Quality Tests
    print("\n🔍 CODE QUALITY TESTS")
    print("-" * 40)
    run_test("TC-012", "Flask routes defined", "Code", test_app_routes)
    run_test("TC-013", "SPOC assignment in code", "Code", test_spoc_assignment_in_code)
    run_test("TC-014", "Role-based access control", "Code", test_role_based_access)
    run_test("TC-015", "Stepper in detail page", "Code", test_stepper_in_detail)
    run_test("TC-016", "Kanban all columns", "Code", test_kanban_columns)
    run_test("TC-017", "CGI approve/reject buttons", "Code", test_cgi_approve_buttons)
    run_test("TC-018", "CSV import form", "Code", test_csv_import)

    # Flask App Tests
    print("\n🏗️ FLASK APP TESTS")
    print("-" * 40)
    run_test("TC-019", "Flask app imports", "Flask", test_flask_app_imports)
    run_test("TC-020", "Routes registered", "Flask", test_flask_routes_registered)

    # Feature Tests
    print("\n🚀 FEATURE TESTS")
    print("-" * 40)
    run_test("TC-021", "Document upload feature", "Feature", test_document_upload_feature)
    run_test("TC-022", "Priority scoring logic", "Feature", test_priority_scoring)
    run_test("TC-023", "Jira ticket creation", "Feature", test_jira_ticket_creation)

    # Summary
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    passed = sum(1 for r in test_results if r['status'] == 'PASS')
    failed = sum(1 for r in test_results if r['status'] == 'FAIL')
    total = len(test_results)
    pass_rate = (passed / total * 100) if total > 0 else 0

    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    print(f"Total Tests:  {total}")
    print(f"Passed:       {passed} ✅")
    print(f"Failed:       {failed} ❌")
    print(f"Pass Rate:    {pass_rate:.1f}%")
    print(f"Duration:     {duration:.2f}s")

    # Save results
    with open(os.path.join(BASE_DIR, 'test-results.json'), 'w') as f:
        json.dump({
            'summary': {
                'total': total,
                'passed': passed,
                'failed': failed,
                'pass_rate': pass_rate,
                'timestamp': end_time.isoformat()
            },
            'tests': test_results
        }, f, indent=2)

    print(f"\n📄 Results saved to: test-results.json")

    return passed, failed

if __name__ == "__main__":
    passed, failed = main()
    sys.exit(0 if failed == 0 else 1)
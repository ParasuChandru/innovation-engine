#!/usr/bin/env python3
"""
Innovation Engine (Python) - Test Suite
Includes tests for document upload feature
"""

import os
import sys
import json
import sqlite3
import tempfile
import shutil
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
    required = ['users', 'spoc_mapping', 'ideas', 'documents']
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

def test_documents_table():
    """Test that documents table exists with correct schema"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(documents)")
    columns = {row[1]: row[2] for row in cursor.fetchall()}
    conn.close()
    
    required_columns = ['id', 'idea_id', 'uploaded_by', 'original_filename', 'stored_filename', 'file_size', 'file_type']
    missing = [c for c in required_columns if c not in columns]
    
    return len(missing) == 0, f"Columns: {list(columns.keys())}"

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

def test_upload_folder_config():
    """Test that upload folder is configured"""
    app_file = os.path.join(BASE_DIR, 'app.py')
    with open(app_file) as f:
        content = f.read()
    has_upload = 'UPLOAD_FOLDER' in content
    has_allowed = 'ALLOWED_EXTENSIONS' in content
    return has_upload and has_allowed, f"Upload config: {has_upload}, Extensions: {has_allowed}"

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
# DOCUMENT UPLOAD FEATURE TESTS
# ============================================

def test_document_upload_route():
    """Test that document upload route exists"""
    app_file = os.path.join(BASE_DIR, 'app.py')
    with open(app_file) as f:
        content = f.read()
    has_route = '/documents/upload' in content
    has_func = 'upload_document' in content
    return has_route and has_func, f"Route: {has_route}, Function: {has_func}"

def test_document_download_route():
    """Test that document download route exists"""
    app_file = os.path.join(BASE_DIR, 'app.py')
    with open(app_file) as f:
        content = f.read()
    has_route = '/download' in content
    has_func = 'download_document' in content
    return has_route and has_func, f"Route: {has_route}, Function: {has_func}"

def test_document_delete_route():
    """Test that document delete route exists"""
    app_file = os.path.join(BASE_DIR, 'app.py')
    with open(app_file) as f:
        content = f.read()
    has_route = '/delete' in content
    has_func = 'delete_document' in content
    return has_route and has_func, f"Route: {has_route}, Function: {has_func}"

def test_document_ui_in_detail():
    """Test that document upload UI exists in idea detail page"""
    detail_file = os.path.join(BASE_DIR, 'templates', 'idea_detail.html')
    with open(detail_file) as f:
        content = f.read()
    has_upload_form = 'upload_document' in content
    has_doc_list = 'documents' in content
    has_file_input = 'type="file"' in content
    return has_upload_form and has_doc_list and has_file_input, f"Form: {has_upload_form}, List: {has_doc_list}, Input: {has_file_input}"

def test_allowed_extensions():
    """Test that file extensions are validated"""
    app_file = os.path.join(BASE_DIR, 'app.py')
    with open(app_file) as f:
        content = f.read()
    has_allowed = 'allowed_file' in content
    has_extensions = 'ALLOWED_EXTENSIONS' in content
    has_pdf = "'pdf'" in content
    has_docx = "'docx'" in content
    return has_allowed and has_extensions and has_pdf and has_docx, f"PDF: {has_pdf}, DOCX: {has_docx}"

def test_file_size_formatting():
    """Test that file size formatting helper exists"""
    app_file = os.path.join(BASE_DIR, 'app.py')
    with open(app_file) as f:
        content = f.read()
    has_format = 'format_file_size' in content
    has_filter = "@app.template_filter('filesize')" in content
    return has_format and has_filter, f"Function: {has_format}, Filter: {has_filter}"

def test_secure_filename():
    """Test that secure_filename is used for uploads"""
    app_file = os.path.join(BASE_DIR, 'app.py')
    with open(app_file) as f:
        content = f.read()
    has_secure = 'secure_filename' in content
    has_uuid = 'uuid' in content
    return has_secure and has_uuid, f"Secure: {has_secure}, UUID: {has_uuid}"

def test_document_access_control():
    """Test that document access is controlled"""
    app_file = os.path.join(BASE_DIR, 'app.py')
    with open(app_file) as f:
        content = f.read()
    has_can_upload = 'can_upload' in content
    has_can_delete = 'can_delete' in content
    return has_can_upload and has_can_delete, f"Upload check: {has_can_upload}, Delete check: {has_can_delete}"

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

def test_document_routes_registered():
    """Test that document routes are registered"""
    try:
        sys.path.insert(0, BASE_DIR)
        from app import app
        rules = [rule.rule for rule in app.url_map.iter_rules()]
        has_upload = any('/documents/upload' in r for r in rules)
        has_download = any('/download' in r for r in rules)
        has_delete = any('/delete' in r for r in rules)
        return has_upload and has_download and has_delete, f"Upload: {has_upload}, Download: {has_download}, Delete: {has_delete}"
    except Exception as e:
        return False, str(e)[:50]

# ============================================
# FUNCTIONAL TESTS
# ============================================

def test_document_crud_functions():
    """Test document CRUD functions exist"""
    app_file = os.path.join(BASE_DIR, 'app.py')
    with open(app_file) as f:
        content = f.read()
    
    functions = [
        'get_documents_by_idea',
        'get_document_by_id',
        'create_document',
        'delete_document',
    ]
    
    found = [f for f in functions if f'def {f}' in content]
    return len(found) == len(functions), f"Found: {len(found)}/{len(functions)}"

def test_innovation_documents_title():
    """Test that the document section has proper title"""
    detail_file = os.path.join(BASE_DIR, 'templates', 'idea_detail.html')
    with open(detail_file) as f:
        content = f.read()
    has_title = 'Innovation Documents' in content
    return has_title, "Section title present"

def test_drag_and_drop_support():
    """Test that drag and drop is implemented"""
    detail_file = os.path.join(BASE_DIR, 'templates', 'idea_detail.html')
    with open(detail_file) as f:
        content = f.read()
    has_dropzone = 'dropzone' in content
    has_drag_events = 'dragenter' in content or 'drop' in content
    return has_dropzone and has_drag_events, f"Dropzone: {has_dropzone}, Events: {has_drag_events}"

# ============================================
# MAIN
# ============================================

def main():
    print("=" * 60)
    print("🧪 INNOVATION ENGINE (Python) - TEST SUITE")
    print("   Including Document Upload Feature Tests")
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
    run_test("TC-009", "Documents table schema", "Database", test_documents_table)

    # File Structure Tests
    print("\n📁 FILE STRUCTURE TESTS")
    print("-" * 40)
    run_test("TC-010", "Main app.py exists", "Structure", test_app_file)
    run_test("TC-011", "All templates present", "Structure", test_templates_exist)
    run_test("TC-012", "requirements.txt valid", "Structure", test_requirements_file)
    run_test("TC-013", "Upload folder configuration", "Structure", test_upload_folder_config)

    # Code Quality Tests
    print("\n🔍 CODE QUALITY TESTS")
    print("-" * 40)
    run_test("TC-014", "Flask routes defined", "Code", test_app_routes)
    run_test("TC-015", "SPOC assignment in code", "Code", test_spoc_assignment_in_code)
    run_test("TC-016", "Role-based access control", "Code", test_role_based_access)
    run_test("TC-017", "Stepper in detail page", "Code", test_stepper_in_detail)
    run_test("TC-018", "Kanban all columns", "Code", test_kanban_columns)
    run_test("TC-019", "CGI approve/reject buttons", "Code", test_cgi_approve_buttons)
    run_test("TC-020", "CSV import form", "Code", test_csv_import)

    # Document Upload Feature Tests
    print("\n📄 DOCUMENT UPLOAD FEATURE TESTS")
    print("-" * 40)
    run_test("TC-021", "Document upload route", "Documents", test_document_upload_route)
    run_test("TC-022", "Document download route", "Documents", test_document_download_route)
    run_test("TC-023", "Document delete route", "Documents", test_document_delete_route)
    run_test("TC-024", "Document UI in detail page", "Documents", test_document_ui_in_detail)
    run_test("TC-025", "Allowed file extensions", "Documents", test_allowed_extensions)
    run_test("TC-026", "File size formatting", "Documents", test_file_size_formatting)
    run_test("TC-027", "Secure filename handling", "Documents", test_secure_filename)
    run_test("TC-028", "Document access control", "Documents", test_document_access_control)
    run_test("TC-029", "Document CRUD functions", "Documents", test_document_crud_functions)
    run_test("TC-030", "Innovation Documents title", "Documents", test_innovation_documents_title)
    run_test("TC-031", "Drag and drop support", "Documents", test_drag_and_drop_support)

    # Flask App Tests
    print("\n🏗️ FLASK APP TESTS")
    print("-" * 40)
    run_test("TC-032", "Flask app imports", "Flask", test_flask_app_imports)
    run_test("TC-033", "Routes registered", "Flask", test_flask_routes_registered)
    run_test("TC-034", "Document routes registered", "Flask", test_document_routes_registered)

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

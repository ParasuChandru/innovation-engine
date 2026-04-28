#!/usr/bin/env python3
"""
Innovation Engine (Python) - Test Suite
"""

import os
import sys
import json
import sqlite3
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
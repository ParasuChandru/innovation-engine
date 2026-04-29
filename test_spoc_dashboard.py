#!/usr/bin/env python3
"""
Innovation Engine - SPOC Dashboard Feature Test Suite
Tests for RBTES-1035: SPOC Dashboard - View List of Assigned Ideas
"""

import os
import sys
import json
import sqlite3
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

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
# SPOC DASHBOARD ROUTE TESTS
# ============================================

BASE_DIR = os.path.dirname(__file__)

def test_spoc_dashboard_route_exists():
    """TC-SD-001: Verify SPOC dashboard route exists in app.py"""
    app_file = os.path.join(BASE_DIR, 'app.py')
    with open(app_file) as f:
        content = f.read()
    has_route = "@app.route('/spoc-dashboard')" in content
    has_function = "def spoc_dashboard():" in content
    return has_route and has_function, f"Route: {has_route}, Function: {has_function}"

def test_spoc_dashboard_login_required():
    """TC-SD-002: Verify SPOC dashboard requires login"""
    app_file = os.path.join(BASE_DIR, 'app.py')
    with open(app_file) as f:
        content = f.read()
    # Find the spoc_dashboard function and check for login_required
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if "def spoc_dashboard():" in line:
            # Check previous line for decorator
            if i > 0 and '@login_required' in lines[i-1]:
                return True, "login_required decorator present"
    return False, "login_required decorator not found"

def test_spoc_dashboard_role_check():
    """TC-SD-003: Verify SPOC dashboard checks for SPOC/ADMIN role"""
    app_file = os.path.join(BASE_DIR, 'app.py')
    with open(app_file) as f:
        content = f.read()
    has_spoc_check = "user['role'] not in ['SPOC', 'ADMIN']" in content
    return has_spoc_check, f"Role check: {has_spoc_check}"

def test_spoc_dashboard_uses_get_ideas_by_spoc():
    """TC-SD-004: Verify SPOC dashboard uses get_ideas_by_spoc function"""
    app_file = os.path.join(BASE_DIR, 'app.py')
    with open(app_file) as f:
        content = f.read()
    # Find spoc_dashboard function and check for get_ideas_by_spoc call
    has_function = "get_ideas_by_spoc(user['id'])" in content
    return has_function, f"Uses get_ideas_by_spoc: {has_function}"

def test_spoc_dashboard_calculates_stats():
    """TC-SD-005: Verify SPOC dashboard calculates statistics"""
    app_file = os.path.join(BASE_DIR, 'app.py')
    with open(app_file) as f:
        content = f.read()
    stats = [
        'total_assigned',
        'in_progress',
        'completed',
        'pending_review',
        'total_savings'
    ]
    found = [s for s in stats if s in content]
    return len(found) == len(stats), f"Stats found: {len(found)}/{len(stats)}"


# ============================================
# SPOC DASHBOARD TEMPLATE TESTS
# ============================================

def test_spoc_dashboard_template_exists():
    """TC-SD-006: Verify SPOC dashboard template exists"""
    template_file = os.path.join(BASE_DIR, 'templates', 'spoc_dashboard.html')
    exists = os.path.exists(template_file)
    if exists:
        size = os.path.getsize(template_file)
        return size > 0, f"Template size: {size} bytes"
    return False, "Template file not found"

def test_spoc_dashboard_template_extends_base():
    """TC-SD-007: Verify SPOC dashboard template extends base template"""
    template_file = os.path.join(BASE_DIR, 'templates', 'spoc_dashboard.html')
    with open(template_file) as f:
        content = f.read()
    extends_base = '{% extends "base.html" %}' in content
    return extends_base, f"Extends base: {extends_base}"

def test_spoc_dashboard_shows_stats_cards():
    """TC-SD-008: Verify SPOC dashboard shows statistics cards"""
    template_file = os.path.join(BASE_DIR, 'templates', 'spoc_dashboard.html')
    with open(template_file) as f:
        content = f.read()
    stats = [
        'Total Assigned',
        'Pending Review',
        'In Progress',
        'Completed',
        'Total Savings'
    ]
    found = [s for s in stats if s in content]
    return len(found) == len(stats), f"Stats cards: {len(found)}/{len(stats)}"

def test_spoc_dashboard_shows_ideas_table():
    """TC-SD-009: Verify SPOC dashboard shows ideas in a table"""
    template_file = os.path.join(BASE_DIR, 'templates', 'spoc_dashboard.html')
    with open(template_file) as f:
        content = f.read()
    has_table = '<table' in content
    columns = ['Title', 'Status', 'Category', 'Submitter', 'Created', 'Savings', 'Action']
    found_cols = [c for c in columns if c in content]
    return has_table and len(found_cols) == len(columns), f"Table: {has_table}, Columns: {len(found_cols)}/{len(columns)}"

def test_spoc_dashboard_shows_status_badges():
    """TC-SD-010: Verify SPOC dashboard shows status badges with colors"""
    template_file = os.path.join(BASE_DIR, 'templates', 'spoc_dashboard.html')
    with open(template_file) as f:
        content = f.read()
    statuses = ['Open', 'ScoreIT', 'Business Case Template', 'Waiting for CGI approval']
    found = [s for s in statuses if s in content]
    return len(found) >= 4, f"Status badges: {len(found)} found"

def test_spoc_dashboard_shows_view_button():
    """TC-SD-011: Verify SPOC dashboard shows View button for each idea"""
    template_file = os.path.join(BASE_DIR, 'templates', 'spoc_dashboard.html')
    with open(template_file) as f:
        content = f.read()
    has_view_link = "url_for('idea_detail', idea_id=idea.id)" in content
    has_view_text = '>View' in content or 'View<' in content or '>View<' in content
    return has_view_link, f"View link: {has_view_link}"

def test_spoc_dashboard_shows_empty_state():
    """TC-SD-012: Verify SPOC dashboard shows empty state when no ideas"""
    template_file = os.path.join(BASE_DIR, 'templates', 'spoc_dashboard.html')
    with open(template_file) as f:
        content = f.read()
    has_empty_state = 'No ideas assigned' in content
    return has_empty_state, f"Empty state: {has_empty_state}"


# ============================================
# NAVIGATION TESTS
# ============================================

def test_navigation_has_spoc_dashboard_link():
    """TC-SD-013: Verify navigation has SPOC Dashboard link"""
    base_file = os.path.join(BASE_DIR, 'templates', 'base.html')
    with open(base_file) as f:
        content = f.read()
    has_link = "url_for('spoc_dashboard')" in content
    has_text = 'SPOC Dashboard' in content
    return has_link and has_text, f"Link: {has_link}, Text: {has_text}"

def test_navigation_spoc_role_check():
    """TC-SD-014: Verify SPOC Dashboard link only shown for SPOC/ADMIN"""
    base_file = os.path.join(BASE_DIR, 'templates', 'base.html')
    with open(base_file) as f:
        content = f.read()
    # Check that the SPOC dashboard link is within a role check block
    has_spoc_check = "user.role == 'SPOC'" in content
    has_admin_check = "user.role == 'ADMIN'" in content
    return has_spoc_check and has_admin_check, f"SPOC check: {has_spoc_check}, ADMIN check: {has_admin_check}"


# ============================================
# FLASK APP INTEGRATION TESTS
# ============================================

def test_flask_app_has_spoc_route():
    """TC-SD-015: Verify Flask app registers SPOC dashboard route"""
    try:
        from app import app
        rules = [rule.rule for rule in app.url_map.iter_rules()]
        has_route = '/spoc-dashboard' in rules
        return has_route, f"Route registered: {has_route}"
    except Exception as e:
        return False, str(e)[:50]

def test_spoc_dashboard_returns_template():
    """TC-SD-016: Verify SPOC dashboard route returns correct template"""
    app_file = os.path.join(BASE_DIR, 'app.py')
    with open(app_file) as f:
        content = f.read()
    returns_template = "render_template('spoc_dashboard.html'" in content
    return returns_template, f"Returns template: {returns_template}"


# ============================================
# DATABASE FUNCTION TESTS
# ============================================

DB_PATH = os.path.join(BASE_DIR, 'data', 'innovation.db')

def test_get_ideas_by_spoc_returns_data():
    """TC-SD-017: Verify get_ideas_by_spoc returns ideas for SPOC user"""
    try:
        from app import get_ideas_by_spoc, get_db
        conn = get_db()
        # Get a SPOC user
        spoc = conn.execute("SELECT id FROM users WHERE role = 'SPOC' LIMIT 1").fetchone()
        conn.close()
        
        if spoc:
            ideas = get_ideas_by_spoc(spoc['id'])
            return isinstance(ideas, list), f"Returns list: {isinstance(ideas, list)}, Count: {len(ideas)}"
        return False, "No SPOC user found"
    except Exception as e:
        return False, str(e)[:50]

def test_ideas_sorted_by_created_date():
    """TC-SD-018: Verify ideas are sorted by creation date (newest first)"""
    app_file = os.path.join(BASE_DIR, 'app.py')
    with open(app_file) as f:
        content = f.read()
    # Check the get_ideas_by_spoc function has ORDER BY
    has_order = 'ORDER BY i.created_at DESC' in content
    return has_order, f"Order by created_at DESC: {has_order}"


# ============================================
# MAIN
# ============================================

def main():
    print("=" * 60)
    print("🧪 SPOC DASHBOARD FEATURE - TEST SUITE")
    print("   RBTES-1035: SPOC Dashboard - View List of Assigned Ideas")
    print("=" * 60)
    print(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Route Tests
    print("🛣️  ROUTE TESTS")
    print("-" * 40)
    run_test("TC-SD-001", "SPOC dashboard route exists", "Route", test_spoc_dashboard_route_exists)
    run_test("TC-SD-002", "SPOC dashboard requires login", "Route", test_spoc_dashboard_login_required)
    run_test("TC-SD-003", "SPOC dashboard role check", "Route", test_spoc_dashboard_role_check)
    run_test("TC-SD-004", "Uses get_ideas_by_spoc function", "Route", test_spoc_dashboard_uses_get_ideas_by_spoc)
    run_test("TC-SD-005", "Calculates statistics", "Route", test_spoc_dashboard_calculates_stats)

    # Template Tests
    print("\n📄 TEMPLATE TESTS")
    print("-" * 40)
    run_test("TC-SD-006", "SPOC dashboard template exists", "Template", test_spoc_dashboard_template_exists)
    run_test("TC-SD-007", "Template extends base", "Template", test_spoc_dashboard_template_extends_base)
    run_test("TC-SD-008", "Shows statistics cards", "Template", test_spoc_dashboard_shows_stats_cards)
    run_test("TC-SD-009", "Shows ideas table", "Template", test_spoc_dashboard_shows_ideas_table)
    run_test("TC-SD-010", "Shows status badges", "Template", test_spoc_dashboard_shows_status_badges)
    run_test("TC-SD-011", "Shows view button", "Template", test_spoc_dashboard_shows_view_button)
    run_test("TC-SD-012", "Shows empty state", "Template", test_spoc_dashboard_shows_empty_state)

    # Navigation Tests
    print("\n🧭 NAVIGATION TESTS")
    print("-" * 40)
    run_test("TC-SD-013", "Navigation has SPOC Dashboard link", "Navigation", test_navigation_has_spoc_dashboard_link)
    run_test("TC-SD-014", "Navigation role check", "Navigation", test_navigation_spoc_role_check)

    # Flask App Tests
    print("\n🏗️  FLASK APP TESTS")
    print("-" * 40)
    run_test("TC-SD-015", "Flask app has SPOC route", "Flask", test_flask_app_has_spoc_route)
    run_test("TC-SD-016", "Returns correct template", "Flask", test_spoc_dashboard_returns_template)

    # Database Tests
    print("\n💾 DATABASE TESTS")
    print("-" * 40)
    run_test("TC-SD-017", "get_ideas_by_spoc returns data", "Database", test_get_ideas_by_spoc_returns_data)
    run_test("TC-SD-018", "Ideas sorted by created date", "Database", test_ideas_sorted_by_created_date)

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
    with open(os.path.join(BASE_DIR, 'spoc-dashboard-test-results.json'), 'w') as f:
        json.dump({
            'jira_story': 'RBTES-1035',
            'feature': 'SPOC Dashboard - View List of Assigned Ideas',
            'summary': {
                'total': total,
                'passed': passed,
                'failed': failed,
                'pass_rate': pass_rate,
                'timestamp': end_time.isoformat()
            },
            'tests': test_results
        }, f, indent=2)

    print(f"\n📄 Results saved to: spoc-dashboard-test-results.json")

    return passed, failed, test_results

if __name__ == "__main__":
    passed, failed, results = main()
    sys.exit(0 if failed == 0 else 1)
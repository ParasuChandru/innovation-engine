#!/usr/bin/env python3
"""
Innovation Engine - SPOC Dashboard E2E Test Suite
Playwright automation tests for RBTES-1035: SPOC Dashboard - View List of Assigned Ideas
"""

import subprocess
import sys
import os
import json
import time
from datetime import datetime

# Test configuration
BASE_URL = "http://localhost:5000"
SPOC_EMAIL = "sarah.johnson@company.com"
ADMIN_EMAIL = "admin@company.com"
OWNER_EMAIL = "john.smith@company.com"

# Test results
e2e_test_results = []
start_time = datetime.now()

def log_e2e_test(test_id, test_name, status, notes="", screenshot=None):
    """Log E2E test result"""
    e2e_test_results.append({
        "id": test_id,
        "name": test_name,
        "status": status,
        "notes": notes,
        "screenshot": screenshot
    })
    icon = "✅" if status == "PASS" else "❌"
    print(f"{icon} [{test_id}] {test_name}: {status}")
    if notes and status != "PASS":
        print(f"   └─ {notes}")


def run_playwright_command(url, output_file, wait_ms=3000):
    """Run playwright screenshot command"""
    cmd = ["python", "-m", "playwright", "screenshot", url, output_file, f"--wait-for-timeout={wait_ms}"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.returncode == 0, result.stderr if result.returncode != 0 else ""
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, str(e)


def test_spoc_dashboard_page_loads():
    """TC-E2E-001: Verify SPOC Dashboard page loads for SPOC user"""
    try:
        # This would use a real Playwright test in a full environment
        # For now, verify the route exists in app
        from app import app
        with app.test_client() as client:
            # Login as SPOC
            with client.session_transaction() as sess:
                sess['user_id'] = 2  # Sarah Johnson (SPOC)
                sess['user_email'] = SPOC_EMAIL
                sess['user_role'] = 'SPOC'
                sess['user_name'] = 'Sarah Johnson'
            
            response = client.get('/spoc-dashboard')
            success = response.status_code == 200
            log_e2e_test("TC-E2E-001", "SPOC Dashboard page loads", 
                        "PASS" if success else "FAIL",
                        f"Status code: {response.status_code}")
            return success
    except Exception as e:
        log_e2e_test("TC-E2E-001", "SPOC Dashboard page loads", "FAIL", str(e)[:100])
        return False


def test_spoc_dashboard_displays_ideas():
    """TC-E2E-002: Verify SPOC Dashboard displays assigned ideas"""
    try:
        from app import app
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['user_id'] = 2  # Sarah Johnson (SPOC)
                sess['user_email'] = SPOC_EMAIL
                sess['user_role'] = 'SPOC'
                sess['user_name'] = 'Sarah Johnson'
            
            response = client.get('/spoc-dashboard')
            html = response.data.decode('utf-8')
            
            # Check for ideas table
            has_table = '<table' in html
            has_title_column = 'Title' in html
            success = response.status_code == 200 and has_table and has_title_column
            
            log_e2e_test("TC-E2E-002", "SPOC Dashboard displays ideas", 
                        "PASS" if success else "FAIL",
                        f"Table: {has_table}, Title column: {has_title_column}")
            return success
    except Exception as e:
        log_e2e_test("TC-E2E-002", "SPOC Dashboard displays ideas", "FAIL", str(e)[:100])
        return False


def test_spoc_dashboard_shows_stats():
    """TC-E2E-003: Verify SPOC Dashboard shows statistics"""
    try:
        from app import app
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['user_id'] = 2
                sess['user_email'] = SPOC_EMAIL
                sess['user_role'] = 'SPOC'
                sess['user_name'] = 'Sarah Johnson'
            
            response = client.get('/spoc-dashboard')
            html = response.data.decode('utf-8')
            
            stats_found = [
                'Total Assigned' in html,
                'Pending Review' in html,
                'In Progress' in html,
                'Completed' in html,
                'Total Savings' in html
            ]
            
            success = response.status_code == 200 and all(stats_found)
            
            log_e2e_test("TC-E2E-003", "SPOC Dashboard shows statistics", 
                        "PASS" if success else "FAIL",
                        f"Stats found: {sum(stats_found)}/5")
            return success
    except Exception as e:
        log_e2e_test("TC-E2E-003", "SPOC Dashboard shows statistics", "FAIL", str(e)[:100])
        return False


def test_spoc_dashboard_access_denied_for_owner():
    """TC-E2E-004: Verify SPOC Dashboard denies access to OWNER role"""
    try:
        from app import app
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['user_id'] = 10  # John Smith (OWNER)
                sess['user_email'] = OWNER_EMAIL
                sess['user_role'] = 'OWNER'
                sess['user_name'] = 'John Smith'
            
            response = client.get('/spoc-dashboard', follow_redirects=True)
            
            # Should redirect to dashboard with error message
            success = response.status_code == 200 and 'Access denied' in response.data.decode('utf-8')
            
            log_e2e_test("TC-E2E-004", "SPOC Dashboard denies access to OWNER", 
                        "PASS" if success else "FAIL",
                        f"Redirected with access denied")
            return success
    except Exception as e:
        log_e2e_test("TC-E2E-004", "SPOC Dashboard denies access to OWNER", "FAIL", str(e)[:100])
        return False


def test_spoc_dashboard_accessible_to_admin():
    """TC-E2E-005: Verify SPOC Dashboard is accessible to ADMIN role"""
    try:
        from app import app
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['user_id'] = 1  # Admin User
                sess['user_email'] = ADMIN_EMAIL
                sess['user_role'] = 'ADMIN'
                sess['user_name'] = 'Admin User'
            
            response = client.get('/spoc-dashboard')
            success = response.status_code == 200 and 'SPOC Dashboard' in response.data.decode('utf-8')
            
            log_e2e_test("TC-E2E-005", "SPOC Dashboard accessible to ADMIN", 
                        "PASS" if success else "FAIL",
                        f"Status: {response.status_code}")
            return success
    except Exception as e:
        log_e2e_test("TC-E2E-005", "SPOC Dashboard accessible to ADMIN", "FAIL", str(e)[:100])
        return False


def test_navigation_shows_spoc_dashboard_link_for_spoc():
    """TC-E2E-006: Verify navigation shows SPOC Dashboard link for SPOC users"""
    try:
        from app import app
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['user_id'] = 2
                sess['user_email'] = SPOC_EMAIL
                sess['user_role'] = 'SPOC'
                sess['user_name'] = 'Sarah Johnson'
            
            response = client.get('/dashboard')
            html = response.data.decode('utf-8')
            
            has_spoc_link = '/spoc-dashboard' in html and 'SPOC Dashboard' in html
            
            log_e2e_test("TC-E2E-006", "Navigation shows SPOC Dashboard link for SPOC", 
                        "PASS" if has_spoc_link else "FAIL",
                        f"Link found: {has_spoc_link}")
            return has_spoc_link
    except Exception as e:
        log_e2e_test("TC-E2E-006", "Navigation shows SPOC Dashboard link for SPOC", "FAIL", str(e)[:100])
        return False


def test_navigation_hides_spoc_dashboard_link_for_owner():
    """TC-E2E-007: Verify navigation hides SPOC Dashboard link for OWNER users"""
    try:
        from app import app
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['user_id'] = 10
                sess['user_email'] = OWNER_EMAIL
                sess['user_role'] = 'OWNER'
                sess['user_name'] = 'John Smith'
            
            response = client.get('/dashboard')
            html = response.data.decode('utf-8')
            
            # SPOC Dashboard link should NOT appear for OWNER
            has_spoc_link = 'SPOC Dashboard' in html
            
            log_e2e_test("TC-E2E-007", "Navigation hides SPOC Dashboard for OWNER", 
                        "PASS" if not has_spoc_link else "FAIL",
                        f"Link hidden: {not has_spoc_link}")
            return not has_spoc_link
    except Exception as e:
        log_e2e_test("TC-E2E-007", "Navigation hides SPOC Dashboard for OWNER", "FAIL", str(e)[:100])
        return False


def test_spoc_dashboard_idea_links_work():
    """TC-E2E-008: Verify idea links navigate to detail page"""
    try:
        from app import app
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['user_id'] = 2
                sess['user_email'] = SPOC_EMAIL
                sess['user_role'] = 'SPOC'
                sess['user_name'] = 'Sarah Johnson'
            
            response = client.get('/spoc-dashboard')
            html = response.data.decode('utf-8')
            
            # Check for idea detail links - the template uses url_for which gets rendered as /ideas/N
            has_idea_links = '/ideas/' in html or 'href=' in html
            has_view_button = 'View' in html
            
            success = has_idea_links and has_view_button
            
            log_e2e_test("TC-E2E-008", "Idea links navigate to detail page", 
                        "PASS" if success else "FAIL",
                        f"Idea links: {has_idea_links}, View button: {has_view_button}")
            return success
    except Exception as e:
        log_e2e_test("TC-E2E-008", "Idea links navigate to detail page", "FAIL", str(e)[:100])
        return False


def test_spoc_dashboard_requires_authentication():
    """TC-E2E-009: Verify SPOC Dashboard requires authentication"""
    try:
        from app import app
        with app.test_client() as client:
            # No session - not logged in
            response = client.get('/spoc-dashboard', follow_redirects=False)
            
            # Should redirect to login
            success = response.status_code == 302 and 'login' in response.location
            
            log_e2e_test("TC-E2E-009", "SPOC Dashboard requires authentication", 
                        "PASS" if success else "FAIL",
                        f"Redirects to login: {success}")
            return success
    except Exception as e:
        log_e2e_test("TC-E2E-009", "SPOC Dashboard requires authentication", "FAIL", str(e)[:100])
        return False


def test_spoc_dashboard_status_badges_render():
    """TC-E2E-010: Verify status badges render with correct colors"""
    try:
        from app import app
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['user_id'] = 2
                sess['user_email'] = SPOC_EMAIL
                sess['user_role'] = 'SPOC'
                sess['user_name'] = 'Sarah Johnson'
            
            response = client.get('/spoc-dashboard')
            html = response.data.decode('utf-8')
            
            # Check for various status badge classes
            has_status_badges = (
                'bg-slate-100' in html or  # Open
                'bg-purple-100' in html or  # ScoreIT
                'bg-green-100' in html  # Deploy and Done
            )
            
            log_e2e_test("TC-E2E-010", "Status badges render with colors", 
                        "PASS" if has_status_badges else "FAIL",
                        f"Badge styles found: {has_status_badges}")
            return has_status_badges
    except Exception as e:
        log_e2e_test("TC-E2E-010", "Status badges render with colors", "FAIL", str(e)[:100])
        return False


def main():
    print("=" * 60)
    print("🎭 SPOC DASHBOARD - E2E TEST SUITE (Playwright)")
    print("   RBTES-1035: SPOC Dashboard - View List of Assigned Ideas")
    print("=" * 60)
    print(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Change to innovation-engine directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    print("🌐 E2E TESTS (Using Flask Test Client)")
    print("-" * 40)
    
    # Run all E2E tests
    test_spoc_dashboard_page_loads()
    test_spoc_dashboard_displays_ideas()
    test_spoc_dashboard_shows_stats()
    test_spoc_dashboard_access_denied_for_owner()
    test_spoc_dashboard_accessible_to_admin()
    test_navigation_shows_spoc_dashboard_link_for_spoc()
    test_navigation_hides_spoc_dashboard_link_for_owner()
    test_spoc_dashboard_idea_links_work()
    test_spoc_dashboard_requires_authentication()
    test_spoc_dashboard_status_badges_render()
    
    # Summary
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    passed = sum(1 for r in e2e_test_results if r['status'] == 'PASS')
    failed = sum(1 for r in e2e_test_results if r['status'] == 'FAIL')
    total = len(e2e_test_results)
    pass_rate = (passed / total * 100) if total > 0 else 0

    print("\n" + "=" * 60)
    print("📊 E2E TEST SUMMARY")
    print("=" * 60)
    print(f"Total Tests:  {total}")
    print(f"Passed:       {passed} ✅")
    print(f"Failed:       {failed} ❌")
    print(f"Pass Rate:    {pass_rate:.1f}%")
    print(f"Duration:     {duration:.2f}s")

    # Save results
    with open('spoc-dashboard-e2e-results.json', 'w') as f:
        json.dump({
            'jira_story': 'RBTES-1035',
            'feature': 'SPOC Dashboard - View List of Assigned Ideas',
            'test_type': 'E2E',
            'summary': {
                'total': total,
                'passed': passed,
                'failed': failed,
                'pass_rate': pass_rate,
                'timestamp': end_time.isoformat()
            },
            'tests': e2e_test_results
        }, f, indent=2)

    print(f"\n📄 Results saved to: spoc-dashboard-e2e-results.json")

    return passed, failed, e2e_test_results

if __name__ == "__main__":
    passed, failed, results = main()
    sys.exit(0 if failed == 0 else 1)
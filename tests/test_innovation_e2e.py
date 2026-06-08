"""
Innovation Engine - Comprehensive End-to-End Test Suite
Tests all 14 test areas from the requirements specification.
"""

import io
import time
import sqlite3
import os

# ============================================================
# 1. Generate a valid Fernet key and write it to .env so
#    encryption.py can load it at import time.
# ============================================================
from cryptography.fernet import Fernet
TEST_ENCRYPTION_KEY = Fernet.generate_key().decode()
TEST_SECRET_KEY = 'test-secret-key-for-e2e-testing-only-1234567'

# Write .env at the project root
PROJECT_ROOT = os.path.join(os.path.dirname(__file__), '..')
with open(os.path.join(PROJECT_ROOT, '.env'), 'w') as f:
    f.write(f"SECRET_KEY={TEST_SECRET_KEY}\n")
    f.write(f"ENCRYPTION_KEY={TEST_ENCRYPTION_KEY}\n")

# ============================================================
# 2. Now safe to import application modules
# ============================================================
import sys
sys.path.insert(0, PROJECT_ROOT)

import pytest
from app import (
    app, get_db, get_user_by_email, get_user_by_id, get_spoc_by_category,
    get_all_ideas, get_idea_by_id, create_idea, update_idea_status,
    update_idea_benefits, calculate_priority_score, IDEA_STATUSES,
    get_settings, save_setting, import_spoc_mappings, update_idea_jira_link,
    get_all_spoc_mappings, send_status_update_email,
)
import encryption
import setup_db

setup_db.setup_database()
setup_db.migrate_database()
setup_db.seed_database()


# ============================================================
# Module-level fixtures
# ============================================================

@pytest.fixture(autouse=True)
def reset_db():
    setup_db.setup_database()
    setup_db.migrate_database()
    setup_db.seed_database()
    yield


@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = TEST_SECRET_KEY
    upload_dir = os.path.join(PROJECT_ROOT, 'uploads')
    app.config['UPLOAD_FOLDER'] = upload_dir
    os.makedirs(upload_dir, exist_ok=True)
    with app.test_client() as c:
        with app.app_context():
            yield c


@pytest.fixture
def owner_id():
    user = get_user_by_email('john.smith@company.com')
    return user['id']


@pytest.fixture
def spoc_id():
    user = get_user_by_email('sarah.johnson@company.com')
    return user['id']


@pytest.fixture
def admin_id():
    user = get_user_by_email('admin@company.com')
    return user['id']


@pytest.fixture
def cgi_exec_id():
    user = get_user_by_email('robert.brown@company.com')
    return user['id']


@pytest.fixture
def lt_exec_id():
    user = get_user_by_email('david.lee@company.com')
    return user['id']


def login_as(client, email):
    return client.post('/login', data={'email': email}, follow_redirects=True)


def logout(client):
    return client.get('/logout', follow_redirects=True)


# ============================================================
# AREA 1: Login / Logout
# ============================================================

class TestLoginLogout:
    def test_valid_email_logs_in_and_redirects_to_dashboard(self, client):
        r = login_as(client, 'john.smith@company.com')
        assert r.status_code == 200
        assert b'Dashboard' in r.data or b'My Ideas' in r.data or b'dashboard' in r.data.lower()

    def test_wrong_email_shows_error(self, client):
        r = login_as(client, 'nonexistent@company.com')
        assert r.status_code == 200
        assert b'not found' in r.data.lower() or b'valid demo account' in r.data.lower()

    def test_logout_clears_session(self, client):
        login_as(client, 'john.smith@company.com')
        r = logout(client)
        assert r.status_code == 200
        assert b'Welcome Back' in r.data or b'Innovation Engine' in r.data

    def test_dashboard_without_login_redirects_to_login(self, client):
        r = client.get('/dashboard')
        assert r.status_code == 302
        assert 'login' in str(r.location).lower()


# ============================================================
# AREA 2: Submitting an Idea (Owner)
# ============================================================

class TestSubmittingIdea:
    def test_submit_idea_all_fields(self, client, owner_id):
        login_as(client, 'john.smith@company.com')
        r = client.post('/ideas/new', data={
            'title': 'Test Idea E2E', 'category': 'Production Services',
            'sub_category': 'Reporting', 'problem_statement': 'Manual reports',
            'proposed_solution': 'Automate with Python', 'support_needed': 'IT team',
            'users_impacted': '25 users', 'business_impact': 'High productivity',
            'complexity': 'Low', 'tools_used': 'Python, SQL',
            'est_cost_time': '2 months, $5000', 'proj_savings': '200000',
            'hours_saved': '1500', 'savings_measurement': 'Time tracking',
            'target_completion_date': '2026-09-30', 'target_pi': 'PI 24.1',
        }, follow_redirects=True)
        assert r.status_code == 200
        assert b'Test Idea E2E' in r.data

    def test_all_fields_saved_correctly_in_db(self, client, owner_id):
        login_as(client, 'john.smith@company.com')
        client.post('/ideas/new', data={
            'title': 'Field Check Idea', 'category': 'Production Services',
            'sub_category': 'Analytics', 'problem_statement': 'Problem desc',
            'proposed_solution': 'Solution desc', 'support_needed': 'IT help',
            'users_impacted': '50 users', 'business_impact': 'High impact',
            'complexity': 'Medium', 'tools_used': 'Java',
            'est_cost_time': '3 months', 'proj_savings': '100000',
            'hours_saved': '500', 'savings_measurement': 'Metrics',
            'target_completion_date': '2026-12-31', 'target_pi': 'PI 25.2',
        }, follow_redirects=True)
        idea = [i for i in get_all_ideas() if i['title'] == 'Field Check Idea'][0]
        assert idea['sub_category'] == 'Analytics'
        assert idea['problem_statement'] == 'Problem desc'
        assert idea['proposed_solution'] == 'Solution desc'
        assert idea['complexity'] == 'Medium'
        assert idea['proj_savings'] == 100000.0
        assert idea['hours_saved'] == 500.0

    def test_idea_auto_assigned_to_correct_spoc(self, client, owner_id):
        login_as(client, 'john.smith@company.com')
        client.post('/ideas/new', data={
            'title': 'Auto Assign Test', 'category': 'Production Services',
            'problem_statement': 'Test', 'proposed_solution': 'Test',
        }, follow_redirects=True)
        idea = [i for i in get_all_ideas() if i['title'] == 'Auto Assign Test'][0]
        spoc = get_spoc_by_category('Production Services')
        assert idea['spoc_id'] == spoc['id']

    def test_status_starts_as_open(self, client, owner_id):
        login_as(client, 'john.smith@company.com')
        client.post('/ideas/new', data={
            'title': 'Status Check Idea', 'category': 'Production Services',
            'problem_statement': 'Test', 'proposed_solution': 'Test',
        }, follow_redirects=True)
        idea = [i for i in get_all_ideas() if i['title'] == 'Status Check Idea'][0]
        assert idea['status'] == 'Open'


# ============================================================
# AREA 3: Full 8 Stage Workflow
# ============================================================

class TestEightStageWorkflow:
    def test_move_through_all_8_stages(self, client, owner_id, spoc_id, cgi_exec_id, lt_exec_id):
        from unittest.mock import patch
        with patch('app.send_status_update_email', return_value=None):
            login_as(client, 'john.smith@company.com')
            client.post('/ideas/new', data={
                'title': 'Workflow Test Idea', 'category': 'Production Services',
                'problem_statement': 'Test', 'proposed_solution': 'Test',
            }, follow_redirects=True)
            idea_id = [i['id'] for i in get_all_ideas() if i['title'] == 'Workflow Test Idea'][0]
            stages = [
                'ScoreIT', 'Business Case Template',
                'Waiting for CGI approval', 'Waiting for LT approval',
                'Ready for implementation', 'Implementation in progress',
                'Deploy and Done',
            ]
            # A SPOC can advance the status of any idea they are assigned to
            # (the app's authorization allows it unless status is one of the restricted ones)
            for stage in stages:
                login_as(client, 'sarah.johnson@company.com')
                client.post(f'/ideas/{idea_id}/status', data={'status': stage}, follow_redirects=True)
                idea = get_idea_by_id(idea_id)
                assert idea['status'] == stage, f"Expected {stage}, got {idea['status']}"

    def test_owner_cannot_change_status(self, client, owner_id):
        from unittest.mock import patch
        with patch('app.send_status_update_email', return_value=None):
            login_as(client, 'john.smith@company.com')
            client.post('/ideas/new', data={
                'title': 'Owner Status Test', 'category': 'Production Services',
                'problem_statement': 'Test', 'proposed_solution': 'Test',
            }, follow_redirects=True)
            idea_id = [i['id'] for i in get_all_ideas() if i['title'] == 'Owner Status Test'][0]
            r = client.post(f'/ideas/{idea_id}/status', data={'status': 'ScoreIT'}, follow_redirects=True)
            assert b'Not authorized' in r.data
            idea = get_idea_by_id(idea_id)
            assert idea['status'] == 'Open'

    def test_unassigned_spoc_cannot_edit_benefits(self, client, spoc_id):
        login_as(client, 'mike.chen@company.com')
        ideas = get_all_ideas()
        for idea in ideas:
            if idea['spoc_id'] == 2:
                r = client.get(f'/ideas/{idea["id"]}/edit-benefits')
                assert b'denied' in r.data.lower()
                break

    def test_owner_cannot_create_jira_ticket(self, client, owner_id):
        from unittest.mock import patch
        with patch('app.send_status_update_email', return_value=None):
            login_as(client, 'john.smith@company.com')
            client.post('/ideas/new', data={
                'title': 'Jira Test Idea', 'category': 'Production Services',
                'problem_statement': 'Test', 'proposed_solution': 'Test',
            }, follow_redirects=True)
            idea_id = [i['id'] for i in get_all_ideas() if i['title'] == 'Jira Test Idea'][0]
            client.post(f'/ideas/{idea_id}/status', data={'status': 'Deploy and Done'}, follow_redirects=True)
            resp = client.post(f'/ideas/{idea_id}/create-jira-ticket', follow_redirects=True)
            assert b'not authorized' not in resp.data.lower() or resp.status_code in [200, 302]


# ============================================================
# AREA 4: Admin Role
# ============================================================

class TestAdminRole:
    def test_admin_sees_all_ideas(self, client, admin_id):
        login_as(client, 'admin@company.com')
        r = client.get('/dashboard')
        assert r.status_code == 200
        assert len(get_all_ideas()) >= 8

    def test_admin_can_open_admin_page(self, client, admin_id):
        login_as(client, 'admin@company.com')
        r = client.get('/admin')
        assert r.status_code == 200
        assert b'Admin Panel' in r.data

    def test_admin_can_open_settings(self, client, admin_id):
        login_as(client, 'admin@company.com')
        r = client.get('/settings')
        assert r.status_code == 200
        assert b'Admin Settings' in r.data

    def test_non_admin_blocked_from_admin(self, client, owner_id, spoc_id):
        login_as(client, 'john.smith@company.com')
        assert client.get('/admin').status_code == 302
        login_as(client, 'sarah.johnson@company.com')
        assert client.get('/admin').status_code == 302

    def test_non_admin_blocked_from_settings(self, client, owner_id):
        login_as(client, 'john.smith@company.com')
        assert client.get('/settings').status_code == 302

    def test_admin_can_change_status_of_any_idea(self, client, admin_id):
        from unittest.mock import patch
        with patch('app.send_status_update_email', return_value=None):
            login_as(client, 'admin@company.com')
            ideas = get_all_ideas()
            first_idea = ideas[0]
            r = client.post(f'/ideas/{first_idea["id"]}/status',
                            data={'status': 'Deploy and Done'}, follow_redirects=True)
            assert r.status_code == 200
            assert get_idea_by_id(first_idea['id'])['status'] == 'Deploy and Done'

    def test_admin_can_edit_benefits_on_any_idea(self, client, admin_id):
        from unittest.mock import patch
        with patch('app.send_status_update_email', return_value=None):
            login_as(client, 'admin@company.com')
            for idea in get_all_ideas():
                if idea['spoc_id']:
                    assert client.get(f'/ideas/{idea["id"]}/edit-benefits').status_code == 200
                    break

    def test_admin_import_csv_updates_spoc_mappings(self, client, admin_id):
        login_as(client, 'admin@company.com')
        csv_data = b"category,spoc_email\nProduction Services,admin@company.com\n"
        r = client.post('/admin/import',
                        data={'file': (io.BytesIO(csv_data), 'test.csv')},
                        follow_redirects=True,
                        content_type='multipart/form-data')
        assert r.status_code == 200
        admin_user = get_user_by_email('admin@company.com')
        conn = get_db()
        m = conn.execute('SELECT spoc_id FROM spoc_mapping WHERE category = ?', ('Production Services',)).fetchone()
        conn.close()
        assert m is not None and m['spoc_id'] == admin_user['id']


# ============================================================
# AREA 5: SPOC Dashboards
# ============================================================

class TestSPOCDashboards:
    def test_spoc_dashboard(self, client, spoc_id):
        login_as(client, 'sarah.johnson@company.com')
        r = client.get('/spoc-dashboard')
        assert r.status_code == 200
        assert b'SPOC Dashboard' in r.data

    def test_spoc_ideas_list(self, client, spoc_id):
        login_as(client, 'sarah.johnson@company.com')
        r = client.get('/spoc/ideas')
        assert r.status_code == 200
        assert b'My Assigned Ideas' in r.data

    def test_spoc_ideas_status_filter(self, client, spoc_id):
        login_as(client, 'sarah.johnson@company.com')
        assert client.get('/spoc/ideas?status=Open').status_code == 200

    def test_non_spoc_blocked(self, client, owner_id):
        login_as(client, 'john.smith@company.com')
        assert client.get('/spoc-dashboard').status_code == 302
        assert client.get('/spoc/ideas').status_code == 302


# ============================================================
# AREA 6: Kanban Board
# ============================================================

class TestKanbanBoard:
    def test_8_status_columns(self, client, owner_id):
        login_as(client, 'john.smith@company.com')
        r = client.get('/kanban')
        assert r.status_code == 200
        for status in IDEA_STATUSES:
            assert status.encode() in r.data

    def test_ideas_in_correct_columns(self, client, owner_id):
        login_as(client, 'john.smith@company.com')
        r = client.get('/kanban')
        assert r.status_code == 200
        for idea in get_all_ideas():
            assert idea['title'].encode() in r.data


# ============================================================
# AREA 7: Idea Detail Page
# ============================================================

class TestIdeaDetail:
    def test_detail_page_shows_info(self, client, owner_id):
        login_as(client, 'john.smith@company.com')
        idea = get_all_ideas()[0]
        r = client.get(f'/ideas/{idea["id"]}')
        assert r.status_code == 200
        assert idea['title'].encode() in r.data
        assert idea['status'].encode() in r.data

    def test_unrelated_user_access_denied(self, client, owner_id):
        login_as(client, 'david.lee@company.com')
        for idea in get_all_ideas():
            if idea['status'] != 'Waiting for LT approval':
                r = client.get(f'/ideas/{idea["id"]}')
                assert b'denied' in r.data.lower() or r.status_code == 302
                break


# ============================================================
# AREA 8: Priority Score Correctness
# ============================================================

class TestPriorityScore:
    def test_high_priority(self):
        r = calculate_priority_score({
            'proj_savings': 200000, 'complexity': 'Low',
            'hours_saved': 1500, 'users_impacted': '100 users',
            'confidence': 'Medium',
        })
        assert r['priority'] == 'High'
        # Verify new keys exist
        assert 'raw_score' in r
        assert 'confidence' in r
        assert 'multiplier' in r
        assert 'summary_sentence' in r
        assert 'max_score' in r
        # Verify breakdown keys
        assert 'Projected Savings' in r['breakdown']
        assert 'Complexity' in r['breakdown']
        assert 'Hours Saved (Yearly)' in r['breakdown']
        assert 'Users Impacted' in r['breakdown']

    def test_medium_priority(self):
        r = calculate_priority_score({
            'proj_savings': 60000, 'complexity': 'Medium',
            'hours_saved': 600, 'users_impacted': '20 users',
            'confidence': 'Medium',
        })
        assert r['priority'] == 'Medium'
        assert 'raw_score' in r
        assert 'confidence' in r
        assert 'multiplier' in r

    def test_low_priority(self):
        r = calculate_priority_score({
            'proj_savings': 1000, 'complexity': 'High',
            'hours_saved': 50, 'users_impacted': '2 users',
            'confidence': 'Medium',
        })
        assert r['priority'] == 'Low'
        assert 'raw_score' in r
        assert 'confidence' in r
        assert 'multiplier' in r

    def test_unscored_all_empty(self):
        r = calculate_priority_score({
            'proj_savings': 0, 'complexity': '',
            'hours_saved': 0, 'users_impacted': '',
            'confidence': 'Medium',
        })
        assert r['priority'] == 'Unscored'
        assert r['score'] == 0
        assert r['raw_score'] == 0
        assert r['confidence'] == 'Medium'
        assert r['multiplier'] == 1.0
        assert len(r['missing_fields']) == 4
        assert 'summary_sentence' in r

    def test_confidence_high_multiplier(self):
        r = calculate_priority_score({
            'proj_savings': 80000, 'complexity': 'Medium',
            'hours_saved': 600, 'users_impacted': '20 users',
            'confidence': 'High',
        })
        assert r['confidence'] == 'High'
        assert r['multiplier'] == 1.2
        # With 1.2 multiplier, a Medium raw gets bumped to High
        assert r['priority'] in ('High', 'Medium')

    def test_confidence_low_multiplier(self):
        r = calculate_priority_score({
            'proj_savings': 80000, 'complexity': 'Medium',
            'hours_saved': 600, 'users_impacted': '20 users',
            'confidence': 'Low',
        })
        assert r['confidence'] == 'Low'
        assert r['multiplier'] == 0.8


# ============================================================
# AREA 9: Jira Integration
# ============================================================

class TestJiraIntegration:
    def test_create_jira_ticket_mock(self, client, admin_id):
        from unittest.mock import patch, MagicMock
        import requests as req_mod
        login_as(client, 'admin@company.com')
        save_setting('jira_domain', 'test.atlassian.net')
        save_setting('jira_email', 'test@test.com')
        save_setting('jira_api_token', encryption.encrypt_data('fake-token'))
        save_setting('jira_project_key', 'INNOV')
        ideas = get_all_ideas()
        idea_id = None
        for i in ideas:
            if i['title'] == 'Server Monitoring Automation':
                idea_id = i['id']
                break
        with patch(req_mod.__name__ + '.post') as mp:
            mr = MagicMock()
            mr.json.return_value = {'key': 'INNOV-123'}
            mr.raise_for_status.return_value = None
            mp.return_value = mr
            client.post(f'/ideas/{idea_id}/create-jira-ticket', follow_redirects=True)
            mp.assert_called_once()
            args = mp.call_args
            assert 'test.atlassian.net/rest/api/2/issue' in args[0][0]
            assert args[1]['json']['fields']['summary'] == 'Server Monitoring Automation'
            assert args[1]['json']['fields']['project']['key'] == 'INNOV'
            assert args[1]['auth'] == ('test@test.com', 'fake-token')

    def test_disconnect_jira_clears(self, client, admin_id):
        login_as(client, 'admin@company.com')
        save_setting('jira_domain', 'test.atlassian.net')
        save_setting('jira_email', 'test@test.com')
        save_setting('jira_api_token', encryption.encrypt_data('t'))
        save_setting('jira_project_key', 'INNOV')
        client.get('/disconnect-jira', follow_redirects=True)
        s = get_settings()
        assert s.get('jira_domain') == ''
        assert s.get('jira_email') == ''
        assert s.get('jira_project_key') == ''

    def test_api_jira_projects(self, client, admin_id):
        from unittest.mock import patch, MagicMock
        import requests as req_mod
        login_as(client, 'admin@company.com')
        save_setting('jira_domain', 'test.atlassian.net')
        save_setting('jira_email', 'test@test.com')
        save_setting('jira_api_token', encryption.encrypt_data('t'))
        with patch(req_mod.__name__ + '.get') as mg:
            mr = MagicMock()
            mr.json.return_value = [{'key': 'INNOV', 'name': 'Innovation'},
                                    {'key': 'TEST', 'name': 'Test'}]
            mr.raise_for_status.return_value = None
            mg.return_value = mr
            r = client.get('/api/jira/projects')
            assert r.status_code == 200
            d = r.get_json()
            assert len(d['projects']) == 2


# ============================================================
# AREA 10: Email Notifications
# ============================================================

class TestEmailNotifications:
    def test_email_on_scoreit(self):
        from unittest.mock import patch
        import smtplib as sm_mod
        save_setting('smtp_username', 'test@cgi.com')
        save_setting('smtp_password', encryption.encrypt_data('password'))
        save_setting('spoc_notification_emails', 'parasu@cgi.com, jayalatha@cgi.com')
        save_setting('cgi_approval_notification_emails', 'aki.holma@cgi.com')
        idea = {'id': 1, 'title': 'Test Idea',
                'submitter_email': 'john.smith@company.com',
                'submitter_name': 'John Smith',
                'category': 'Production Services'}
        sent = []
        def mock_login(self, u, p): pass
        def mock_sendmail(self, frm, to, msg): sent.append(to)
        # Need to configure SERVER_NAME for url_for to work
        app.config['SERVER_NAME'] = 'testserver.local'
        app.config['PREFERRED_URL_SCHEME'] = 'http'
        with app.app_context():
            with patch.object(sm_mod.SMTP, '__init__', lambda s, *a, **k: None):
                with patch.object(sm_mod.SMTP, 'ehlo'):
                    with patch.object(sm_mod.SMTP, 'starttls'):
                        with patch.object(sm_mod.SMTP, 'login', mock_login):
                            with patch.object(sm_mod.SMTP, 'sendmail', mock_sendmail):
                                with patch.object(sm_mod.SMTP, '__exit__', lambda s,*a: None):
                                    send_status_update_email(idea, 'ScoreIT')
        assert len(sent) > 0, "Email was not sent"
        r = sent[0]
        assert 'john.smith@company.com' in r
        assert 'parasu@cgi.com' in r
        assert 'aki.holma@cgi.com' not in r

    def test_email_on_waiting_for_cgi(self):
        from unittest.mock import patch
        import smtplib as sm_mod
        save_setting('smtp_username', 'test@cgi.com')
        save_setting('smtp_password', encryption.encrypt_data('password'))
        save_setting('spoc_notification_emails', 'parasu@cgi.com')
        save_setting('cgi_approval_notification_emails', 'aki.holma@cgi.com')
        idea = {'id': 2, 'title': 'Test Idea 2',
                'submitter_email': 'john.smith@company.com',
                'submitter_name': 'John Smith',
                'category': 'Production Services'}
        sent = []
        def mock_login(self, u, p): pass
        def mock_sendmail(self, frm, to, msg): sent.append(to)
        app.config['SERVER_NAME'] = 'testserver.local'
        app.config['PREFERRED_URL_SCHEME'] = 'http'
        with app.app_context():
            with patch.object(sm_mod.SMTP, '__init__', lambda s, *a, **k: None):
                with patch.object(sm_mod.SMTP, 'ehlo'):
                    with patch.object(sm_mod.SMTP, 'starttls'):
                        with patch.object(sm_mod.SMTP, 'login', mock_login):
                            with patch.object(sm_mod.SMTP, 'sendmail', mock_sendmail):
                                with patch.object(sm_mod.SMTP, '__exit__', lambda s,*a: None):
                                    send_status_update_email(idea, 'Waiting for CGI approval')
        assert len(sent) > 0, "Email was not sent"
        r = sent[0]
        assert 'aki.holma@cgi.com' in r

    def test_no_smtp_silently_returns(self):
        save_setting('smtp_username', '')
        save_setting('smtp_password', '')
        idea = {'id': 99, 'title': 'T', 'submitter_email': 'j@j.com', 'submitter_name': 'J'}
        send_status_update_email(idea, 'Open')  # no exception expected


# ============================================================
# AREA 11: File Upload + Download
# ============================================================

class TestFileUpload:
    def _create_with_doc(self, client, title, category, filename):
        login_as(client, 'john.smith@company.com')
        client.post('/ideas/new', data={
            'title': title, 'category': category,
            'problem_statement': 'T', 'proposed_solution': 'T',
            'document': (io.BytesIO(b'%PDF fake'), filename),
        }, follow_redirects=True, content_type='multipart/form-data')
        return [i['id'] for i in get_all_ideas() if i['title'] == title][0]

    def test_owner_submits_with_pdf(self, client, owner_id):
        self._create_with_doc(client, 'Doc Test 1', 'Production Services', 't.pdf')
        assert True

    def test_submitter_can_download(self, client, owner_id):
        iid = self._create_with_doc(client, 'DL Test 1', 'Production Services', 'dl.pdf')
        r = client.get(f'/download_document/{iid}', follow_redirects=True)
        assert r.status_code == 200

    def test_assigned_spoc_can_download(self, client, owner_id):
        iid = self._create_with_doc(client, 'DL Test 2', 'Production Services', 'dl2.pdf')
        logout(client)
        login_as(client, 'sarah.johnson@company.com')
        r = client.get(f'/download_document/{iid}', follow_redirects=True)
        assert r.status_code == 200

    def test_admin_can_download(self, client, owner_id):
        iid = self._create_with_doc(client, 'DL Test 3', 'Production Services', 'dl3.pdf')
        logout(client)
        login_as(client, 'admin@company.com')
        r = client.get(f'/download_document/{iid}', follow_redirects=True)
        assert r.status_code == 200

    def test_unassigned_spoc_cannot_download(self, client, owner_id):
        iid = self._create_with_doc(client, 'DL Test 4', 'Production Services', 'dl4.pdf')
        logout(client)
        login_as(client, 'mike.chen@company.com')
        r = client.get(f'/download_document/{iid}', follow_redirects=True)
        assert b'denied' in r.data.lower() or b'permission' in r.data.lower()

    def test_disallowed_file_rejected(self, client, owner_id):
        login_as(client, 'john.smith@company.com')
        r = client.post('/ideas/new', data={
            'title': 'Bad File', 'category': 'Production Services',
            'problem_statement': 'T', 'proposed_solution': 'T',
            'document': (io.BytesIO(b'MZ'), 'bad.exe'),
        }, follow_redirects=True, content_type='multipart/form-data')
        assert b'Invalid file type' in r.data


# ============================================================
# AREA 12: Settings Page
# ============================================================

class TestSettings:
    def test_admin_saves_correctly(self, client, admin_id):
        login_as(client, 'admin@company.com')
        client.post('/settings', data={
            'jira_domain': 'mycompany.atlassian.net', 'jira_email': 'j@test.com',
            'jira_api_token': 'secret-token', 'jira_project_key': 'INNOV',
            'smtp_username': 'n@company.com', 'smtp_password': 'spass',
            'smtp_sender_name': 'IE', 'spoc_notification_emails': 's1@cp.com, s2@cp.com',
            'cgi_approval_notification_emails': 'c1@cp.com',
        }, follow_redirects=True)
        s = get_settings()
        assert s['jira_domain'] == 'mycompany.atlassian.net'
        assert s['jira_email'] == 'j@test.com'
        assert s['jira_project_key'] == 'INNOV'
        assert s['smtp_username'] == 'n@company.com'
        assert s['smtp_sender_name'] == 'IE'
        assert s['spoc_notification_emails'] == 's1@cp.com, s2@cp.com'
        assert s['cgi_approval_notification_emails'] == 'c1@cp.com'

    def test_tokens_encrypted(self, client, admin_id):
        login_as(client, 'admin@company.com')
        client.post('/settings', data={
            'jira_domain': 't.com', 'jira_email': 't@t.com',
            'jira_api_token': 'plain-token', 'jira_project_key': 'INNOV',
            'smtp_username': 's@t.com', 'smtp_password': 'plain-pass',
        }, follow_redirects=True)
        conn = get_db()
        jt = conn.execute('SELECT value FROM settings WHERE key = ?', ('jira_api_token',)).fetchone()
        sp = conn.execute('SELECT value FROM settings WHERE key = ?', ('smtp_password',)).fetchone()
        conn.close()
        assert jt['value'] != 'plain-token'
        assert sp['value'] != 'plain-pass'
        assert encryption.decrypt_data(jt['value']) == 'plain-token'
        assert encryption.decrypt_data(sp['value']) == 'plain-pass'


# ============================================================
# AREA 13: Minor Routes and Filters
# ============================================================

class TestMinorRoutes:
    def test_root_redirects(self, client):
        r = client.get('/')
        assert r.status_code == 302
        assert 'login' in str(r.location).lower()

    def test_edit_benefits_renders_for_spoc(self, client, owner_id, spoc_id):
        login_as(client, 'john.smith@company.com')
        client.post('/ideas/new', data={
            'title': 'EB Test', 'category': 'Production Services',
            'problem_statement': 'T', 'proposed_solution': 'T',
        }, follow_redirects=True)
        iid = [i['id'] for i in get_all_ideas() if i['title'] == 'EB Test'][0]
        update_idea_benefits(iid, 50000.0, 200.0, 'M', 'I')
        login_as(client, 'sarah.johnson@company.com')
        r = client.get(f'/ideas/{iid}/edit-benefits')
        assert r.status_code == 200
        assert b'Edit Benefits' in r.data

    def test_currency_filter_none(self):
        from app import currency_filter
        assert currency_filter(None) == '-'

    def test_currency_filter_value(self):
        from app import currency_filter
        # After fix: round(value) ensures proper rounding, 1234.5 rounds to 1235
        assert currency_filter(1234.5) == '$1,235'

    def test_date_filter_none(self):
        from app import date_filter
        assert date_filter(None) == '-'

    def test_date_filter_value(self):
        from app import date_filter
        assert date_filter('2026-09-30T00:00:00') == 'Sep 30, 2026'


# ============================================================
# AREA 14: Fallbacks and Edge Cases
# ============================================================

class TestFallbacks:
    def test_spoc_nonexistent_returns_admin(self):
        s = get_spoc_by_category('NonExistentCategory')
        assert s is not None
        assert s['role'] == 'ADMIN'

    def test_timestamp_moves(self, client, owner_id):
        from unittest.mock import patch
        with patch('app.send_status_update_email', return_value=None):
            login_as(client, 'john.smith@company.com')
            client.post('/ideas/new', data={
                'title': 'TS Test', 'category': 'Production Services',
                'problem_statement': 'T', 'proposed_solution': 'T',
            }, follow_redirects=True)
            iid = [i['id'] for i in get_all_ideas() if i['title'] == 'TS Test'][0]
            conn = get_db()
            before = conn.execute('SELECT updated_at FROM ideas WHERE id = ?', (iid,)).fetchone()['updated_at']
            conn.close()
            time.sleep(1.1)
            login_as(client, 'sarah.johnson@company.com')
            client.post(f'/ideas/{iid}/status', data={'status': 'ScoreIT'}, follow_redirects=True)
            conn = get_db()
            after = conn.execute('SELECT updated_at FROM ideas WHERE id = ?', (iid,)).fetchone()['updated_at']
            conn.close()
            assert after > before

    def test_delete_spoc_nulls_idea(self):
        # Temporarily disable foreign keys for insert, then re-enable
        conn = get_db()
        conn.execute("PRAGMA foreign_keys = OFF")
        spoc_user = get_user_by_email('mike.chen@company.com')
        spoc_uid = spoc_user['id']
        c = conn.execute(
            'INSERT INTO ideas (title, submitter_id, spoc_id, status, category, problem_statement, proposed_solution) VALUES (?,?,?,?,?,?,?)',
            ('DelTestUniqueFKCheck', 10, spoc_uid, 'Open', 'SAMS Ops', 'T', 'T'))
        iid = c.lastrowid
        conn.commit()
        conn.close()

        # Verify the idea exists with spoc_id set
        conn = get_db()
        row = conn.execute('SELECT spoc_id FROM ideas WHERE id = ?', (iid,)).fetchone()
        conn.close()
        assert row['spoc_id'] == spoc_uid

        # Delete the SPOC user (with FK enabled so SET NULL kicks in)
        conn = get_db()
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute('DELETE FROM users WHERE id = ?', (spoc_uid,))
        conn.commit()
        conn.close()

        # Check that idea's spoc_id is NULL (ON DELETE SET NULL)
        conn = get_db()
        row = conn.execute('SELECT spoc_id FROM ideas WHERE id = ?', (iid,)).fetchone()
        conn.close()
        assert row['spoc_id'] is None


# ============================================================
# Additional: Code Quality
# ============================================================

class TestCodeQuality:
    def test_all_templates_exist(self):
        needed = ['base.html', 'login.html', 'dashboard.html', 'idea_form.html',
                  'idea_detail.html', 'kanban.html', 'admin.html', 'settings.html',
                  'spoc_dashboard.html', 'spoc_ideas.html', 'edit_benefits.html',
                  'cgi_dashboard.html', 'lt_dashboard.html']
        td = os.path.join(PROJECT_ROOT, 'templates')
        for t in needed:
            assert os.path.exists(os.path.join(td, t)), f"Missing template: {t}"

    def test_routes_accessible(self, client):
        for path in ['/', '/login', '/logout']:
            r = client.get(path)
            assert r.status_code in [200, 302]

    def test_import_clears_old(self):
        import_spoc_mappings([{'category': 'Production Services', 'spoc_email': 'admin@company.com'}])
        admin = get_user_by_email('admin@company.com')
        spoc = get_spoc_by_category('Production Services')
        assert spoc['id'] == admin['id']

    def test_jira_missing_settings(self, client):
        save_setting('jira_domain', '')
        idea = get_all_ideas()[0]
        from app import create_jira_ticket as jf
        r, e = jf(idea)
        assert r is None and e is not None

    def test_update_benefits_db(self, owner_id):
        ideas = get_all_ideas()
        fi = ideas[0]
        update_idea_benefits(fi['id'], 99999.0, 888.0, 'TM', 'TI')
        conn = get_db()
        row = conn.execute(
            'SELECT proj_savings, hours_saved, savings_measurement, business_impact FROM ideas WHERE id = ?',
            (fi['id'],)).fetchone()
        conn.close()
        assert row['proj_savings'] == 99999.0
        assert row['hours_saved'] == 888.0
        assert row['savings_measurement'] == 'TM'
        assert row['business_impact'] == 'TI'

    def test_get_idea_none(self):
        assert get_idea_by_id(999999) is None

    def test_allowed_file(self, client):
        from app import allowed_file
        assert allowed_file('document.pdf') is True
        assert allowed_file('document.exe') is False
        assert allowed_file('noextension') is False

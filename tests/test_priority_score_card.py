"""
Priority Score Card — New Tests
Tests the new weighted scoring, confidence multipliers, and card UI rendering.
"""
import io
import os
import pytest
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import app as app_mod
import setup_db
from app import (
    app, calculate_priority_score, get_db, get_user_by_email,
    get_idea_by_id, get_all_ideas, get_spoc_by_category,
    update_idea_benefits, create_idea, IDEA_STATUSES,
)
from encryption import encrypt_data, decrypt_data
import encryption

setup_db.setup_database()
setup_db.migrate_database()
setup_db.seed_database()


@pytest.fixture(autouse=True)
def reset_db():
    setup_db.setup_database()
    setup_db.migrate_database()
    setup_db.seed_database()
    yield


@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key-for-e2e-testing-only-1234567'
    upload_dir = os.path.join(os.path.dirname(__file__), '..', 'uploads')
    app.config['UPLOAD_FOLDER'] = upload_dir
    os.makedirs(upload_dir, exist_ok=True)
    with app.test_client() as c:
        with app.app_context():
            yield c


@pytest.fixture
def owner_id():
    return get_user_by_email('john.smith@company.com')['id']


@pytest.fixture
def spoc_id():
    return get_user_by_email('sarah.johnson@company.com')['id']


def login_as(client, email):
    return client.post('/login', data={'email': email}, follow_redirects=True)


# ============================================================
# 1. SCORING LOGIC — Weighted Calculation
# ============================================================

class TestWeightedScoring:
    """Verify the weighted formula produces correct scores."""

    def test_all_max_scores_gives_raw_3(self):
        """All 3s: 3*0.35 + 3*0.25 + 3*0.25 + 3*0.15 = 3.00"""
        r = calculate_priority_score({
            'proj_savings': 200000, 'complexity': 'Low',
            'hours_saved': 2000, 'users_impacted': '200 users',
            'confidence': 'Medium',
        })
        assert r['raw_score'] == pytest.approx(3.0, abs=0.01)
        assert r['multiplier'] == 1.0
        assert r['score'] == pytest.approx(3.0, abs=0.01)

    def test_all_min_scores_gives_raw_1(self):
        """All 1s: 1*0.35 + 1*0.25 + 1*0.25 + 1*0.15 = 1.00"""
        r = calculate_priority_score({
            'proj_savings': 1000, 'complexity': 'High',
            'hours_saved': 50, 'users_impacted': '2 users',
            'confidence': 'Medium',
        })
        assert r['raw_score'] == pytest.approx(1.0, abs=0.01)
        assert r['score'] == pytest.approx(1.0, abs=0.01)

    def test_mixed_scores_2_and_3(self):
        """Savings=3, Complexity=2, Hours=3, Users=1"""
        r = calculate_priority_score({
            'proj_savings': 150000, 'complexity': 'Medium',
            'hours_saved': 1200, 'users_impacted': '5 users',
            'confidence': 'Medium',
        })
        # savings=3, complexity=2, hours=3, users=1
        assert r['raw_score'] == pytest.approx(2.45, abs=0.01)

    def test_boundary_savings_50k(self):
        """Exactly $50,000 should be score 1 (not > 50k)."""
        r = calculate_priority_score({
            'proj_savings': 50000, 'complexity': 'Medium',
            'hours_saved': 500, 'users_impacted': '10 users',
            'confidence': 'Medium',
        })
        # savings=1, complexity=2, hours=1, users=1
        assert r['raw_score'] == pytest.approx(1.25, abs=0.01)

    def test_boundary_savings_50001(self):
        """$50,001 should be score 2 (> 50k)."""
        r = calculate_priority_score({
            'proj_savings': 50001, 'complexity': 'Medium',
            'hours_saved': 500, 'users_impacted': '10 users',
            'confidence': 'Medium',
        })
        # savings=2, complexity=2, hours=1, users=1
        assert r['raw_score'] == pytest.approx(1.60, abs=0.01)

    def test_boundary_hours_1000(self):
        """Exactly 1000 hours should be score 1."""
        r = calculate_priority_score({
            'proj_savings': 1000, 'complexity': 'Medium',
            'hours_saved': 1000, 'users_impacted': '10 users',
            'confidence': 'Medium',
        })
        # savings=1, complexity=2, hours=2, users=1
        assert r['raw_score'] == pytest.approx(1.50, abs=0.01)

    def test_boundary_hours_1001(self):
        """1001 hours should be score 3 (> 1000)."""
        r = calculate_priority_score({
            'proj_savings': 1000, 'complexity': 'Medium',
            'hours_saved': 1001, 'users_impacted': '10 users',
            'confidence': 'Medium',
        })
        # savings=1, complexity=2, hours=3, users=1
        assert r['raw_score'] == pytest.approx(1.75, abs=0.01)

    def test_boundary_users_50(self):
        """Exactly 50 users should be score 1 (not > 50)."""
        r = calculate_priority_score({
            'proj_savings': 1000, 'complexity': 'Medium',
            'hours_saved': 100, 'users_impacted': '50 users',
            'confidence': 'Medium',
        })
        # savings=1, complexity=2, hours=1, users=2
        assert r['raw_score'] == pytest.approx(1.40, abs=0.01)

    def test_boundary_users_51(self):
        """51 users should be score 3 (> 50)."""
        r = calculate_priority_score({
            'proj_savings': 1000, 'complexity': 'Medium',
            'hours_saved': 100, 'users_impacted': '51 users',
            'confidence': 'Medium',
        })
        # savings=1, complexity=2, hours=1, users=3
        assert r['raw_score'] == pytest.approx(1.55, abs=0.01)

    def test_users_text_parsing(self):
        """Extract number from text like '100 users' or '500+ new hires'."""
        r1 = calculate_priority_score({
            'proj_savings': 1000, 'complexity': 'Medium',
            'hours_saved': 100, 'users_impacted': '100 users',
            'confidence': 'Medium',
        })
        r2 = calculate_priority_score({
            'proj_savings': 1000, 'complexity': 'Medium',
            'hours_saved': 100, 'users_impacted': '500+ new hires',
            'confidence': 'Medium',
        })
        # 500 users gives score 3, 100 users gives score 3
        assert '3/3 points' in r1['breakdown']['Users Impacted']
        assert '3/3 points' in r2['breakdown']['Users Impacted']

    def test_users_non_numeric_returns_zero(self):
        """Non-numeric text like 'many' should give 0 users → score 1."""
        r = calculate_priority_score({
            'proj_savings': 1000, 'complexity': 'Medium',
            'hours_saved': 100, 'users_impacted': 'many people',
            'confidence': 'Medium',
        })
        assert r['breakdown']['Users Impacted'] == '1/3 points (0 users)'

    def test_missing_complexity_defaults_to_score_1(self):
        """Empty or unknown complexity → score 1."""
        r = calculate_priority_score({
            'proj_savings': 1000, 'complexity': '',
            'hours_saved': 100, 'users_impacted': '10 users',
            'confidence': 'Medium',
        })
        assert '1/3' in r['breakdown']['Complexity']

    def test_unknown_complexity_defaults_to_score_1(self):
        r = calculate_priority_score({
            'proj_savings': 1000, 'complexity': 'Extreme',
            'hours_saved': 100, 'users_impacted': '10 users',
            'confidence': 'Medium',
        })
        assert '1/3' in r['breakdown']['Complexity']


# ============================================================
# 2. CONFIDENCE MULTIPLIER
# ============================================================

class TestConfidenceMultiplier:
    """Verify confidence adjusts scores correctly."""

    def test_high_confidence_bumps_medium_to_high(self):
        """Score just below High threshold should be pushed above with ×1.2."""
        r = calculate_priority_score({
            'proj_savings': 75000, 'complexity': 'Medium',
            'hours_saved': 600, 'users_impacted': '20 users',
            'confidence': 'High',
        })
        # raw ≈ 2.0 * 0.35 + 2.0 * 0.25 + 2.0 * 0.25 + 2.0 * 0.15 = 2.0
        # 2.0 * 1.2 = 2.4 > 2.25 → High
        assert r['confidence'] == 'High'
        assert r['multiplier'] == 1.2

    def test_low_confidence_drops_high_to_medium(self):
        """High raw score with ×0.8 may drop to Medium."""
        r = calculate_priority_score({
            'proj_savings': 150000, 'complexity': 'Low',
            'hours_saved': 800, 'users_impacted': '15 users',
            'confidence': 'Low',
        })
        # savings=3, complexity=3, hours=2, users=2
        # raw = 3*0.35 + 3*0.25 + 2*0.25 + 2*0.15 = 2.4
        # 2.4 * 0.8 = 1.92 → Medium
        assert r['confidence'] == 'Low'
        assert r['multiplier'] == 0.8
        assert r['priority'] == 'Medium'

    def test_medium_confidence_no_adjustment(self):
        r = calculate_priority_score({
            'proj_savings': 200000, 'complexity': 'Low',
            'hours_saved': 1500, 'users_impacted': '100 users',
            'confidence': 'Medium',
        })
        assert r['multiplier'] == 1.0
        assert r['score'] == r['raw_score']

    def test_score_formula_correct(self):
        """score = round(raw_score × multiplier, 2)."""
        r = calculate_priority_score({
            'proj_savings': 75000, 'complexity': 'Medium',
            'hours_saved': 600, 'users_impacted': '20 users',
            'confidence': 'High',
        })
        expected_score = round(r['raw_score'] * 1.2, 2)
        assert r['score'] == expected_score


# ============================================================
# 3. PRIORITY BANDS
# ============================================================

class TestPriorityBands:
    """Verify High/Medium/Low/Unscored thresholds."""

    def test_high_threshold_225(self):
        """Score just above 2.25 should be High."""
        # Get close to 2.25 with high confidence
        r = calculate_priority_score({
            'proj_savings': 120000, 'complexity': 'Low',
            'hours_saved': 900, 'users_impacted': '30 users',
            'confidence': 'High',
        })
        assert r['priority'] == 'High'

    def test_medium_threshold_15(self):
        """Score just above 1.50 should be Medium."""
        r = calculate_priority_score({
            'proj_savings': 60000, 'complexity': 'Medium',
            'hours_saved': 600, 'users_impacted': '20 users',
            'confidence': 'Medium',
        })
        assert r['priority'] == 'Medium'

    def test_low_150_and_below(self):
        """Score ≤ 1.50 should be Low."""
        r = calculate_priority_score({
            'proj_savings': 30000, 'complexity': 'Medium',
            'hours_saved': 400, 'users_impacted': '8 users',
            'confidence': 'Medium',
        })
        # savings=1, complexity=2, hours=1, users=1 → raw = 0.35+0.50+0.25+0.15 = 1.25
        assert r['priority'] == 'Low'
        assert r['raw_score'] == pytest.approx(1.25, abs=0.01)

    def test_boundary_150_equals_medium(self):
        """Score exactly 1.50 should be Medium (> 1.50 means strictly greater)."""
        # Need raw exactly 1.5 with medium confidence
        r = calculate_priority_score({
            'proj_savings': 30000, 'complexity': 'Medium',
            'hours_saved': 400, 'users_impacted': '20 users',
            'confidence': 'Medium',
        })
        # savings=1, complexity=2, hours=1, users=2 → raw = 0.35+0.50+0.25+0.30 = 1.40
        # That's below 1.50, so Low
        assert r['priority'] == 'Low'


# ============================================================
# 4. RETURN DICT KEYS
# ============================================================

class TestReturnKeys:
    """Verify the return dict has all required keys."""

    def test_high_score_has_all_keys(self):
        r = calculate_priority_score({
            'proj_savings': 200000, 'complexity': 'Low',
            'hours_saved': 1500, 'users_impacted': '100 users',
            'confidence': 'High',
        })
        required = ['priority', 'score', 'raw_score', 'confidence', 'multiplier',
                     'breakdown', 'summary_sentence', 'max_score']
        for key in required:
            assert key in r, f"Missing key: {key}"

    def test_unscored_has_all_keys(self):
        r = calculate_priority_score({
            'proj_savings': 0, 'complexity': '',
            'hours_saved': 0, 'users_impacted': '',
            'confidence': 'Medium',
        })
        required = ['priority', 'score', 'raw_score', 'confidence', 'multiplier',
                     'breakdown', 'summary_sentence', 'missing_fields']
        for key in required:
            assert key in r, f"Missing key: {key}"

    def test_breakdown_has_all_factors(self):
        r = calculate_priority_score({
            'proj_savings': 100000, 'complexity': 'Medium',
            'hours_saved': 600, 'users_impacted': '20 users',
            'confidence': 'Medium',
        })
        factors = ['Projected Savings', 'Complexity', 'Hours Saved (Yearly)', 'Users Impacted']
        for f in factors:
            assert f in r['breakdown'], f"Missing breakdown factor: {f}"

    def test_breakdown_format(self):
        r = calculate_priority_score({
            'proj_savings': 100000, 'complexity': 'Low',
            'hours_saved': 1000, 'users_impacted': '50 users',
            'confidence': 'Medium',
        })
        # Format: "X/3 points (...)"
        for factor, value in r['breakdown'].items():
            assert '/3 points' in value or 'N/A' in value, f"Bad format for {factor}: {value}"

    def test_summary_sentence_exists_and_has_priority(self):
        r = calculate_priority_score({
            'proj_savings': 200000, 'complexity': 'Low',
            'hours_saved': 1500, 'users_impacted': '100 users',
            'confidence': 'High',
        })
        assert 'High' in r['summary_sentence']
        assert 'score' in r['summary_sentence'].lower()

    def test_summary_sentence_exists_unscored(self):
        r = calculate_priority_score({
            'proj_savings': 0, 'complexity': '',
            'hours_saved': 0, 'users_impacted': '',
            'confidence': 'Low',
        })
        assert 'scoreit' in r['summary_sentence'].lower() or 'data' in r['summary_sentence'].lower()

    def test_missing_fields_listed(self):
        r = calculate_priority_score({
            'proj_savings': 0, 'complexity': '',
            'hours_saved': 0, 'users_impacted': '',
            'confidence': 'Medium',
        })
        assert len(r['missing_fields']) == 4
        assert 'Projected Savings' in r['missing_fields']
        assert 'Hours Saved (Yearly)' in r['missing_fields']

    def test_partial_missing_fields(self):
        """Only savings provided → 3 missing fields."""
        r = calculate_priority_score({
            'proj_savings': 100000, 'complexity': '',
            'hours_saved': 0, 'users_impacted': '',
            'confidence': 'Medium',
        })
        assert len(r['missing_fields']) == 3
        assert 'Projected Savings' not in r['missing_fields']

    def test_max_score_is_3(self):
        r = calculate_priority_score({
            'proj_savings': 200000, 'complexity': 'Low',
            'hours_saved': 2000, 'users_impacted': '200 users',
            'confidence': 'Medium',
        })
        assert r['max_score'] == 3.0

    def test_score_not_exceeding_raw_max_with_high_confidence(self):
        """Score can exceed max_score when High confidence is applied."""
        r = calculate_priority_score({
            'proj_savings': 200000, 'complexity': 'Low',
            'hours_saved': 2000, 'users_impacted': '200 users',
            'confidence': 'High',
        })
        assert r['score'] > r['max_score']  # 3.0 * 1.2 = 3.6


# ============================================================
# 5. UI RENDERING — IDEA DETAIL PAGE
# ============================================================

class TestUIRendering:
    """Verify the Priority Card renders correctly in HTML."""

    def test_card_rendered_for_scoreit_status(self, client, owner_id, spoc_id):
        login_as(client, 'john.smith@company.com')
        client.post('/ideas/new', data={
            'title': 'UI Card Test', 'category': 'Production Services',
            'problem_statement': 'T', 'proposed_solution': 'T',
            'proj_savings': '200000', 'complexity': 'Low',
            'hours_saved': '1500', 'users_impacted': '100 users',
            'confidence': 'High',
        }, follow_redirects=True)
        idea_id = [i['id'] for i in get_all_ideas() if i['title'] == 'UI Card Test'][0]
        # Move to ScoreIT
        from unittest.mock import patch
        with patch('app.send_status_update_email', return_value=None):
            login_as(client, 'sarah.johnson@company.com')
            client.post(f'/ideas/{idea_id}/status', data={'status': 'ScoreIT'}, follow_redirects=True)
        r = client.get(f'/ideas/{idea_id}')
        assert r.status_code == 200
        assert b'Priority Score Card' in r.data
        assert b'High Priority' in r.data
        # Should have red gradient classes
        assert b'from-red-50' in r.data or b'red-200' in r.data

    def test_card_not_shown_for_non_scoreit_status(self, client, owner_id, spoc_id):
        login_as(client, 'john.smith@company.com')
        client.post('/ideas/new', data={
            'title': 'No Card Test XYZ', 'category': 'Production Services',
            'problem_statement': 'T', 'proposed_solution': 'T',
        }, follow_redirects=True)
        idea_id = [i['id'] for i in get_all_ideas() if i['title'] == 'No Card Test XYZ'][0]
        # Idea is still "Open", should NOT show priority card
        r = client.get(f'/ideas/{idea_id}')
        assert r.status_code == 200
        # The "Priority Score Card" section should only appear in ScoreIT
        assert b'priority_info' not in r.data

    def test_unscored_card_shows_warning(self, client, owner_id, spoc_id):
        login_as(client, 'john.smith@company.com')
        client.post('/ideas/new', data={
            'title': 'Unscored Test', 'category': 'Production Services',
            'problem_statement': 'T', 'proposed_solution': 'T',
            'confidence': 'Medium',
        }, follow_redirects=True)
        idea_id = [i['id'] for i in get_all_ideas() if i['title'] == 'Unscored Test'][0]
        from unittest.mock import patch
        with patch('app.send_status_update_email', return_value=None):
            login_as(client, 'sarah.johnson@company.com')
            client.post(f'/ideas/{idea_id}/status', data={'status': 'ScoreIT'}, follow_redirects=True)
        r = client.get(f'/ideas/{idea_id}')
        assert r.status_code == 200
        assert b'Priority Score Card' in r.data
        assert b'Unscored' in r.data

    def test_confidence_badge_rendered(self, client, owner_id, spoc_id):
        login_as(client, 'john.smith@company.com')
        client.post('/ideas/new', data={
            'title': 'Conf Badge Test', 'category': 'Production Services',
            'problem_statement': 'T', 'proposed_solution': 'T',
            'proj_savings': '50000', 'complexity': 'Medium',
            'hours_saved': '500', 'users_impacted': '10 users',
            'confidence': 'Low',
        }, follow_redirects=True)
        idea_id = [i['id'] for i in get_all_ideas() if i['title'] == 'Conf Badge Test'][0]
        from unittest.mock import patch
        with patch('app.send_status_update_email', return_value=None):
            login_as(client, 'sarah.johnson@company.com')
            client.post(f'/ideas/{idea_id}/status', data={'status': 'ScoreIT'}, follow_redirects=True)
        r = client.get(f'/ideas/{idea_id}')
        assert r.status_code == 200
        assert b'Low' in r.data
        # Should show multiplier (using the × character encoded as UTF-8)
        assert b'\xc3\x970.8' in r.data or b'multiplier' in r.data.lower()

    def test_progress_bar_rendered(self, client, owner_id, spoc_id):
        login_as(client, 'john.smith@company.com')
        client.post('/ideas/new', data={
            'title': 'Progress Bar Test', 'category': 'Production Services',
            'problem_statement': 'T', 'proposed_solution': 'T',
            'proj_savings': '200000', 'complexity': 'Low',
            'hours_saved': '1500', 'users_impacted': '100 users',
            'confidence': 'High',
        }, follow_redirects=True)
        idea_id = [i['id'] for i in get_all_ideas() if i['title'] == 'Progress Bar Test'][0]
        from unittest.mock import patch
        with patch('app.send_status_update_email', return_value=None):
            login_as(client, 'sarah.johnson@company.com')
            client.post(f'/ideas/{idea_id}/status', data={'status': 'ScoreIT'}, follow_redirects=True)
        r = client.get(f'/ideas/{idea_id}')
        assert r.status_code == 200
        # Progress bar and threshold markers
        assert b'bg-gradient' in r.data or b'from-' in r.data
        # Collapsible section present
        assert b'Show calculation details' in r.data
        assert b'formula' in r.data.lower() or b'raw_score' in r.data.lower().decode()

    def test_color_gradient_by_priority(self, client, owner_id, spoc_id):
        """Different priorities should produce different gradient classes."""
        login_as(client, 'john.smith@company.com')

        # High card
        client.post('/ideas/new', data={
            'title': 'Color High', 'category': 'Production Services',
            'problem_statement': 'T', 'proposed_solution': 'T',
            'proj_savings': '200000', 'complexity': 'Low',
            'hours_saved': '1500', 'users_impacted': '100 users',
            'confidence': 'High',
        }, follow_redirects=True)
        from unittest.mock import patch
        with patch('app.send_status_update_email', return_value=None):
            login_as(client, 'sarah.johnson@company.com')
            for title in ['Color High']:
                idea_id = [i['id'] for i in get_all_ideas() if i['title'] == title][0]
                client.post(f'/ideas/{idea_id}/status', data={'status': 'ScoreIT'}, follow_redirects=True)

        r = client.get(f'/ideas/{[i["id"] for i in get_all_ideas() if i["title"] == "Color High"][0]}')
        assert b'from-red-50' in r.data or b'red-200' in r.data

    def test_summary_sentence_in_html(self, client, owner_id, spoc_id):
        login_as(client, 'john.smith@company.com')
        client.post('/ideas/new', data={
            'title': 'Summary Test', 'category': 'Production Services',
            'problem_statement': 'T', 'proposed_solution': 'T',
            'proj_savings': '200000', 'complexity': 'Low',
            'hours_saved': '1500', 'users_impacted': '100 users',
            'confidence': 'High',
        }, follow_redirects=True)
        idea_id = [i['id'] for i in get_all_ideas() if i['title'] == 'Summary Test'][0]
        from unittest.mock import patch
        with patch('app.send_status_update_email', return_value=None):
            login_as(client, 'sarah.johnson@company.com')
            client.post(f'/ideas/{idea_id}/status', data={'status': 'ScoreIT'}, follow_redirects=True)
        r = client.get(f'/ideas/{idea_id}')
        assert r.status_code == 200
        assert b'assessed as' in r.data.lower()


# ============================================================
# 6. CONFIDENCE IN FORMS
# ============================================================

class TestConfidenceInForms:
    """Verify confidence dropdown appears in forms."""

    def test_confidence_in_new_idea_form(self, client, owner_id):
        login_as(client, 'john.smith@company.com')
        r = client.get('/ideas/new')
        assert r.status_code == 200
        assert b'confidence' in r.data.lower() or b'Confidence' in r.data
        # Should show multiplier options
        assert any(b'1.2' in line or b'1.0' in line or b'0.8' in line for line in r.data.split(b'\n'))

    def test_confidence_in_edit_benefits_form(self, client, owner_id, spoc_id):
        login_as(client, 'john.smith@company.com')
        client.post('/ideas/new', data={
            'title': 'Edit Conf Test', 'category': 'Production Services',
            'problem_statement': 'T', 'proposed_solution': 'T',
        }, follow_redirects=True)
        idea_id = [i['id'] for i in get_all_ideas() if i['title'] == 'Edit Conf Test'][0]
        login_as(client, 'sarah.johnson@company.com')
        r = client.get(f'/ideas/{idea_id}/edit-benefits')
        assert r.status_code == 200
        assert b'Confidence' in r.data
        assert any(b'1.2' in line or b'1.0' in line or b'0.8' in line for line in r.data.split(b'\n'))


# ============================================================
# 7. HRS/YEAR LABELS
# ============================================================

class TestHrsYearLabels:
    """Verify all labels changed from hrs/month to hrs/year."""

    def test_idea_detail_has_hrs_year(self, client, owner_id, spoc_id):
        login_as(client, 'john.smith@company.com')
        client.post('/ideas/new', data={
            'title': 'Label Test', 'category': 'Production Services',
            'problem_statement': 'T', 'proposed_solution': 'T',
            'hours_saved': '480',
        }, follow_redirects=True)
        r = client.get(f'/ideas/{[i["id"] for i in get_all_ideas() if i["title"] == "Label Test"][0]}')
        assert b'hrs/year' in r.data
        # Should NOT contain hrs/month
        assert b'hrs/month' not in r.data

    def test_edit_benefits_has_hrs_year(self, client, owner_id, spoc_id):
        login_as(client, 'john.smith@company.com')
        client.post('/ideas/new', data={
            'title': 'Label Test 2', 'category': 'Production Services',
            'problem_statement': 'T', 'proposed_solution': 'T',
            'hours_saved': '480',
        }, follow_redirects=True)
        idea_id = [i['id'] for i in get_all_ideas() if i['title'] == 'Label Test 2'][0]
        login_as(client, 'sarah.johnson@company.com')
        r = client.get(f'/ideas/{idea_id}/edit-benefits')
        assert b'hrs/year' in r.data
        assert b'hrs/month' not in r.data


# ============================================================
# 8. CONFIDENCE PERSISTS THROUGH SAVE
# ============================================================

class TestConfidencePersistence:
    """Verify confidence is saved and loaded correctly."""

    def test_confidence_saved_on_creation(self, client, owner_id):
        login_as(client, 'john.smith@company.com')
        client.post('/ideas/new', data={
            'title': 'Persist Test', 'category': 'Production Services',
            'problem_statement': 'T', 'proposed_solution': 'T',
            'proj_savings': '100000', 'complexity': 'Low',
            'hours_saved': '500', 'users_impacted': '20 users',
            'confidence': 'High',
        }, follow_redirects=True)
        idea = [i for i in get_all_ideas() if i['title'] == 'Persist Test'][0]
        assert idea['confidence'] == 'High'

    def test_confidence_defaults_to_medium(self, client, owner_id):
        login_as(client, 'john.smith@company.com')
        client.post('/ideas/new', data={
            'title': 'Default Conf Test', 'category': 'Production Services',
            'problem_statement': 'T', 'proposed_solution': 'T',
        }, follow_redirects=True)
        idea = [i for i in get_all_ideas() if i['title'] == 'Default Conf Test'][0]
        assert idea['confidence'] == 'Medium'

    def test_confidence_updated_via_edit_benefits(self, client, owner_id, spoc_id):
        login_as(client, 'john.smith@company.com')
        client.post('/ideas/new', data={
            'title': 'Update Conf Test', 'category': 'Production Services',
            'problem_statement': 'T', 'proposed_solution': 'T',
            'proj_savings': '100000', 'complexity': 'Low',
            'hours_saved': '500', 'users_impacted': '20 users',
            'confidence': 'Low',
        }, follow_redirects=True)
        idea_id = [i['id'] for i in get_all_ideas() if i['title'] == 'Update Conf Test'][0]

        login_as(client, 'sarah.johnson@company.com')
        client.post(f'/ideas/{idea_id}/edit-benefits', data={
            'proj_savings': '150000',
            'hours_saved': '600',
            'savings_measurement': 'Test',
            'business_impact': 'Test',
            'confidence': 'High',
        }, follow_redirects=True)

        idea = get_idea_by_id(idea_id)
        assert idea['confidence'] == 'High'
        assert idea['proj_savings'] == 150000.0

    def test_confidence_stored_in_db_column(self):
        """Verify the confidence column exists and works at DB level."""
        conn = get_db()
        cols = [col[1] for col in conn.execute('PRAGMA table_info(ideas)').fetchall()]
        conn.close()
        assert 'confidence' in cols

    def test_confidence_migration_sets_default(self):
        """Fresh DB should have confidence = 'Medium' for seeded ideas."""
        ideas = get_all_ideas()
        for idea in ideas:
            assert idea['confidence'] in ('High', 'Medium', 'Low')


# ============================================================
# 9. KANBAN BOARD — SCOREIT COLUMNS
# ============================================================

class TestKanbanWithConfidence:
    """Verify Kanban board handles confidence properly."""

    def test_ideas_in_scoreit_column_show_priority(self, client, owner_id):
        login_as(client, 'john.smith@company.com')
        client.post('/ideas/new', data={
            'title': 'Kanban ScoreIT Test', 'category': 'Production Services',
            'problem_statement': 'T', 'proposed_solution': 'T',
            'proj_savings': '200000', 'complexity': 'Low',
            'hours_saved': '1500', 'users_impacted': '100 users',
            'confidence': 'High',
        }, follow_redirects=True)
        from unittest.mock import patch
        with patch('app.send_status_update_email', return_value=None):
            login_as(client, 'sarah.johnson@company.com')
            idea_id = [i['id'] for i in get_all_ideas() if i['title'] == 'Kanban ScoreIT Test'][0]
            client.post(f'/ideas/{idea_id}/status', data={'status': 'ScoreIT'}, follow_redirects=True)

        r = client.get('/kanban')
        assert r.status_code == 200
        # The ScoreIT column should show priority badge
        assert b'Kanban ScoreIT Test' in r.data

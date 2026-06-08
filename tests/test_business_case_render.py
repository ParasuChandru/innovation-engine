"""
Innovation Engine - Business Case Render Integration Tests

These three tests verify that the three previously-crashing URLs now work
end-to-end when accessed via the Flask test client.
"""

import os
import sys

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, PROJECT_ROOT)

import pytest
from cryptography.fernet import Fernet

# ── bootstrap: write .env so encryption.py loads ──────────────────────
TEST_SECRET_KEY = 'test-secret-key-for-e2e-testing-only-1234567'
TEST_ENCRYPTION_KEY = Fernet.generate_key().decode()
with open(os.path.join(PROJECT_ROOT, '.env'), 'w') as f:
    f.write(f"SECRET_KEY={TEST_SECRET_KEY}\n")
    f.write(f"ENCRYPTION_KEY={TEST_ENCRYPTION_KEY}\n")

import app
import setup_db

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
    app.app.config['TESTING'] = True
    app.app.config['SECRET_KEY'] = TEST_SECRET_KEY
    upload_dir = os.path.join(PROJECT_ROOT, 'uploads')
    app.app.config['UPLOAD_FOLDER'] = upload_dir
    os.makedirs(upload_dir, exist_ok=True)
    with app.app.test_client() as c:
        yield c


def login_as(client, email):
    return client.post('/login', data={'email': email}, follow_redirects=True)


class TestBusinessCaseIntegration:
    """
    These three tests cover the URLs that used to return HTTP 500.
    Each one logs in as the SPOC assigned to an idea in the
    "Business Case Template" stage and asserts the expected response.

    The idea used is "Fleet Telematics Optimization" (id=9 in the seed
    data), assigned to emily.davis@company.com (SPOC for Supply Chain).
    """

    def test_idea_detail_page_200_with_business_case_card(self, client):
        """
        TEST ONE — /ideas/<id>
        Log in as the SPOC assigned to the Business Case Template idea,
        open the idea detail page, assert HTTP 200 and that the HTML
        contains the words "Business Case".
        """
        # Find the right idea and user by title/email (IDs shift between runs)
        from app import get_all_ideas, get_user_by_email
        bc_idea = None
        for i in get_all_ideas():
            if i['status'] == 'Business Case Template':
                bc_idea = i
                break
        assert bc_idea is not None, "No idea in Business Case Template status found"
        
        spoc = get_user_by_email('emily.davis@company.com')
        assert spoc is not None, "emily.davis@company.com not found"
        assert bc_idea['spoc_id'] == spoc['id'], f"spoc_id mismatch: {bc_idea['spoc_id']} != {spoc['id']}"
        
        login_as(client, 'emily.davis@company.com')
        r = client.get(f'/ideas/{bc_idea["id"]}')
        assert r.status_code == 200, f"Expected 200, got {r.status_code} redirecting to {getattr(r, 'location', 'N/A')}. First 600 bytes: {r.data[:600]}"
        assert b'Business Case' in r.data or b'business case' in r.data.lower(), (
            f"Response HTML must contain 'Business Case'. First 600 bytes: {r.data[:600]}"
        )

    def test_business_case_form_page_200_with_fields(self, client):
        """
        TEST TWO — /ideas/<id>/business-case
        Log in as the same SPOC, open the business-case edit page,
        assert HTTP 200 and that the response HTML contains at least
        two of these form field names: executive_summary, benefit_type, kpis.
        """
        from app import get_all_ideas, get_user_by_email
        bc_idea = next((i for i in get_all_ideas() if i['status'] == 'Business Case Template'), None)
        assert bc_idea is not None
        
        login_as(client, 'emily.davis@company.com')
        r = client.get(f'/ideas/{bc_idea["id"]}/business-case')
        assert r.status_code == 200, f"Expected 200, got {r.status_code}. First 600 bytes: {r.data[:600]}"
        text = r.data.decode('utf-8').lower()
        found = sum([
            'executive_summary' in text,
            'benefit_type' in text,
            'kpis' in text,
        ])
        assert found >= 2, (
            f"Expected at least 2 of [executive_summary, benefit_type, kpis] in the "
            f"HTML. Found {found}. First 800 bytes: {r.data[:800]}"
        )

    def test_business_case_pdf_generates_valid_pdf(self, client):
        """
        TEST THREE — /ideas/<id>/business-case-pdf
        Log in as the same SPOC, download the PDF, assert HTTP 200,
        assert response bytes start with %PDF, then verify with pypdf
        that the PDF has at least one page and is not corrupted.
        """
        from app import get_all_ideas
        bc_idea = next((i for i in get_all_ideas() if i['status'] == 'Business Case Template'), None)
        assert bc_idea is not None
        
        login_as(client, 'emily.davis@company.com')
        r = client.get(f'/ideas/{bc_idea["id"]}/business-case-pdf')
        assert r.status_code == 200, f"Expected 200, got {r.status_code}. First 200 bytes: {r.data[:200]}"

        # 1. Check PDF magic bytes
        assert r.data.startswith(b'%PDF'), (
            f"PDF response must start with %PDF. First 10 bytes: {r.data[:10]}"
        )

        # 2. Validate with pypdf — a malformed PDF will raise
        from pypdf import PdfReader
        from io import BytesIO

        reader = PdfReader(BytesIO(r.data))
        num_pages = len(reader.pages)
        assert num_pages >= 1, (
            f"PDF must have at least 1 page but has {num_pages}"
        )

        # 3. Sanity-check: the title should appear in the PDF content
        page_text = reader.pages[0].extract_text() or ''
        assert 'Fleet Telematics' in page_text or 'Innovation Engine' in page_text, (
            f"First page text should contain the idea title or 'Innovation Engine'. "
            f"Got: {page_text[:200]}"
        )

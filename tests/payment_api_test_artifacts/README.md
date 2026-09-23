# Payment API Test Artifacts

Traceability: Jira Epic `RBTES-1567` with stories `RBTES-1582`, `RBTES-1584`, and `RBTES-1611`.

This folder contains testing-only assets for the payment initiation and payment status API work:

- `Payment_API_Test_Cases.xlsx` - structured manual/API test cases with Jira traceability
- `mock_payment_api.py` - self-contained Flask mock payment API harness
- `test_payment_api_playwright.py` - Playwright API automation covering initiation, status, validation, auth, and idempotency flows
- `payment_api_openapi_stub.yaml` - lightweight OpenAPI stub used as executable contract reference for tests

Notes:
- No existing executable HTTP payment endpoint was found in the repo. `payment_api.py` currently provides an in-memory service component only.
- The mock harness wraps the repo's `PaymentService` behavior and adds validation, auth checks, and status retrieval routes so automation can be authored without unrelated app changes.
- Artifacts are intentionally isolated under `tests/payment_api_test_artifacts/` to avoid impacting the main Flask application.

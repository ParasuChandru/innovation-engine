"""Playwright API automation for payment initiation and status retrieval.

These tests are authored as deliverable artifacts and are not executed by this task.
Traceability:
- RBTES-1582: request/response contract, validation, invalid request errors
- RBTES-1584: OpenAPI/security/error handling considerations
- RBTES-1611: POST initiation, GET status by system id, GET status by customer id
"""

from __future__ import annotations

import os
import random
import sys
from pathlib import Path

import pytest
from playwright.sync_api import APIRequestContext, Playwright

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

BASE_URL = os.getenv('PAYMENT_API_BASE_URL', 'http://127.0.0.1:5010')
API_TOKEN = os.getenv('PAYMENT_API_TOKEN', 'test-token')


def build_payload(customer_request_id: str | None = None, amount: str = '125.50') -> dict:
    return {
        'customerRequestId': customer_request_id or f'CUST-REQ-{random.randint(10000, 99999)}',
        'debtor': {'account': {'iban': 'DE89370400440532013000'}},
        'creditor': {'name': 'ABC Utilities', 'account': {'iban': 'FR7630006000011234567890189'}},
        'instructedAmount': {'currency': 'EUR', 'amount': amount},
        'requestedExecutionDate': '2026-09-25',
    }


@pytest.fixture(scope='session')
def api_context(playwright: Playwright) -> APIRequestContext:
    return playwright.request.new_context(
        base_url=BASE_URL,
        extra_http_headers={
            'Authorization': f'Bearer {API_TOKEN}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        },
    )


def test_payment_initiation_returns_accepted_and_ids(api_context: APIRequestContext):
    payload = build_payload()
    response = api_context.post('/api/payments', data=payload, headers={'Idempotency-Key': 'PW-INIT-00000001'})

    assert response.status == 202, response.text()
    body = response.json()
    assert body['status'] == 'ACCEPTED'
    assert body['paymentId'].startswith('PAY-')
    assert body['traceId'].startswith('TRC-')
    assert body['idempotencyKey'] == 'PW-INIT-00000001'
    assert body['replayed'] is False


def test_payment_status_retrieval_by_system_payment_id(api_context: APIRequestContext):
    payload = build_payload(customer_request_id='CUST-REQ-STATUS-10001')
    init_response = api_context.post('/api/payments', data=payload, headers={'Idempotency-Key': 'PW-STATUS-000001'})
    payment_id = init_response.json()['paymentId']

    status_response = api_context.get(f'/api/payments/{payment_id}/status')

    assert status_response.status == 200, status_response.text()
    body = status_response.json()
    assert body['paymentId'] == payment_id
    assert body['customerRequestId'] == 'CUST-REQ-STATUS-10001'
    assert body['transactionStatus'] == 'ACCP'


def test_payment_status_retrieval_by_customer_request_id(api_context: APIRequestContext):
    payload = build_payload(customer_request_id='CUST-REQ-STATUS-10002')
    api_context.post('/api/payments', data=payload, headers={'Idempotency-Key': 'PW-STATUS-000002'})

    status_response = api_context.get('/api/payments/status', params={'customerRequestId': 'CUST-REQ-STATUS-10002'})

    assert status_response.status == 200, status_response.text()
    body = status_response.json()
    assert body['customerRequestId'] == 'CUST-REQ-STATUS-10002'
    assert body['paymentStatus'] == 'ACCEPTED'


def test_repeated_request_with_same_idempotency_key_returns_original_response(api_context: APIRequestContext):
    payload = build_payload(customer_request_id='CUST-REQ-IDEMP-10001')

    first = api_context.post('/api/payments', data=payload, headers={'Idempotency-Key': 'PW-IDEMP-000001'})
    second = api_context.post('/api/payments', data=payload, headers={'Idempotency-Key': 'PW-IDEMP-000001'})

    assert first.status == 202, first.text()
    assert second.status == 200, second.text()
    assert second.json()['paymentId'] == first.json()['paymentId']
    assert second.json()['replayed'] is True


def test_same_idempotency_key_with_different_payload_returns_conflict(api_context: APIRequestContext):
    first_payload = build_payload(customer_request_id='CUST-REQ-IDEMP-10002', amount='125.50')
    second_payload = build_payload(customer_request_id='CUST-REQ-IDEMP-10002', amount='130.00')

    api_context.post('/api/payments', data=first_payload, headers={'Idempotency-Key': 'PW-IDEMP-000002'})
    conflict = api_context.post('/api/payments', data=second_payload, headers={'Idempotency-Key': 'PW-IDEMP-000002'})

    assert conflict.status == 409, conflict.text()
    body = conflict.json()
    assert body['code'] == 'IDEMPOTENCY_KEY_CONFLICT'
    assert body['status'] == 'CONFLICT'


def test_missing_required_field_returns_validation_error(api_context: APIRequestContext):
    payload = build_payload()
    del payload['customerRequestId']

    response = api_context.post('/api/payments', data=payload, headers={'Idempotency-Key': 'PW-NEG-000001'})

    assert response.status == 400, response.text()
    body = response.json()
    assert body['code'] == 'VALIDATION_ERROR'
    assert body['field'] == 'customerRequestId'


def test_invalid_json_returns_bad_request(api_context: APIRequestContext):
    response = api_context.post(
        '/api/payments',
        data='not-json',
        headers={'Idempotency-Key': 'PW-NEG-000002', 'Content-Type': 'application/json'},
    )

    assert response.status == 400, response.text()
    assert response.json()['code'] == 'INVALID_JSON'


def test_missing_authentication_returns_unauthorized(playwright: Playwright):
    api_context = playwright.request.new_context(base_url=BASE_URL)
    response = api_context.get('/api/payments/status', params={'customerRequestId': 'CUST-REQ-STATUS-10002'})

    assert response.status == 401, response.text()
    assert response.json()['code'] == 'UNAUTHORIZED'


def test_invalid_token_returns_forbidden(playwright: Playwright):
    api_context = playwright.request.new_context(
        base_url=BASE_URL,
        extra_http_headers={'Authorization': 'Bearer wrong-token'},
    )
    response = api_context.get('/api/payments/status', params={'customerRequestId': 'CUST-REQ-STATUS-10002'})

    assert response.status == 403, response.text()
    assert response.json()['code'] == 'FORBIDDEN'


def test_unknown_payment_identifier_returns_not_found(api_context: APIRequestContext):
    response = api_context.get('/api/payments/PAY-UNKNOWN/status')

    assert response.status == 404, response.text()
    assert response.json()['code'] == 'PAYMENT_NOT_FOUND'

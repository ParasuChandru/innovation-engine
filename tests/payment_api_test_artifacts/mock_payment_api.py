"""Self-contained mock payment API harness for testing artifacts only.

Traceability:
- RBTES-1567 API Contract & Design
- RBTES-1582 payment API request/response contract and validation
- RBTES-1584 OpenAPI/security/error handling considerations
- RBTES-1611 POST initiation and GET status endpoints
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from typing import Any, Dict

from flask import Flask, jsonify, request

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.insert(0, PROJECT_ROOT)

from payment_api import IdempotencyError, PaymentService


API_TOKEN = os.getenv('PAYMENT_API_TOKEN', 'test-token')
app = Flask(__name__)
service = PaymentService()
_payment_status_store: Dict[str, Dict[str, Any]] = {}
_customer_request_index: Dict[str, str] = {}


def _error(status_code: int, code: str, message: str, field: str | None = None):
    response = {
        'code': code,
        'message': message,
        'status': status_code,
        'timestamp': datetime.utcnow().replace(microsecond=0).isoformat() + 'Z',
    }
    if field:
        response['field'] = field
    return jsonify(response), status_code


def _require_auth():
    auth_header = request.headers.get('Authorization', '')
    if not auth_header:
        return _error(401, 'UNAUTHORIZED', 'Authorization header is required')
    if auth_header != f'Bearer {API_TOKEN}':
        return _error(403, 'FORBIDDEN', 'Bearer token is invalid or not permitted')
    return None


def _validate_payload(payload: Dict[str, Any]):
    required_fields = ['customerRequestId', 'debtor', 'creditor', 'instructedAmount', 'requestedExecutionDate']
    for field in required_fields:
        if field not in payload:
            return _error(400, 'VALIDATION_ERROR', f'Missing required field: {field}', field)

    amount = payload.get('instructedAmount', {}).get('amount')
    currency = payload.get('instructedAmount', {}).get('currency')
    if currency != 'EUR':
        return _error(400, 'VALIDATION_ERROR', 'Only EUR currency is supported in the mock harness', 'instructedAmount.currency')

    try:
        numeric_amount = float(amount)
    except (TypeError, ValueError):
        return _error(400, 'VALIDATION_ERROR', 'Amount must be numeric', 'instructedAmount.amount')

    if numeric_amount <= 0:
        return _error(400, 'VALIDATION_ERROR', 'Amount must be greater than zero', 'instructedAmount.amount')

    debtor_iban = payload.get('debtor', {}).get('account', {}).get('iban')
    creditor_iban = payload.get('creditor', {}).get('account', {}).get('iban')
    if not debtor_iban:
        return _error(400, 'VALIDATION_ERROR', 'Debtor IBAN is required', 'debtor.account.iban')
    if not creditor_iban:
        return _error(400, 'VALIDATION_ERROR', 'Creditor IBAN is required', 'creditor.account.iban')

    return None


@app.get('/health')
def health():
    return jsonify({'status': 'ok'})


@app.post('/api/payments')
def initiate_payment():
    auth_error = _require_auth()
    if auth_error:
        return auth_error

    payload = request.get_json(silent=True)
    if payload is None:
        return _error(400, 'INVALID_JSON', 'Request body must be valid JSON')

    validation_error = _validate_payload(payload)
    if validation_error:
        return validation_error

    try:
        response, replayed = service.initiate_payment(payload, request.headers.get('Idempotency-Key'))
    except IdempotencyError as exc:
        return _error(400, 'IDEMPOTENCY_ERROR', str(exc), 'Idempotency-Key')

    if response.get('code') == 'IDEMPOTENCY_KEY_CONFLICT':
        return jsonify(response), 409

    payment_id = response['paymentId']
    _payment_status_store[payment_id] = {
        'paymentId': payment_id,
        'customerRequestId': payload['customerRequestId'],
        'traceId': response['traceId'],
        'transactionStatus': 'ACCP',
        'paymentStatus': 'ACCEPTED',
        'replayed': replayed,
        'statusReason': 'Payment initiation accepted for processing',
        'lastUpdatedAt': response['receivedAt'],
    }
    _customer_request_index[payload['customerRequestId']] = payment_id

    status_code = 200 if replayed else 202
    return jsonify({**response, 'replayed': replayed}), status_code


@app.get('/api/payments/<payment_id>/status')
def get_status_by_payment_id(payment_id: str):
    auth_error = _require_auth()
    if auth_error:
        return auth_error

    result = _payment_status_store.get(payment_id)
    if not result:
        return _error(404, 'PAYMENT_NOT_FOUND', 'Payment ID was not found', 'paymentId')
    return jsonify(result)


@app.get('/api/payments/status')
def get_status_by_customer_request_id():
    auth_error = _require_auth()
    if auth_error:
        return auth_error

    customer_request_id = request.args.get('customerRequestId')
    if not customer_request_id:
        return _error(400, 'VALIDATION_ERROR', 'customerRequestId query parameter is required', 'customerRequestId')

    payment_id = _customer_request_index.get(customer_request_id)
    if not payment_id:
        return _error(404, 'PAYMENT_NOT_FOUND', 'Customer request ID was not found', 'customerRequestId')

    return jsonify(_payment_status_store[payment_id])


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5010, debug=True)

"""Unit tests for payment API idempotent initiation support."""

import os
import sys

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, PROJECT_ROOT)

import pytest

from payment_api import (
    IdempotencyError,
    PaymentService,
)


@pytest.fixture
def service():
    return PaymentService()


def sample_payload(amount="125.50"):
    return {
        "customerRequestId": "CUST-REQ-10001",
        "debtor": {"account": {"iban": "DE89370400440532013000"}},
        "creditor": {"name": "ABC Utilities", "account": {"iban": "FR7630006000011234567890189"}},
        "instructedAmount": {"currency": "EUR", "amount": amount},
        "requestedExecutionDate": "2026-09-25",
    }


def test_repeated_equivalent_request_returns_original_response(service):
    payload = sample_payload()

    first_response, first_replayed = service.initiate_payment(payload, "IDEMP-12345678")
    second_response, second_replayed = service.initiate_payment(payload, "IDEMP-12345678")

    assert first_replayed is False
    assert second_replayed is True
    assert second_response == first_response
    assert second_response["paymentId"] == first_response["paymentId"]


def test_same_key_with_different_payload_returns_conflict_response(service):
    service.initiate_payment(sample_payload(amount="125.50"), "IDEMP-12345678")

    conflict_response, replayed = service.initiate_payment(sample_payload(amount="130.00"), "IDEMP-12345678")

    assert replayed is False
    assert conflict_response["code"] == "IDEMPOTENCY_KEY_CONFLICT"
    assert conflict_response["status"] == "CONFLICT"
    assert conflict_response["idempotencyKey"] == "IDEMP-12345678"


def test_missing_idempotency_key_is_rejected(service):
    with pytest.raises(IdempotencyError):
        service.initiate_payment(sample_payload(), None)


def test_invalid_idempotency_key_format_is_rejected(service):
    with pytest.raises(IdempotencyError):
        service.initiate_payment(sample_payload(), "bad key")

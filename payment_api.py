"""Payment API component with idempotent initiation support."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Tuple
import hashlib
import re
import uuid


IDEMPOTENCY_KEY_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9:_\-]{7,127}$")


class IdempotencyError(ValueError):
    """Raised when an idempotency key is missing or invalid."""


class IdempotencyConflictError(ValueError):
    """Raised when the same idempotency key is reused with a different payload."""


@dataclass
class PaymentRecord:
    payment_id: str
    trace_id: str
    idempotency_key: str
    request_payload: Dict[str, Any]
    payload_hash: str
    created_at: str

    def to_response(self) -> Dict[str, Any]:
        return {
            "paymentId": self.payment_id,
            "traceId": self.trace_id,
            "idempotencyKey": self.idempotency_key,
            "status": "ACCEPTED",
            "receivedAt": self.created_at,
        }


class PaymentService:
    """In-memory payment initiation service with idempotency enforcement."""

    def __init__(self) -> None:
        self._idempotency_records: Dict[str, PaymentRecord] = {}

    def validate_idempotency_key(self, idempotency_key: str | None) -> str:
        if not idempotency_key:
            raise IdempotencyError("Idempotency-Key header is required")
        normalized_key = idempotency_key.strip()
        if not IDEMPOTENCY_KEY_PATTERN.match(normalized_key):
            raise IdempotencyError(
                "Idempotency-Key must be 8-128 characters and contain only letters, numbers, colon, underscore, or hyphen"
            )
        return normalized_key

    def initiate_payment(self, payload: Dict[str, Any], idempotency_key: str | None) -> Tuple[Dict[str, Any], bool]:
        normalized_key = self.validate_idempotency_key(idempotency_key)
        payload_hash = self._hash_payload(payload)
        existing = self._idempotency_records.get(normalized_key)

        if existing:
            if existing.payload_hash != payload_hash:
                raise IdempotencyConflictError(
                    "Idempotency-Key has already been used with a different payment initiation request"
                )
            return existing.to_response(), True

        record = PaymentRecord(
            payment_id=f"PAY-{uuid.uuid4().hex[:12].upper()}",
            trace_id=f"TRC-{uuid.uuid4()}",
            idempotency_key=normalized_key,
            request_payload=payload,
            payload_hash=payload_hash,
            created_at=datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        )
        self._idempotency_records[normalized_key] = record
        return record.to_response(), False

    @staticmethod
    def _hash_payload(payload: Dict[str, Any]) -> str:
        import json

        canonical_payload = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()


payment_service = PaymentService()

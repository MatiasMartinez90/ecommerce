import hashlib
import hmac
from uuid import uuid4

import pytest

from ecommerce_api.security import (
    InvalidSignature,
    sign_order,
    validate_callback_signature,
    verify_order,
)

SECRET = "a-secret-that-is-longer-than-thirty-two-characters"


def test_order_token_round_trip() -> None:
    order_id = uuid4()
    assert verify_order(sign_order(order_id, SECRET), SECRET) == order_id


def test_order_token_rejects_tampering() -> None:
    token = sign_order(uuid4(), SECRET)
    with pytest.raises(InvalidSignature):
        verify_order(token + "x", SECRET)


def test_callback_signature_and_timestamp() -> None:
    payload = b'{"status":"approved"}'
    timestamp = "1000"
    signature = hmac.new(
        SECRET.encode(), timestamp.encode() + b"." + payload, hashlib.sha256
    ).hexdigest()
    validate_callback_signature(payload, timestamp, signature, SECRET, now=1001)
    with pytest.raises(InvalidSignature):
        validate_callback_signature(payload, timestamp, signature, SECRET, now=1400)

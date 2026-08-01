import base64
import hashlib
import hmac
import time
from uuid import UUID


class InvalidSignature(ValueError):
    pass


def hash_token(value: str) -> bytes:
    return hashlib.sha256(value.encode()).digest()


def _b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def _unb64url(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def sign_order(order_id: UUID, secret: str) -> str:
    encoded = _b64url(str(order_id).encode())
    signature = _b64url(hmac.new(secret.encode(), encoded.encode(), hashlib.sha256).digest())
    return f"{encoded}.{signature}"


def verify_order(token: str, secret: str) -> UUID:
    if len(secret) < 32 or len(token) > 1000 or token.count(".") != 1:
        raise InvalidSignature("invalid order token")
    encoded, supplied = token.split(".", 1)
    expected = _b64url(hmac.new(secret.encode(), encoded.encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(supplied, expected):
        raise InvalidSignature("invalid order token")
    try:
        return UUID(_unb64url(encoded).decode())
    except (ValueError, UnicodeDecodeError) as error:
        raise InvalidSignature("invalid order token") from error


def validate_callback_signature(
    payload: bytes,
    timestamp: str,
    signature: str,
    secret: str,
    *,
    now: int | None = None,
    max_skew_seconds: int = 300,
) -> None:
    try:
        parsed = int(timestamp)
    except ValueError as error:
        raise InvalidSignature("invalid callback timestamp") from error
    current = int(time.time()) if now is None else now
    if abs(current - parsed) > max_skew_seconds:
        raise InvalidSignature("expired callback")
    expected = hmac.new(
        secret.encode(), timestamp.encode() + b"." + payload, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise InvalidSignature("invalid callback signature")

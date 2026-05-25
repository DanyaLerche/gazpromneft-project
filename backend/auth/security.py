import base64
import hashlib
import hmac
import json
import os
from datetime import UTC, datetime, timedelta
from uuid import UUID

from config import settings


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(raw: str) -> bytes:
    padding = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(raw + padding)


def hash_password(password: str) -> str:
    iterations = settings.AUTH_PBKDF2_ITERATIONS
    salt = os.urandom(16)
    pwd_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return (
        f"pbkdf2_sha256${iterations}$"
        f"{_b64url_encode(salt)}${_b64url_encode(pwd_hash)}"
    )


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algo, iterations_s, salt_s, hash_s = password_hash.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        iterations = int(iterations_s)
        salt = _b64url_decode(salt_s)
        expected_hash = _b64url_decode(hash_s)
    except Exception:
        return False

    actual_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return hmac.compare_digest(actual_hash, expected_hash)


def _sign_jwt(payload: dict, secret: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    header_part = _b64url_encode(
        json.dumps(header, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    )
    payload_part = _b64url_encode(
        json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    )
    signing_input = f"{header_part}.{payload_part}".encode("ascii")
    signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{header_part}.{payload_part}.{_b64url_encode(signature)}"


def _decode_jwt(token: str, secret: str) -> dict | None:
    try:
        header_part, payload_part, signature_part = token.split(".", 2)
        signing_input = f"{header_part}.{payload_part}".encode("ascii")
        expected_sig = hmac.new(
            secret.encode("utf-8"),
            signing_input,
            hashlib.sha256,
        ).digest()
        actual_sig = _b64url_decode(signature_part)
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None
        payload_raw = _b64url_decode(payload_part)
        payload = json.loads(payload_raw.decode("utf-8"))
        if not isinstance(payload, dict):
            return None
        return payload
    except Exception:
        return None


def create_access_token(user_id: UUID) -> str:
    now = datetime.now(UTC)
    exp = now + timedelta(minutes=settings.JWT_ACCESS_TTL_MINUTES)
    payload = {
        "sub": str(user_id),
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return _sign_jwt(payload, settings.JWT_SECRET_KEY)


def create_refresh_token(user_id: UUID) -> str:
    now = datetime.now(UTC)
    exp = now + timedelta(days=settings.JWT_REFRESH_TTL_DAYS)
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "nonce": _b64url_encode(os.urandom(16)),
    }
    return _sign_jwt(payload, settings.JWT_REFRESH_SECRET_KEY)


def verify_access_token(token: str) -> dict | None:
    payload = _decode_jwt(token, settings.JWT_SECRET_KEY)
    if not payload:
        return None
    if payload.get("type") != "access":
        return None
    exp = payload.get("exp")
    if not isinstance(exp, int):
        return None
    if exp <= int(datetime.now(UTC).timestamp()):
        return None
    return payload


def verify_refresh_token(token: str) -> dict | None:
    payload = _decode_jwt(token, settings.JWT_REFRESH_SECRET_KEY)
    if not payload:
        return None
    if payload.get("type") != "refresh":
        return None
    exp = payload.get("exp")
    if not isinstance(exp, int):
        return None
    if exp <= int(datetime.now(UTC).timestamp()):
        return None
    return payload


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

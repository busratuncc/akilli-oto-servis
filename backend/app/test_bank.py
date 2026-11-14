import hashlib
import hmac
import secrets
from datetime import datetime, timezone


def create_token() -> tuple[str, str]:
    token = secrets.token_urlsafe(48)
    return token, token_hash(token)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def token_matches(token: str, expected_hash: str) -> bool:
    return hmac.compare_digest(token_hash(token), expected_hash)


def is_expired(expires_at: datetime) -> bool:
    normalized = expires_at if expires_at.tzinfo else expires_at.replace(tzinfo=timezone.utc)
    return normalized <= datetime.now(timezone.utc)

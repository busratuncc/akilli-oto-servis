import hashlib
import hmac
import secrets
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo


def new_approval_token() -> str:
    return secrets.token_urlsafe(32)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def token_matches(token: str, expected_hash: str | None) -> bool:
    if not expected_hash:
        return False
    return hmac.compare_digest(token_hash(token), expected_hash)


def end_of_valid_day(valid_until: date) -> datetime:
    local_end = datetime.combine(
        valid_until,
        time(23, 59, 59),
        tzinfo=ZoneInfo("Europe/Istanbul"),
    )
    return local_end.astimezone(timezone.utc)


def is_expired(expires_at: datetime | None, now: datetime | None = None) -> bool:
    if expires_at is None:
        return True
    reference = now or datetime.now(timezone.utc)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)
    return expires_at <= reference

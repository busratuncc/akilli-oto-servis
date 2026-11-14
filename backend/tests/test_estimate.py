from datetime import date, datetime, timezone

from app import estimate


def test_approval_tokens_are_random_and_hash_verifiable():
    first = estimate.new_approval_token()
    second = estimate.new_approval_token()
    digest = estimate.token_hash(first)

    assert first != second
    assert first not in digest
    assert len(digest) == 64
    assert estimate.token_matches(first, digest)
    assert not estimate.token_matches(second, digest)
    assert not estimate.token_matches(first, None)


def test_valid_day_ends_in_istanbul_then_normalizes_to_utc():
    expires_at = estimate.end_of_valid_day(date(2026, 11, 14))

    assert expires_at == datetime(2026, 11, 14, 20, 59, 59, tzinfo=timezone.utc)


def test_expiry_uses_aware_reference_time():
    expires_at = datetime(2026, 11, 14, 20, 59, 59, tzinfo=timezone.utc)

    assert not estimate.is_expired(
        expires_at,
        datetime(2026, 11, 14, 20, 59, 58, tzinfo=timezone.utc),
    )
    assert estimate.is_expired(
        expires_at,
        datetime(2026, 11, 14, 20, 59, 59, tzinfo=timezone.utc),
    )

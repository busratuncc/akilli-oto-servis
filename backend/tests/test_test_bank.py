from datetime import datetime, timedelta, timezone

from app import test_bank


def test_challenge_token_is_random_and_only_hash_matches():
    token, hashed = test_bank.create_token()
    other_token, _ = test_bank.create_token()

    assert token != other_token
    assert token != hashed
    assert len(hashed) == 64
    assert test_bank.token_matches(token, hashed)
    assert not test_bank.token_matches(other_token, hashed)


def test_challenge_expiry_uses_utc_time():
    assert test_bank.is_expired(datetime.now(timezone.utc) - timedelta(seconds=1))
    assert not test_bank.is_expired(datetime.now(timezone.utc) + timedelta(minutes=1))

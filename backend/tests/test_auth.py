import uuid

import pytest
from pydantic import ValidationError

from app import auth
from app.schemas import OTPVerify, RegistrationRequest


def test_email_normalization_and_otp_hashing() -> None:
    challenge_id = uuid.uuid4()

    assert auth.normalize_email("  USTA@Example.COM ") == "usta@example.com"
    assert auth._otp_hash(challenge_id, "USTA@example.com", "123456") == auth._otp_hash(
        challenge_id, "usta@example.com", "123456"
    )
    assert auth._otp_hash(challenge_id, "usta@example.com", "123456") != auth._otp_hash(
        challenge_id, "usta@example.com", "654321"
    )


def test_session_token_is_hashed_before_storage() -> None:
    token = "secret-session-token"

    assert auth._token_hash(token) != token
    assert auth._token_hash(token) == auth._token_hash(token)


def test_otp_schema_requires_exactly_six_digits() -> None:
    assert OTPVerify(email="usta@example.com", code="001234").code == "001234"

    with pytest.raises(ValidationError):
        OTPVerify(email="usta@example.com", code="12345")
    with pytest.raises(ValidationError):
        OTPVerify(email="usta@example.com", code="12A456")


def test_registration_requires_numeric_phone_and_mandatory_consents() -> None:
    valid = {
        "full_name": "Büşra Tunç",
        "email": "busra@example.com",
        "phone_country_code": "+90",
        "phone_number": "5551112233",
        "privacy_accepted": True,
        "terms_accepted": True,
    }

    assert RegistrationRequest(**valid).phone_number == "5551112233"

    with pytest.raises(ValidationError):
        RegistrationRequest(**{**valid, "phone_number": "555-ABC"})
    with pytest.raises(ValidationError):
        RegistrationRequest(**{**valid, "privacy_accepted": False})

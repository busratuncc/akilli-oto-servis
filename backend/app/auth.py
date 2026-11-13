import hashlib
import hmac
import math
import secrets
import smtplib
import uuid
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app import models, schemas
from app.config import settings


class OTPError(RuntimeError):
    pass


class OTPRateLimitError(OTPError):
    def __init__(self, retry_after: int):
        super().__init__("Yeni kod istemeden önce bekleyin")
        self.retry_after = retry_after


class OTPInvalidError(OTPError):
    pass


class UserNotRegisteredError(OTPError):
    pass


class RegistrationConflictError(OTPError):
    pass


def normalize_email(email: str) -> str:
    return email.strip().casefold()


def _otp_hash(challenge_id: uuid.UUID, email: str, code: str) -> str:
    message = f"{challenge_id}:{normalize_email(email)}:{code}".encode()
    return hmac.new(settings.auth_secret.encode(), message, hashlib.sha256).hexdigest()


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def add_audit_event(
    db: Session,
    user_id: uuid.UUID,
    event_type: str,
    *,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    event_data: dict | None = None,
) -> None:
    db.add(
        models.AuditEvent(
            user_id=user_id,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            event_data=event_data or {},
        )
    )


def is_registered(user: models.User | None) -> bool:
    return bool(
        user
        and user.full_name
        and user.phone_country_code
        and user.phone_number
        and user.privacy_accepted_at
        and user.terms_accepted_at
    )


def register_user(db: Session, payload: schemas.RegistrationRequest) -> models.User:
    email = normalize_email(str(payload.email))
    existing_user = db.scalar(select(models.User).where(models.User.email == email))
    if is_registered(existing_user):
        raise RegistrationConflictError("Bu e-posta adresi zaten kayıtlı")
    phone_owner_id = db.scalar(
        select(models.User.id).where(
            models.User.phone_country_code == payload.phone_country_code,
            models.User.phone_number == payload.phone_number,
        )
    )
    if phone_owner_id and (existing_user is None or phone_owner_id != existing_user.id):
        raise RegistrationConflictError("Bu telefon numarası zaten kayıtlı")

    accepted_at = datetime.now(timezone.utc)
    user = existing_user or models.User(email=email)
    user.full_name = payload.full_name
    user.workshop_name = payload.workshop_name
    user.phone_country_code = payload.phone_country_code
    user.phone_number = payload.phone_number
    user.preferred_language = payload.preferred_language
    user.privacy_accepted_at = accepted_at
    user.terms_accepted_at = accepted_at
    user.consent_version = "2026-11-v1"
    user.marketing_consent = payload.marketing_consent
    if existing_user is None:
        db.add(user)
    try:
        db.flush()
        add_audit_event(
            db,
            user.id,
            "account.registered",
            entity_type="user",
            entity_id=user.id,
            event_data={"consent_version": user.consent_version},
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise RegistrationConflictError("E-posta veya telefon numarası zaten kayıtlı") from exc
    db.refresh(user)
    return user


def _send_otp_email(email: str, code: str, language: str) -> None:
    message = EmailMessage()
    message["From"] = settings.mail_from
    message["To"] = email
    if language == "en":
        message["Subject"] = "Your Smart Auto Service login code"
        plain = (
            f"Your one-time login code is: {code}\n\n"
            f"This code expires in {settings.otp_expiry_minutes} minutes. "
            "If you did not request it, you can ignore this email."
        )
        heading = "Your login code"
        expiry = f"Valid for {settings.otp_expiry_minutes} minutes"
    else:
        message["Subject"] = "Akıllı Oto Servis giriş kodunuz"
        plain = (
            f"Tek kullanımlık giriş kodunuz: {code}\n\n"
            f"Bu kod {settings.otp_expiry_minutes} dakika geçerlidir. "
            "Bu isteği siz yapmadıysanız e-postayı yok sayabilirsiniz."
        )
        heading = "Giriş kodunuz"
        expiry = f"{settings.otp_expiry_minutes} dakika geçerlidir"

    message.set_content(plain)
    message.add_alternative(
        f"""
        <html><body style="font-family:Arial,sans-serif;background:#f4f6f8;padding:28px">
          <div style="max-width:460px;margin:auto;background:#fff;border-radius:16px;padding:28px">
            <p style="color:#ee6c2f;font-weight:700">Akıllı Oto Servis</p>
            <h2 style="color:#142231">{heading}</h2>
            <div style="font-size:32px;letter-spacing:10px;font-weight:800;padding:18px 0">{code}</div>
            <p style="color:#6c7887">{expiry}</p>
          </div>
        </body></html>
        """,
        subtype="html",
    )

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
        if settings.smtp_starttls:
            smtp.starttls()
        if settings.smtp_username and settings.smtp_password:
            smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(message)


def request_otp(db: Session, email: str, language: str) -> None:
    normalized = normalize_email(email)
    user = db.scalar(select(models.User).where(models.User.email == normalized))
    if not is_registered(user):
        raise UserNotRegisteredError("Önce kayıt olmalısınız")
    assert user is not None

    if settings.local_auth_enabled:
        return

    now = datetime.now(timezone.utc)
    latest = db.scalar(
        select(models.OTPChallenge)
        .where(models.OTPChallenge.email == normalized)
        .order_by(models.OTPChallenge.created_at.desc())
        .limit(1)
    )
    if latest and latest.created_at:
        elapsed = (now - latest.created_at).total_seconds()
        if elapsed < settings.otp_request_interval_seconds:
            raise OTPRateLimitError(
                math.ceil(settings.otp_request_interval_seconds - elapsed)
            )

    code = f"{secrets.randbelow(1_000_000):06d}"
    challenge_id = uuid.uuid4()
    challenge = models.OTPChallenge(
        id=challenge_id,
        email=normalized,
        code_hash=_otp_hash(challenge_id, normalized, code),
        language=language,
        expires_at=now + timedelta(minutes=settings.otp_expiry_minutes),
    )
    db.add(challenge)
    db.commit()

    try:
        _send_otp_email(normalized, code, language)
    except Exception:
        db.delete(challenge)
        db.commit()
        raise


def verify_otp(db: Session, email: str, code: str, language: str) -> tuple[models.User, str]:
    normalized = normalize_email(email)
    now = datetime.now(timezone.utc)
    user = db.scalar(select(models.User).where(models.User.email == normalized))
    if not is_registered(user):
        raise UserNotRegisteredError("Önce kayıt olmalısınız")
    assert user is not None

    if settings.local_auth_enabled:
        if not hmac.compare_digest(code, settings.local_login_code):
            raise OTPInvalidError("Yerel giriş kodu geçersiz")
        return _create_session(db, user, language, now)

    challenge = db.scalar(
        select(models.OTPChallenge)
        .where(
            models.OTPChallenge.email == normalized,
            models.OTPChallenge.consumed_at.is_(None),
            models.OTPChallenge.expires_at > now,
        )
        .order_by(models.OTPChallenge.created_at.desc())
        .limit(1)
    )
    if challenge is None or challenge.attempts >= settings.otp_max_attempts:
        raise OTPInvalidError("Kod geçersiz veya süresi dolmuş")

    if not hmac.compare_digest(challenge.code_hash, _otp_hash(challenge.id, normalized, code)):
        challenge.attempts += 1
        db.commit()
        raise OTPInvalidError("Kod geçersiz veya süresi dolmuş")

    challenge.consumed_at = now
    return _create_session(db, user, language, now)


def _create_session(
    db: Session,
    user: models.User,
    language: str,
    now: datetime,
) -> tuple[models.User, str]:
    user.preferred_language = language
    user.last_login_at = now

    db.execute(
        delete(models.AuthSession).where(
            models.AuthSession.user_id == user.id,
            models.AuthSession.expires_at <= now,
        )
    )
    token = secrets.token_urlsafe(48)
    db.add(
        models.AuthSession(
            user_id=user.id,
            token_hash=_token_hash(token),
            expires_at=now + timedelta(days=settings.session_expiry_days),
        )
    )
    add_audit_event(db, user.id, "auth.login", entity_type="user", entity_id=user.id)
    db.commit()
    db.refresh(user)
    return user, token


def get_user_by_session(db: Session, token: str | None) -> models.User | None:
    if not token:
        return None
    now = datetime.now(timezone.utc)
    auth_session = db.scalar(
        select(models.AuthSession)
        .options(selectinload(models.AuthSession.user))
        .where(
            models.AuthSession.token_hash == _token_hash(token),
            models.AuthSession.expires_at > now,
        )
    )
    return auth_session.user if auth_session else None


def update_profile(
    db: Session,
    user: models.User,
    payload: schemas.UserProfileUpdate,
) -> models.User:
    phone_owner_id = db.scalar(
        select(models.User.id).where(
            models.User.phone_country_code == payload.phone_country_code,
            models.User.phone_number == payload.phone_number,
            models.User.id != user.id,
        )
    )
    if phone_owner_id:
        raise RegistrationConflictError("Bu telefon numarası başka bir hesapta kayıtlı")

    user.full_name = payload.full_name
    user.workshop_name = payload.workshop_name
    user.phone_country_code = payload.phone_country_code
    user.phone_number = payload.phone_number
    user.marketing_consent = payload.marketing_consent
    add_audit_event(db, user.id, "account.profile_updated", entity_type="user", entity_id=user.id)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise RegistrationConflictError("Telefon numarası başka bir hesapta kayıtlı") from exc
    db.refresh(user)
    return user


def delete_session(db: Session, token: str | None, user_id: uuid.UUID | None = None) -> None:
    if token:
        db.execute(
            delete(models.AuthSession).where(models.AuthSession.token_hash == _token_hash(token))
        )
        if user_id:
            add_audit_event(db, user_id, "auth.logout", entity_type="user", entity_id=user_id)
        db.commit()

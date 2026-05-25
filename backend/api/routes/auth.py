from __future__ import annotations

from datetime import UTC, datetime, timedelta
import hashlib
import hmac
import secrets
from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from backend import schemas
from backend.api.dependencies import CurrentUser, Session
from backend.auth.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
    verify_refresh_token,
)
from backend.models import (
    AuthCredential,
    AuthEvent,
    PendingRegistration,
    RefreshToken,
    User,
)
from backend.services.email_service import send_email
from config import settings

router = APIRouter(tags=["Auth"])


def _normalize_email(value: str) -> str:
    return value.strip().lower()


def _token_expiry_from_payload(payload: dict) -> datetime:
    exp = payload.get("exp")
    if not isinstance(exp, int):
        raise HTTPException(status_code=400, detail="Invalid token")
    return datetime.fromtimestamp(exp, tz=UTC)


def _generate_verification_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _hash_verification_code(email: str, code: str) -> str:
    normalized_email = _normalize_email(email)
    raw = f"{normalized_email}:{code}:{settings.AUTH_EMAIL_VERIFICATION_SECRET}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


async def _issue_tokens(session: Session, user: User) -> schemas.LoginResponse:
    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)
    refresh_payload = verify_refresh_token(refresh_token)
    if not refresh_payload:
        raise HTTPException(status_code=400, detail="Cannot issue refresh token")
    session.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(refresh_token),
            expires_at=_token_expiry_from_payload(refresh_payload),
        )
    )
    return schemas.LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=user,
    )


def _verification_email_text(code: str) -> str:
    ttl = settings.AUTH_EMAIL_VERIFICATION_TTL_MINUTES
    return (
        "Task Tracker: код подтверждения\n\n"
        f"Ваш код подтверждения: {code}\n"
        f"Код действует {ttl} минут.\n\n"
        "Если вы не запрашивали регистрацию, просто проигнорируйте это письмо."
    )


async def _send_verification_email(email: str, code: str) -> None:
    if not settings.SMTP_HOST.strip():
        raise HTTPException(
            status_code=503,
            detail="SMTP is not configured. Set SMTP_HOST/SMTP_PORT/SMTP credentials.",
        )
    try:
        await send_email(
            recipient=email,
            subject="Task Tracker: подтверждение email",
            body=_verification_email_text(code),
        )
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Unable to send verification code email. Try again later.",
        )


async def _upsert_pending_registration(
    session: Session,
    *,
    email: str,
    full_name: str,
    password_hash: str,
    code: str,
) -> None:
    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=settings.AUTH_EMAIL_VERIFICATION_TTL_MINUTES)
    code_hash = _hash_verification_code(email, code)

    record = (
        await session.execute(
            select(PendingRegistration).where(PendingRegistration.email == email)
        )
    ).scalar_one_or_none()
    if record is None:
        session.add(
            PendingRegistration(
                email=email,
                full_name=full_name,
                password_hash=password_hash,
                code_hash=code_hash,
                expires_at=expires_at,
                attempts=0,
                last_sent_at=now,
            )
        )
        return

    record.full_name = full_name
    record.password_hash = password_hash
    record.code_hash = code_hash
    record.expires_at = expires_at
    record.attempts = 0
    record.last_sent_at = now


@router.post("/auth/register", status_code=201, response_model=schemas.RegisterResponse)
async def register(
    body: schemas.RegisterRequest,
    session: Session,
):
    email = _normalize_email(body.email)
    existing = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="A user with this email already exists")

    full_name = body.full_name.strip()
    password_hash = hash_password(body.password)
    verification_code = _generate_verification_code()

    try:
        await _upsert_pending_registration(
            session,
            email=email,
            full_name=full_name,
            password_hash=password_hash,
            code=verification_code,
        )
        await _send_verification_email(email, verification_code)
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="A user with this email already exists")
    except HTTPException:
        await session.rollback()
        raise
    return schemas.RegisterResponse(email=email, verification_required=True)


@router.post("/auth/verify-email", response_model=schemas.VerifyEmailResponse)
async def verify_email(
    body: schemas.VerifyEmailRequest,
    session: Session,
):
    email = _normalize_email(body.email)
    pending = (
        await session.execute(select(PendingRegistration).where(PendingRegistration.email == email))
    ).scalar_one_or_none()
    if not pending:
        existing_user = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
        if existing_user and existing_user.is_email_verified:
            return schemas.VerifyEmailResponse(verified=True)
        raise HTTPException(status_code=400, detail="Invalid verification code")

    now = datetime.now(UTC)
    if pending.expires_at <= now:
        raise HTTPException(status_code=400, detail="Verification code has expired")

    expected_hash = _hash_verification_code(email, body.code.strip())
    if not hmac.compare_digest(pending.code_hash, expected_hash):
        pending.attempts += 1
        await session.commit()
        raise HTTPException(status_code=400, detail="Invalid verification code")

    user = User(
        email=email,
        full_name=pending.full_name,
        is_active=True,
        is_email_verified=True,
    )
    try:
        session.add(user)
        await session.flush()
        session.add(
            AuthCredential(
                user_id=user.id,
                password_hash=pending.password_hash,
            )
        )
        await session.delete(pending)
        session.add(AuthEvent(user_id=user.id, event_type="register"))
        session.add(AuthEvent(user_id=user.id, event_type="email_verified"))
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="A user with this email already exists")
    return schemas.VerifyEmailResponse(verified=True)


@router.post("/auth/resend-verification", response_model=schemas.ResendVerificationResponse)
async def resend_verification(
    body: schemas.ResendVerificationRequest,
    session: Session,
):
    email = _normalize_email(body.email)
    pending = (
        await session.execute(select(PendingRegistration).where(PendingRegistration.email == email))
    ).scalar_one_or_none()
    if not pending:
        return schemas.ResendVerificationResponse(sent=True)

    now = datetime.now(UTC)
    if (now - pending.last_sent_at).total_seconds() < settings.AUTH_EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS:
        raise HTTPException(status_code=429, detail="Resend is temporarily limited")

    verification_code = _generate_verification_code()
    await _upsert_pending_registration(
        session,
        email=pending.email,
        full_name=pending.full_name,
        password_hash=pending.password_hash,
        code=verification_code,
    )
    await _send_verification_email(pending.email, verification_code)
    await session.commit()
    return schemas.ResendVerificationResponse(sent=True)


@router.post("/auth/login", response_model=schemas.LoginResponse)
async def login(
    body: schemas.LoginRequest,
    session: Session,
):
    email = _normalize_email(body.email)
    user = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if not user:
        session.add(AuthEvent(user_id=None, event_type="login_failed"))
        await session.commit()
        raise HTTPException(status_code=400, detail="Invalid email or password")

    creds = (
        await session.execute(select(AuthCredential).where(AuthCredential.user_id == user.id))
    ).scalar_one_or_none()
    if not creds or not verify_password(body.password, creds.password_hash):
        session.add(AuthEvent(user_id=user.id, event_type="login_failed"))
        await session.commit()
        raise HTTPException(status_code=400, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User is disabled")
    if not user.is_email_verified:
        raise HTTPException(status_code=403, detail="Email is not verified")

    tokens = await _issue_tokens(session, user)
    session.add(AuthEvent(user_id=user.id, event_type="login_success"))
    await session.commit()
    return tokens


@router.post("/auth/refresh", response_model=schemas.LoginResponse)
async def refresh_token(
    body: schemas.RefreshRequest,
    session: Session,
):
    payload = verify_refresh_token(body.refresh_token)
    if not payload:
        raise HTTPException(status_code=400, detail="Invalid refresh token")

    sub = payload.get("sub")
    try:
        user_id = UUID(str(sub))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid refresh token")

    stored = (
        await session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(body.refresh_token))
        )
    ).scalar_one_or_none()
    if not stored or stored.revoked_at is not None:
        raise HTTPException(status_code=400, detail="Refresh token revoked")
    if stored.expires_at <= datetime.now(UTC):
        raise HTTPException(status_code=400, detail="Refresh token expired")
    if stored.user_id != user_id:
        raise HTTPException(status_code=400, detail="Invalid refresh token")

    user = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=400, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User is disabled")

    stored.revoked_at = datetime.now(UTC)
    tokens = await _issue_tokens(session, user)
    session.add(AuthEvent(user_id=user.id, event_type="refresh"))
    await session.commit()
    return tokens


@router.post("/auth/logout", status_code=204)
async def logout(
    session: Session,
    current_user: CurrentUser,
):
    await session.execute(
        update(RefreshToken)
        .where(
            RefreshToken.user_id == current_user.id,
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=datetime.now(UTC))
    )
    session.add(AuthEvent(user_id=current_user.id, event_type="logout"))
    await session.commit()


@router.get("/me", response_model=schemas.MeResponse)
async def me(current_user: CurrentUser):
    return {"user": current_user}


@router.patch("/me/profile", response_model=schemas.MeResponse)
async def update_my_profile(
    body: schemas.UpdateMyProfileRequest,
    session: Session,
    current_user: CurrentUser,
):
    avatar_url = (body.avatar_url or "").strip()
    current_user.avatar_url = avatar_url or None
    await session.commit()
    await session.refresh(current_user)
    return {"user": current_user}
